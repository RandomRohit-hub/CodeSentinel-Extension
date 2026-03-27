import os
import re
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Literal
from dotenv import load_dotenv
import google.generativeai as genai
from openai import OpenAI
from analyzer import analyze_code

load_dotenv()

app = FastAPI(title="Algo-Sentry 3-Layer AI Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- Models & Schema ---

class AnalyzeRequest(BaseModel):
    code: str
    language: Optional[str] = "python"
    fileName: Optional[str] = "snippet.py"

class AnalyzeResponse(BaseModel):
    concept: str
    complexity: str
    confidence: float
    is_meaningful_dsa: bool = False

class QuizRequest(BaseModel):
    code: str
    concept: str
    complexity: str
    language: Optional[str] = "python"
    recent_questions: Optional[List[str]] = None
    personality: Optional[Literal["genz", "mentor", "interview"]] = "genz"

class QuizResponse(BaseModel):
    question: str
    options: List[str]
    correct: str
    explanation: str

class ValidateRequest(BaseModel):
    user_answer: str
    correct_answer: str
    question_context: dict
    code: str
    personality: Optional[Literal["genz", "mentor", "interview"]] = "genz"

class ValidateResponse(BaseModel):
    feedback: str

# --- AI Clients ---

def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key: return None
    return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

def get_gemini_client():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key: return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-1.5-flash")

# --- Memory / Anti-Repetition logic ---
def construct_recent_context(recent: List[str]) -> str:
    if not recent: return "None"
    return "\n".join([f"- {q}" for q in recent[-10:]])

# --- Prompts ---

QUIZ_PROMPT = """You are an expert DSA mentor ({personality_tone}).
Generate a fast, dynamic, and unique Multiple Choice Question (MCQ) based strictly on this code snippet.
Concept Detected: {concept}
Time Complexity: {complexity}

Code snippet:
```
{code}
```

ANTI-REPETITION:
Do NOT ask these recent questions:
{recent_questions}

Requirements:
- The question MUST be about the time/space complexity, a potential optimization, or the conceptual mechanism of this specific code.
- Provide EXACTLY 3 or 4 options.
- 'correct' must be the exact string of the correct option (e.g. "O(n^2)").
- 'explanation' must be a short 1-2 sentence explanation of WHY it is correct.
- Return ONLY valid JSON matching this schema:
{{
  "question": "...",
  "options": ["...", "...", "..."],
  "correct": "...",
  "explanation": "..."
}}
"""

VALIDATE_PROMPT = """You are an expert DSA mentor ({personality_tone}).
The user just answered a question about their code. Evaluate their answer.

Code:
```
{code}
```

Question asked: {question}
User's Answer: {user_answer}
Correct Answer: {correct_answer}

If the user's answer matches the correct answer (even approximately), give positive reinforcement.
If the user's answer is wrong, explain concisely WHY based on the code.
Keep it strictly under 3 sentences.

Return ONLY valid JSON matching this schema:
{{
  "feedback": "..."
}}
"""

TONES = {
    "genz": "Use some Gen-Z slang and emojis (e.g. 'yo coder 👀', '🔥', 'no cap', 'let him cook', 'sus')",
    "mentor": "Use a warm, encouraging, and professional teaching tone.",
    "interview": "Be strict, concise, and professional like a FAANG interviewer."
}

# --- Layer 1: Fast Analyzer Endpoint ---

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_endpoint(req: AnalyzeRequest):
    # Runs in <10ms, no AI used.
    result = analyze_code(req.code, req.language)
    confidence = result.get("confidence", 0.0)
    concept = result.get("concept", "generic")
    
    # Meaningful DSA definitions for trigger
    meaningful = confidence >= 0.75 and concept not in ["generic", "loops"]
    
    return AnalyzeResponse(
        concept=concept,
        complexity=result.get("complexity", "O(1)"),
        confidence=confidence,
        is_meaningful_dsa=meaningful
    )

# --- Layer 2: Groq Engine (Question Gen) ---

@app.post("/generate_quiz", response_model=QuizResponse)
async def generate_quiz_endpoint(req: QuizRequest):
    client = get_groq_client()
    
    # Layer 3 Fallback to Gemini if Groq fails to init
    if not client:
        return await _generate_fallback_gemini(req)
        
    prompt = QUIZ_PROMPT.format(
        personality_tone=TONES.get(req.personality, TONES["genz"]),
        concept=req.concept,
        complexity=req.complexity,
        code=req.code[:2000],
        recent_questions=construct_recent_context(req.recent_questions)
    )
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        data = json.loads(completion.choices[0].message.content)
        return QuizResponse(**data)
    except Exception as e:
        print(f"Groq Quiz Error: {e}")
        # Layer 3 Fallback trigger
        return await _generate_fallback_gemini(req)


async def _generate_fallback_gemini(req: QuizRequest) -> QuizResponse:
    # Layer 3 Deep mode fallback
    model = get_gemini_client()
    if not model:
        raise Exception("Both Groq and Gemini failed (API Keys invalid).")
    prompt = QUIZ_PROMPT.format(
        personality_tone=TONES.get(req.personality, TONES["genz"]),
        concept=req.concept,
        complexity=req.complexity,
        code=req.code[:2000],
        recent_questions=construct_recent_context(req.recent_questions)
    )
    res = model.generate_content(prompt)
    try:
        data = json.loads(re.search(r'\{.*\}', res.text, re.DOTALL).group())
        return QuizResponse(**data)
    except Exception:
        return QuizResponse(
            question="What is the time complexity here?",
            options=["O(1)", "O(n)", "O(n^2)"],
            correct="O(n)",
            explanation="Fallback question generated."
        )

# --- Validation Engine ---

@app.post("/validate", response_model=ValidateResponse)
async def validate_endpoint(req: ValidateRequest):
    client = get_groq_client()
    prompt = VALIDATE_PROMPT.format(
        personality_tone=TONES.get(req.personality, TONES["genz"]),
        code=req.code[:2000],
        question=req.question_context.get("question", ""),
        user_answer=req.user_answer,
        correct_answer=req.correct_answer
    )
    
    if client:
        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Extremely fast inference for validation
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            data = json.loads(completion.choices[0].message.content)
            return ValidateResponse(feedback=data.get("feedback", "Nice answer!"))
        except Exception as e:
            print(f"Groq Validation error: {e}")
            
    # Fallback response
    if req.user_answer.strip().lower() == req.correct_answer.strip().lower():
        return ValidateResponse(feedback="Correct! ✅")
    return ValidateResponse(feedback=f"Incorrect ❌. The right answer was: {req.correct_answer}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

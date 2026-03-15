"""
Algo-Sentry backend: code analysis + MCQ quizzes (Google Gemini, OpenAI, or fallback bank).

  cd backend_stub
  pip install -r requirements.txt
  # Use Google Gemini (recommended):
  set GOOGLE_API_KEY=your-gemini-api-key
  # Or use OpenAI:
  set OPENAI_API_KEY=sk-...
  uvicorn main:app --reload --port 8000

  Optional: LLM_PROVIDER=google|openai to force one; otherwise Google is used if GOOGLE_API_KEY is set.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Literal, List
import random
import os
import json
import re

app = FastAPI(title="Algo-Sentry Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class AnalyzeRequest(BaseModel):
    code: str
    language: Optional[str] = None
    fileName: Optional[str] = None
    difficulty: Optional[Literal["beginner", "intermediate", "advanced"]] = "beginner"
    cursorLine: Optional[int] = None
    codeSnippet: Optional[str] = None  # Focused region (e.g. function at cursor) for better context
    recent_questions: Optional[List[str]] = None  # Avoid repeating these


class AnalyzeResponse(BaseModel):
    pattern: Optional[str] = None
    concept: Optional[str] = None
    complexity: Optional[str] = None
    spaceComplexity: Optional[str] = None
    suggestion: Optional[str] = None
    question: Optional[str] = None
    tip: Optional[str] = None
    options: Optional[List[str]] = None
    correct_index: Optional[int] = None
    explanation: Optional[str] = None  # Shown when user picks wrong answer


# MCQ bank: each entry has question, 4 options, and correct_index (0-3)
MCQ_BANK: dict[str, list[dict]] = {
    "nested_loop": [
        {
            "question": "What is the time complexity of this nested loop in terms of n?",
            "options": ["O(n)", "O(n²)", "O(n log n)", "O(2^n)"],
            "correct_index": 1,
        },
        {
            "question": "If the outer loop runs n times and the inner loop n times, total iterations are:",
            "options": ["n", "2n", "n²", "n log n"],
            "correct_index": 2,
        },
        {
            "question": "Which data structure could help avoid the inner loop and reduce complexity?",
            "options": ["Another array", "Hash map or set", "A single variable", "Linked list"],
            "correct_index": 1,
        },
    ],
    "recursion": [
        {
            "question": "What is the base case in this recursive function?",
            "options": ["The first line", "The condition that stops recursion", "The return type", "The recursive call"],
            "correct_index": 1,
        },
        {
            "question": "Roughly how many recursive calls for input size n?",
            "options": ["O(1)", "O(n)", "O(n²)", "Depends on recurrence"],
            "correct_index": 3,
        },
        {
            "question": "Which technique can reduce repeated work in this recursion?",
            "options": ["More loops", "Memoization or dynamic programming", "Larger stack", "Faster CPU"],
            "correct_index": 1,
        },
    ],
    "stack": [
        {
            "question": "What is the time complexity of push and pop on this stack?",
            "options": ["O(n)", "O(log n)", "O(1)", "O(n²)"],
            "correct_index": 2,
        },
        {
            "question": "This structure behaves as:",
            "options": ["FIFO (queue)", "LIFO (stack)", "Priority order", "Random order"],
            "correct_index": 1,
        },
        {
            "question": "When would a deque be better than a list for this stack?",
            "options": ["Never", "When you need O(1) pop from the left", "When you need sorting", "When you need indexing"],
            "correct_index": 1,
        },
    ],
    "hash_map": [
        {
            "question": "Average time complexity of lookup in this hash map?",
            "options": ["O(n)", "O(1)", "O(log n)", "O(n²)"],
            "correct_index": 1,
        },
        {
            "question": "When can hash map operations degrade to O(n)?",
            "options": ["Always", "With many collisions", "With small keys", "With integer keys"],
            "correct_index": 1,
        },
    ],
    "sliding_window": [
        {
            "question": "Why is this sliding window approach O(n)?",
            "options": ["It uses one loop", "Each element is processed a constant number of times", "It has no recursion", "It uses an array"],
            "correct_index": 1,
        },
    ],
    "binary_search": [
        {
            "question": "What is the time complexity of binary search?",
            "options": ["O(n)", "O(log n)", "O(n²)", "O(1)"],
            "correct_index": 1,
        },
        {
            "question": "Why must the input be sorted for binary search?",
            "options": ["To avoid errors", "So we can discard half the search space each step", "To use less memory", "It does not need to be sorted"],
            "correct_index": 1,
        },
    ],
    "dynamic_programming": [
        {
            "question": "What is the main idea of dynamic programming used here?",
            "options": ["Brute force", "Store and reuse subproblem results", "Use more loops", "Sort the input"],
            "correct_index": 1,
        },
        {
            "question": "What is the typical time complexity when using memoization/tabulation?",
            "options": ["O(2^n)", "O(n) or O(n²) depending on subproblems", "O(log n)", "O(1)"],
            "correct_index": 1,
        },
    ],
    "sorting": [
        {
            "question": "What is the time complexity of this sorting approach?",
            "options": ["O(n)", "O(n log n) for comparison sorts", "O(n²)", "Depends on the algorithm used"],
            "correct_index": 3,
        },
        {
            "question": "When is an in-place sort preferred?",
            "options": ["Always", "When extra space is limited", "Never", "Only for small arrays"],
            "correct_index": 1,
        },
    ],
    "graph_traversal": [
        {
            "question": "Which traversal is used here (BFS vs DFS)?",
            "options": ["BFS uses a queue; DFS uses a stack/recursion", "Both use a stack", "Both use a queue", "Neither"],
            "correct_index": 0,
        },
        {
            "question": "What is the time complexity of traversing a graph with V vertices and E edges?",
            "options": ["O(V)", "O(V + E)", "O(E)", "O(V²)"],
            "correct_index": 1,
        },
    ],
    "loop": [
        {
            "question": "What is the time complexity of this loop in terms of n?",
            "options": ["O(1)", "O(n)", "O(n²)", "O(log n)"],
            "correct_index": 1,
        },
        {
            "question": "How many times does the loop body execute for an input of size n?",
            "options": ["Once", "n times", "n² times", "Depends on the loop condition"],
            "correct_index": 3,
        },
    ],
    "array": [
        {
            "question": "What is the time complexity of indexing into this array?",
            "options": ["O(n)", "O(1)", "O(log n)", "O(n²)"],
            "correct_index": 1,
        },
        {
            "question": "When would you prefer an array over a hash map?",
            "options": ["When you need O(1) lookup by key", "When indices are contiguous and you need order", "When you need to remove elements often", "When keys are strings"],
            "correct_index": 1,
        },
    ],
    "generic": [
        {
            "question": "What is the overall time complexity of this code in terms of n?",
            "options": ["O(1)", "O(n)", "O(n²)", "Depends on loop structure and data operations"],
            "correct_index": 3,
        },
        {
            "question": "If n doubles, how does the runtime typically change?",
            "options": ["Stays same", "Doubles (if O(n))", "Quadruples (if O(n²))", "B or C depending on complexity"],
            "correct_index": 3,
        },
    ],
}


def pick_mcq(concept: str, recent_questions: Optional[List[str]] = None) -> dict:
    bank = MCQ_BANK.get(concept, MCQ_BANK["generic"])
    recent_set = {q.strip().lower() for q in (recent_questions or []) if q and isinstance(q, str)}
    candidates = [m for m in bank if (m.get("question") or "").strip().lower() not in recent_set]
    if not candidates:
        candidates = bank
    return random.choice(candidates).copy()


def pick_question(concept: str, difficulty: str) -> str:
    """
    Small hand-written question bank.
    We randomly sample per request so the same code does not always get the same question.
    """
    difficulty = difficulty or "beginner"
    bank = {
        "nested_loop": {
            "beginner": [
                "What is the time complexity of this nested loop in terms of n?",
                "If the outer loop runs n times and the inner loop runs n times, how many total iterations do you get?",
            ],
            "intermediate": [
                "Could you reduce this nested loop using a hash map or set? What would the new complexity be?",
                "Is there any repeated work inside these loops that you could precompute?",
            ],
            "advanced": [
                "If the inner loop does an early break for some cases, how does that affect the average vs worst-case complexity?",
                "Can you rewrite this nested loop as a single pass with a better data structure?",
            ],
        },
        "recursion": {
            "beginner": [
                "What is the base case for this recursive function?",
                "Roughly how many times will this function call itself for input size n?",
            ],
            "intermediate": [
                "Can you write the recurrence relation for this recursive function?",
                "Could this recursion overflow the call stack for large n? How would you avoid that?",
            ],
            "advanced": [
                "Can you convert this recursion into an iterative solution with the same complexity?",
                "Where could memoization or tabulation help in this recursive logic?",
            ],
        },
        "stack": {
            "beginner": [
                "What are the time complexities of push and pop on this stack?",
                "Is this structure behaving like LIFO or FIFO?",
            ],
            "intermediate": [
                "How would you implement an undo feature using this stack?",
                "What could go wrong if you forget to handle an empty stack before popping?",
            ],
            "advanced": [
                "Could you use two stacks here to implement a queue? What would the amortized complexity be?",
            ],
        },
        "hash_map": {
            "beginner": [
                "What is the average time complexity of lookups in this hash map?",
                "Why is a hash map a good fit for this part of the code?",
            ],
            "intermediate": [
                "When could the operations on this hash map degrade to O(n)?",
                "How would choosing a bad hash function impact performance here?",
            ],
            "advanced": [
                "Can you think of a way to use a hash map to reduce a nested loop elsewhere in this code?",
            ],
        },
        "sliding_window": {
            "beginner": [
                "How many times does each element enter and leave the sliding window?",
            ],
            "intermediate": [
                "What makes this approach O(n) even though there are nested-looking operations?",
            ],
            "advanced": [
                "Could you adapt this sliding window to also track the maximum in each window efficiently?",
            ],
        },
        "generic": {
            "beginner": [
                "What is the overall time complexity of this code in terms of n?",
                "Where is most of the work happening in this snippet?",
            ],
            "intermediate": [
                "If n doubles, roughly how does the runtime change?",
                "Is there any part of this code that could be turned from O(n²) to O(n log n) or O(n)?",
            ],
            "advanced": [
                "What is the tightest Big-O bound you can give for this snippet, and why?",
            ],
        },
    }
    concept_key = concept if concept in bank else "generic"
    questions_for_level = bank[concept_key].get(difficulty, bank[concept_key]["beginner"])
    return random.choice(questions_for_level)


def detect_patterns(code: str, difficulty: str, recent_questions: Optional[List[str]] = None) -> AnalyzeResponse:
    """
    Lightweight heuristic detector for common DSA patterns. Returns MCQ with variety (avoids recent_questions).
    """
    code_lower = code.lower()

    has_for = "for " in code
    has_while = "while " in code
    loop_count = code.count("for ") + code.count("while ")
    has_recursion = False

    if "def " in code_lower:
        for line in code_lower.splitlines():
            line = line.strip()
            if line.startswith("def ") and "(" in line:
                name = line[4 : line.index("(")].strip()
                if name and f"{name}(" in code_lower.split(line, 1)[-1]:
                    has_recursion = True
                    break

    uses_stack = any(w in code_lower for w in ["stack", "push", "pop"])
    uses_dict = any(w in code_lower for w in ["dict", "{}", "hashmap", "defaultdict"])
    uses_window = "sliding window" in code_lower or ("left" in code_lower and "right" in code_lower and ("while" in code_lower or "for" in code_lower))

    # Binary search: mid, low/high, halving
    uses_binary_search = (
        ("mid" in code_lower or "middle" in code_lower)
        and ("low" in code_lower or "high" in code_lower or "left" in code_lower or "right" in code_lower)
        and ("// 2" in code or "/ 2" in code_lower or ">> 1" in code or "binary" in code_lower)
    )
    # DP: memo, cache, dp array, recurrence
    uses_dp = any(w in code_lower for w in ["memo", "cache", "dp[", "dp ", "tabulation", "memoization", "recurrence"])
    # Sorting
    uses_sorting = any(w in code_lower for w in ["sort(", ".sort(", "sorted(", "quicksort", "mergesort", "heapsort"])
    # Graph: BFS, DFS, adjacency, graph, vertex, edge
    uses_graph = any(w in code_lower for w in ["bfs", "dfs", "adjacency", "graph", "vertex", "vertices", "edge", "neighbor"])

    def _response(concept_key: str, pattern: str, concept: str, complexity: str, space: Optional[str], suggestion: str, tip: str) -> AnalyzeResponse:
        mcq = pick_mcq(concept_key, recent_questions)
        return AnalyzeResponse(
            pattern=pattern,
            concept=concept,
            complexity=complexity,
            spaceComplexity=space,
            suggestion=suggestion,
            question=mcq["question"],
            options=mcq["options"],
            correct_index=mcq["correct_index"],
            tip=tip,
        )

    # 1) Nested loops
    if loop_count >= 2 and (has_for or has_while):
        return _response(
            "nested_loop",
            "Nested loop",
            "Time complexity",
            "O(n²) (likely)",
            "O(1)",
            "See if you can remove the inner loop using a hash map, set, or prefix computation.",
            "Nested loops often hint at O(n²) or worse. Ask yourself if you really need to compare every pair.",
        )

    # 2) Recursion
    if has_recursion:
        return _response(
            "recursion",
            "Recursive function",
            "Recursion",
            "Depends on recurrence.",
            None,
            "Identify the base case and how the input size shrinks on each call.",
            "Try to write the recurrence T(n) and then solve or approximate it.",
        )

    # 3) Stack usage
    if uses_stack:
        return _response(
            "stack",
            "Stack",
            "Stack",
            "push/pop typically O(1)",
            None,
            "Check that you never pop from an empty stack and that push/pop are balanced.",
            "Stacks are great for DFS, undo operations, and matching brackets.",
        )

    # 4) Hash map usage
    if uses_dict:
        return _response(
            "hash_map",
            "Hash map",
            "Hash map",
            "Average O(1) lookup/insert",
            None,
            "Think about keys: are they unique, and do you ever overwrite values accidentally?",
            "Hash maps are perfect for frequency counting, memoization, and quick membership tests.",
        )

    # 5) Sliding window style
    if uses_window:
        return _response(
            "sliding_window",
            "Sliding window",
            "Sliding window",
            "Usually O(n) if each index moves at most once.",
            None,
            "Verify that both pointers only move forward and each element is processed a constant number of times.",
            "Sliding window shines on subarray / substring problems with contiguous ranges.",
        )

    # 6) Binary search
    if uses_binary_search:
        return _response(
            "binary_search",
            "Binary search",
            "Binary search",
            "O(log n)",
            "O(1) iterative / O(log n) stack for recursive",
            "Ensure boundaries (low/high) are updated correctly to avoid infinite loop.",
            "Binary search requires sorted input so we can discard half the space each step.",
        )

    # 7) Dynamic programming
    if uses_dp:
        return _response(
            "dynamic_programming",
            "Dynamic programming",
            "DP",
            "Typically O(n) or O(n²) with memoization/tabulation",
            "O(n) or O(n²) for table",
            "Identify the recurrence and base cases; avoid recomputing subproblems.",
            "DP optimizes by storing solutions to subproblems.",
        )

    # 8) Sorting
    if uses_sorting:
        return _response(
            "sorting",
            "Sorting",
            "Sorting",
            "O(n log n) for comparison-based sorts",
            "O(1) in-place or O(n) auxiliary",
            "Choose sort by stability and space requirements.",
            "Comparison sorts are lower-bounded by O(n log n).",
        )

    # 9) Graph traversal
    if uses_graph:
        return _response(
            "graph_traversal",
            "Graph traversal",
            "BFS/DFS",
            "O(V + E)",
            "O(V) for visited/queue/stack",
            "Use BFS for shortest path in unweighted graph; DFS for cycles or connectivity.",
            "Graph traversal visits each vertex and edge a constant number of times.",
        )

    # 10) Single loop
    if loop_count == 1 and (has_for or has_while):
        return _response(
            "loop",
            "Loop",
            "Time complexity",
            "O(n) (typical for one loop)",
            "O(1)",
            "Consider what happens when n grows; watch for early break or continue.",
            "A single loop often gives O(n); nested loops give O(n²) or worse.",
        )

    # 11) Array / list usage (indexing, iteration)
    uses_array = any(w in code_lower for w in ["[i]", "[0]", "len(", "append", "array", "list", "arr["])
    if uses_array:
        return _response(
            "array",
            "Array / list",
            "Arrays",
            "O(1) index / O(n) scan",
            "O(n) for storage",
            "Think about random access vs iteration; when to use prefix sums.",
            "Arrays give O(1) access by index; use when order matters.",
        )

    # 12) Generic fall-back
    return _response(
        "generic",
        "Code snippet",
        "Time complexity",
        "Depends on loop structure.",
        None,
        "Scan your loops and data structure operations and annotate each with its Big-O cost.",
        "Even if the logic works, always ask: what is the time and space complexity?",
    )


def _parse_mcq_response(text: str) -> Optional[dict]:
    """Extract and validate MCQ JSON from LLM response (handles markdown and extra text)."""
    raw = (text or "").strip()
    # Try code block first
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
    if m:
        raw = m.group(1).strip()
    # If no code block, try to find a JSON object (first { to last })
    if not raw.startswith("{"):
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            raw = raw[start : end + 1]
    try:
        data = json.loads(raw)
        q = data.get("question") or ""
        opts = data.get("options")
        idx = data.get("correct_index")
        if not q or not isinstance(opts, list) or len(opts) != 4 or idx not in (0, 1, 2, 3):
            return None
        out = {"question": q, "options": [str(o) for o in opts], "correct_index": int(idx)}
        if data.get("explanation"):
            out["explanation"] = str(data["explanation"]).strip()
        return out
    except Exception:
        return None


# Smarter prompt: analyze code, then generate a varied, non-repeated MCQ.
MCQ_PROMPT_TEMPLATE = """You are an expert DSA interviewer and educator. Generate ONE multiple-choice question that tests understanding of THIS specific code. The user will see many questions over time—each must be DIFFERENT in topic and phrasing.

## Code (language: {language}){cursor_hint}
```
{code}
```

## Concepts to detect and ask about (use what fits THIS code)
Loops, nested loops, recursion, hash maps/dictionaries, arrays, binary search, sliding window, dynamic programming, sorting, graph traversal (BFS/DFS). Also: time/space complexity, base cases, edge cases, optimization.

## Question variety (pick ONE style per question; rotate across requests)
- **Concept**: e.g. "What is the role of the base case in this recursion?" or "Why is a hash map useful here?"
- **Complexity**: e.g. "What is the time complexity of this loop?" or "What is the space complexity?"
- **Optimization**: e.g. "How could you reduce the time complexity of this code?" or "What data structure would avoid the inner loop?"
- **Edge case**: e.g. "What happens if the input array is empty?" or "When could this recursion overflow the stack?"
- **Quiz-style MCQ**: same as above but with 4 clear options (one correct, three plausible wrong answers).

## Rules
1. Question must be specific to THIS code (reference "this loop", "the base case here", "this variable", etc.).
2. Do NOT repeat any of these (user already saw them): {recent_questions}
3. Vary phrasing and topic each time. Wrong options must be plausible.
4. Output ONLY valid JSON, no markdown. Keys: "question", "options" (array of exactly 4 strings), "correct_index" (0-3), "explanation" (one sentence for when the user is wrong).

Difficulty: **{difficulty}**.

Example:
{{"question": "What is the time complexity of the nested loops in this code?", "options": ["O(n)", "O(n²)", "O(n log n)", "O(1)"], "correct_index": 1, "explanation": "The outer and inner loop each run up to n times, so total iterations are O(n²)."}}
"""


def _build_mcq_prompt(
    code: str,
    language: str,
    difficulty: str,
    recent_questions: Optional[List[str]] = None,
    cursor_line: Optional[int] = None,
) -> str:
    """Build prompt for LLM; use code as-is (caller may pass codeSnippet)."""
    recent = (recent_questions or [])[:8]
    recent_str = ", ".join(f'"{q[:60]}..."' if len(q) > 60 else f'"{q}"' for q in recent) if recent else "(none)"
    cursor_hint = f" (focus around line {cursor_line})" if cursor_line else ""
    return MCQ_PROMPT_TEMPLATE.format(
        language=language or "unknown",
        code=code[:4500],
        difficulty=difficulty or "beginner",
        recent_questions=recent_str,
        cursor_hint=cursor_hint,
    )


def get_mcq_from_gemini(
    code: str,
    language: str,
    difficulty: str,
    recent_questions: Optional[List[str]] = None,
    cursor_line: Optional[int] = None,
) -> Optional[dict]:
    """
    Call Google Gemini API to generate one MCQ from the code.
    """
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key or not api_key.strip():
        return None

    prompt = _build_mcq_prompt(code, language, difficulty, recent_questions, cursor_line)

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key.strip())
        # Use a stronger model for better reasoning (1.5-pro); override with GEMINI_MODEL if needed
        model_name = os.environ.get("GEMINI_MODEL", "gemini-1.5-pro")
        model = genai.GenerativeModel(model_name)
        resp = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=800,
                top_p=0.95,
            ),
        )
        text = (resp.text or "").strip()
        return _parse_mcq_response(text)
    except Exception:
        return None


def get_mcq_from_openai(
    code: str,
    language: str,
    difficulty: str,
    recent_questions: Optional[List[str]] = None,
    cursor_line: Optional[int] = None,
) -> Optional[dict]:
    """
    Call OpenAI-compatible API to generate one MCQ from the code.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        return None

    prompt = _build_mcq_prompt(code, language, difficulty, recent_questions, cursor_line)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        base_url = os.environ.get("OPENAI_BASE_URL")
        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url.rstrip("/"))
        resp = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=500,
        )
        text = (resp.choices[0].message.content or "").strip()
        return _parse_mcq_response(text)
    except Exception:
        return None


def get_mcq_from_llm(
    code: str,
    language: str,
    difficulty: str,
    recent_questions: Optional[List[str]] = None,
    cursor_line: Optional[int] = None,
) -> Optional[dict]:
    """
    Try Google Gemini first, then OpenAI. Uses code (e.g. snippet) and avoids recent_questions.
    """
    kwargs = dict(code=code, language=language, difficulty=difficulty, recent_questions=recent_questions, cursor_line=cursor_line)
    provider = (os.environ.get("LLM_PROVIDER") or "").strip().lower()
    if provider == "openai":
        return get_mcq_from_openai(**kwargs)
    if provider == "google":
        return get_mcq_from_gemini(**kwargs)
    mcq = get_mcq_from_gemini(**kwargs)
    if mcq:
        return mcq
    return get_mcq_from_openai(**kwargs)


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    difficulty = req.difficulty or "beginner"
    recent = req.recent_questions or []
    # Prefer snippet for LLM (focused context); use full code for pattern detection
    code_for_llm = (req.codeSnippet or req.code).strip() or req.code
    code_for_detect = req.code

    mcq = get_mcq_from_llm(
        code_for_llm,
        req.language or "",
        difficulty,
        recent_questions=recent,
        cursor_line=req.cursorLine,
    )
    if mcq:
        fallback = detect_patterns(code_for_detect, difficulty, recent_questions=recent)
        return AnalyzeResponse(
            pattern=fallback.pattern,
            concept=fallback.concept,
            complexity=fallback.complexity,
            spaceComplexity=fallback.spaceComplexity,
            question=mcq["question"],
            options=mcq["options"],
            correct_index=mcq["correct_index"],
            explanation=mcq.get("explanation"),
            suggestion=fallback.suggestion,
            tip=fallback.tip,
        )

    return detect_patterns(code_for_detect, difficulty, recent_questions=recent)

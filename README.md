# Algo-Sentry VS Code Extension 🤖

> **Transforming the way you write and understand Data Structures & Algorithms.**

Algo-Sentry is not just a syntax checker—it is a **real-time, multi-language Socratic AI Mentor** living inside your VS Code. Instead of blindly pointing out errors or giving you the answers, it tracks your logic, recognizes your architectural decisions, and actively challenges your thinking with context-aware, open-ended questions.

---

## 💡 The Motive 

Developers often memorize syntax or copy-paste algorithm implementations without understanding the core trade-offs. The original goal of this project was to detect patterns and give quizzes, but that quickly became a repetitive, unhelpful "topic detector". 

**The new motive** is to build a genuine learning companion that forces you to understand the *Why*, *What*, and *How* of your code:
👉 **Why** did you use a HashMap instead of an Array?
👉 **What** happens to your execution time if `n` scales to 1 million?
👉 **How** efficient is the `.append()` operation you just placed inside a loop?

Algo-Sentry makes you articulate your reasoning, cementing fundamental computer science concepts as you type.

---

## 🏗️ How It Was Built: The 3-Layer Architecture

To make this feel like a blazing-fast, deterministic mentor rather than a laggy, hallucinating LLM wrapper, Algo-Sentry was completely rebuilt using a strict **3-Layer Hybrid Pipeline**:

### Layer 1: The Atomic Analyzer (Speed & Precision)
*   **Zero AI Overhead:** Runs completely locally on the Python backend in **<10ms**.
*   **Multi-Language AST & Regex:** Uses Python's native `ast` module (and highly-tuned Regular Expressions for Java and C++) to traverse your code and detect *atomic* choices: initializing a `vector<int>`, writing a `while` loop, invoking `.sort()`, or doing binary fraction operations.
*   **The Source of Truth:** It passes a definitive array of features (e.g., `["dict_init", "nested_loop"]`) to the AI layers so they don't have to guess what pattern you are writing.

### Layer 2: The Socratic Engine (Groq / Llama 3.3)
*   **Fast Question Generation:** Using Groq's insanely fast inference, Layer 2 takes the atomic features and generates an array of 2 to 4 sequential, open-ended questions.
*   **Language-Agnostic:** Prompt-engineered to ignore syntax trivia (like *"What does range() do?"*) and strictly ask concept-level algorithmic questions.
*   **Anti-Repetition Memory:** Tracks your recent question history locally to ensure you don't get asked the same concepts redundantly.

### Layer 3: The Validation Mentor (Gemini / Groq)
*   **Natural Language Evaluation:** The VS Code interface presents the questions via a sequential input box loop. You type out your reasoning in human language (e.g., *"Because it's O(1) lookup"*).
*   **Deep Reasoning:** The backend maps your answer against the actual code snippet context, sending it to Gemini (or a fast fallback model) to evaluate your logic. It responds with personalized feedback—either enthusiastic positive reinforcement or a gentle, code-specific correction.

---

## 🚀 Key Features

*   **Multi-Language Support:** Instantly understands Python (`.py`), Java (`.java`), and C++ (`.cpp`, `.cc`, `.h`) structural choices.
*   **Socratic Flow:** Replaces standard "A/B/C" multiple choice clicks with requiring you to type out your actual logic.
*   **Non-Intrusive UX:** Operates silently in the background (debounced analysis) and respectfully prompts you via simple corner notifications only when meaningful structural code is detected. No command palettes, no interrupted typing.
*   **Dynamic Personalities:** Mentors you in a tone of your choice (Gen-Z slang, Professional Mentor, or FAANG Interviewer).

---

## 🛠️ Getting Started

### 1. Backend Setup
1.  Navigate into the `backend_stub` directory:
    ```bash
    cd backend_stub
    ```
2.  Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```
3.  Set up your `.env` file with your API keys:
    ```env
    GOOGLE_API_KEY=your-gemini-key
    GROQ_API_KEY=your-groq-key
    ```
4.  Run the FastAPI layer:
    ```bash
    uvicorn main:app --reload --port 8000
    ```

### 2. Extension Setup
1. Open the root project folder in VS Code.
2. Install dependencies and compile:
    ```bash
    npm install
    npm run compile
    ```
3. Press **`F5`** to launch the Extension Development Host.
4. **Test it out:** Open a `.py` or `.java` or `.cpp` file, write a loop or initialize a data structure, and wait 2 seconds for the status bar to parse your code. Accept the prompt to begin the Socratic loop!

---

## ⚙️ Configuration
You can tweak Algo-Sentry in your VS Code Settings:
- `algosentry.backendUrl` – Point to your local FastAPI server.
- `algosentry.personality` – Set the mentor's tone.
- `algosentry.quizCooldownSeconds` – Control how often you want to be interrupted.

*(Packaged manually via `vsce package` for standalone `.vsix` distribution).*

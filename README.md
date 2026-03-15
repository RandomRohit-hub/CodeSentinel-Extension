# Algo-Sentry VS Code Extension

> [!WARNING]
> **Project Under Construction** 🚧
> This project is actively being developed and is currently under construction.

Algo-Sentry is an AI-powered mentor for Data Structures & Algorithms practice inside VS Code. It watches the code you write in real time, sends it to a FastAPI backend for analysis, and gives you gentle nudges about patterns, complexity, and possible optimizations.

## Features (Phase 1–9 implemented)

- **Real-time monitoring**: Listens to document changes and periodically sends the active file content to your backend (with debounce).
- **AI backend integration**: Sends `code`, `language`, `fileName`, and `difficulty` to your FastAPI `/analyze` endpoint and expects back fields such as `pattern`, `complexity`, `spaceComplexity`, `suggestion`, `question`, and `concept`.
- **Popup feedback**: Shows questions/suggestions in VS Code notifications with `Answer`, `Skip`, and `Hint` options.
- **Personality modes**: `genz`, `mentor`, and `interview` personalities change the tone of messages.
- **Difficulty settings**: `beginner`, `intermediate`, and `advanced` affect the payload sent to the backend.
- **Status bar display**: Shows detected pattern and complexity in the status bar.
- **Sidebar webview panel**: A modern-looking Algo-Sentry panel that explains what the extension is doing and what patterns it focuses on.

## Requirements

- Node.js (LTS version is recommended).
- VS Code (1.85.0 or newer recommended).
- A running FastAPI backend exposing `POST /analyze` (see `backend_stub/`).

### Smarter MCQs with Google Gemini or OpenAI

The backend can use **Google Gemini** or **OpenAI** to generate code-aware multiple-choice questions. Without an API key it falls back to a built-in MCQ bank.

- **Google Gemini (recommended):** Get an API key from [Google AI Studio](https://aistudio.google.com/apikey), then:
  ```bash
  cd backend_stub
  pip install -r requirements.txt
  set GOOGLE_API_KEY=your-gemini-api-key
  uvicorn main:app --reload --port 8000
  ```
- **OpenAI:** Set `OPENAI_API_KEY` instead; the backend will use it if `GOOGLE_API_KEY` is not set.
- **Force provider:** Set `LLM_PROVIDER=google` or `LLM_PROVIDER=openai` to use only that API.

Example FastAPI stub:

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class AnalyzeRequest(BaseModel):
    code: str
    language: str | None = None
    fileName: str | None = None
    difficulty: str | None = None


class AnalyzeResponse(BaseModel):
    pattern: str | None = None
    complexity: str | None = None
    spaceComplexity: str | None = None
    suggestion: str | None = None
    question: str | None = None
    concept: str | None = None
    tip: str | None = None


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    # TODO: replace stub with real analysis & pattern detection
    if "for" in req.code and "for" in req.code.split("for", 1)[1]:
        return AnalyzeResponse(
            pattern="Nested loop detected",
            complexity="O(n^2)",
            suggestion="Consider using a hash map to reduce nested scans.",
            question="What is the time complexity of this nested loop?"
        )
    return AnalyzeResponse(
        pattern="Simple scan",
        complexity="O(n)",
        question="Could this be improved with a different data structure?"
    )
```

## Getting Started (Development)

1. **Install dependencies**

   ```bash
   npm install
   ```

2. **Compile the extension**

   ```bash
   npm run compile
   ```

3. **Launch the Extension Development Host**

   - Open this folder in VS Code.
   - Press `F5` to start debugging.
   - A new VS Code window (Extension Development Host) will open.

4. **Use Algo-Sentry**

   - Start your FastAPI backend (by default at `http://localhost:8000/analyze` or update the setting).
   - In the Extension Development Host, open or create a file with some DSA code (loops, recursion, etc.).
   - Start typing; after a short pause (default: 2s debounce), Algo-Sentry will send your code to the backend.
   - Watch for:
     - Status bar updates (`Algo-Sentry: ...`) on the left.
     - Popup questions and suggestions.
   - Open the sidebar panel via the command palette:
     - `Ctrl+Shift+P` → **Algo-Sentry: Open Assistant Panel**.

## Configuration

In VS Code settings (search for “Algo-Sentry”) you can change:

- `algosentry.backendUrl` – URL of your FastAPI `/analyze` endpoint.
- `algosentry.personality` – `"genz" | "mentor" | "interview"`.
- `algosentry.difficulty` – `"beginner" | "intermediate" | "advanced"`.
- `algosentry.analysisDebounceMs` – debounce time in milliseconds (e.g. 2000).
- `algosentry.enableStatusBar` – enable/disable status bar feedback.

## Packaging

To build a `.vsix` package:

```bash
npm run compile
npm install -g vsce   # if not installed
vsce package
```

This will create a file like `algo-sentry-0.0.1.vsix`.

You can then install it in VS Code:

- Go to the Extensions view.
- Click the `...` menu → **Install from VSIX...**.
- Select the generated `.vsix` file.

## Next Steps / Ideas

- Deeper AST-based analysis for multiple languages.
- More fine-grained question sets per concept and difficulty.
- History view of past feedback & answered questions in the panel.
- Per-language tuning and test-case integration.


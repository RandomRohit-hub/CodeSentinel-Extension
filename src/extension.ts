import * as vscode from "vscode";
import axios from "axios";

type AlgoSentryPersonality = "genz" | "mentor" | "interview";
type AlgoSentryDifficulty = "beginner" | "intermediate" | "advanced";

interface AlgoSentryConfig {
  backendUrl: string;
  personality: AlgoSentryPersonality;
  difficulty: AlgoSentryDifficulty;
  debounceMs: number;
  enableStatusBar: boolean;
  quizCooldownSeconds: number;
  periodicQuestionIntervalSeconds: number;
  idleThresholdSeconds: number;
}

interface AlgoSentryAnalysisResponse {
  features: string[];
  concept: string;
  confidence: number;
  is_meaningful_dsa: boolean;
}

interface AlgoSentrySocraticResponse {
  questions: string[];
}

interface AlgoSentryValidateResponse {
  feedback: string;
}

let statusBarItem: vscode.StatusBarItem | undefined;
let analysisTimeout: NodeJS.Timeout | undefined;
let outputChannel: vscode.OutputChannel | undefined;

/** Max number of recent question texts to send to backend to avoid repeats */
const RECENT_QUESTIONS_MAX = 10;
/** Lines of context around cursor when extracting "active" code (or full function if detected) */
const CURSOR_CONTEXT_LINES = 45;

let extensionContext: vscode.ExtensionContext | undefined;

/** User chose "Disable questions for this session" — no prompts until restart */
let questionsDisabledForSession = false;
/** Last time we showed the "Want to try a quiz?" prompt (for cooldown) */
let lastQuizPromptTime = 0;
/** Last time the user edited a document (for "actively coding" check) */
let lastEditTime = 0;
/** Timer for periodic question offers; cleared on deactivate */
let periodicQuestionTimer: ReturnType<typeof setInterval> | undefined;

function getRecentQuestions(): string[] {
  if (!extensionContext) return [];
  const raw = extensionContext.globalState.get<string[]>("algosentry.recentQuestions", []);
  return Array.isArray(raw) ? raw.slice(-RECENT_QUESTIONS_MAX) : [];
}

function pushRecentQuestion(question: string): void {
  if (!extensionContext || !question.trim()) return;
  const recent = getRecentQuestions();
  const next = [...recent.filter((q) => q !== question), question].slice(-RECENT_QUESTIONS_MAX);
  extensionContext.globalState.update("algosentry.recentQuestions", next);
}

function log(msg: string) {
  if (!outputChannel) outputChannel = vscode.window.createOutputChannel("Algo-Sentry");
  outputChannel.appendLine(`[${new Date().toLocaleTimeString()}] ${msg}`);
}

function getConfig(): AlgoSentryConfig {
  const config = vscode.workspace.getConfiguration("algosentry");
  return {
    backendUrl: config.get<string>("backendUrl", "http://localhost:8000/analyze"),
    personality: config.get<AlgoSentryPersonality>("personality", "genz"),
    difficulty: config.get<AlgoSentryDifficulty>("difficulty", "beginner"),
    debounceMs: config.get<number>("analysisDebounceMs", 2000),
    enableStatusBar: config.get<boolean>("enableStatusBar", true),
    quizCooldownSeconds: Math.max(60, Math.min(600, config.get<number>("quizCooldownSeconds", 90))),
    periodicQuestionIntervalSeconds: Math.max(30, Math.min(300, config.get<number>("periodicQuestionIntervalSeconds", 30))),
    idleThresholdSeconds: Math.max(30, Math.min(600, config.get<number>("idleThresholdSeconds", 120))),
  };
}

function ensureStatusBarItem(): vscode.StatusBarItem {
  if (!statusBarItem) {
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBarItem.text = "Algo-Sentry: Click to analyze";
    statusBarItem.tooltip = "Click to analyze current file and get DSA feedback / quiz";
    statusBarItem.command = "algosentry.analyzeNow";
    statusBarItem.show();
  }
  return statusBarItem;
}

/**
 * Get code context for analysis: cursor line (1-based) and a snippet focused around the cursor
 * (current function/block or a window of lines) so the backend can analyze relevant portion.
 */
function getCodeContext(editor: vscode.TextEditor): { code: string; cursorLine: number; codeSnippet: string } {
  const document = editor.document;
  const fullCode = document.getText();
  const cursorLine = editor.selection.active.line + 1; // 1-based for backend

  const lines = document.getText().split(/\r?\n/);
  const totalLines = lines.length;
  const cursorIndex = editor.selection.active.line;

  // Try to find function/block boundaries around cursor (common patterns)
  const languageId = document.languageId.toLowerCase();
  const isPy = languageId === "python";
  const isJs = /^(javascript|typescript|jsx|tsx)$/.test(languageId);
  const isJava = /^(java|kotlin)$/.test(languageId);
  const isCpp = /^(c|cpp|c\+\+)$/.test(languageId);

  let start = Math.max(0, cursorIndex - CURSOR_CONTEXT_LINES);
  let end = Math.min(totalLines, cursorIndex + CURSOR_CONTEXT_LINES + 1);

  if (isPy) {
    for (let i = cursorIndex; i >= 0; i--) {
      const t = lines[i].trim();
      if (t.startsWith("def ") || t.startsWith("class ") || (t && !t.startsWith("#") && t.endsWith(":"))) {
        start = i;
        break;
      }
    }
    for (let i = cursorIndex + 1; i < totalLines; i++) {
      const t = lines[i].trim();
      const indent = lines[i].search(/\S/);
      if (indent >= 0 && indent <= (lines[start].search(/\S/) || 0) && t && !t.startsWith("#")) {
        end = i;
        break;
      }
    }
  } else if (isJs || isJava || isCpp) {
    for (let i = cursorIndex; i >= 0; i--) {
      const t = lines[i].trim();
      if (/^(function|def|void|int|bool|string|const|let|var)\s+\w+\s*\(/.test(t) || /\{\s*$/.test(t) || /^\s*(public|private|protected)\s+/.test(t)) {
        start = i;
        break;
      }
    }
    let brace = 0;
    for (let i = start; i < totalLines; i++) {
      for (const c of lines[i]) {
        if (c === "{") brace++;
        else if (c === "}") brace--;
      }
      if (brace > 0 && i > cursorIndex) { end = i + 1; break; }
      if (brace === 0 && i > start) { end = i + 1; break; }
    }
  }

  const snippetLines = lines.slice(start, end);
  const codeSnippet = snippetLines.join("\n").trim() || fullCode.slice(0, 8000);

  return { code: fullCode, cursorLine, codeSnippet: codeSnippet.slice(0, 6000) };
}

/**
 * @param forceShowQuiz When true (e.g. user ran "Analyze current file now"), skip the "Want to try?" prompt and show the quiz directly.
 */
async function analyzeActiveDocument(forceShowQuiz = false) {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    log("No active editor — open a code file and try again.");
    vscode.window.showWarningMessage("Algo-Sentry: Open a code file first, then click the status bar or run \"Algo-Sentry: Analyze current file now\".");
    return;
  }

  const document = editor.document;
  const fullCode = document.getText();
  if (!fullCode.trim()) {
    log("Active file is empty — add some code and try again.");
    vscode.window.showWarningMessage("Algo-Sentry: The current file is empty. Add some code and try again.");
    return;
  }

  const { code, cursorLine, codeSnippet } = getCodeContext(editor);
  const recentQuestions = getRecentQuestions();

  const cfg = getConfig();
  log(`Analyzing ${document.fileName} (${document.languageId}) line ${cursorLine} → ${cfg.backendUrl}`);

  const status = ensureStatusBarItem();
  if (cfg.enableStatusBar) {
    status.text = "Algo-Sentry: Analyzing…";
    status.show();
  }

  try {
    const response = await axios.post<AlgoSentryAnalysisResponse>(cfg.backendUrl, {
      code,
      language: document.languageId,
      fileName: document.fileName,
      difficulty: cfg.difficulty,
      cursorLine,
      codeSnippet: codeSnippet || undefined,
      recent_questions: recentQuestions.length > 0 ? recentQuestions : undefined,
      personality: cfg.personality,
    }, { timeout: 25000 }); // Increased timeout for AI reasoning

    const data = response.data || {};
    const features = data.features || [];
    const isMeaningfulPattern = data.is_meaningful_dsa || false;

    log(`Layer 1 response: features=[${features.join(", ")}], meaningful=${isMeaningfulPattern}`);

    if (cfg.enableStatusBar) {
      status.text = `Algo-Sentry: Analyzing...`;
      status.show();
    }

    let userWantsQuiz = false;

    if (forceShowQuiz && isMeaningfulPattern) {
      userWantsQuiz = true;
    } else if (isMeaningfulPattern) {
      if (questionsDisabledForSession) {
        log("Quiz skipped — questions disabled for this session.");
        return;
      }
      const cooldownMs = cfg.quizCooldownSeconds * 1000;
      const now = Date.now();
      if (now - lastQuizPromptTime < cooldownMs && !forceShowQuiz) {
        log(`Quiz prompt skipped — cooldown (${cfg.quizCooldownSeconds}s) not elapsed.`);
        return;
      }

      const promptMessage = "Quick check based on your code 👀 Want to try a quick DSA question?";
      const userChoice = await vscode.window.showInformationMessage(
        `Algo-Sentry 🤖\n${promptMessage}`,
        "Yes, ask me",
        "Not now",
        "Disable questions for this session"
      );

      if (userChoice === "Disable questions for this session") {
        questionsDisabledForSession = true;
        lastQuizPromptTime = now;
        vscode.window.showInformationMessage("Algo-Sentry: No more questions this session. Restart the editor to re-enable.");
        return;
      }
      if (userChoice === "Not now") {
        lastQuizPromptTime = now;
        return;
      }
      if (userChoice === "Yes, ask me") {
        lastQuizPromptTime = now;
        userWantsQuiz = true;
      }
    } else {
      log("Quiz skipped — no meaningful algorithm pattern detected.");
    }

    if (userWantsQuiz) {
      // Prompt user with loading status
      status.text = "Algo-Sentry: Preparing questions...";
      
      const socraticRes = await axios.post<AlgoSentrySocraticResponse>(`${cfg.backendUrl.replace("/analyze", "")}/generate_questions`, {
          code,
          features,
          language: document.languageId,
          recent_questions: recentQuestions.length > 0 ? recentQuestions : undefined,
          personality: cfg.personality,
      }, { timeout: 25000 });
      
      const sData = socraticRes.data;
      if (sData && sData.questions && sData.questions.length > 0) {
        for (let i = 0; i < sData.questions.length; i++) {
          const q = sData.questions[i];
          pushRecentQuestion(q);
          
          const userAnswer = await vscode.window.showInputBox({
            title: `Algo-Sentry Mentor (${i + 1}/${sData.questions.length})`,
            prompt: q,
            placeHolder: "Type your reasoning here (or hit ESC to cancel)...",
            ignoreFocusOut: true
          });
          
          if (!userAnswer) {
            // User cancelled
            break;
          }
          
          status.text = "Algo-Sentry: Validating...";
          const valRes = await axios.post<AlgoSentryValidateResponse>(`${cfg.backendUrl.replace("/analyze", "")}/validate`, {
              user_answer: userAnswer,
              question: q,
              code: codeSnippet,
              features,
              language: document.languageId,
              personality: cfg.personality,
          }, { timeout: 15000 });
          
          if (i < sData.questions.length - 1) {
            const btn = await vscode.window.showInformationMessage(`Algo-Sentry 🤖\n${valRes.data.feedback}`, "Next Question");
            if (btn !== "Next Question") {
              break;
            }
          } else {
            vscode.window.showInformationMessage(`Algo-Sentry 🤖\n${valRes.data.feedback}`);
          }
        }
        status.text = "Algo-Sentry: Ready";
      }
    } else if (forceShowQuiz && !isMeaningfulPattern) {
        vscode.window.showInformationMessage(
          "Algo-Sentry: Analysis done. No relevant decisions detected here for a Socratic check.",
          "Analyze again"
        ).then((choice) => {
          if (choice === "Analyze again") analyzeActiveDocument();
        });
    }

  } catch (err: any) {
    log(`Backend error: ${err?.message ?? err}`);
    if (cfg.enableStatusBar) {
      status.text = "Algo-Sentry: Backend unreachable";
      status.show();
    }
    // Always notify so user knows why there are no quizzes/feedback
    const msg = axios.isAxiosError(err) && err.code === "ECONNREFUSED"
      ? `Algo-Sentry: Backend not running. Start your FastAPI server at ${cfg.backendUrl.replace(/\/analyze.*$/, "")} to get analysis and quizzes.`
      : "Algo-Sentry: Could not reach backend. Check that the FastAPI server is running at the URL in settings.";
    vscode.window.showWarningMessage(msg, "Open settings").then((choice) => {
      if (choice === "Open settings") {
        vscode.commands.executeCommand("workbench.action.openSettings", "algosentry.backendUrl");
      }
    });
  }
}

function scheduleAnalysis() {
  if (analysisTimeout) {
    clearTimeout(analysisTimeout);
  }
  const cfg = getConfig();
  analysisTimeout = setTimeout(() => {
    analyzeActiveDocument();
  }, cfg.debounceMs);
}

function createOrRevealPanel(context: vscode.ExtensionContext) {
  const panel = vscode.window.createWebviewPanel(
    "algoSentryPanel",
    "Algo-Sentry",
    vscode.ViewColumn.Two,
    {
      enableScripts: true,
    }
  );

  const cfg = getConfig();

  panel.webview.html = getWebviewHtml(cfg);
}

function getWebviewHtml(cfg: AlgoSentryConfig): string {
  const personalityLabel =
    cfg.personality === "genz"
      ? "Gen-Z"
      : cfg.personality === "mentor"
        ? "Mentor"
        : "Interview";

  return `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Algo-Sentry</title>
    <style>
      body {
        margin: 0;
        padding: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: #0b1020;
        color: #f5f5f5;
      }
      .container {
        padding: 16px 20px;
      }
      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;
      }
      .title {
        font-size: 18px;
        font-weight: 600;
      }
      .badge-row {
        display: flex;
        gap: 8px;
        font-size: 11px;
      }
      .badge {
        padding: 2px 8px;
        border-radius: 999px;
        border: 1px solid rgba(255, 255, 255, 0.15);
        background: rgba(255, 255, 255, 0.03);
      }
      .card {
        border-radius: 12px;
        padding: 12px 14px;
        background: radial-gradient(circle at top left, #20264b, #0b1020);
        border: 1px solid rgba(255, 255, 255, 0.06);
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
        margin-bottom: 12px;
      }
      .card-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: rgba(255, 255, 255, 0.6);
        margin-bottom: 6px;
      }
      .card-main {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .card-main strong {
        font-size: 13px;
      }
      .hint {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.7);
      }
      .metric-row {
        display: flex;
        gap: 8px;
        font-size: 12px;
        margin-top: 4px;
      }
      .metric-pill {
        padding: 2px 8px;
        border-radius: 999px;
        background: rgba(0, 255, 163, 0.1);
        border: 1px solid rgba(0, 255, 163, 0.2);
        color: #a9ffdd;
      }
      .footer {
        margin-top: 14px;
        font-size: 11px;
        color: rgba(255, 255, 255, 0.5);
      }
    </style>
  </head>
  <body>
    <div class="container">
      <div class="header">
        <div class="title">Algo-Sentry</div>
        <div class="badge-row">
          <div class="badge">${personalityLabel} mode</div>
          <div class="badge">${cfg.difficulty} level</div>
        </div>
      </div>

      <div class="card">
        <div class="card-label">Status</div>
        <div class="card-main">
          <div>
            <strong>Real-time DSA mentor running</strong>
            <div class="hint">
              Edit a file with algorithms to see live feedback in popups and the status bar.
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-label">What Algo-Sentry watches for</div>
        <div class="metric-row">
          <div class="metric-pill">Nested loops</div>
          <div class="metric-pill">Recursion</div>
        </div>
        <div class="metric-row">
          <div class="metric-pill">Hash maps</div>
          <div class="metric-pill">Binary search</div>
        </div>
        <div class="metric-row">
          <div class="metric-pill">Sliding window</div>
          <div class="metric-pill">Dynamic programming</div>
        </div>
      </div>

      <div class="footer">
        Tips:
        <br />• Adjust personality & difficulty in VS Code settings (search for "Algo-Sentry").
        <br />• Ensure your FastAPI backend is running at the configured URL.
      </div>
    </div>
  </body>
</html>`;
}

export function activate(context: vscode.ExtensionContext) {
  console.log("Algo-Sentry activated");

  const cfg = getConfig();
  if (cfg.enableStatusBar) {
    ensureStatusBarItem();
  }

  const changeSubscription = vscode.workspace.onDidChangeTextDocument(() => {
    lastEditTime = Date.now();
    scheduleAnalysis();
  });

  const activeEditorSubscription = vscode.window.onDidChangeActiveTextEditor(() => {
    scheduleAnalysis();
  });

  const openDocSubscription = vscode.workspace.onDidOpenTextDocument((doc) => {
    if (doc.languageId && doc.getText().trim()) scheduleAnalysis();
  });

  const openPanelCommand = vscode.commands.registerCommand("algosentry.openPanel", () => {
    createOrRevealPanel(context);
  });

  const analyzeNowCommand = vscode.commands.registerCommand("algosentry.analyzeNow", () => {
    if (analysisTimeout) {
      clearTimeout(analysisTimeout);
      analysisTimeout = undefined;
    }
    analyzeActiveDocument(true);
  });

  extensionContext = context;

  // Periodic question mode: every N seconds, if user is actively coding, offer a new question
  function runPeriodicQuestionCheck() {
    if (questionsDisabledForSession) return;
    const editor = vscode.window.activeTextEditor;
    if (!editor?.document.getText().trim()) return;
    const cfg = getConfig();
    const idleMs = cfg.idleThresholdSeconds * 1000;
    if (Date.now() - lastEditTime > idleMs) {
      log("Periodic question skipped — editor idle (no recent edit).");
      return;
    }
    analyzeActiveDocument(false);
  }

  const intervalSec = getConfig().periodicQuestionIntervalSeconds;
  periodicQuestionTimer = setInterval(runPeriodicQuestionCheck, intervalSec * 1000);

  context.subscriptions.push(
    changeSubscription,
    activeEditorSubscription,
    openDocSubscription,
    openPanelCommand,
    analyzeNowCommand,
    {
      dispose() {
        if (periodicQuestionTimer) {
          clearInterval(periodicQuestionTimer);
          periodicQuestionTimer = undefined;
        }
      },
    }
  );
}

export function deactivate() {
  if (statusBarItem) {
    statusBarItem.dispose();
    statusBarItem = undefined;
  }
  if (analysisTimeout) {
    clearTimeout(analysisTimeout);
  }
  if (periodicQuestionTimer) {
    clearInterval(periodicQuestionTimer);
    periodicQuestionTimer = undefined;
  }
  outputChannel = undefined;
}


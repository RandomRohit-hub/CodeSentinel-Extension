# Code Sentinal VS Code Extension 🤖

> **Improve your DSA understanding while you code.**

**Code Sentinal** is an AI-powered VS Code extension that helps you learn Data Structures and Algorithms (DSA) in real time.
Instead of just checking errors, it reads your code and asks simple questions to help you understand your logic.

---

## 💡 The Motive

Many developers write code without fully understanding why it works.

Code Sentinal is built to change that.

It asks small, meaningful questions while you code:

* Why did you choose this data structure?
* What is the time complexity of this loop?
* Can this be made faster?

The goal is to make you think about your decisions and build strong fundamentals.

---

## 🏗️ How It Works (3-Layer System)

To make the extension fast and accurate, it uses a **3-layer architecture**:

### Layer 1: Code Analyzer (Fast & Local)

* Runs instantly (no AI delay)
* Detects loops, recursion, data structures, and patterns
* Works across Python, Java, and C++

---

### Layer 2: Question Generator (Groq AI)

* Generates simple, clear questions
* Based on your actual code
* Avoids repeating the same questions

---

### Layer 3: Answer Evaluation (Gemini / Groq)

* Checks your answer
* Gives clear feedback
* Explains mistakes in simple terms

---

## 🚀 Key Features

* ✅ Real-time code analysis inside VS Code
* ✅ Supports Python, Java, and C++
* ✅ Simple, easy-to-understand questions
* ✅ Helps improve DSA concepts step by step
* ✅ Non-intrusive popup system
* ✅ Works like a coding mentor

---

## 🧠 How It Helps

Code Sentinal does not give answers directly.

It helps you:

* think about your code
* understand complexity
* choose better data structures
* improve problem-solving skills

---

## 🛠️ Getting Started

### 1. Backend Setup

```bash
cd backend_stub
pip install -r requirements.txt
```

Create a `.env` file:

```env
GOOGLE_API_KEY=your-gemini-key
GROQ_API_KEY=your-groq-key
```

Run backend:

```bash
uvicorn main:app --reload --port 8000
```

---

### 2. Extension Setup

```bash
npm install
npm run compile
```

Press **F5** to run the extension.

---

### 3. Try It

* Open a `.py`, `.java`, or `.cpp` file
* Write some code (loop, array, map, etc.)
* Wait a few seconds
* A question will appear automatically

---

## ⚙️ Configuration

You can change settings in VS Code:

* `codesentinal.backendUrl` → backend server URL
* `codesentinal.quizCooldownSeconds` → question interval

---

## 🎯 Final Goal

Code Sentinal acts like:

👉 **A simple mentor sitting beside you while you code**

It helps you understand:

* why your code works
* how efficient it is
* how it can be improved

---

## 📦 Build & Package

To create extension file:

```bash
vsce package
```

Install manually using `.vsix` file.

---

## ⭐ Summary

Code Sentinal is not just a tool — it is a **learning companion** that helps you build strong DSA fundamentals while coding in real time.

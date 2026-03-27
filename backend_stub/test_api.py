import requests
import json

base_url = "http://localhost:8000"

req_data = {
    "code": "def binary_search(arr, x):\n  low = 0\n  high = len(arr) - 1\n  while low <= high:\n    mid = (high + low) // 2\n    if arr[mid] < x:\n      low = mid + 1\n    elif arr[mid] > x:\n      high = mid - 1\n    else:\n      return mid\n  return -1",
    "language": "python",
}

print("1. /analyze")
res_analyze = requests.post(f"{base_url}/analyze", json=req_data)
analysis = res_analyze.json()
print(json.dumps(analysis, indent=2))

if analysis.get("is_meaningful_dsa"):
    print("\n2. /generate_quiz")
    quiz_req = {
        "code": req_data["code"],
        "concept": analysis["concept"],
        "complexity": analysis["complexity"],
        "language": "python",
        "recent_questions": ["What is O(n)?"],
        "personality": "genz"
    }
    res_quiz = requests.post(f"{base_url}/generate_quiz", json=quiz_req)
    quiz = res_quiz.json()
    print(json.dumps(quiz, indent=2))
    
    print("\n3. /validate")
    val_req = {
        "user_answer": "It's array traversal so O(n)",  # wrong answer
        "correct_answer": quiz.get("correct", "O(log n)"),
        "question_context": {"question": quiz.get("question", "")},
        "code": req_data["code"],
        "personality": "genz"
    }
    res_val = requests.post(f"{base_url}/validate", json=val_req)
    print(json.dumps(res_val.json(), indent=2))

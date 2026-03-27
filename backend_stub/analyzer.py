import ast
import re

def analyze_code(code: str, language: str) -> dict:
    """
    Layer 1: Fast Rule-Based Analyzer.
    Runs in <10ms. Does not call LLMs.
    Output: { "concept": "...", "complexity": "...", "confidence": float }
    """
    lang = language.lower() if language else "python"
    
    if lang == "python":
        return _analyze_python_ast(code)
    else:
        return _analyze_regex_heuristics(code)

def _analyze_python_ast(code: str) -> dict:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return _analyze_regex_heuristics(code)  # Fallback if invalid python code snippet
        
    concept = "generic"
    complexity = "O(1)"
    confidence = 0.5
    
    has_loop = False
    has_nested_loop = False
    has_recursion = False
    has_hash_map = False
    
    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.loops = 0
            self.max_depth = 0
            self.current_depth = 0
            self.has_dict = False
            self.func_name = None
            self.recursive_calls = 0

        def visit_FunctionDef(self, node):
            self.func_name = node.name
            self.generic_visit(node)

        def visit_Call(self, node):
            if isinstance(node.func, ast.Name) and self.func_name and node.func.id == self.func_name:
                self.recursive_calls += 1
            self.generic_visit(node)

        def visit_Dict(self, node):
            self.has_dict = True
            self.generic_visit(node)

        def visit_For(self, node):
            self.loops += 1
            self.current_depth += 1
            self.max_depth = max(self.max_depth, self.current_depth)
            self.generic_visit(node)
            self.current_depth -= 1

        def visit_While(self, node):
            self.loops += 1
            self.current_depth += 1
            self.max_depth = max(self.max_depth, self.current_depth)
            self.generic_visit(node)
            self.current_depth -= 1

    visitor = Visitor()
    visitor.visit(tree)
    
    has_nested_loop = visitor.max_depth > 1
    has_recursion = visitor.recursive_calls > 0
    has_hash_map = visitor.has_dict
    
    # Simple semantic heuristics based on text since AST for "binary search" is complex
    code_lower = code.lower()
    if 'low' in code_lower and 'high' in code_lower and 'mid' in code_lower and ('+' in code_lower and '/' in code_lower):
        concept = "binary_search"
        complexity = "O(log n)"
        confidence = 0.95
    elif has_recursion:
        if 'memo' in code_lower or 'cache' in code_lower or 'dp' in code_lower:
            concept = "dynamic_programming"
            complexity = "O(n) or O(n^2)"
            confidence = 0.9
        else:
            concept = "recursion"
            complexity = "O(b^d)" # branching factor
            confidence = 0.8
    elif has_nested_loop:
        if 'dp' in code_lower or 'cache' in code_lower or 'memo' in code_lower:
            concept = "dynamic_programming"
            complexity = "O(n^2)"
            confidence = 0.85
        else:
            concept = "nested_loops"
            complexity = "O(n^2)"
            confidence = 0.9
    elif visitor.loops > 0:
        if 'left' in code_lower and 'right' in code_lower and ('window' in code_lower or 'max' in code_lower):
            concept = "sliding_window"
            complexity = "O(n)"
            confidence = 0.85
        else:
            concept = "loops"
            complexity = "O(n)"
            confidence = 0.8
    elif has_hash_map:
        concept = "hash_maps"
        complexity = "O(1) lookup"
        confidence = 0.85
        
    return {"concept": concept, "complexity": complexity, "confidence": confidence}

def _analyze_regex_heuristics(code: str) -> dict:
    code_lower = code.lower()
    
    # Nested loops regex (crude)
    loop_matches = len(re.findall(r'(for|while)\s*\(', code_lower))
    has_nested_loop = loop_matches >= 2 # rough approximation if snippet is short
    
    has_recursion = re.search(r'function\s+(\w+).*?\{\s*.*?\b\1\s*\(', code_lower, re.DOTALL) is not None
    if not has_recursion:
        has_recursion = re.search(r'(?:public|private|protected)?\s*\w+\s+(\w+)\s*\(.*?\s*\{.*?\b\1\s*\(', code_lower, re.DOTALL) is not None

    has_hash_map = 'new map(' in code_lower or 'hashmap' in code_lower or 'dict(' in code_lower or 'new set(' in code_lower
    
    concept = "generic"
    complexity = "O(1)"
    confidence = 0.5
    
    if 'low' in code_lower and 'high' in code_lower and 'mid' in code_lower and '/' in code_lower:
        concept = "binary_search"
        complexity = "O(log n)"
        confidence = 0.95
    elif has_recursion:
        concept = "recursion"
        complexity = "O(b^d)"
        confidence = 0.8
    elif has_nested_loop:
        concept = "nested_loops"
        complexity = "O(n^2)"
        confidence = 0.85
    elif loop_matches == 1:
        if 'left' in code_lower and 'right' in code_lower:
            concept = "sliding_window"
            complexity = "O(n)"
            confidence = 0.8
        else:
            concept = "loops"
            complexity = "O(n)"
            confidence = 0.8
    elif has_hash_map:
        concept = "hash_maps"
        complexity = "O(1) lookup"
        confidence = 0.8
        
    return {"concept": concept, "complexity": complexity, "confidence": confidence}

# Local test
if __name__ == "__main__":
    test_code = """
    def search(arr, target):
        low, high = 0, len(arr) - 1
        while low <= high:
            mid = (low + high) // 2
            if arr[mid] == target: return mid
        return -1
    """
    print(analyze_code(test_code, "python"))

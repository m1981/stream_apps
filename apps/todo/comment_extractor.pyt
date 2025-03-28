import ast
import os
import sys
from typing import Dict, List, Tuple

def extract_docstrings(file_path: str) -> List[Tuple[str, str, int]]:
    """
    Extract docstrings from a Python file.
    Returns list of tuples (context, docstring, line_number)
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    docstrings = []
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) and ast.get_docstring(node):
            context = ""
            line_no = 1  # Default for module docstring
            
            if isinstance(node, ast.ClassDef):
                context = f"Class: {node.name}"
                line_no = node.lineno
            elif isinstance(node, ast.FunctionDef):
                context = f"Function: {node.name}"
                line_no = node.lineno
            else:
                context = "Module"
                
            docstrings.append((
                context,
                ast.get_docstring(node),
                line_no
            ))
    
    return docstrings

def process_directory(directory: str):
    """Process all Python files in directory and print comments to stdout"""
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, directory)

                docstrings = extract_docstrings(file_path)
                if docstrings:
                    print(f"File: {relative_path}")

                    for context, docstring, line in docstrings:
                        print(f"Location: {context} (line {line})")
                        print(f"{'-'*8}")
                        print(f"{docstring.strip()}\n")

def main():
    if len(sys.argv) != 2:
        print("Usage: python comment_extractor.py <project_directory>")
        sys.exit(1)

    project_dir = sys.argv[1]
    if not os.path.isdir(project_dir):
        print(f"Error: '{project_dir}' is not a valid directory")
        sys.exit(1)

    process_directory(project_dir)

if __name__ == "__main__":
    main()
import os
from pathlib import Path

def get_codebase_context(project_root=".", exclude_dirs=[".git", "venv"]):
    """Walk through the codebase and create a structured context"""
    context = {}
    for root, dirs, files in os.walk(project_root):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            file_path = Path(root) / file
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    context[str(file_path)] = f.read()
            except UnicodeDecodeError:
                # Skip binary files
                continue
    return context

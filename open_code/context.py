import os
from pathlib import Path

def get_codebase_context(project_root=".", 
                         exclude_dirs=["node_modules", ".venv", "venv", ".git", "__pycache__", 
                                      "dist", "build", ".pytest_cache", ".next"]):
    """Walk through the codebase and create a structured context"""
    context = {}
    for root, dirs, files in os.walk(project_root):
        # skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            file_path = Path(root) / file
            if file_path.stat().st_size > 1_000_000:  # skip files > 1MB
                continue
                
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    context[str(file_path)] = f.read()
            except (UnicodeDecodeError, PermissionError):
                # skip bin files and some which has permission issues
                continue
    return context

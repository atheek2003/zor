import os
from pathlib import Path
from .config import load_config

def get_codebase_context(project_root="."):
    """Walk through the codebase and create a structured context"""
    config = load_config()
    exclude_dirs = config.get("exclude_dirs", ["node_modules", ".venv", "venv", ".git", "__pycache__", 
                                             "dist", "build", ".pytest_cache", ".next"])
    exclude_files = config.get("exclude_files", [".env", "*.pyc", "*.jpg", "*.png", "*.pdf"])
    
    context = {}
    for root, dirs, files in os.walk(project_root):
        # skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            file_path = Path(root) / file
            
            # Skip files based on exclude patterns
            skip_file = False
            for pattern in exclude_files:
                if pattern.startswith("*.") and file.endswith(pattern[1:]):
                    skip_file = True
                    break
                elif pattern == file:
                    skip_file = True
                    break
            
            if skip_file:
                continue
                
            if file_path.stat().st_size > 1_000_000:  # skip files > 1MB
                continue
                
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    context[str(file_path)] = f.read()
            except (UnicodeDecodeError, PermissionError):
                # skip bin files and some which has permission issues
                continue
    return context

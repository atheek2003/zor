import os
import mimetypes
from pathlib import Path
import fnmatch
from .config import load_config

def is_binary_file(file_path):
    """Check if a file is binary by reading a small sample"""
    try:
        with open(file_path, 'rb') as file:
            # Read the first chunk of the file
            chunk = file.read(8192)
            # Check for null bytes which often indicate binary data
            if b'\x00' in chunk:
                return True
            # Try decoding as text
            try:
                chunk.decode('utf-8')
                return False
            except UnicodeDecodeError:
                return True
    except (IOError, OSError):
        # If we can't read the file, treat it as binary to be safe
        return True

def should_exclude_directory(dir_name, exclude_dirs):
    """Check if a directory should be excluded"""
    for pattern in exclude_dirs:
        if fnmatch.fnmatch(dir_name, pattern):
            return True
    return False

def should_exclude_file(file_path, exclude_files, exclude_extensions):
    """Check if a file should be excluded based on name or extension"""
    file_name = os.path.basename(file_path)
    
    # Check against excluded file patterns
    for pattern in exclude_files:
        if fnmatch.fnmatch(file_name, pattern):
            return True
    
    # Check file extension
    _, ext = os.path.splitext(file_path)
    if ext.lower() in exclude_extensions:
        return True
    
    # Check if it's a binary file
    if is_binary_file(file_path):
        return True
    
    return False

def get_codebase_context(project_root="."):
    """Walk through the codebase and create a structured context"""
    config = load_config()
    
    # Default exclusion lists with wildcards
    exclude_dirs = config.get("exclude_dirs", [
        "node_modules", ".venv", "venv", ".git", "__pycache__", 
        "dist", "build", ".pytest_cache", ".next", ".*"
    ])
    
    exclude_files = config.get("exclude_files", [
        ".env", "*.pyc", "*.jpg", "*.png", "*.pdf", "*.lock"
    ])
    
    # Common binary and unwanted extensions
    exclude_extensions = config.get("exclude_extensions", [
        ".zip", ".tar", ".gz", ".rar", ".7z", ".jar", ".war", ".ear",
        ".class", ".obj", ".dll", ".exe", ".so", ".dylib",
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".ico", ".svg", ".webp",
        ".mp3", ".mp4", ".avi", ".mov", ".flv", ".wmv", ".wav", ".ogg",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".db", ".sqlite", ".sqlite3", ".mdb", ".accdb",
        ".pyc", ".pyo", ".pyd", ".o", ".a", ".lib"
    ])
    
    # Initialize mimetypes
    mimetypes.init()
    
    # Debug information
    print(f"Starting context collection from {project_root}")
    print(f"Excluding directories matching: {exclude_dirs}")
    
    context = {}
    file_count = 0
    dir_count = 0
    
    # Use os.walk which traverses directories recursively
    for root, dirs, files in os.walk(project_root):
        dir_count += 1
        
        # Filter out excluded directories before traversal continues
        # This modifies dirs in-place to avoid traversing excluded directories
        dirs[:] = [d for d in dirs if not should_exclude_directory(d, exclude_dirs)]
        
        for file in files:
            file_path = os.path.join(root, file)
            file_count += 1
            
            try:
                # Skip large files
                file_size = os.path.getsize(file_path)
                if file_size > 1_000_000:  # 1MB
                    continue
                
                # Skip excluded files
                if should_exclude_file(file_path, exclude_files, exclude_extensions):
                    continue
                
                # Read the file content
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                # Add to context if not empty
                if content.strip():
                    # Use a path that's relative to project_root for better context
                    relative_path = os.path.relpath(file_path, project_root)
                    context[relative_path] = content
                    
            except (UnicodeDecodeError, PermissionError, OSError) as e:
                # Skip files that can't be read as text
                continue
    
    print(f"Processed {dir_count} directories and {file_count} files")
    print(f"Added {len(context)} files to context")
    
    return context

import typer
from typing import Optional
from pathlib import Path

def edit_file(file_path: str, changes: str, backup: bool = True):
    """Edit a file with Gemini's suggested changes"""
    path = Path(file_path)
    if not path.exists():
        typer.echo(f"Error: File {file_path} does not exist", err=True)
        return False
    
    if backup:
        backup_path = path.with_suffix(f"{path.suffix}.bak")
        path.rename(backup_path)
    
    try:
        with open(file_path, "w") as f:
            f.write(changes)
        return True
    except Exception as e:
        typer.echo(f"Error writing file: {e}", err=True)
        return False

import typer
from typing import Optional
from pathlib import Path

def show_diff(original_content: str, new_content: str, file_path: str):
    """Show diff between original and new content"""
    import difflib
    from rich.console import Console
    from rich.syntax import Syntax
    
    console = Console()
    
    # Get the diff
    diff = difflib.unified_diff(
        original_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        n=3
    )
    
    # Print the diff
    diff_text = "".join(diff)
    if diff_text:
        console.print(f"\nChanges for {file_path}:")
        syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)
        console.print(syntax)
    else:
        console.print("\nNo changes detected.")
    
    return diff_text != ""

def edit_file(file_path: str, changes: str, backup: bool = True, preview: bool = True):
    """Edit a file with Gemini's suggested changes"""
    path = Path(file_path)
    if not path.exists():
        typer.echo(f"Error: File {file_path} does not exist", err=True)
        return False
    
    # Read the original content
    with open(path, "r") as f:
        original_content = f.read()
    
    # Show diff if preview is enabled
    if preview:
        changes_detected = show_diff(original_content, changes, file_path)
        if not changes_detected:
            return False
    
    if backup:
        backup_path = path.with_suffix(f"{path.suffix}.bak")
        with open(backup_path, "w") as f:
            f.write(original_content)
        typer.echo(f"Backup created at {backup_path}")
    
    try:
        with open(file_path, "w") as f:
            f.write(changes)
        return True
    except Exception as e:
        typer.echo(f"Error writing file: {e}", err=True)
        return False

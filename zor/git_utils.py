import subprocess
import typer

def git_commit(message: str):
    """Create a git commit with the given message"""
    try:
        if subprocess.run(["git", "add", "."], check=True).returncode != 0:
            subprocess.run(["git", "init"], check=True)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", message], check=True)
        return True
    except Exception as e:
        typer.echo(f"Git error: {e}", err=True)
        return False

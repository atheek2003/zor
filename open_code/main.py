import os
import typer
from dotenv import load_dotenv
import google.generativeai as genai
from .context import get_codebase_context
from .file_ops import edit_file
from .git_utils import git_commit
from typing import Optional

app = typer.Typer()

# Load API key from environment
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_with_context(prompt: str, context: dict):
    """Generate a response with codebase context"""
    model = genai.GenerativeModel('gemini-1.5-flash')
    context_str = "\n".join(f"File: {path}\n{content}" for path, content in context.items())
    full_prompt = f"Codebase Context:\n{context_str}\n\nUser Prompt: {prompt}"
    response = model.generate_content(full_prompt)
    return response.text

@app.command()
def ask(prompt: str):
    """Ask Gemini about your codebase"""
    context = get_codebase_context()
    response = generate_with_context(prompt, context)
    print(response)

@app.command()
def edit(file_path: str, prompt: str):
    """Edit a file based on natural language instructions"""
    context = get_codebase_context()
    instruction = f"Modify the file {file_path} to: {prompt}. Return only the complete new file content."
    new_content = generate_with_context(instruction, context)
    
    if typer.confirm("Apply these changes?"):
        if edit_file(file_path, new_content):
            typer.echo("File updated successfully")
        else:
            typer.echo("File update failed", err=True)

@app.command()
def commit(message: str):
    """Create a git commit with the given message"""
    if git_commit(message):
        typer.echo("Commit created successfully")
    else:
        typer.echo("Commit failed", err=True)

if __name__ == "__main__":
    app()

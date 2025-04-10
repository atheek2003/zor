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

@app.command()
def interactive():
    """Start an interactive session with the AI assistant"""
    typer.echo("Starting interactive session. Type 'exit' to quit.")
    typer.echo("Loading codebase context...")
    
    # Load context once at the beginning
    context = get_codebase_context()
    typer.echo(f"Loaded context from {len(context)} files.")
    
    # Setup conversation history
    history = []
    
    while True:
        try:
            prompt = typer.prompt("\nWhat would you like to do?", prompt_suffix="\n> ")
            
            if prompt.lower() in ("exit", "quit"):
                break
                
            # Add prompt to history
            history.append({"role": "user", "content": prompt})
            
            # Generate response with context and history
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Create context string
            context_str = "\n".join(f"File: {path}\n{content}" for path, content in context.items())
            
            # Create history string (simplified)
            history_str = "\n".join(
                f"{'User' if h['role'] == 'user' else 'Assistant'}: {h['content']}" 
                for h in history[:-1]
            )
            
            # Combine everything
            if history_str:
                full_prompt = (
                    f"You are an AI coding assistant working with the following codebase:\n\n"
                    f"Codebase Context:\n{context_str}\n\n"
                    f"Previous conversation:\n{history_str}\n\n"
                    f"User: {prompt}"
                )
            else:
                full_prompt = (
                    f"You are an AI coding assistant working with the following codebase:\n\n"
                    f"Codebase Context:\n{context_str}\n\n"
                    f"User: {prompt}"
                )
            
            # Get response with error handling and rate limiting
            try:
                response = model.generate_content(full_prompt)
                answer = response.text
                typer.echo(f"\n{answer}")
                
                # Add response to history
                history.append({"role": "assistant", "content": answer})
                
                # Check if we need to perform file operations
                if "```" in answer and "edit file" in prompt.lower():
                    # Simple extraction of code blocks (would need more sophisticated parsing in production)
                    file_to_edit = typer.prompt("Enter file path to edit")
                    if file_to_edit and Path(file_to_edit).exists():
                        code_blocks = extract_code_blocks(answer)
                        if code_blocks and typer.confirm("Apply these changes?"):
                            edit_file(file_to_edit, code_blocks[0], backup=True)
                            typer.echo(f"Updated {file_to_edit}")
                
            except Exception as e:
                typer.echo(f"Error: {e}", err=True)
                # Implement exponential backoff for rate limiting here
                
        except KeyboardInterrupt:
            typer.echo("\nExiting interactive mode.")
            break
    
    typer.echo("Interactive session ended.")

def extract_code_blocks(text):
    """Extract code blocks from markdown text"""
    import re
    pattern = r"```(?:\w+)?\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    return matches


@app.command()
def generate_test(file_path: str, test_framework: str = "pytest"):
    """Generate tests for a specific file"""
    context = get_codebase_context()
    
    # Read the target file
    with open(file_path, "r") as f:
        target_file = f.read()
    
    # Create the prompt
    prompt = f"""Generate comprehensive unit tests for the following file using {test_framework}.
The tests should cover all functions and edge cases.
Return only the test code without explanations.

File to test:
```python
{target_file}
```

Existing codebase context is available for reference."""
    
    # Generate the tests
    tests = generate_with_context(prompt, context)
    
    # Determine test file path
    test_file_path = str(Path(file_path).parent / f"test_{Path(file_path).name}")
    
    # Show the generated tests
    typer.echo("\nGenerated tests:")
    typer.echo(tests)
    
    # Ask to save
    if typer.confirm(f"Save tests to {test_file_path}?"):
        with open(test_file_path, "w") as f:
            f.write(tests)
        typer.echo(f"Tests saved to {test_file_path}")


@app.command()
def refactor(prompt: str):
    """Refactor code across multiple files based on instructions"""
    context = get_codebase_context()
    
    instruction = f"""You are a coding assistant helping with a refactoring task across multiple files.
    
Task description: {prompt}

For each file that needs to be modified, please specify:
1. The file path
2. The complete new content for that file

Format your response like this:

FILE: path/to/file1
```python
# New content for file1
```

FILE: path/to/file2
```python
# New content for file2
```

Only include files that need to be changed. Do not include any explanations outside of the file blocks.
"""
    
    # Get the refactoring plan
    refactoring_plan = generate_with_context(instruction, context)
    
    # Parse the plan to extract file paths and contents
    import re
    file_changes = re.findall(r"FILE: (.+?)\n```(?:python|java|javascript|typescript)?\n(.+?)```", 
                             refactoring_plan, re.DOTALL)
    
    if not file_changes:
        typer.echo("No file changes were specified in the response.", err=True)
        return
    
    # Show summary of changes
    typer.echo(f"\nRefactoring will modify {len(file_changes)} files:")
    for file_path, _ in file_changes:
        typer.echo(f"- {file_path.strip()}")
    
    # Show diffs and ask for confirmation
    if typer.confirm("Show detailed changes?"):
        for file_path, new_content in file_changes:
            file_path = file_path.strip()
            try:
                # Read current content if file exists
                if Path(file_path).exists():
                    with open(file_path, "r") as f:
                        current_content = f.read()
                else:
                    current_content = ""
                    typer.echo(f"Note: {file_path} will be created.")
                
                # Show diff
                show_diff(current_content, new_content, file_path)
                
            except Exception as e:
                typer.echo(f"Error processing {file_path}: {e}", err=True)
    
    # Confirm and apply changes
    if typer.confirm("Apply these changes?"):
        for file_path, new_content in file_changes:
            file_path = file_path.strip()
            
            # Create directory if needed
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Apply changes
            if edit_file(file_path, new_content, backup=True, preview=False):
                typer.echo(f"Updated {file_path}")
            else:
                typer.echo(f"Failed to update {file_path}", err=True)
        
        # Offer to commit changes
        if typer.confirm("Commit these changes?"):
            commit_msg = typer.prompt("Enter commit message", 
                                    default=f"Refactor: {prompt[:50]}")
            if git_commit(commit_msg):
                typer.echo("Changes committed successfully")


if __name__ == "__main__":
    app()

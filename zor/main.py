import os
import typer
from dotenv import load_dotenv
import google.generativeai as genai
from pathlib import Path
from .context import get_codebase_context
from .file_ops import edit_file, show_diff
from .git_utils import git_commit
from .api import generate_with_context
from .config import load_config, save_config
from typing import Optional, Annotated, Callable, List
from functools import wraps
from typer.core import TyperGroup
from rich.console import Console
from rich.panel import Panel
import subprocess
import shutil

app = typer.Typer()

load_dotenv()

# Global flag to track if API key is validated
api_key_valid = False

# Load API key from environment or config
def load_api_key():
    global api_key_valid
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        config = load_config()
        api_key = config.get("api_key")
    
    if api_key:
        try:
            genai.configure(api_key=api_key)
            # Quick validation attempt - keep this lightweight
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content("Test")
            api_key_valid = True
            return True
        except Exception:
            api_key_valid = False
            return False
    
    api_key_valid = False
    return False

# Try to load API key on startup
load_api_key()

# Decorator to ensure API key exists before running commands
def require_api_key(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        global api_key_valid
        
        # Skip API key check for setup command
        if func.__name__ == "setup":
            return func(*args, **kwargs)
        
        # Check if API key is valid
        if not api_key_valid:
            typer.echo("No valid Gemini API key found. Please run 'zor setup' to configure your API key.", err=True)
            raise typer.Exit(1)
            
        return func(*args, **kwargs)
    return wrapper

@app.command()
def help():
    """Display all available commands and their descriptions"""
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    
    table = Table(title="Available Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="green")
    
    commands = [
        ("ask", "Ask Zor about your codebase"),
        ("init", "Create a new project based on natural language instructions"),
        ("edit", "Edit a file based on natural language instructions"),
        ("commit", "Create a git commit with the given message"),
        ("config", "View configuration"),
        ("interactive", "Start an interactive session with the Zor AI assistant"),
        ("history", "Show conversation history"),
        ("generate_test", "Generate tests for a specific file"),
        ("refactor", "Refactor code across multiple files based on instructions"),
        ("setup", "Configure your Gemini API key"),
        ("help", "Display all available commands and their descriptions")
    ]
    
    for cmd, desc in commands:
        table.add_row(cmd, desc)
    
    console.print(table)
    console.print("\nFor more details on a specific command, run: zor [COMMAND] --help")

    if not api_key_valid:
        console.print("\n[bold red]Warning:[/bold red] No valid API key configured. Please run 'zor setup' first.", style="red")


@app.command()
@require_api_key
def ask(prompt: str):
    """Ask Zor about your codebase"""
    context = get_codebase_context()
    response = generate_with_context(prompt, context)
    print(response)


@app.command()
@require_api_key
def edit(file_path: str, prompt: str):
    """Edit a file based on natural language instructions"""
    # Check if file exists first
    if not Path(file_path).exists():
        typer.echo(f"Error: File {file_path} does not exist", err=True)
        return
        
    # Get current content of the file
    with open(file_path, "r") as f:
        original_content = f.read()
        
    context = get_codebase_context()
    instruction = f"Modify the file {file_path} to: {prompt}. Return only the complete new file content."
    response = generate_with_context(instruction, context)
    
    # Clean md res
    import re
    pattern = r"```(?:\w+)?\n(.*?)```"
    matches = re.findall(pattern, response, re.DOTALL)
    
    if matches:
        # Use the first code block found
        new_content = matches[0]
    else:
        # If no code block markers, use the response as is
        new_content = response
    
    # Show diff to user before confirmation
    show_diff(original_content, new_content, file_path)
    
    if typer.confirm("Apply these changes?"):
        if edit_file(file_path, new_content, preview=False):  # Set preview=False to avoid showing diff twice
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
def config(key: str = None, value: str = None):
    """View configuration"""
    current_config = load_config()
    
    if key is None and value is None:
        # Display current config
        for k, v in current_config.items():
            if k == "api_key" and v:
                # Don't show the actual API key, just indicate if it exists
                typer.echo(f"{k}: ***** (configured)")
            else:
                typer.echo(f"{k}: {v}")
                
        # Show API key status
        if not api_key_valid:
            typer.echo("\nWarning: No valid API key configured. Please run 'zor setup'.", err=True)
        return
    
    if key not in current_config:
        typer.echo(f"Unknown configuration key: {key}", err=True)
        return
    
    if value is None:
        # Display specific key
        if key == "api_key" and current_config[key]:
            typer.echo(f"{key}: ***** (configured)")
        else:
            typer.echo(f"{key}: {current_config[key]}")
        return

    current_type = type(current_config[key])
    if current_type == bool:
        current_config[key] = value.lower() in ("true", "1", "yes", "y")
    elif current_type == int:
        current_config[key] = int(value)
    elif current_type == float:
        current_config[key] = float(value)
    elif current_type == list:
        current_config[key] = value.split(",")
    else:
        current_config[key] = value
    
    save_config(current_config)
    typer.echo(f"Updated {key} to {current_config[key]}")

def extract_code_blocks(text):
    """Extract code blocks from markdown text"""
    import re
    pattern = r"```(?:\w+)?\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    return matches

@app.command()
@require_api_key
def interactive():
    """Start an interactive session with the Zor AI assistant"""
    typer.echo("Starting interactive session. Type 'exit' to quit.")
    typer.echo("Loading codebase context...")
    
    # load context once at the start
    context = get_codebase_context()
    typer.echo(f"Loaded context : {len(context)} tokens")
    
    # conversation history
    history = []
    
    while True:
        try:
            prompt = typer.prompt("\nWhat would you like to do?", prompt_suffix="\n> ")
            
            if prompt.lower() in ("exit", "quit"):
                break
                
            # add prompt to history
            history.append({"role": "user", "content": prompt})
            
            # create history string
            history_str = "\n".join(
                f"{'User' if h['role'] == 'user' else 'Assistant'}: {h['content']}" 
                for h in history[:-1]
            )
            
            # Create context for API call
            context_with_history = context.copy()
            if history_str:
                context_with_history["_conversation_history"] = history_str
            
            try:
                answer = generate_with_context(prompt, context_with_history)
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
                
        except KeyboardInterrupt:
            typer.echo("\nExiting interactive mode.")
            break
    
    typer.echo("Interactive session ended.")

@app.command()
@require_api_key
def history(limit: int = 5):
    """Show conversation history"""
    from rich.console import Console
    from rich.table import Table
    from .history import load_history
    
    console = Console()
    history_items = load_history(max_items=limit)
    
    if not history_items:
        console.print("No history found")
        return
    
    table = Table(title="Conversation History")
    table.add_column("Date", style="cyan")
    table.add_column("Prompt", style="green")
    table.add_column("Response", style="yellow")
    
    for item in history_items[-limit:]:
        # Truncate long text
        prompt = item["prompt"][:50] + "..." if len(item["prompt"]) > 50 else item["prompt"]
        response = item["response"][:50] + "..." if len(item["response"]) > 50 else item["response"]
        
        table.add_row(item["datetime"], prompt, response)
    
    console.print(table)

@app.command()
@require_api_key
def generate_test(file_path: str, test_framework: str = "pytest"):
    """Generate tests for a specific file"""
    if not Path(file_path).exists():
        typer.echo(f"Error: File {file_path} does not exist", err=True)
        return

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

    # clean
    code_blocks = extract_code_blocks(tests)

    if code_blocks:
        test_code = code_blocks[0]
    else:
        test_code = tests
    
    from rich.console import Console
    from rich.syntax import Syntax
    
    console = Console()
    console.print("\nGenerated test:")
    syntax = Syntax(test_code, "python", theme="monokai", line_numbers=True)
    console.print(syntax)
    
    # if test exists -> show diff
    if Path(test_file_path).exists():
        with open(test_file_path, "r") as f:
            existing_test_code = f.read()
        show_diff(existing_test_code, test_code, test_file_path)
    else:
        typer.echo(f"Note: Creating new test file at {test_file_path}")
    
    # Ask to save
    if typer.confirm(f"Save tests to {test_file_path}?"):
        with open(test_file_path, "w") as f:
            f.write(tests)
        typer.echo(f"Tests saved to {test_file_path}")

@app.command()
@require_api_key
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

@app.command()
def setup():
    """Configure your Gemini API key"""
    global api_key_valid
    
    config = load_config()
    current_api_key = config.get("api_key")
    
    # Check if API key already exists
    if current_api_key:
        if not typer.confirm("An API key is already configured. Do you want to replace it?", default=False):
            typer.echo("Setup cancelled. Keeping existing API key.")
            return

    api_key = typer.prompt("Enter your Gemini API key", hide_input=True)
    
    # Validate API key
    typer.echo("Validating API key...")
    try:
        # Configure temporarily with the new key
        genai.configure(api_key=api_key)
        
        # Try a simple API call to validate the key
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content("Just respond with 'OK' if this API key is valid.")
        
        if not response or not hasattr(response, 'text') or "error" in response.text.lower():
            typer.echo("Error: The API key appears to be invalid.", err=True)
            return
            
        typer.echo("API key validated successfully!")
        api_key_valid = True
    except Exception as e:
        typer.echo(f"Error: Unable to validate API key: {str(e)}", err=True)
        if not typer.confirm("The API key could not be validated. Save it anyway?", default=False):
            return
    
    # Create .env file or update existing one
    env_path = Path(".env")
    
    # Check if file exists and contains the API key
    env_content = ""
    if env_path.exists():
        with open(env_path, "r") as f:
            env_content = f.read()
    
    # Update or add the API key
    if "GEMINI_API_KEY=" in env_content:
        import re
        env_content = re.sub(r"GEMINI_API_KEY=.*", f"GEMINI_API_KEY={api_key}", env_content)
    else:
        env_content += f"\nGEMINI_API_KEY={api_key}\n"
    
    # Write the updated content
    try:
        with open(env_path, "w") as f:
            f.write(env_content)
        
        # Also store in global config
        config["api_key"] = api_key
        save_config(config)
        
        # Update the current session's API key
        genai.configure(api_key=api_key)
        
        typer.echo("API key configured and saved successfully!")
        typer.echo("You can now use zor with your Gemini API key.")
    except Exception as e:
        typer.echo(f"Error saving API key: {str(e)}", err=True)

# NEW FEAT: INIT
@app.command()
@require_api_key
def init(prompt: str, directory: str = None):
    """Create a new project based on natural language instructions"""
    console = Console()
    
    # Handle project directory
    if directory:
        project_dir = Path(directory)
    else:
        # Extract project name from prompt using more intelligent parsing
        words = prompt.lower().split()
        project_name = words[0].replace(" ", "_")
        
        # Check for actual project name in the first few words
        name_indicators = ["called", "named", "name", "project"]
        for i, word in enumerate(words):
            if word in name_indicators and i+1 < len(words):
                project_name = words[i+1].replace(" ", "_")
                break
        
        # Confirm with user
        project_dir = Path(typer.prompt(
            "Project directory name", 
            default=project_name
        ))
    
    # Check if directory exists
    if project_dir.exists() and any(project_dir.iterdir()):
        if not typer.confirm(f"Directory {project_dir} exists and is not empty. Continue anyway?", default=False):
            typer.echo("Project initialization cancelled.")
            raise typer.Exit()
    
    # Create directory if it doesn't exist
    project_dir.mkdir(exist_ok=True, parents=True)
    
    # Generate project structure based on prompt
    with console.status("[bold green]Analyzing project requirements...", spinner="dots") as status:
        # Create context for API call
        context = {"project_prompt": prompt}
        
        # First, get the project plan and type with a more comprehensive prompt
        planning_prompt = f"""
        I need to create a new project with this description: "{prompt}"
        
        Please provide a comprehensive analysis and detailed project plan. Include:
        
        1. Project type and main technologies (language, framework, libraries)
        2. Project architecture and design patterns to use
        3. Required file structure with explanation of each component
        4. Key files that need to be created with their purpose
        5. Dependencies that would need to be installed
        6. Development environment recommendations
        7. Any best practices specific to this type of project
        
        Format the response as:
        
        PROJECT_TYPE: [project type]
        
        MAIN_TECHNOLOGIES: [comma-separated list of main technologies]
        
        ARCHITECTURE: [Brief description of recommended architecture]
        
        PROJECT_PLAN:
        [Detailed explanation of the project structure and components]
        
        DEPENDENCIES:
        [List of key dependencies with versions if applicable]
        
        SETUP_COMMANDS:
        [List of commands that would be used to initialize and setup the project]
        
        FILE_STRUCTURE:
        [Tree structure of directories and files to be created]
        
        DEVELOPMENT_RECOMMENDATIONS:
        [Recommendations for development environment and workflows]
        """
        
        status.update("[bold green]Generating project blueprint...")
        plan_response = generate_with_context(planning_prompt, context)
        
        # Parse the response to extract project information
        import re
        
        # Extract all sections with improved regex patterns
        sections = {
            "project_type": re.search(r"PROJECT_TYPE:\s*(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:)", plan_response + "\n\n", re.DOTALL),
            "main_technologies": re.search(r"MAIN_TECHNOLOGIES:\s*(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:)", plan_response + "\n\n", re.DOTALL),
            "architecture": re.search(r"ARCHITECTURE:\s*(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:)", plan_response + "\n\n", re.DOTALL),
            "dependencies": re.search(r"DEPENDENCIES:(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:)", plan_response + "\n\n", re.DOTALL),
            "setup_commands": re.search(r"SETUP_COMMANDS:(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:)", plan_response + "\n\n", re.DOTALL),
            "development_recommendations": re.search(r"DEVELOPMENT_RECOMMENDATIONS:(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:|$)", plan_response + "\n\n", re.DOTALL)
        }
        
        # Process extracted sections
        project_info = {}
        for key, match in sections.items():
            project_info[key] = match.group(1).strip() if match else "Not specified"
        
        # Get project type with fallback
        project_type = project_info.get("project_type", "Unknown")
        setup_commands = project_info.get("setup_commands", "")
        
        # Show the project plan to the user with improved formatting
        status.stop()
        
        console.print("\n[bold cyan]📋 Project Blueprint[/bold cyan]")
        console.print(f"\n[bold]Project Type:[/bold] {project_type}")
        
        if project_info.get("main_technologies") != "Not specified":
            console.print(f"\n[bold]Main Technologies:[/bold]")
            console.print(project_info.get("main_technologies"))
            
        if project_info.get("architecture") != "Not specified":
            console.print(f"\n[bold]Architecture:[/bold]")
            console.print(project_info.get("architecture"))
        
        console.print("\n[bold]Project Plan:[/bold]")
        console.print(plan_response)
        
        # Confirm with user before proceeding
        if not typer.confirm("\nProceed with project creation?", default=True):
            typer.echo("Project initialization cancelled.")
            raise typer.Exit()
        
        # Improved file generation prompt with more context
        file_generation_prompt = f"""
        Based on the project description: "{prompt}"
        
        And identified project type: {project_type}
        
        Generate the content for each key file in the project. For each file, provide:
        1. The file path relative to the project root
        2. The complete content of the file
        3. A brief comment at the top of each file explaining its purpose
        
        Format your response like this:
        
        FILE: path/to/file1
        ```
        // Purpose: Brief explanation of this file's role in the project
        // content of file1
        ```
        
        FILE: path/to/file2
        ```
        // Purpose: Brief explanation of this file's role in the project
        // content of file2
        ```
        
        IMPORTANT GUIDELINES:
        - Always include a comprehensive README.md with:
          * Project description and features
          * Setup instructions (installation, configuration)
          * Usage examples with code snippets
          * API documentation if applicable
          * Contribution guidelines
        - Include appropriate configuration files (.gitignore, package.json, requirements.txt, etc.)
        - Provide complete, functional code for each file (no placeholders or TODOs)
        - For React or web projects, include necessary HTML, CSS, and JS files
        - For Python projects, include appropriate requirements.txt and setup files
        - Ensure code follows best practices and style conventions for the language
        - Add appropriate comments and documentation in the code
        - Include unit tests where appropriate
        """
        
        # Generate file contents
        with console.status("[bold green]Generating project files...", spinner="dots") as status:
            files_response = generate_with_context(file_generation_prompt, context)
            status.stop()
            
        # Parse the response to extract file paths and contents
        file_matches = re.findall(r"FILE: (.+?)\n```(?:\w+)?\n(.+?)```", files_response, re.DOTALL)
        
        if not file_matches:
            typer.echo("Error: Could not parse file generation response", err=True)
            console.print(files_response)
            raise typer.Exit(1)
        
        # Create the files with improved error handling and reporting
        console.print(Panel.fit(f"Creating {len(file_matches)} files...", title="File Creation"))
        
        created_files = []
        failed_files = []
        
        for file_path, content in file_matches:
            full_path = project_dir / file_path.strip()
            
            # Create directories if they don't exist
            try:
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write the file
                with open(full_path, "w") as f:
                    f.write(content)
                created_files.append(str(full_path))
                console.print(f"Created: [green]{file_path}[/green]")
            except Exception as e:
                failed_files.append((file_path, str(e)))
                console.print(f"Error creating {file_path}: {str(e)}", style="bold red")
        
        # Always display setup commands (but don't execute them)
        console.print("\n[bold]Setup Commands (for reference):[/bold]")
        if setup_commands and setup_commands != "Not specified":
            console.print(setup_commands)
        else:
            console.print("[italic]No setup commands specified[/italic]")
        
        # Show development recommendations
        if project_info.get("development_recommendations") != "Not specified":
            console.print("\n[bold]Development Recommendations:[/bold]")
            console.print(project_info.get("development_recommendations"))
        
        # Final success message with next steps
        if failed_files:
            console.print("\n[bold red]Warning: Some files could not be created:[/bold red]")
            for file_path, error in failed_files:
                console.print(f"  - {file_path}: {error}")
        
        console.print(Panel.fit(
            f"Project initialization complete!\n\n"
            f"Created {len(created_files)} files in {project_dir}\n\n"
            f"[bold]Next Steps:[/bold]\n"
            f"  1. cd {project_dir}\n"
            f"  2. Review the README.md for project details\n"
            f"  3. Install dependencies as mentioned in the setup commands\n"
            f"  4. Start development based on the project structure",
            title="Project Ready!",
            border_style="green"
        ))

if __name__ == "__main__":
    app()

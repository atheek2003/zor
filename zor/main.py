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
        ("help", "Display all available commands and their descriptions"),
        ("review", "Analyze the codebase and provides insights")
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
def init(prompt: str, directory: str = None, install: bool = typer.Option(True, "--install", "-i", help="Install dependencies after project creation"), run: bool = typer.Option(True, "--run", "-r", help="Run the application after setup")):
    """Create a new project based on natural language instructions and optionally install dependencies and run the app"""
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
    
    # Store the original user-specified directory
    orig_project_dir = project_dir
    
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
        8. For any framework, specify the official scaffolding command that would initialize the project
        
        Format the response as:
        
        PROJECT_TYPE: [project type]
        
        MAIN_TECHNOLOGIES: [comma-separated list of main technologies]
        
        ARCHITECTURE: [Brief description of recommended architecture]
        
        SCAFFOLD_COMMAND: [Official scaffolding command if applicable, or NONE if not applicable]
        
        SCAFFOLD_TYPE: [One of: CREATES_OWN_DIR, NEEDS_EMPTY_DIR, IN_PLACE, or NONE. Indicates how the scaffolding tool behaves]
        
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
        
        For SCAFFOLD_COMMAND, provide the exact command that should be run to initialize the project with the official tooling.
        Examples:
        - For React: npx create-react-app my-app
        - For Vue: npm init vue@latest my-app
        - For Angular: ng new my-app
        - For Next.js: npx create-next-app my-app
        - For Express: npx express-generator my-app
        - For Django: django-admin startproject myproject
        - For Spring Boot: spring init --dependencies=web,data-jpa my-project
        - For Flutter: flutter create my_app
        - For Rails: rails new my_app
        - For .NET Core: dotnet new webapp -o MyApp
        - For Gatsby: npx gatsby new my-site
        - For Svelte: npm create svelte@latest my-app
        - For Electron: npx create-electron-app my-app
        - For NestJS: nest new my-nest-app
        - For Laravel: composer create-project laravel/laravel my-app
        
        For SCAFFOLD_TYPE, specify how the scaffold command behaves:
        - CREATES_OWN_DIR: The command creates its own directory (like create-react-app my-app)
        - NEEDS_EMPTY_DIR: The command needs to be run inside an empty directory
        - IN_PLACE: The command adds files to the current directory structure
        - NONE: No scaffolding command is needed or available
        """
        
        status.update("[bold green]Generating project blueprint...")
        plan_response = generate_with_context(planning_prompt, context)
        
        # Parse the response to extract project information
        import re
        import shlex
        import subprocess
        import sys
        import os
        import shutil
        
        # Extract all sections with improved regex patterns
        sections = {
            "project_type": re.search(r"PROJECT_TYPE:\s*(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:)", plan_response + "\n\n", re.DOTALL),
            "main_technologies": re.search(r"MAIN_TECHNOLOGIES:\s*(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:)", plan_response + "\n\n", re.DOTALL),
            "architecture": re.search(r"ARCHITECTURE:\s*(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:)", plan_response + "\n\n", re.DOTALL),
            "scaffold_command": re.search(r"SCAFFOLD_COMMAND:\s*(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:)", plan_response + "\n\n", re.DOTALL),
            "scaffold_type": re.search(r"SCAFFOLD_TYPE:\s*(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:)", plan_response + "\n\n", re.DOTALL),
            "dependencies": re.search(r"DEPENDENCIES:(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:)", plan_response + "\n\n", re.DOTALL),
            "setup_commands": re.search(r"SETUP_COMMANDS:(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:)", plan_response + "\n\n", re.DOTALL),
            "development_recommendations": re.search(r"DEVELOPMENT_RECOMMENDATIONS:(.*?)(?:\n\s*\n|\n\s*[A-Z_]+:|$)", plan_response + "\n\n", re.DOTALL)
        }
        
        # Process extracted sections
        project_info = {}
        for key, match in sections.items():
            project_info[key] = match.group(1).strip() if match else "Not specified"
        
        # Get project information with fallbacks
        project_type = project_info.get("project_type", "Unknown")
        setup_commands = project_info.get("setup_commands", "")
        scaffold_command = project_info.get("scaffold_command", "NONE")
        scaffold_type = project_info.get("scaffold_type", "NONE").upper()
        
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
        
        # Check if we need to run a scaffold command
        if scaffold_command and scaffold_command.lower() != "none":
            # Parse the original scaffold command
            command_parts = shlex.split(scaffold_command)
            project_name = project_dir.name
            
            # Handle different scaffold types properly
            if scaffold_type == "CREATES_OWN_DIR":
                # --------------------------------------
                # KEY FIX: Handle directory creation for tools like create-react-app
                # --------------------------------------
                
                if "create-react-app" in scaffold_command:
                    # For create-react-app, the format is: npx create-react-app project-name
                    scaffold_command = f"npx create-react-app {project_name}"
                elif "vue@latest" in scaffold_command:
                    # For Vue: npm init vue@latest project-name
                    scaffold_command = f"npm init vue@latest {project_name}"
                elif "ng new" in scaffold_command:
                    # For Angular: ng new project-name
                    scaffold_command = f"ng new {project_name}"
                elif "create-next-app" in scaffold_command:
                    # For Next.js: npx create-next-app project-name
                    scaffold_command = f"npx create-next-app {project_name}"
                else:
                    # Default behavior for other commands
                    has_project_arg = False
                    project_name_position = -1
                    for i, part in enumerate(command_parts[1:], 1):  # Skip the executable
                        if not part.startswith("-") and "/" not in part and "=" not in part:
                            has_project_arg = True
                            project_name_position = i
                            break

                    if has_project_arg:
                        original_name = command_parts[project_name_position]
                        command_parts[project_name_position] = project_name
                        scaffold_command = " ".join(command_parts)
                    else:
                        scaffold_command = f"{scaffold_command} {project_name}"
                
                
                # For CREATES_OWN_DIR, we'll now:
                # 1. First remove the target directory if it exists
                # 2. Then execute the scaffold command from the parent directory
                # 3. Later verify the directory was created where we expected
                
                # Check if we need to remove the existing directory
                if project_dir.exists():
                    if any(project_dir.iterdir()):
                        if typer.confirm(f"Directory {project_dir} exists. Remove it for clean scaffolding?", default=False):
                            try:
                                shutil.rmtree(project_dir)
                                console.print(f"[bold]Removed existing directory: {project_dir}[/bold]")
                            except Exception as e:
                                console.print(f"[bold red]Error removing directory: {str(e)}[/bold red]")
                                if not typer.confirm("Continue anyway?", default=False):
                                    typer.echo("Project initialization cancelled.")
                                    raise typer.Exit()
                    else:
                        # If directory exists but is empty, remove it anyway for clean scaffolding
                        try:
                            project_dir.rmdir()
                            console.print(f"[bold]Removed empty directory: {project_dir}[/bold]")
                        except Exception as e:
                            console.print(f"[bold yellow]Could not remove empty directory: {str(e)}[/bold yellow]")
                
                # The working directory will be the parent directory
                working_dir = project_dir.parent
                
            elif scaffold_type == "NEEDS_EMPTY_DIR":
                # For NEEDS_EMPTY_DIR, we'll run inside the project directory but ensure it's empty
                if any(project_dir.iterdir()):
                    if typer.confirm(f"Directory {project_dir} is not empty. Clear it for scaffolding?", default=False):
                        try:
                            # Remove all contents but keep the directory
                            for item in project_dir.iterdir():
                                if item.is_dir():
                                    shutil.rmtree(item)
                                else:
                                    item.unlink()
                            console.print(f"[bold]Cleared directory contents: {project_dir}[/bold]")
                        except Exception as e:
                            console.print(f"[bold red]Error clearing directory: {str(e)}[/bold red]")
                            if not typer.confirm("Continue anyway?", default=False):
                                typer.echo("Project initialization cancelled.")
                                raise typer.Exit()
                
                # Check if the command has a project name and remove it if needed
                for i, part in enumerate(command_parts[1:], 1):
                    if not part.startswith("-") and "/" not in part and "=" not in part:
                        # Remove the project name since we're running in the directory already
                        command_parts.pop(i)
                        scaffold_command = " ".join(command_parts)
                        break
                
                working_dir = project_dir
                
            else:  # IN_PLACE or default
                # For IN_PLACE, we'll just run in the directory
                working_dir = project_dir
            
            # If command has placeholders, replace them
            if "{project_name}" in scaffold_command:
                scaffold_command = scaffold_command.replace("{project_name}", project_name)
            if "{project_dir}" in scaffold_command:
                scaffold_command = scaffold_command.replace("{project_dir}", str(project_dir))
            
            # Ask user permission to run the scaffold command
            console.print(f"\n[bold]Official scaffolding command detected:[/bold]")
            console.print(f"[green]{scaffold_command}[/green]")
            console.print(f"Scaffold type: [cyan]{scaffold_type}[/cyan]")
            console.print(f"Will execute in: [cyan]{working_dir}[/cyan]")
            
            if typer.confirm("\nRun this scaffolding command?", default=True):
                console.print("\n[bold green]Executing scaffolding command...[/bold green]")
                
                try:
                    # Handle platform-specific command execution
                    shell = False
                    if sys.platform == "win32":
                        shell = True
                        # On Windows, use shell=True for npm/npx commands
                        process = subprocess.run(
                            scaffold_command,
                            cwd=working_dir,
                            capture_output=True,
                            text=True,
                            shell=shell
                        )
                    else:
                        # Split the command properly using shlex for Unix-like systems
                        command_args = shlex.split(scaffold_command)
                        process = subprocess.run(
                            command_args,
                            cwd=working_dir,
                            capture_output=True,
                            text=True,
                            shell=shell
                        )
                    
                    if process.returncode == 0:
                        console.print(f"[bold green]Scaffolding completed successfully![/bold green]")
                        console.print(process.stdout)
                    else:
                        console.print(f"[bold red]Scaffolding command failed with code {process.returncode}[/bold red]")
                        console.print(f"Error: {process.stderr}")
                        
                        # Ask if user wants to continue with file generation even though scaffolding failed
                        if not typer.confirm("Continue with file generation anyway?", default=False):
                            typer.echo("Project initialization cancelled.")
                            raise typer.Exit()
                except Exception as e:
                    console.print(f"[bold red]Error executing scaffolding command: {str(e)}[/bold red]")
                    
                    # Ask if user wants to continue with file generation despite the error
                    if not typer.confirm("Continue with file generation anyway?", default=False):
                        typer.echo("Project initialization cancelled.")
                        raise typer.Exit()
                
                # Handle directory verification and cleanup after scaffolding
                if scaffold_type == "CREATES_OWN_DIR":
                    # Check if the expected directory was created
                    if project_dir.exists():
                        console.print(f"[bold green]Project directory created successfully at: {project_dir}[/bold green]")
                    else:
                        # Check common variations of the project directory name
                        potential_dirs = [
                            working_dir / project_name.lower(),
                            working_dir / project_name.replace("-", "_"),
                            working_dir / project_name.replace("_", "-")
                        ]
                        
                        found_dir = None
                        for potential_dir in potential_dirs:
                            if potential_dir.exists() and potential_dir != project_dir:
                                found_dir = potential_dir
                                break
                        
                        if found_dir:
                            console.print(f"[bold yellow]Project was created at: {found_dir}[/bold yellow]")
                            
                            # Three options: move files, rename directory, or use the new dir
                            console.print("\nOptions:")
                            console.print(f"1. Move files from {found_dir} to {project_dir}")
                            console.print(f"2. Use {found_dir} as the project directory")
                            console.print(f"3. Cancel project creation")
                            
                            choice = typer.prompt("Choose option", type=int, default=1)
                            
                            if choice == 1:
                                # Create the target directory if it doesn't exist
                                project_dir.mkdir(exist_ok=True, parents=True)
                                
                                # Move all contents from found_dir to project_dir
                                try:
                                    # Copy all files and subdirectories
                                    for item in found_dir.iterdir():
                                        if item.is_dir():
                                            shutil.copytree(item, project_dir / item.name)
                                        else:
                                            shutil.copy2(item, project_dir / item.name)
                                    
                                    # Remove the source directory
                                    shutil.rmtree(found_dir)
                                    console.print(f"[green]Successfully moved files to {project_dir}[/green]")
                                except Exception as e:
                                    console.print(f"[bold red]Error moving files: {str(e)}[/bold red]")
                                    console.print(f"[yellow]Will continue using {found_dir} as project directory[/yellow]")
                                    project_dir = found_dir
                            elif choice == 2:
                                # Use the found directory
                                project_dir = found_dir
                                console.print(f"[green]Using {project_dir} as project directory[/green]")
                            else:
                                typer.echo("Project initialization cancelled.")
                                raise typer.Exit()
                        else:
                            console.print(f"[bold red]Expected project directory was not created at {project_dir}[/bold red]")
                            
                            # Let user specify where the project was created
                            new_dir = typer.prompt("Please enter the path where the project was created (or leave empty to cancel)")
                            
                            if new_dir:
                                potential_dir = Path(new_dir)
                                if potential_dir.exists():
                                    project_dir = potential_dir
                                    console.print(f"[green]Using {project_dir} as project directory[/green]")
                                else:
                                    console.print(f"[bold red]Directory {potential_dir} does not exist.[/bold red]")
                                    if not typer.confirm("Continue with file generation anyway?", default=False):
                                        typer.echo("Project initialization cancelled.")
                                        raise typer.Exit()
                            else:
                                typer.echo("Project initialization cancelled.")
                                raise typer.Exit()
        
        # Improved file generation prompt with more context - now considers scaffolded files
        file_generation_prompt = f"""
        Based on the project description: "{prompt}"
        
        And identified project type: {project_type}
        
        {"A scaffolding command was executed to set up the basic project structure using the official tools for this framework/language." if scaffold_command and scaffold_command.lower() != "none" else "No scaffolding command was executed. You need to provide all necessary files for a complete project."}
        
        Generate the content for {"additional" if scaffold_command and scaffold_command.lower() != "none" else ""} key files needed in the project. For each file, provide:
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
        - {"If scaffolding was executed, focus on customizing and extending the scaffolded project. Do not recreate files that are typically generated by the scaffolding tool." if scaffold_command and scaffold_command.lower() != "none" else "Provide a complete set of files for a functioning project."}
        - Always include a comprehensive README.md with:
          * Project description and features
          * Setup instructions (installation, configuration)
          * Usage examples with code snippets
          * API documentation if applicable
          * Contribution guidelines
        - Include appropriate configuration files (.gitignore, package.json, requirements.txt, etc.) if not already created by scaffolding
        - Provide complete, functional code for each file (no placeholders or TODOs)
        - Ensure code follows best practices and style conventions for the language/framework
        - Add appropriate comments and documentation in the code
        - Include unit tests where appropriate
        
        For specific frameworks, ensure you include:
        - React: Component files, styling, routing if needed
        - Angular: Modules, components, services
        - Vue: Components, views, router setup
        - Node.js: Controllers, models, routes
        - Python: Modules, packages, tests
        - Django: Models, views, templates, URLs
        - Flask: Routes, templates, forms
        - Spring Boot: Controllers, services, repositories
        - Laravel: Controllers, models, migrations, views
        - .NET: Controllers, models, views
        - Flutter: Widgets, services, state management
        """
        
        # Generate file contents
        with console.status("[bold green]Generating additional project files...", spinner="dots") as status:
            files_response = generate_with_context(file_generation_prompt, context)
            status.stop()
            
        # Parse the response to extract file paths and contents
        file_matches = re.findall(r"FILE: (.+?)\n```(?:\w+)?\n(.+?)```", files_response, re.DOTALL)
        
        if not file_matches:
            typer.echo("Error: Could not parse file generation response", err=True)
            console.print(files_response)
            raise typer.Exit(1)
        
        # Create the files with improved error handling and reporting
        console.print(Panel.fit(f"Creating {len(file_matches)} additional files...", title="File Creation"))
        
        created_files = []
        failed_files = []
        skipped_files = []
        
        for file_path, content in file_matches:
            full_path = project_dir / file_path.strip()
            
            # Check if file already exists (might have been created by scaffolding)
            if full_path.exists():
                # Ask if user wants to overwrite existing files
                if typer.confirm(f"File {file_path} already exists. Overwrite?", default=False):
                    try:
                        with open(full_path, "w") as f:
                            f.write(content)
                        created_files.append(str(full_path))
                        console.print(f"Overwritten: [blue]{file_path}[/blue]")
                    except Exception as e:
                        failed_files.append((file_path, str(e)))
                        console.print(f"Error overwriting {file_path}: {str(e)}", style="bold red")
                else:
                    console.print(f"Skipped (already exists): [yellow]{file_path}[/yellow]")
                    skipped_files.append(str(full_path))
                continue
            
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
        
        # Extract setup commands from the project info
        setup_commands_list = []
        if setup_commands and setup_commands != "Not specified":
            # Split commands by newlines and filter empty lines or comments
            setup_commands_list = [cmd.strip() for cmd in re.split(r"\n+", setup_commands.strip()) 
                                  if cmd.strip() and not cmd.strip().startswith("#")]
        
        # NEW: Enhanced command execution function that supports a queue of commands
        def execute_command_sequence(commands, working_directory, console):
            """Execute a sequence of commands, ensuring npm install commands run before start commands"""
            
            # Track the current working directory for this sequence
            current_dir = working_directory
            environment = os.environ.copy()
            success_count = 0
            failed_count = 0
            
            # Parse and clean commands from the input
            cleaned_commands = []
            for cmd in commands:
                cmd = cmd.strip()
                
                # Extract the actual command from numbered format like "1. npm install"
                if re.match(r'^\d+\.\s+', cmd):
                    cmd = re.sub(r'^\d+\.\s+', '', cmd)
                
                # Remove surrounding quotes and backticks if present
                if (cmd.startswith("'") and cmd.endswith("'")) or (cmd.startswith('"') and cmd.endswith('"')):
                    cmd = cmd[1:-1]
                
                # Remove backticks
                cmd = cmd.replace('`', '')
                
                # Remove parenthetical comments or notes - like (install dependencies)
                cmd = re.sub(r'\s*\([^)]*\)', '', cmd)
                
                # Skip empty commands
                if not cmd:
                    continue
                    
                cleaned_commands.append(cmd)
            
            # Organize commands by type
            create_app_command = None
            install_commands = []
            start_command = None
            other_commands = []
            
            for cmd in cleaned_commands:
                # Skip CD commands entirely as requested
                if cmd.startswith('cd '):
                    console.print(f"[yellow]Skipping CD command: {cmd} - already in target directory[/yellow]")
                    continue
                    
                # Handle create-react-app command (but typically skip execution)
                elif 'npx create-react-app' in cmd:
                    create_app_command = cmd
                    continue
                    
                # Handle npm/yarn install commands - prioritize these
                elif ('npm install' in cmd or 'yarn add' in cmd or 'pnpm install' in cmd):
                    install_commands.append(cmd)
                    
                # Handle start commands - these should run last
                elif ('npm start' in cmd or 'npm run start' in cmd or 'yarn start' in cmd):
                    start_command = cmd
                    
                # All other commands
                else:
                    other_commands.append(cmd)
            
            # Create the final ordered command list - installs first, then other commands, then start command
            final_commands = install_commands + other_commands
            if start_command:
                final_commands.append(start_command)
            
            # Execute commands in order
            for cmd in final_commands:
                console.print(f"\n[bold]Executing:[/bold] {cmd}")
                
                try:
                    shell = sys.platform == "win32"  # Use shell=True for Windows
                    
                    if shell:
                        process = subprocess.run(
                            cmd,
                            cwd=current_dir,
                            capture_output=True,
                            text=True,
                            shell=True,
                            env=environment
                        )
                    else:
                        # Split the command properly using shlex for Unix-like systems
                        command_args = shlex.split(cmd)
                        process = subprocess.run(
                            command_args,
                            cwd=current_dir,
                            capture_output=True,
                            text=True,
                            env=environment
                        )
                    
                    if process.returncode == 0:
                        console.print(f"[green]Command completed successfully[/green]")
                        if process.stdout:
                            console.print(process.stdout)
                        success_count += 1
                    else:
                        console.print(f"[bold red]Command failed with code {process.returncode}[/bold red]")
                        console.print(f"Error: {process.stderr}")
                        
                        # If a command fails with "module not found" or similar, try installing it
                        if "Cannot find module" in process.stderr or "not found" in process.stderr:
                            # Extract package name from error message
                            error_lines = process.stderr.splitlines()
                            for line in error_lines:
                                if "Cannot find module" in line or "not found" in line:
                                    # Try to extract package name
                                    match = re.search(r"'([^']+)'", line)
                                    if match:
                                        package_name = match.group(1)
                                        console.print(f"[yellow]Attempting to install missing package: {package_name}[/yellow]")
                                        
                                        # Try to install the missing package
                                        install_cmd = f"npm install {package_name}"
                                        console.print(f"[bold]Executing:[/bold] {install_cmd}")
                                        
                                        try:
                                            if shell:
                                                install_process = subprocess.run(
                                                    install_cmd,
                                                    cwd=current_dir,
                                                    capture_output=True,
                                                    text=True,
                                                    shell=True,
                                                    env=environment
                                                )
                                            else:
                                                install_process = subprocess.run(
                                                    shlex.split(install_cmd),
                                                    cwd=current_dir,
                                                    capture_output=True,
                                                    text=True,
                                                    env=environment
                                                )
                                            
                                            if install_process.returncode == 0:
                                                console.print(f"[green]Package {package_name} installed successfully[/green]")
                                                # Retry the original command
                                                console.print(f"[yellow]Retrying original command: {cmd}[/yellow]")
                                                if shell:
                                                    process = subprocess.run(
                                                        cmd,
                                                        cwd=current_dir,
                                                        capture_output=True,
                                                        text=True,
                                                        shell=True,
                                                        env=environment
                                                    )
                                                else:
                                                    process = subprocess.run(
                                                        shlex.split(cmd),
                                                        cwd=current_dir,
                                                        capture_output=True,
                                                        text=True,
                                                        env=environment
                                                    )
                                                
                                                if process.returncode == 0:
                                                    console.print(f"[green]Command completed successfully after installing dependencies[/green]")
                                                    success_count += 1
                                                    continue
                                            else:
                                                console.print(f"[bold red]Failed to install package {package_name}[/bold red]")
                                        except Exception as e:
                                            console.print(f"[bold red]Error installing package: {str(e)}[/bold red]")
                        
                        failed_count += 1
                        
                        # Ask to continue or abort
                        if not typer.confirm("Command failed. Continue with next command?", default=True):
                            break
                except Exception as e:
                    console.print(f"[bold red]Error executing command: {str(e)}[/bold red]")
                    failed_count += 1
                    
                    # Ask to continue or abort
                    if not typer.confirm("Error occurred. Continue with next command?", default=True):
                        break
            
            return success_count, failed_count
        
        # Detect package manager and dependencies
        package_manager = "npm"  # Default to npm
        
        # Try to detect the right package manager
        if (project_dir / "yarn.lock").exists():
            package_manager = "yarn"
        elif (project_dir / "pnpm-lock.yaml").exists():
            package_manager = "pnpm"
        elif (project_dir / "bun.lockb").exists():
            package_manager = "bun"
        
        # Determine if this is a Node.js or other type of project
        is_node_project = (project_dir / "package.json").exists()
        is_python_project = (project_dir / "requirements.txt").exists() or (project_dir / "setup.py").exists() or list(project_dir.glob("*.py"))
        is_ruby_project = (project_dir / "Gemfile").exists()
        is_java_project = (project_dir / "pom.xml").exists() or (project_dir / "build.gradle").exists()
        is_dotnet_project = list(project_dir.glob("*.csproj")) or list(project_dir.glob("*.fsproj"))
        is_php_project = (project_dir / "composer.json").exists()
        is_flutter_project = (project_dir / "pubspec.yaml").exists()
        
        # Determine install and run commands based on project type
        install_commands = []
        run_commands = []
        
        # If setup commands were provided in the project plan, use those first
        if setup_commands_list:
            # Look for commands that appear to be installation commands
            install_patterns = ["install", "restore", "update", "bundle", "composer", "pip", "npm i", "yarn"]
            for cmd in setup_commands_list:
                # Check if this looks like an install command
                if any(pattern in cmd.lower() for pattern in install_patterns):
                    install_commands.append(cmd)
                    setup_commands_list.remove(cmd)
                    break
        
        # If no install commands were found in setup_commands, generate based on project type
        if not install_commands:
            if is_node_project:
                # For Node.js projects
                install_commands.append(f"{package_manager} install")
            elif is_python_project:
                # For Python projects
                if (project_dir / "requirements.txt").exists():
                    install_commands.append("pip install -r requirements.txt")
                elif (project_dir / "setup.py").exists():
                    install_commands.append("pip install -e .")
                else:
                    # Look for any Pipfile as an alternative
                    if (project_dir / "Pipfile").exists():
                        install_commands.append("pipenv install")
            elif is_ruby_project:
                install_commands.append("bundle install")
            elif is_java_project:
                if (project_dir / "pom.xml").exists():
                    install_commands.append("mvn install")
                else:
                    install_commands.append("gradle build")
            elif is_dotnet_project:
                install_commands.append("dotnet restore")
            elif is_php_project:
                install_commands.append("composer install")
            elif is_flutter_project:
                install_commands.append("flutter pub get")
        
        # Determine run commands if needed
        if run and not run_commands:
            if is_node_project:
                # Check package.json for scripts
                try:
                    import json
                    package_json_path = project_dir / "package.json"
                    if package_json_path.exists():
                        with open(package_json_path, 'r') as f:
                            package_data = json.load(f)
                            scripts = package_data.get('scripts', {})
                            
                            # Priority order for scripts
                            for script_name in ['dev', 'start', 'serve', 'develop']:
                                if script_name in scripts:
                                    run_commands.append(f"{package_manager} run {script_name}")
                                    break
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not parse package.json: {str(e)}[/yellow]")
            elif is_python_project:
                # Try to detect Flask, Django, or FastAPI apps
                if list(project_dir.glob("**/manage.py")):
                    run_commands.append("python manage.py runserver")
                elif list(project_dir.glob("**/app.py")) or list(project_dir.glob("**/main.py")):
                    main_file = next(project_dir.glob("**/app.py"), None) or next(project_dir.glob("**/main.py"), None)
                    if main_file:
                        run_commands.append(f"python {main_file.relative_to(project_dir)}")
            elif is_ruby_project:
                if (project_dir / "config.ru").exists() or (project_dir / "config" / "application.rb").exists():
                    run_commands.append("rails server")
            elif is_dotnet_project:
                run_commands.append("dotnet run")
            elif is_flutter_project:
                run_commands.append("flutter run")
        
        # Add any remaining setup commands to the execution queue
        execution_queue = []
        if install and install_commands:
            execution_queue.extend(install_commands)
        
        # Add remaining setup commands
        if setup_commands_list:
            execution_queue.extend(setup_commands_list)
        
        # Add run commands at the end
        if run and run_commands:
            execution_queue.extend(run_commands)
        
        # Execute all queued commands if there are any
        if execution_queue:
            console.print(Panel.fit("Executing Setup Commands", title="Setup"))
            
            for i, cmd in enumerate(execution_queue):
                console.print(f"\n[bold cyan]Command {i+1}/{len(execution_queue)}:[/bold cyan] {cmd}")
            
            # Ask user permission before running commands
            if typer.confirm("\nRun these setup commands?", default=True):
                success_count, failed_count = execute_command_sequence(execution_queue, project_dir, console)
                
                if failed_count > 0:
                    console.print(f"\n[bold yellow]Command execution completed with {failed_count} errors[/bold yellow]")
                else:
                    console.print("\n[bold green]All commands executed successfully![/bold green]")
            else:
                console.print("\n[yellow]Setup commands skipped[/yellow]")
        
        # Final project summary
        console.print(Panel.fit(f"Project setup complete: {project_dir}", title="Success"))
        
        console.print(f"\n[bold green]Project Files:[/bold green]")
        console.print(f"Created {len(created_files)} files, Skipped {len(skipped_files)} files, Failed {len(failed_files)} files")
        
        # Instructions for next steps
        console.print("\n[bold]Next Steps:[/bold]")
        console.print(f"1. Navigate to the project directory: cd {project_dir}")
        
        if not execution_queue or not install:
            if install_commands:
                console.print(f"2. Install dependencies: {install_commands[0]}")
        
        if not execution_queue or not run:
            if run_commands:
                console.print(f"3. Run the application: {run_commands[0]}")
        
        # Record any warnings or errors for future reference
        if failed_files:
            console.print("\n[bold red]Warning: Some files could not be created:[/bold red]")
            for file_path, error in failed_files:
                console.print(f"- {file_path}: {error}")
        
        # Final message
        if not execution_queue or (failed_count > 0 and success_count == 0):
            console.print("\n[bold yellow]Note: Setup commands were not fully executed. You may need to run them manually.[/bold yellow]")
        
        # Create a project report
        try:
            report_path = project_dir / "claude_project_report.md"
            with open(report_path, "w") as f:
                f.write(f"# Project Setup Report\n\n")
                f.write(f"## Project Description\n\n{prompt}\n\n")
                f.write(f"## Project Type\n\n{project_type}\n\n")
                f.write(f"## Project Blueprint\n\n{plan_response}\n\n")
                f.write(f"## Files Created\n\n")
                for file in created_files:
                    f.write(f"- {file}\n")
                if skipped_files:
                    f.write(f"\n## Files Skipped\n\n")
                    for file in skipped_files:
                        f.write(f"- {file}\n")
                if failed_files:
                    f.write(f"\n## Files Failed\n\n")
                    for file_path, error in failed_files:
                        f.write(f"- {file_path}: {error}\n")
                if execution_queue:
                    f.write(f"\n## Setup Commands\n\n")
                    for cmd in execution_queue:
                        f.write(f"- `{cmd}`\n")
            console.print(f"\n[green]Project report created at: {report_path}[/green]")
        except Exception as e:
            console.print(f"[yellow]Could not create project report: {str(e)}[/yellow]")

@app.command()
@require_api_key
def review(
    threshold: int = typer.Option(5, "--threshold", "-t", help="Minimum severity score (1-10)"),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text, json, or markdown"),
):
    """Identify and quantify technical debt in the project"""
    # Show a simple progress message
    print("Analyzing codebase for technical debt...", flush=True)
    
    # Get codebase context
    context = get_codebase_context()
    
    # Improved prompt with clearer instructions
    prompt = f"""
    Analyze the codebase for technical debt. Identify issues like:
    
    1. Code duplication
    2. Overly complex functions (high cyclomatic complexity)
    3. Outdated dependencies or patterns
    4. Poor error handling
    5. Lack of tests
    6. Hard-coded values
    7. Poor documentation
    
    For each issue:
    - Rate its severity on a scale of 1-10 (where 10 is critical)
    - Identify affected files/areas with specific line numbers when possible
    - Provide specific refactoring suggestions with code examples
    - Explain why this is a problem (risks and consequences)
    
    Group issues by category and order by severity (highest first).
    Only include issues with severity >= {threshold}.
    
    At the end, include a summary with:
    1. Total number of issues found by category
    2. Top 3 most critical issues to fix first
    3. Quick wins (issues that are easy to fix but have high impact)
    
    Return in {format} format with clear headings and structure.
    """
    
    # Generate analysis
    try:
        print("Generating debt analysis report...")
        analysis = generate_with_context(prompt, context)
        print("\n" + "="*50 + " TECHNICAL DEBT REPORT " + "="*50 + "\n")
        print(analysis)
        print("\n" + "="*120)
    except Exception as e:
        print(f"Error analyzing code: {str(e)}")
                
if __name__ == "__main__":
    app()

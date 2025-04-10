import json
import os
from pathlib import Path
import typer

# Default configuration
DEFAULT_CONFIG = {
    "model": "gemini-1.5-flash",
    "temperature": 0.2,
    "max_tokens": 8192,
    "exclude_dirs": ["node_modules", ".venv", "venv", ".git", "__pycache__", 
                    "dist", "build", ".pytest_cache", ".next"],
    "exclude_files": [".env", "*.pyc", "*.jpg", "*.png", "*.pdf"],
    "backup_files": True,
    "history_size": 10,
    "rate_limit_retries": 3,
}

def get_config_path():
    """Get path to config file, prioritizing local then global config"""
    # Check for project-specific config
    local_config = Path("./.ninjaconfig.json")
    if local_config.exists():
        return local_config
    
    # Fall back to global config
    home_dir = Path.home()
    global_config = home_dir / ".config" / "ninja" / "config.json"
    return global_config

def load_config():
    """Load configuration from file or create default if not exists"""
    config_path = get_config_path()
    
    # If config doesn't exist, create default
    if not config_path.exists():
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write default config
        with open(config_path, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        
        return DEFAULT_CONFIG
    
    # Load existing config
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            
        # Update with any missing default keys
        updated = False
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
                updated = True
        
        # Write back if updated
        if updated:
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
        
        return config
    except Exception as e:
        typer.echo(f"Error loading config: {e}. Using defaults.", err=True)
        return DEFAULT_CONFIG

def save_config(config):
    """Save configuration to file"""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    return True

# Add to open_code/main.py

@app.command()
def config(key: str = None, value: str = None):
    """View or update configuration"""
    current_config = load_config()
    
    if key is None and value is None:
        # Display current config
        for k, v in current_config.items():
            typer.echo(f"{k}: {v}")
        return
    
    if key not in current_config:
        typer.echo(f"Unknown configuration key: {key}", err=True)
        return
    
    if value is None:
        # Display specific key
        typer.echo(f"{key}: {current_config[key]}")
        return
    
    # Update config
    # Convert value to appropriate type based on current value type
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

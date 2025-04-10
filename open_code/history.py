import json
import os
from pathlib import Path
import time
from typing import List, Dict

def get_history_path():
    """Get path to history file"""
    home_dir = Path.home()
    history_dir = home_dir / ".config" / "ninja" / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir / "history.json"

def load_history(max_items=100) -> List[Dict]:
    """Load conversation history"""
    history_path = get_history_path()
    
    if not history_path.exists():
        return []
    
    try:
        with open(history_path, "r") as f:
            history = json.load(f)
        
        # Return only the most recent items
        return history[-max_items:]
    except Exception:
        return []

def save_history_item(prompt: str, response: str):
    """Save a conversation item to history"""
    history_path = get_history_path()
    
    # Load existing history
    history = load_history(max_items=1000)  # Keep more in storage than we show
    
    # Add new item
    history.append({
        "timestamp": time.time(),
        "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
        "prompt": prompt,
        "response": response
    })
    
    # Save updated history
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)

# Add to open_code/main.py

@app.command()
def history(limit: int = 5):
    """Show conversation history"""
    from rich.console import Console
    from rich.table import Table
    
    console = Console()
    history = load_history(max_items=limit)
    
    if not history:
        console.print("No history found")
        return
    
    table = Table(title="Conversation History")
    table.add_column("Date", style="cyan")
    table.add_column("Prompt", style="green")
    table.add_column("Response", style="yellow")
    
    for item in history[-limit:]:
        # Truncate long text
        prompt = item["prompt"][:50] + "..." if len(item["prompt"]) > 50 else item["prompt"]
        response = item["response"][:50] + "..." if len(item["response"]) > 50 else item["response"]
        
        table.add_row(item["datetime"], prompt, response)
    
    console.print(table)

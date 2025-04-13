import json
import os
from pathlib import Path
import time
from typing import List, Dict

def get_history_path():
    """Get path to history file"""
    home_dir = Path.home()
    history_dir = home_dir / ".config" / "zor" / "history"
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


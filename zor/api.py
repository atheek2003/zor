import time
import random
from functools import wraps
import typer
import google.generativeai as genai
from .config import load_config

class RateLimitError(Exception):
    """Exception raised when API rate limit is hit"""
    pass

def exponential_backoff(max_retries=3):
    """Decorator for exponential backoff on rate limiting"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = load_config()
            max_attempts = config.get("rate_limit_retries", max_retries)
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Check if it looks like a rate limit error
                    error_str = str(e).lower()
                    is_rate_limit = any(term in error_str for term in 
                                       ["rate limit", "quota", "too many requests"])
                    
                    if is_rate_limit and attempt < max_attempts - 1:
                        # Calculate backoff with jitter
                        backoff_time = (2 ** attempt) + random.uniform(0, 1)
                        typer.echo(f"Rate limit hit. Retrying in {backoff_time:.1f}s...")
                        time.sleep(backoff_time)
                        continue
                    else:
                        # Re-raise the exception
                        raise
        return wrapper
    return decorator

@exponential_backoff()
def generate_with_context(prompt: str, context: dict):
    """Generate a response with codebase context with rate limiting"""
    config = load_config()
    model_name = config.get("model", "gemini-2.0-flash")
    temperature = config.get("temperature", 0.2)
    
    model = genai.GenerativeModel(model_name, 
                                 generation_config={"temperature": temperature})
    
    context_str = "\n".join(f"File: {path}\n{content}" for path, content in context.items())
    full_prompt = f"Codebase Context:\n{context_str}\n\nUser Prompt: {prompt}"
    
    response = model.generate_content(full_prompt)
    
    # Save to history
    try:
        from .history import save_history_item
        save_history_item(prompt, response.text)
    except ImportError:
        pass
    
    return response.text


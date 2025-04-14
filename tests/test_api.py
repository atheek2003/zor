import pytest
from unittest.mock import patch, MagicMock
from zor.api import generate_with_context, exponential_backoff, RateLimitError

def test_exponential_backoff_decorator():
    # Test the decorator retries on rate limit errors
    mock_func = MagicMock()
    mock_func.side_effect = [Exception("rate limit exceeded"), "success"]
    
    decorated_func = exponential_backoff(max_retries=2)(mock_func)
    
    result = decorated_func()
    assert result == "success"
    assert mock_func.call_count == 2

@patch("zor.api.genai.GenerativeModel")
@patch("zor.api.load_config")
def test_generate_with_context(mock_load_config, mock_genai_model):
    # Setup
    mock_load_config.return_value = {"model": "test-model", "temperature": 0.5}
    mock_model_instance = MagicMock()
    mock_genai_model.return_value = mock_model_instance
    
    mock_response = MagicMock()
    mock_response.text = "Generated response"
    mock_model_instance.generate_content.return_value = mock_response
    
    # Test
    result = generate_with_context("Test prompt", {"file.py": "file content"})
    
    # Assert
    assert result == "Generated response"
    mock_genai_model.assert_called_once_with("test-model", generation_config={"temperature": 0.5})
    mock_model_instance.generate_content.assert_called_once()

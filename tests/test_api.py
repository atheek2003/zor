import pytest
from unittest.mock import patch, MagicMock
import time
from zor.api import generate_with_context, exponential_backoff, RateLimitError

class TestAPI:
    @patch('zor.api.genai.GenerativeModel')
    @patch('zor.api.load_config')
    def test_generate_with_context(self, mock_load_config, mock_model_class, mock_generative_model):
        # Setup
        mock_load_config.return_value = {"model": "test-model", "temperature": 0.2}
        mock_model_instance = mock_generative_model
        mock_model_class.return_value = mock_model_instance
        
        context = {"file1.py": "def test(): pass", "file2.py": "print('hello')"}
        prompt = "Generate tests for this codebase"
        
        # Test
        result = generate_with_context(prompt, context)
        
        # Assertions
        assert result == "Test response"
        mock_model_class.assert_called_once_with('test-model', generation_config={"temperature": 0.2})
        
        # Check that the context was properly formatted in the prompt
        called_prompt = mock_model_instance.generate_content.call_args[0][0]
        assert "Codebase Context:" in called_prompt
        assert "file1.py" in called_prompt
        assert "file2.py" in called_prompt
        assert "User Prompt: Generate tests for this codebase" in called_prompt

    @patch('zor.api.load_config')
    @patch('time.sleep')
    def test_exponential_backoff_decorator(self, mock_sleep, mock_load_config):
        mock_load_config.return_value = {"rate_limit_retries": 3}
        
        # Create a function that fails with rate limit error twice then succeeds
        call_count = [0]
        
        @exponential_backoff(max_retries=3)
        def test_function():
            call_count[0] += 1
            if call_count[0] <= 2:
                raise Exception("Rate limit exceeded")
            return "Success"
        
        # Test
        result = test_function()
        
        # Assertions
        assert result == "Success"
        assert call_count[0] == 3  # Function was called 3 times
        assert mock_sleep.call_count == 2  # Sleep was called twice (after first and second failures)
        
        # Check that backoff increases
        first_backoff = mock_sleep.call_args_list[0][0][0]
        second_backoff = mock_sleep.call_args_list[1][0][0]
        assert second_backoff > first_backoff  # Second backoff should be longer

    @patch('zor.api.load_config')
    @patch('time.sleep')
    def test_exponential_backoff_max_retries(self, mock_sleep, mock_load_config):
        mock_load_config.return_value = {"rate_limit_retries": 3}
        
        # Create a function that always fails with rate limit error
        @exponential_backoff(max_retries=3)
        def test_function():
            raise Exception("Rate limit exceeded")
        
        # Test
        with pytest.raises(Exception, match="Rate limit exceeded"):
            test_function()
        
        # Assertions
        assert mock_sleep.call_count == 2  # Sleep called twice (3 attempts total, but no sleep after last attempt)

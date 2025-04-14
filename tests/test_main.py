import pytest
import os
import re
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call
import typer
from typer.testing import CliRunner

from zor.main import (
    app, require_api_key, load_api_key, help, ask, edit, config,
    interactive, history, generate_test, refactor, setup,
    extract_code_blocks
)

# Setup test runner
runner = CliRunner()

@pytest.fixture
def mock_context():
    """Mock context dictionary for testing"""
    return {
        "file1.py": "def test(): pass",
        "file2.py": "# Test comment"
    }

@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    return {
        "model": "gemini-2.0-flash",
        "temperature": 0.2,
        "max_tokens": 8192,
        "exclude_dirs": ["node_modules", ".git"],
        "exclude_files": [".env"],
        "api_key": "test_key"
    }

def test_load_api_key_from_env():
    """Test loading API key from environment variable"""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test_env_key"}):
        with patch('google.generativeai.configure') as mock_configure:
            with patch('google.generativeai.GenerativeModel') as mock_model:
                mock_instance = mock_model.return_value
                mock_instance.generate_content.return_value = MagicMock()
                
                result = load_api_key()
                assert result is True
                mock_configure.assert_called_once_with(api_key="test_env_key")

def test_load_api_key_from_config():
    """Test loading API key from config file"""
    with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=True):
        with patch('zor.main.load_config', return_value={"api_key": "test_config_key"}):
            with patch('google.generativeai.configure') as mock_configure:
                with patch('google.generativeai.GenerativeModel') as mock_model:
                    mock_instance = mock_model.return_value
                    mock_instance.generate_content.return_value = MagicMock()
                    
                    result = load_api_key()
                    assert result is True
                    mock_configure.assert_called_once_with(api_key="test_config_key")

def test_load_api_key_invalid():
    """Test behavior with invalid API key"""
    with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=True):
        with patch('zor.main.load_config', return_value={"api_key": "invalid_key"}):
            with patch('google.generativeai.configure') as mock_configure:
                with patch('google.generativeai.GenerativeModel') as mock_model:
                    mock_model.side_effect = Exception("Invalid API key")
                    
                    result = load_api_key()
                    assert result is False
                    mock_configure.assert_called_once_with(api_key="invalid_key")

def test_require_api_key_decorator_valid():
    """Test require_api_key decorator with valid API key"""
    mock_func = MagicMock()
    mock_func.__name__ = "test_func"
    decorated_func = require_api_key(mock_func)
    
    with patch('zor.main.api_key_valid', True):
        decorated_func()
        mock_func.assert_called_once()

def test_require_api_key_decorator_invalid():
    """Test require_api_key decorator with invalid API key"""
    mock_func = MagicMock()
    mock_func.__name__ = "test_func"
    decorated_func = require_api_key(mock_func)
    
    with patch('zor.main.api_key_valid', False):
        with pytest.raises(typer.Exit):
            decorated_func()
        mock_func.assert_not_called()

def test_help_command():
    """Test help command output"""
    with patch('zor.main.api_key_valid', True):
        result = runner.invoke(app, ["help"])
        assert result.exit_code == 0
        assert "Available Commands" in result.stdout

@patch('zor.main.get_codebase_context')
@patch('zor.main.generate_with_context')
def test_ask_command(mock_generate, mock_get_context, mock_context):
    """Test ask command"""
    mock_get_context.return_value = mock_context
    mock_generate.return_value = "Test response"
    
    with patch('zor.main.api_key_valid', True):
        result = runner.invoke(app, ["ask", "Test prompt"])
        assert result.exit_code == 0
        assert "Test response" in result.stdout
        mock_generate.assert_called_once_with("Test prompt", mock_context)

@patch('zor.main.Path.exists')
def test_edit_command_file_not_exists(mock_exists):
    """Test edit command when file doesn't exist"""
    mock_exists.return_value = False
    
    with patch('zor.main.api_key_valid', True):
        result = runner.invoke(app, ["edit", "nonexistent.py", "Fix bug"])
        assert result.exit_code == 0
        assert "Error: File nonexistent.py does not exist" in result.stdout

@patch('zor.main.Path.exists')
@patch('builtins.open', new_callable=mock_open, read_data="original content")
@patch('zor.main.get_codebase_context')
@patch('zor.main.generate_with_context')
@patch('zor.main.show_diff')
@patch('zor.main.edit_file')
def test_edit_command_successful(mock_edit_file, mock_show_diff, mock_generate, 
                               mock_get_context, mock_open, mock_exists, mock_context):
    """Test edit command with successful edit"""
    mock_exists.return_value = True
    mock_get_context.return_value = mock_context
    mock_generate.return_value = "```python\nnew content\n```"
    mock_show_diff.return_value = True
    mock_edit_file.return_value = True
    
    with patch('zor.main.api_key_valid', True):
        with patch('typer.confirm', return_value=True):
            result = runner.invoke(app, ["edit", "test.py", "Fix bug"])
            assert result.exit_code == 0
            assert "File updated successfully" in result.stdout
            mock_edit_file.assert_called_once_with(
                "test.py", "new content\n", preview=False
            )

@patch('zor.main.load_config')
@patch('zor.main.save_config')
def test_config_command_display(mock_save_config, mock_load_config, mock_config):
    """Test config command displaying current config"""
    mock_load_config.return_value = mock_config
    
    with patch('zor.main.api_key_valid', True):
        result = runner.invoke(app, ["config"])
        assert result.exit_code == 0
        assert "model: gemini-2.0-flash" in result.stdout
        assert "temperature: 0.2" in result.stdout
        mock_save_config.assert_not_called()

@patch('zor.main.load_config')
@patch('zor.main.save_config')
def test_config_command_update(mock_save_config, mock_load_config, mock_config):
    """Test config command updating a value"""
    mock_load_config.return_value = mock_config
    
    with patch('zor.main.api_key_valid', True):
        # Test valid update
        result = runner.invoke(app, ["config", "temperature", "0.5"])
        assert result.exit_code == 0
        assert "Updated temperature to 0.5" in result.stdout
        
        # Check save_config was called with updated config
        updated_config = mock_config.copy()
        updated_config["temperature"] = 0.5
        mock_save_config.assert_called_once_with(updated_config)

def test_extract_code_blocks():
    """Test extract_code_blocks function"""
    markdown_text = "```python\ncode1\n```\n```python\ncode2\n```"
    result = extract_code_blocks(markdown_text)
    assert result == ["code1", "code2"]

@patch('zor.main.Path.exists', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data="def test(): pass")
@patch('zor.main.get_codebase_context')
@patch('zor.main.generate_with_context')
@patch('zor.main.extract_code_blocks')
@patch('zor.main.show_diff')
def test_generate_test_command(mock_show_diff, mock_extract, mock_generate, 
                            mock_get_context, mock_open, mock_exists, mock_context):
    """Test generate_test command"""
    mock_get_context.return_value = mock_context
    mock_generate.return_value = "```python\ndef test_function(): assert True\n```"
    mock_extract.return_value = ["def test_function(): assert True"]
    
    with patch('zor.main.api_key_valid', True):
        with patch('typer.confirm', return_value=True):
            result = runner.invoke(app, ["generate_test", "sample.py"])
            assert result.exit_code == 0
            mock_generate.assert_called_once()
            mock_extract.assert_called_once()
            mock_open.assert_called_with(Path("sample.py"), "w")

@patch('zor.main.load_config')
@patch('zor.main.save_config')
@patch('builtins.open', new_callable=mock_open)
@patch('google.generativeai.configure')
@patch('google.generativeai.GenerativeModel')
def test_setup_command_successful(mock_model, mock_configure, mock_open_file, 
                               mock_save_config, mock_load_config, mock_config):
    """Test setup command with successful API key validation"""
    mock_load_config.return_value = mock_config
    mock_instance = mock_model.return_value
    mock_instance.generate_content.return_value = MagicMock(text="OK")
    
    with patch('typer.prompt', return_value="new_test_key"):
        with patch('typer.confirm', return_value=True):
            result = runner.invoke(app, ["setup"])
            assert result.exit_code == 0
            updated_config = mock_config.copy()
            updated_config["api_key"] = "new_test_key"
            mock_save_config.assert_called_once_with(updated_config)
            mock_configure.assert_called_once_with(api_key="new_test_key")

import pytest
from unittest.mock import patch, MagicMock, mock_open
import typer
from typer.testing import CliRunner
from zor.main import app, load_api_key, require_api_key, ask, edit, commit, config

runner = CliRunner()

def test_load_api_key_from_env():
    with patch("os.getenv") as mock_getenv:
        mock_getenv.return_value = "test-api-key"
        with patch("google.generativeai.configure") as mock_configure:
            with patch("google.generativeai.GenerativeModel") as mock_model_class:
                mock_model = MagicMock()
                mock_model_class.return_value = mock_model
                mock_model.generate_content.return_value = MagicMock()
                
                result = load_api_key()
                
                assert result is True
                mock_configure.assert_called_once_with(api_key="test-api-key")

def test_require_api_key_decorator():
    # Test function to decorate
    def test_func():
        return "success"
    
    # Create decorated function
    decorated_func = require_api_key(test_func)
    
    # Test when API key is valid
    with patch("zor.main.api_key_valid", True):
        result = decorated_func()
        assert result == "success"
    
    # Test when API key is invalid
    with patch("zor.main.api_key_valid", False):
        with pytest.raises(typer.Exit):
            decorated_func()

@patch("zor.main.generate_with_context")
@patch("zor.main.get_codebase_context")
def test_ask_command(mock_get_context, mock_generate):
    mock_get_context.return_value = {"file.py": "content"}
    mock_generate.return_value = "Generated response"
    
    with patch("builtins.print") as mock_print:
        with patch("zor.main.api_key_valid", True):
            ask("Test prompt")
            
            mock_get_context.assert_called_once()
            mock_generate.assert_called_once_with("Test prompt", {"file.py": "content"})
            mock_print.assert_called_once_with("Generated response")

@patch("zor.main.edit_file")
@patch("zor.main.show_diff")
@patch("zor.main.generate_with_context")
@patch("zor.main.get_codebase_context")
def test_edit_command(mock_get_context, mock_generate, mock_show_diff, mock_edit_file):
    # Setup mocks
    mock_get_context.return_value = {"file.py": "content"}
    mock_generate.return_value = "```\nnew content\n```"
    mock_show_diff.return_value = True
    mock_edit_file.return_value = True
    
    with patch("builtins.open", mock_open(read_data="original content")):
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("typer.confirm") as mock_confirm:
                mock_confirm.return_value = True
                with patch("zor.main.api_key_valid", True):
                    edit("file.py", "update file")
                    
                    mock_get_context.assert_called_once()
                    mock_generate.assert_called_once()
                    mock_show_diff.assert_called_once()
                    mock_edit_file.assert_called_once()

@patch("zor.main.git_commit")
def test_commit_command(mock_git_commit):
    # Test successful commit
    mock_git_commit.return_value = True
    
    with patch("zor.main.api_key_valid", True):
        with patch("typer.echo") as mock_echo:
            commit("Test commit message")
            
            mock_git_commit.assert_called_once_with("Test commit message")
            mock_echo.assert_called_once_with("Commit created successfully")
    
    # Test failed commit
    mock_git_commit.reset_mock()
    mock_git_commit.return_value = False
    
    with patch("zor.main.api_key_valid", True):
        with patch("typer.echo") as mock_echo:
            commit("Test commit message")
            
            mock_git_commit.assert_called_once_with("Test commit message")
            mock_echo.assert_called_once_with("Commit failed", err=True)

def test_config_command_display():
    mock_config = {"model": "test-model", "api_key": "secret"}
    
    with patch("zor.main.load_config") as mock_load_config:
        mock_load_config.return_value = mock_config
        with patch("typer.echo") as mock_echo:
            config()
            
            # Should print each config item
            assert mock_echo.call_count >= 2
            
            # API key should be masked
            api_key_call = [call for call in mock_echo.call_args_list if "api_key" in call[0][0]][0]
            assert "***** (configured)" in api_key_call[0][0]

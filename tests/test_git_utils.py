import pytest
from unittest.mock import patch, MagicMock
from zor.git_utils import git_commit

class TestGitUtils:
    @patch('subprocess.run')
    def test_git_commit_success(self, mock_run):
        # Setup - both commands succeed
        mock_run.return_value = MagicMock(returncode=0)
        
        # Call the function
        result = git_commit("Test commit message")
        
        # Assertions
        assert result is True
        assert mock_run.call_count == 2
        
        # Check first call (git add)
        first_call_args = mock_run.call_args_list[0][0][0]
        assert first_call_args == ["git", "add", "."]
        
        # Check second call (git commit)
        second_call_args = mock_run.call_args_list[1][0][0]
        assert second_call_args == ["git", "commit", "-m", "Test commit message"]
        
        # Check that check=True was passed
        for call in mock_run.call_args_list:
            assert call[1]['check'] is True

    @patch('subprocess.run')
    @patch('typer.echo')
    def test_git_commit_failure(self, mock_echo, mock_run):
        # Setup - git commit command fails
        mock_run.side_effect = [
            MagicMock(returncode=0),  # First call (git add) succeeds
            subprocess.CalledProcessError(1, "git commit")  # Second call fails
        ]
        
        # Call the function
        result = git_commit("Test commit message")
        
        # Assertions
        assert result is False
        assert mock_run.call_count == 1  # Only first command was called
        
        # Check error message
        mock_echo.assert_called_once()
        assert "Git error" in mock_echo.call_args[0][0]
        assert mock_echo.call_args[1]['err'] is True

    @patch('subprocess.run')
    @patch('typer.echo')
    def test_git_add_failure(self, mock_echo, mock_run):
        # Setup - git add command fails
        mock_run.side_effect = subprocess.CalledProcessError(1, "git add")
        
        # Call the function
        result = git_commit("Test commit message")
        
        # Assertions
        assert result is False
        assert mock_run.call_count == 1  # Only first command was called
        
        # Check error message
        mock_echo.assert_called_once()
        assert "Git error" in mock_echo.call_args[0][0]
        assert mock_echo.call_args[1]['err'] is True

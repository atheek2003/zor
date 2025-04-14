import pytest
from unittest.mock import patch, MagicMock
from zor.git_utils import git_commit
import subprocess

def test_git_commit_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock()
        
        result = git_commit("Test commit message")
        
        assert result is True
        assert mock_run.call_count == 2

        mock_run.assert_any_call(["git", "add", "."], check=True)
        mock_run.assert_any_call(["git", "commit", "-m", "Test commit message"], check=True)

def test_git_commit_failure():
    with patch("subprocess.run") as mock_run:
        # Simulate a failure in the first git command
        mock_run.side_effect = subprocess.CalledProcessError(1, "git add")
        
        result = git_commit("Test commit message")
        
        assert result is False
        # Verify it only ran the first command before failing
        mock_run.assert_called_once_with(["git", "add", "."], check=True)

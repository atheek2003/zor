import pytest
from unittest.mock import patch, MagicMock
from zor.git_utils import git_commit
import subprocess
import typer

def test_git_commit_normal_success():
    with patch("subprocess.run") as mock_run:
        # Mock successful execution
        mock_run.return_value = MagicMock(returncode=0)
        
        result = git_commit("Test commit message")
        
        assert result is True
        # Verify calls
        assert mock_run.call_count == 2
        mock_run.assert_any_call(["git", "add", "."], check=True)
        mock_run.assert_any_call(["git", "commit", "-m", "Test commit message"], check=True)

def test_git_commit_with_init():
    with patch("subprocess.run") as mock_run:
        # First git add raises CalledProcessError (simulating check=True failure)
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, "git add"),
            MagicMock(returncode=0),  # git init
            MagicMock(returncode=0),  # git add after init
            MagicMock(returncode=0)   # git commit
        ]
        
        result = git_commit("Test commit message")
        
        assert result is True
        # Verify calls in order
        assert mock_run.call_count == 4
        calls = [
            (["git", "add", "."],),
            (["git", "init"],),
            (["git", "add", "."],),
            (["git", "commit", "-m", "Test commit message"],)
        ]
        for i, call in enumerate(calls):
            assert mock_run.call_args_list[i][0] == call
            assert mock_run.call_args_list[i][1] == {"check": True}

def test_git_commit_failure_after_init():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, "git add"),  # First git add
            MagicMock(returncode=0),                     # git init
            subprocess.CalledProcessError(1, "git add")  # Second git add fails
        ]
        
        with patch("typer.echo") as mock_echo:
            result = git_commit("Test commit message")
            
            assert result is False
            assert mock_run.call_count == 3
            mock_echo.assert_called_once()
            assert "Git error" in mock_echo.call_args[0][0]

def test_git_commit_init_failure():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, "git add"),  # First git add
            subprocess.CalledProcessError(1, "git init")  # git init fails
        ]
        
        with patch("typer.echo") as mock_echo:
            result = git_commit("Test commit message")
            
            assert result is False
            assert mock_run.call_count == 2
            mock_echo.assert_called_once()
            assert "Git error" in mock_echo.call_args[0][0]

def test_git_commit_general_exception():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = Exception("Something went wrong")
        
        with patch("typer.echo") as mock_echo:
            result = git_commit("Test commit message")
            
            assert result is False
            mock_run.assert_called_once_with(["git", "add", "."], check=True)
            mock_echo.assert_called_once()
            assert "Git error: Something went wrong" in mock_echo.call_args[0][0]

import pytest
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path
from zor.file_ops import show_diff, edit_file

def test_show_diff():
    # Test with changes
    with patch("rich.console.Console") as mock_console:
        console_instance = MagicMock()
        mock_console.return_value = console_instance
        
        result = show_diff("original", "modified", "test.py")
        
        assert result is True
        assert console_instance.print.call_count >= 2

    # Test without changes
    with patch("rich.console.Console") as mock_console:
        console_instance = MagicMock()
        mock_console.return_value = console_instance
        
        result = show_diff("same", "same", "test.py")
        
        assert result is False
        assert console_instance.print.call_count == 1

def test_edit_file_nonexistent():
    with patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = False
        
        result = edit_file("nonexistent.py", "new content")
        
        assert result is False

def test_edit_file_success():
    with patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = True
        
        with patch("builtins.open", mock_open(read_data="original content")):
            with patch("zor.file_ops.show_diff") as mock_show_diff:
                mock_show_diff.return_value = True
                
                result = edit_file("test.py", "new content", backup=True, preview=True)
                
                assert result is True

def test_edit_file_with_backup():
    with patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = True
        
        with patch("builtins.open", mock_open(read_data="original content")):
            with patch("zor.file_ops.show_diff") as mock_show_diff:
                mock_show_diff.return_value = True
                
                with patch("pathlib.Path.with_suffix") as mock_with_suffix:
                    backup_path = MagicMock()
                    mock_with_suffix.return_value = backup_path
                    
                    result = edit_file("test.py", "new content", backup=True, preview=False)
                    
                    assert result is True

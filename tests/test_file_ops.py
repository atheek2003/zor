import pytest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from zor.file_ops import show_diff, edit_file

class TestFileOps:
    @patch('zor.file_ops.Console')
    @patch('zor.file_ops.Syntax')
    @patch('difflib.unified_diff')
    def test_show_diff_with_changes(self, mock_unified_diff, mock_syntax, mock_console):
        # Setup
        original = "line1\nline2\nline3"
        new = "line1\nmodified\nline3"
        file_path = "test.py"
        
        # Mock the diff result
        mock_unified_diff.return_value = [
            "--- a/test.py\n",
            "+++ b/test.py\n",
            "@@ -1,3 +1,3 @@\n",
            " line1\n",
            "-line2\n",
            "+modified\n",
            " line3\n"
        ]
        
        console_instance = mock_console.return_value
        
        # Call the function
        result = show_diff(original, new, file_path)
        
        # Assertions
        assert result is True  # Changes detected
        mock_unified_diff.assert_called_once()
        mock_syntax.assert_called_once()
        assert console_instance.print.call_count == 2
        
        # Check the message printed
        first_call_args = console_instance.print.call_args_list[0][0]
        assert "Changes for test.py" in first_call_args[0]

    @patch('zor.file_ops.Console')
    @patch('difflib.unified_diff')
    def test_show_diff_no_changes(self, mock_unified_diff, mock_console):
        # Setup
        original = "line1\nline2\nline3"
        new = "line1\nline2\nline3"  # Identical
        file_path = "test.py"
        
        # Mock the diff result (empty for no changes)
        mock_unified_diff.return_value = []
        
        console_instance = mock_console.return_value
        
        # Call the function
        result = show_diff(original, new, file_path)
        
        # Assertions
        assert result is False  # No changes detected
        mock_unified_diff.assert_called_once()
        
        # Check the message printed
        console_instance.print.assert_called_once_with("\nNo changes detected.")

    @patch('zor.file_ops.show_diff')
    def test_edit_file_nonexistent(self, mock_show_diff):
        # Test with non-existent file
        with patch('pathlib.Path.exists', return_value=False):
            with patch('typer.echo') as mock_echo:
                result = edit_file("nonexistent.py", "new content")
                
                # Assertions
                assert result is False
                mock_echo.assert_called_once_with("Error: File nonexistent.py does not exist", err=True)
                mock_show_diff.assert_not_called()

    @patch('zor.file_ops.show_diff')
    def test_edit_file_preview_no_changes(self, mock_show_diff):
        # Setup
        mock_show_diff.return_value = False  # No changes detected
        
        # Test with a file that exists but has no changes
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data="original content")):
                result = edit_file("test.py", "original content", preview=True)
                
                # Assertions
                assert result is False
                mock_show_diff.assert_called_once_with("original content", "original content", "test.py")

    @patch('zor.file_ops.show_diff')
    def test_edit_file_with_backup(self, mock_show_diff):
        # Setup
        mock_show_diff.return_value = True  # Changes detected
        file_path = "test.py"
        original_content = "original content"
        new_content = "new content"
        
        # Test successful edit with backup
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=original_content)) as m:
                with patch('typer.echo') as mock_echo:
                    result = edit_file(file_path, new_content, backup=True, preview=True)
                    
                    # Assertions
                    assert result is True
                    mock_show_diff.assert_called_once_with(original_content, new_content, file_path)
                    
                    # Check backup file was created
                    m.assert_any_call("test.py.bak", "w")
                    
                    # Check original file was updated
                    m.assert_any_call(file_path, "w")
                    
                    # Check backup message
                    mock_echo.assert_called_once()
                    assert "Backup created" in mock_echo.call_args[0][0]

    @patch('zor.file_ops.show_diff')
    def test_edit_file_without_preview(self, mock_show_diff):
        # Setup
        file_path = "test.py"
        original_content = "original content"
        new_content = "new content"
        
        # Test edit without preview
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=original_content)) as m:
                result = edit_file(file_path, new_content, backup=False, preview=False)
                
                # Assertions
                assert result is True
                mock_show_diff.assert_not_called()
                
                # Check no backup was created
                assert any("test.py.bak" in str(c) for c in m.call_args_list) is False
                
                # Check original file was updated
                m.assert_called_with(file_path, "w")
                handle = m()
                handle.write.assert_called_with(new_content)

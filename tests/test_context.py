import os
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
from zor.context import get_codebase_context, is_binary_file, should_exclude_directory, should_exclude_file

class TestContext:
    def test_is_binary_file(self):
        # Test with text file
        with patch('builtins.open', mock_open(read_data="def hello():\n    return 'world'")):
            assert is_binary_file('text_file.py') is False
        
        # Test with binary file (contains null byte)
        with patch('builtins.open', mock_open(read_data=b'hello\x00world')):
            assert is_binary_file('binary_file.bin') is True
        
        # Test with file that raises on decode
        m = mock_open()
        m.return_value.read.return_value = b'\xff\xfe'  # Invalid UTF-8
        with patch('builtins.open', m):
            assert is_binary_file('invalid_utf8.txt') is True
        
        # Test with file that can't be opened
        with patch('builtins.open', side_effect=IOError):
            assert is_binary_file('nonexistent.txt') is True

    def test_should_exclude_directory(self):
        exclude_dirs = ["node_modules", "venv", ".git", "__pycache__", ".*"]
        
        assert should_exclude_directory("node_modules", exclude_dirs) is True
        assert should_exclude_directory("venv", exclude_dirs) is True
        assert should_exclude_directory(".git", exclude_dirs) is True
        assert should_exclude_directory(".hidden", exclude_dirs) is True  # Matches wildcard ".*"
        assert should_exclude_directory("src", exclude_dirs) is False
        assert should_exclude_directory("app", exclude_dirs) is False

    def test_should_exclude_file(self, temp_directory):
        exclude_files = [".env", "*.pyc", "*.png", "*.pdf"]
        exclude_extensions = [".pyc", ".png", ".pdf", ".jpg"]
        
        # Create test files in temp directory
        env_file = temp_directory / ".env"
        env_file.write_text("SECRET=test")
        
        pyc_file = temp_directory / "test.pyc"
        pyc_file.write_text("binary content")
        
        txt_file = temp_directory / "readme.txt"
        txt_file.write_text("This is a readme")
        
        # Test exclusions
        assert should_exclude_file(str(env_file), exclude_files, exclude_extensions) is True
        assert should_exclude_file(str(pyc_file), exclude_files, exclude_extensions) is True
        assert should_exclude_file(str(txt_file), exclude_files, exclude_extensions) is False
        
        # Test with binary file
        binary_file = temp_directory / "binary_file.dat"
        with open(binary_file, "wb") as f:
            f.write(b'\x00\x01\x02\x03')
        assert should_exclude_file(str(binary_file), exclude_files, exclude_extensions) is True

    @patch('zor.context.load_config')
    @patch('zor.context.should_exclude_directory')
    @patch('zor.context.should_exclude_file')
    @patch('os.walk')
    def test_get_codebase_context(self, mock_walk, mock_should_exclude_file, 
                                  mock_should_exclude_dir, mock_load_config):
        # Setup mock config
        mock_load_config.return_value = {
            "exclude_dirs": ["node_modules", ".git"],
            "exclude_files": [".env", "*.pyc"],
            "exclude_extensions": [".pyc", ".jpg"]
        }
        
        # Mock directory walking
        mock_walk.return_value = [
            ('/root', ['src', 'node_modules', '.git'], ['README.md', '.env']),
            ('/root/src', [], ['main.py', 'test.pyc']),
        ]
        
        # Mock exclusion functions
        mock_should_exclude_dir.side_effect = lambda d, _: d in ['node_modules', '.git']
        mock_should_exclude_file.side_effect = lambda f, _, __: '.env' in f or f.endswith('.pyc')
        
        # Mock file reading
        def mock_file_read(filename, *args, **kwargs):
            content_map = {
                '/root/README.md': 'Test README',
                '/root/src/main.py': 'def main():\n    print("Hello")'
            }
            m = mock_open(read_data=content_map.get(filename, ''))
            return m(filename, *args, **kwargs)
        
        # Mock file existence and size
        def mock_getsize(path):
            return 100  # Small size to ensure files are included
            
        # Apply the patches
        with patch('builtins.open', mock_file_read):
            with patch('os.path.getsize', mock_getsize):
                # Call the function
                context = get_codebase_context('/root')
                
                # Assertions
                assert len(context) == 2
                assert 'README.md' in context
                assert 'src/main.py' in context
                assert context['README.md'] == 'Test README'
                assert context['src/main.py'] == 'def main():\n    print("Hello")'
                
                # Excluded files should not be in context
                assert '.env' not in context
                assert 'src/test.pyc' not in context

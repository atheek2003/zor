import pytest
from unittest.mock import patch, mock_open, MagicMock
from zor.context import is_binary_file, should_exclude_directory, should_exclude_file, get_codebase_context

def test_is_binary_file():
    # Test binary file (contains null byte)
    with patch("builtins.open", mock_open(read_data=b"test\x00data")):
        assert is_binary_file("binary_file.bin") is True
    
    # Test text file
    with patch("builtins.open", mock_open(read_data=b"text data")):
        assert is_binary_file("text_file.txt") is False
    
    # Test file with unicode error
    with patch("builtins.open", mock_open(read_data=b"\xff\xfe")):
        assert is_binary_file("unicode_error.txt") is True

def test_should_exclude_directory():
    # Test matching pattern
    assert should_exclude_directory("node_modules", ["node_modules", "venv"]) is True
    
    # Test non-matching pattern
    assert should_exclude_directory("src", ["node_modules", "venv"]) is False
    
    # Test wildcard pattern
    assert should_exclude_directory(".git", ["node_modules", ".*"]) is True

def test_should_exclude_file():
    # Test excluded file pattern
    with patch("zor.context.is_binary_file") as mock_is_binary:
        mock_is_binary.return_value = False
        assert should_exclude_file(".env", [".env", "*.pyc"], []) is True
    
    # Test excluded extension
    with patch("zor.context.is_binary_file") as mock_is_binary:
        mock_is_binary.return_value = False
        assert should_exclude_file("image.jpg", [], [".jpg"]) is True
    
    # Test binary file
    with patch("zor.context.is_binary_file") as mock_is_binary:
        mock_is_binary.return_value = True
        assert should_exclude_file("text.txt", [], []) is True
    
    # Test included file
    with patch("zor.context.is_binary_file") as mock_is_binary:
        mock_is_binary.return_value = False
        assert should_exclude_file("file.py", [".env"], []) is False

@patch("zor.context.load_config")
@patch("zor.context.os.walk")
@patch("zor.context.os.path.getsize")
def test_get_codebase_context(mock_getsize, mock_walk, mock_load_config):
    # Setup mocks
    mock_load_config.return_value = {
        "exclude_dirs": ["node_modules", ".git"],
        "exclude_files": [".env"]
    }
    mock_walk.return_value = [
        (".", ["src", "node_modules"], ["file1.py", ".env"]),
        ("./src", [], ["file2.py"])
    ]
    mock_getsize.return_value = 100  # Small file size
    
    # Mock file open operations
    file_contents = {
        "./file1.py": "content1",
        "./src/file2.py": "content2"
    }
    
    def mock_open_file(filename, *args, **kwargs):
        mock = MagicMock()
        mock.__enter__ = lambda s: s
        mock.__exit__ = lambda *args: None
        if filename in file_contents:
            mock.read.return_value = file_contents[filename]
        return mock
    
    with patch("builtins.open", side_effect=mock_open_file):
        # Use another patch to handle should_exclude_file
        with patch("zor.context.should_exclude_file") as mock_exclude_file:
            mock_exclude_file.side_effect = lambda path, *args: path.endswith(".env")
            
            # Call the function
            context = get_codebase_context(".")
            
            # Verify result
            assert "file1.py" in context
            assert context["file1.py"] == "content1"
            assert "src/file2.py" in context
            assert context["src/file2.py"] == "content2"
            assert len(context) == 2

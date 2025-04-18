import os
import tempfile
import pytest
from unittest.mock import patch

from zor import context 

mock_config = {
    "exclude_dirs": ["exclude_this_dir"],
    "exclude_files": ["excluded_file.py", "*.png"],
    "exclude_extensions": [".jpg", ".exe"]
}

def test_is_binary_file_with_text():
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("This is a text file.")
        path = f.name
    assert context.is_binary_file(path) is False
    os.remove(path)

def test_is_binary_file_with_binary():
    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
        f.write(b'\x00\x01\x02\x03')
        path = f.name
    assert context.is_binary_file(path) is True
    os.remove(path)

def test_should_exclude_directory():
    assert context.should_exclude_directory("exclude_this_dir", ["exclude_this_dir", ".*"]) is True
    assert context.should_exclude_directory("keep_dir", ["exclude_this_dir", ".*"]) is False

def test_should_exclude_file_by_name():
    assert context.should_exclude_file("test/excluded_file.py", ["excluded_file.py"], []) is True

def test_should_exclude_file_by_extension():
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(b"This is fake image data")
        path = f.name
    assert context.should_exclude_file(path, [], [".jpg"]) is True
    os.remove(path)

def test_get_codebase_context_basic():
    with tempfile.TemporaryDirectory() as tempdir:
        included_path = os.path.join(tempdir, "include_me.py")
        with open(included_path, "w", encoding="utf-8") as f:
            f.write("print('hello world')")

        excluded_path = os.path.join(tempdir, "excluded_file.py")
        with open(excluded_path, "w", encoding="utf-8") as f:
            f.write("print('exclude me')")

        binary_path = os.path.join(tempdir, "binary_file.exe")
        with open(binary_path, "wb") as f:
            f.write(b'\x00\x01\x02\x03')

        with patch('zor.context.load_config', return_value=mock_config):
            result = context.get_codebase_context(tempdir)
            assert "include_me.py" in result
            assert "excluded_file.py" not in result
            assert "binary_file.exe" not in result


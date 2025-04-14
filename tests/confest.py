import pytest
import os
import tempfile
from pathlib import Path

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = os.getcwd()
        os.chdir(tmpdir)
        yield Path(tmpdir)
        os.chdir(original_dir)

@pytest.fixture
def test_file(temp_dir):
    """Create a test file with content"""
    file_path = temp_dir / "test_file.py"
    with open(file_path, 'w') as f:
        f.write("# Test content\ndef hello():\n    return 'world'\n")
    return file_path

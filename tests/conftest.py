import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    return {
        "model": "gemini-2.0-flash",
        "temperature": 0.2,
        "max_tokens": 8192,
        "exclude_dirs": ["node_modules", ".venv", "venv", ".git", "__pycache__"],
        "exclude_files": [".env", "*.pyc", "*.jpg", "*.png", "*.pdf"],
        "backup_files": True,
        "history_size": 10,
        "rate_limit_retries": 3,
    }

@pytest.fixture
def temp_config_file(tmp_path, mock_config):
    """Create a temporary config file for testing"""
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        json.dump(mock_config, f)
    return config_path

@pytest.fixture
def temp_directory(tmp_path):
    """Create a temporary directory structure for testing"""
    # Create some test files
    python_file = tmp_path / "test_file.py"
    python_file.write_text("def hello():\n    return 'world'")
    
    # Create a test directory with a file
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    test_file = test_dir / "nested_file.py"
    test_file.write_text("# A nested file\n")
    
    # Create some binary-like file
    binary_file = tmp_path / "binary_file.dat"
    with open(binary_file, "wb") as f:
        f.write(b'\x00\x01\x02\x03')
    
    return tmp_path

@pytest.fixture
def sample_history():
    """Sample history data for testing"""
    return [
        {
            "timestamp": 1650000000,
            "datetime": "2022-04-15 12:00:00",
            "prompt": "Test prompt 1",
            "response": "Test response 1"
        },
        {
            "timestamp": 1650001000,
            "datetime": "2022-04-15 12:16:40",
            "prompt": "Test prompt 2",
            "response": "Test response 2"
        }
    ]

@pytest.fixture
def mock_generative_model():
    """Mock for Google's GenerativeModel"""
    mock = MagicMock()
    mock.generate_content.return_value = MagicMock(text="Test response")
    return mock

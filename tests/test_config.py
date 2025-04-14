import pytest
import json
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path
from zor.config import load_config, save_config, DEFAULT_CONFIG, get_config_path

def test_get_config_path_local():
    with patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = True
        result = get_config_path()
        assert str(result).endswith(".zor_config.json")

def test_get_config_path_global():
    with patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = False
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = Path("/home/user")
            result = get_config_path()
            assert str(result).endswith(".config/zor/config.json")

def test_load_config_existing():
    mock_config = {"model": "custom-model", "temperature": 0.8}
    
    with patch("zor.config.get_config_path") as mock_path:
        mock_path.return_value = Path("config.json")
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("builtins.open", mock_open(read_data=json.dumps(mock_config))):
                config = load_config()
                
                # Should return the loaded config
                assert config["model"] == "custom-model"
                assert config["temperature"] == 0.8
                
                # Should have default values for missing keys
                for key in DEFAULT_CONFIG:
                    assert key in config

def test_load_config_create_default():
    with patch("zor.config.get_config_path") as mock_path:
        # Create a MagicMock for the Path object
        mock_path_instance = MagicMock(spec=Path)
        mock_path.return_value = mock_path_instance
        
        # Set up the exists and parent mocks
        mock_path_instance.exists.return_value = False
        mock_parent = MagicMock()
        mock_path_instance.parent = mock_parent
        
        with patch("builtins.open", mock_open()) as mock_file:
            config = load_config()

            # Should return the default config
            assert config == DEFAULT_CONFIG
            mock_parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
            mock_file.assert_called_once_with(mock_path_instance, "w")

def test_save_config():
    test_config = {"model": "test-model"}

    with patch("zor.config.get_config_path") as mock_path:
        # Create a MagicMock for the Path object
        mock_path_instance = MagicMock(spec=Path)
        mock_path.return_value = mock_path_instance
        
        # Set up the parent mock
        mock_parent = MagicMock()
        mock_path_instance.parent = mock_parent
        
        with patch("builtins.open", mock_open()) as mock_file:
            result = save_config(test_config)

            assert result is True
            mock_parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
            mock_file.assert_called_once_with(mock_path_instance, "w")

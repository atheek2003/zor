import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
from zor.config import load_config, save_config, get_config_path, DEFAULT_CONFIG

class TestConfig:
    def test_get_config_path_local(self):
        with patch('pathlib.Path.exists', return_value=True):
            config_path = get_config_path()
            assert config_path == Path('./.zor_config.json')

    @patch('pathlib.Path.home')
    def test_get_config_path_global(self, mock_home):
        mock_home.return_value = Path('/mock/home')
        
        # Patch local config to not exist
        with patch('pathlib.Path.exists', return_value=False):
            config_path = get_config_path()
            assert config_path == Path('/mock/home/.config/zor/config.json')

    @patch('zor.config.get_config_path')
    def test_load_config_new(self, mock_get_config_path, tmp_path):
        config_path = tmp_path / "new_config.json"
        mock_get_config_path.return_value = config_path
        
        # Test loading a config that doesn't exist yet
        with patch('pathlib.Path.exists', return_value=False):
            with patch('builtins.open', mock_open()) as m:
                config = load_config()
                
                # Check that the default config was returned
                assert config == DEFAULT_CONFIG
                
                # Check that the file was written
                m.assert_called_once_with(config_path, 'w')
                
                # Check write call args - should be JSON of DEFAULT_CONFIG
                handle = m()
                write_call = handle.write.call_args[0][0]
                assert json.loads(write_call) == DEFAULT_CONFIG

    @patch('zor.config.get_config_path')
    def test_load_config_existing(self, mock_get_config_path, tmp_path):
        config_path = tmp_path / "existing_config.json"
        mock_get_config_path.return_value = config_path
        
        # Create test config with some values
        test_config = {
            "model": "custom-model",
            "temperature": 0.5,
            # Missing some keys that are in DEFAULT_CONFIG
        }
        
        # Test loading an existing config
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(test_config))) as m:
                config = load_config()
                
                # Check that the values from the test config were preserved
                assert config["model"] == "custom-model"
                assert config["temperature"] == 0.5
                
                # Check that missing keys were added from DEFAULT_CONFIG
                for key in DEFAULT_CONFIG:
                    assert key in config
                
                # Check that the config was written back with the updated values
                m.assert_called_with(config_path, 'w')

    @patch('zor.config.get_config_path')
    def test_save_config(self, mock_get_config_path, tmp_path):
        config_path = tmp_path / "save_config.json"
        mock_get_config_path.return_value = config_path
        
        test_config = {
            "model": "new-model",
            "temperature": 0.7,
        }
        
        with patch('builtins.open', mock_open()) as m:
            result = save_config(test_config)
            
            # Check return value
            assert result is True
            
            # Check that file was written
            m.assert_called_once_with(config_path, 'w')
            
            # Check write call args
            handle = m()
            write_call = handle.write.call_args[0][0]
            assert json.loads(write_call) == test_config

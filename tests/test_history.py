import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
from zor.history import get_history_path, load_history, save_history_item

class TestHistory:
    @patch('pathlib.Path.home')
    def test_get_history_path(self, mock_home):
        # Setup
        mock_home.return_value = Path('/mock/home')
        
        # Test
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            result = get_history_path()
            
            # Assertions
            assert result == Path('/mock/home/.config/zor/history/history.json')
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('zor.history.get_history_path')
    def test_load_history_file_exists(self, mock_get_history_path, sample_history):
        # Setup
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_get_history_path.return_value = mock_path
        
        # Mock file read
        with patch('builtins.open', mock_open(read_data=json.dumps(sample_history))):
            # Test with default max_items
            result = load_history()
            
            # Assertions
            assert len(result) == 2
            assert result[0]['prompt'] == "Test prompt 1"
            assert result[1]['prompt'] == "Test prompt 2"
            
            # Test with custom max_items
            with patch('builtins.open', mock_open(read_data=json.dumps(sample_history))):
                result = load_history(max_items=1)
                
                # Should only return the most recent item
                assert len(result) == 1
                assert result[0]['prompt'] == "Test prompt 2"

    @patch('zor.history.get_history_path')
    def test_load_history_file_does_not_exist(self, mock_get_history_path):
        # Setup
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_get_history_path.return_value = mock_path
        
        # Test
        result = load_history()
        
        # Assertions
        assert result == []

    @patch('zor.history.get_history_path')
    def test_load_history_json_error(self, mock_get_history_path):
        # Setup
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_get_history_path.return_value = mock_path
        
        # Mock file read with invalid JSON
        with patch('builtins.open', mock_open(read_data="invalid json")):
            # Test
            result = load_history()
            
            # Assertions
            assert result == []

    @patch('zor.history.get_history_path')
    @patch('zor.history.load_history')
    @patch('time.time')
    @patch('time.strftime')
    def test_save_history_item(self, mock_strftime, mock_time, mock_load_history, mock_get_history_path):
        # Setup
        mock_time.return_value = 1650002000
        mock_strftime.return_value = "2022-04-15 12:33:20"
        mock_path = MagicMock()
        mock_get_history_path.return_value = mock_path
        
        # Mock existing history
        existing_history = []
        mock_load_history.return_value = existing_history
        
        # Test
        with patch('builtins.open', mock_open()) as m:
            save_history_item("New prompt", "New response")
            
            # Assertions
            mock_load_history.assert_called_once_with(max_items=1000)
            
            # Check that file was written with updated history
            m.assert_called_once_with(mock_path, 'w')
            
            # Check write call
            handle = m()
            write_call = handle.write.call_args[0][0]
            written_history = json.loads(write_call)
            
            assert len(written_history) == 1
            assert written_history[0]['timestamp'] == 1650002000
            assert written_history[0]['datetime'] == "2022-04-15 12:33:20"
            assert written_history[0]['prompt'] == "New prompt"
            assert written_history[0]['response'] == "New response"

import json
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import pytest
from zor.history import get_history_path, load_history, save_history_item

def test_get_history_path():
    with patch("pathlib.Path.home") as mock_home:
        mock_home.return_value = Path("/home/user")
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            result = get_history_path()
            assert str(result) == "/home/user/.config/zor/history/history.json"
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

def test_load_history_missing_file():
    with patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = False
        result = load_history()
        assert result == []

def test_load_history_existing_file():
    test_data = [{"prompt": "test", "response": "response"}]
    with patch("pathlib.Path.exists") as mock_exists:
        mock_exists.return_value = True
        with patch("builtins.open", mock_open(read_data=json.dumps(test_data))):
            result = load_history()
            assert result == test_data

def test_save_history_item_existing():
    existing_data = [{"prompt": "old", "response": "old"}]

    with patch("zor.history.load_history") as mock_load:
        mock_load.return_value = existing_data
        mock_file = mock_open()

        with patch("builtins.open", mock_file):
            save_history_item("new", "new")

            handle = mock_file()
            written_str = "".join(call.args[0] for call in handle.write.call_args_list)
            written_data = json.loads(written_str)

            assert len(written_data) == 2
            assert written_data[0]["prompt"] == "old"
            assert written_data[1]["prompt"] == "new"


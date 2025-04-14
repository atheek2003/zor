import pytest
from unittest.mock import patch
from zor.safety import confirm_action

def test_confirm_action_approved():
    with patch("typer.confirm") as mock_confirm:
        mock_confirm.return_value = True
        
        result = confirm_action("test action")
        
        assert result is True
        mock_confirm.assert_called_once()

def test_confirm_action_rejected():
    with patch("typer.confirm") as mock_confirm:
        mock_confirm.side_effect = Exception("Abort")
        
        with pytest.raises(Exception):
            confirm_action("test action")

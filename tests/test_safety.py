import pytest
from unittest.mock import patch
from zor.safety import confirm_action

def test_confirm_action_confirmed():
    """Test that confirm_action returns True when user confirms"""
    with patch('typer.confirm', return_value=True):
        result = confirm_action("test action")
        assert result is True

def test_confirm_action_rejected():
    """Test that confirm_action returns False when user rejects"""
    with patch('typer.confirm', side_effect=KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            confirm_action("test action")

def test_confirm_action_passes_message():
    """Test that the action description is passed to typer.confirm"""
    test_description = "dangerous operation"
    
    with patch('typer.confirm') as mock_confirm:
        mock_confirm.return_value = True
        confirm_action(test_description)
        
        # Verify the first argument contains our test description
        args, kwargs = mock_confirm.call_args
        assert test_description in args[0]
        
        # Verify that default is False and abort is True
        assert kwargs.get('default') is False
        assert kwargs.get('abort') is True

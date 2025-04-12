import typer

def confirm_action(action_description: str) -> bool:
    """Get user confirmation for potentially dangerous actions"""
    return typer.confirm(
        f"About to: {action_description}. Continue?",
        default=False,
        abort=True
    )

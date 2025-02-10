import sys
from ..logger import setup_logger

logger = setup_logger(__name__)

def prompt_continue(message: str = "Continue?") -> bool:
    """Prompt user to continue execution.
    
    Args:
        message: Message to display in prompt
    
    Returns:
        bool: True if user wants to continue, False otherwise
    """
        
    response = input(f"{message} [y/N]: ").strip().lower()
    return response in ['y', 'Y', 'yes'] 
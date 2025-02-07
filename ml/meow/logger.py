import logging
import colorlog
import sys
import os
from datetime import datetime

# Define default log level from environment
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

LOG_LEVEL_STR_MAPPING = {
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

def setup_logger(name=None):
    """Set up logger with color and timestamp formatting.
    
    Args:
        name (str): Logger name, typically __name__ from the calling module
    """
    # Create logger with module name
    logger = logging.getLogger(name if name else "meow")
    
    # Set level from environment variable
    logger.setLevel(LOG_LEVEL_STR_MAPPING.get(LOG_LEVEL, logging.INFO))
    
    # Remove existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Create color formatter with module path
    formatter = colorlog.ColoredFormatter(
        "%(asctime)s %(log_color)s%(levelname)-8s%(reset)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        reset=True,
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)    
    
    return logger

# Example usage:
if __name__ == "__main__":
    test_logger = setup_logger("test")
    test_logger.debug("Debug message")
    test_logger.info("Info message")
    test_logger.warning("Warning message")
    test_logger.error("Error message")
    test_logger.critical("Critical message")

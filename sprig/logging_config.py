import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(name="sprig"):
    """Set up logging configuration for the main application."""
    logger = logging.getLogger(name)
    if not logger.handlers:  # Only add handlers if they don't exist
        logger.setLevel(logging.DEBUG)
        
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # File handler
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'sprig.log'),
            maxBytes=1024*1024,  # 1MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Create formatter and add it to the handler
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        
        # Add the handler to the logger
        logger.addHandler(file_handler)
    
    return logger

def setup_shell_logging():
    """Set up logging configuration specifically for the shell component."""
    logger = logging.getLogger('sprig.shell')
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # File handler for shell-specific logs
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'shell.log'),
            maxBytes=1024*1024,  # 1MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Create formatter and add it to the handler
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Add the handler to the logger
        logger.addHandler(file_handler)
    
    return logger

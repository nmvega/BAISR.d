"""
BAIS Centralized Logging Module
================================
Simple, consistent logging across all modules.
NO OVER-ENGINEERING - Just clean, useful logs.

Usage:
    from utils.app_logger import get_logger
    logger = get_logger(__name__)
    logger.info("Component created successfully")
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


def setup_logger(
    name: str = 'BAIS',
    level: str = 'INFO',
    log_format: Optional[str] = None,
    log_file: Optional[Path] = None
) -> logging.Logger:
    """
    Create a simple, consistent logger for BAIS application.
    
    Args:
        name: Logger name (typically module name)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Custom log format string
        log_file: Optional file path for file logging
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Default format if not provided
    if log_format is None:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    formatter = logging.Formatter(log_format)
    
    # Console handler - always add
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.addHandler(console_handler)
    
    # File handler - optional
    if log_file:
        try:
            # Create log directory if it doesn't exist
            log_file = Path(log_file)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"Could not create file handler: {e}")
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance with BAIS configuration.
    
    Args:
        name: Logger name (typically __name__ from calling module)
        
    Returns:
        Configured logger instance
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Starting component import")
    """
    # Import config here to avoid circular dependency
    try:
        from .config import get_config
        config = get_config()
        
        # Get logging settings from config
        log_config = config.get_logging_config()
        level = log_config.get('level', 'INFO')
        log_format = log_config.get('format')
        
        # Check if file logging is enabled
        log_file = None
        if config.get('logging.file.enabled', False):
            log_file = config.get('logging.file.path', 'logs/bais.log')
    except ImportError:
        # Fallback if config not available
        level = 'INFO'
        log_format = None
        log_file = None
    
    # Use calling module name if provided, otherwise use BAIS
    logger_name = name if name else 'BAIS'
    
    return setup_logger(
        name=logger_name,
        level=level,
        log_format=log_format,
        log_file=log_file
    )


class LoggerMixin:
    """
    Mixin class to add logging capability to any class.
    Simple pattern for consistent logging across classes.
    
    Usage:
        class MyClass(LoggerMixin):
            def my_method(self):
                self.logger.info("Doing something")
    """
    
    @property
    def logger(self) -> logging.Logger:
        """
        Get logger instance for this class.
        
        Returns:
            Logger named after the class
        """
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger


def log_execution_time(func):
    """
    Simple decorator to log function execution time.
    Useful for performance monitoring without complexity.
    
    Usage:
        @log_execution_time
        def slow_function():
            time.sleep(1)
    """
    import functools
    import time
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.debug(f"{func.__name__} completed in {elapsed:.2f} seconds")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"{func.__name__} failed after {elapsed:.2f} seconds: {e}")
            raise
    
    return wrapper


def log_database_operation(operation: str, schema: str = None):
    """
    Log database operations with consistent format.
    
    Args:
        operation: Description of the operation
        schema: Optional schema name
        
    Example:
        >>> log_database_operation("INSERT component", "live")
    """
    logger = get_logger('BAIS.Database')
    
    if schema:
        logger.info(f"[{schema}] {operation}")
    else:
        logger.info(f"{operation}")


def log_auth_event(event: str, username: str = None, success: bool = True):
    """
    Log authentication events with consistent format.
    
    Args:
        event: Type of auth event (login, logout, etc.)
        username: User involved in the event
        success: Whether the event was successful
        
    Example:
        >>> log_auth_event("login", "admin@prutech.com", True)
    """
    logger = get_logger('BAIS.Auth')
    
    level = logging.INFO if success else logging.WARNING
    status = "SUCCESS" if success else "FAILED"
    
    if username:
        logger.log(level, f"{event.upper()} {status}: {username}")
    else:
        logger.log(level, f"{event.upper()} {status}")


# Global logger instance for module-level logging
logger = get_logger('BAIS')

# Convenience functions for module-level logging
def debug(msg: str, *args, **kwargs):
    """Module-level debug logging."""
    logger.debug(msg, *args, **kwargs)

def info(msg: str, *args, **kwargs):
    """Module-level info logging."""
    logger.info(msg, *args, **kwargs)

def warning(msg: str, *args, **kwargs):
    """Module-level warning logging."""
    logger.warning(msg, *args, **kwargs)

def error(msg: str, *args, **kwargs):
    """Module-level error logging."""
    logger.error(msg, *args, **kwargs)

def critical(msg: str, *args, **kwargs):
    """Module-level critical logging."""
    logger.critical(msg, *args, **kwargs)
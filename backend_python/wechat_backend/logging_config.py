import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path


def setup_logging(log_level=None, log_file=None, max_bytes=10485760, backup_count=5):
    """
    Setup logging configuration for the application
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional, defaults to logs/app.log)
        max_bytes: Maximum size of log file before rotation (default 10MB)
        backup_count: Number of backup files to keep
    """
    
    # Determine log level from config or environment, default to INFO
    if log_level is None:
        log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
        
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent.parent / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # Set up log file path
    if log_file is None:
        log_file = logs_dir / 'app.log'
    else:
        log_file = Path(log_file)
        if not log_file.parent.exists():
            log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s'
    )
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation for production
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Specific loggers for different modules
    app_logger = logging.getLogger('wechat_backend')
    app_logger.setLevel(numeric_level)
    
    api_logger = logging.getLogger('wechat_backend.api')
    api_logger.setLevel(numeric_level)
    
    db_logger = logging.getLogger('wechat_backend.database')
    db_logger.setLevel(numeric_level)
    
    wechat_logger = logging.getLogger('wechat_backend.wechat')
    wechat_logger.setLevel(numeric_level)
    
    print(f"Logging initialized with level: {log_level}, file: {log_file}")
    return root_logger


def get_logger(name):
    """
    Get a named logger instance
    
    Args:
        name: Name of the logger (e.g., 'wechat_backend.api')
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Predefined loggers for common use cases
app_logger = get_logger('wechat_backend')
api_logger = get_logger('wechat_backend.api')
db_logger = get_logger('wechat_backend.database')
wechat_logger = get_logger('wechat_backend.wechat')
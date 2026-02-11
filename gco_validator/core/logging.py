"""
Logging configuration for the GEO Content Quality Validator
"""
import logging
import logging.config
import os
from gco_validator.config.settings import settings


def setup_logging():
    """Setup logging configuration"""
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(settings.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure logging
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': settings.LOG_FORMAT
            },
            'detailed': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(module)s - %(funcName)s - %(message)s'
            },
        },
        'handlers': {
            'console': {
                'level': settings.LOG_LEVEL,
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
                'stream': 'ext://sys.stdout',
            },
            'file': {
                'level': settings.LOG_LEVEL,
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'detailed',
                'filename': settings.LOG_FILE,
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
            },
        },
        'loggers': {
            '': {  # root logger
                'handlers': ['console', 'file'],
                'level': settings.LOG_LEVEL,
                'propagate': False
            },
            'gco_validator': {
                'handlers': ['console', 'file'],
                'level': settings.LOG_LEVEL,
                'propagate': False
            },
        }
    }
    
    logging.config.dictConfig(logging_config)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name"""
    return logging.getLogger(name)
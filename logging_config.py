"""
Logging configuration for the TraceTrack application.
Optimized for high-traffic environments.
"""

import logging
import logging.handlers
import os
from logging.config import dictConfig

# Base directory for log files
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')

# Create log directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

# Log file paths
ACCESS_LOG = os.path.join(LOG_DIR, 'access.log')
ERROR_LOG = os.path.join(LOG_DIR, 'error.log')
APP_LOG = os.path.join(LOG_DIR, 'app.log')

# Logging configuration dictionary
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(name)s [%(module)s:%(lineno)d]: %(message)s'
        },
        'access': {
            'format': '%(asctime)s [%(levelname)s] %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'detailed',
            'filename': APP_LOG,
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'encoding': 'utf8'
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'detailed',
            'filename': ERROR_LOG,
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'encoding': 'utf8'
        },
        'access_file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'level': 'INFO',
            'formatter': 'access',
            'filename': ACCESS_LOG,
            'when': 'midnight',
            'interval': 1,
            'backupCount': 30,
            'encoding': 'utf8'
        }
    },
    'loggers': {
        '': {  # Root logger
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': True
        },
        'gunicorn.access': {
            'handlers': ['access_file'],
            'level': 'INFO',
            'propagate': False
        },
        'gunicorn.error': {
            'handlers': ['error_file'],
            'level': 'INFO',
            'propagate': False
        },
        'werkzeug': {
            'handlers': ['console', 'access_file'],
            'level': 'WARNING',
            'propagate': False
        },
        'sqlalchemy.engine': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False
        }
    }
}

def setup_logging():
    """Configure application logging"""
    # Create logs directory if it doesn't exist
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Apply logging configuration
    dictConfig(LOGGING_CONFIG)
    
    # Log the application startup
    logger = logging.getLogger(__name__)
    logger.info("Logging configured successfully")
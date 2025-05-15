"""
Logging configuration for the TraceTrack application.
Optimized for high-traffic environments.
"""
import os
import logging
import logging.handlers
from flask import has_request_context, request


class RequestFormatter(logging.Formatter):
    """
    Formatter that adds request-specific information to logs.
    """
    def format(self, record):
        if has_request_context():
            record.url = request.url
            record.remote_addr = request.remote_addr
            record.method = request.method
            if hasattr(request, 'user_id'):
                record.user_id = request.user_id
            else:
                record.user_id = 'Anonymous'
        else:
            record.url = None
            record.remote_addr = None
            record.method = None
            record.user_id = None
            
        return super().format(record)


def setup_logging():
    """Configure application logging"""
    # Get the root logger
    logger = logging.getLogger()
    
    # Clear any existing handlers
    logger.handlers = []
    
    # Set the log level based on environment
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    logger.setLevel(getattr(logging, log_level))
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatters
    simple_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    
    # More detailed formatter for when request context is available
    detailed_formatter = RequestFormatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s | '
        'URL: %(url)s | IP: %(remote_addr)s | Method: %(method)s | User: %(user_id)s'
    )
    
    # Set formatters for handlers
    console_handler.setFormatter(simple_formatter)
    
    # Add handlers to the logger
    logger.addHandler(console_handler)
    
    # Optional file handler for permanent logging
    if os.environ.get('LOG_TO_FILE'):
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Create rotating file handler (10 MB per file, max 5 files)
        file_handler = logging.handlers.RotatingFileHandler(
            'logs/tracetrack.log',
            maxBytes=10*1024*1024,
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    
    # Set Flask app logger to use the same configuration
    app_logger = logging.getLogger('app')
    app_logger.setLevel(logging.INFO)
    
    # Configure SQLAlchemy logger to be less verbose
    sa_logger = logging.getLogger('sqlalchemy.engine')
    sa_logger.setLevel(logging.WARNING)
    
    logger.info("Logging configured successfully")
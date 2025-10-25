"""
Request ID Tracking Middleware for Distributed Tracing

This module provides middleware to track requests across the application
with unique request IDs, enabling better logging, debugging, and distributed tracing.
"""

import uuid
import logging
from flask import request, g
from functools import wraps
import time

logger = logging.getLogger(__name__)


def generate_request_id():
    """
    Generate a unique request ID for tracking.
    
    Returns:
        str: A unique request ID (UUID4)
    """
    return str(uuid.uuid4())


def get_request_id():
    """
    Get the current request ID from Flask's request context.
    
    Returns:
        str: The current request ID, or None if not set
    """
    return getattr(g, 'request_id', None)


def setup_request_tracking(app):
    """
    Set up request ID tracking middleware for the Flask application.
    
    This middleware:
    - Generates or extracts a unique request ID for each request
    - Stores it in Flask's request context (g.request_id)
    - Adds it to response headers for client tracking (even on errors)
    - Logs request start/end with timing information
    - Handles exceptions and ensures tracking on error responses
    
    Args:
        app: Flask application instance
    """
    
    @app.before_request
    def track_request_start():
        """
        Before each request:
        1. Generate or extract request ID from headers
        2. Store in Flask request context
        3. Store request start time for duration tracking
        4. Log request start
        """
        # Check if client sent a request ID (for distributed tracing)
        request_id = request.headers.get('X-Request-ID')
        
        # Generate new ID if not provided
        if not request_id:
            request_id = generate_request_id()
        
        # Store in request context for access throughout the request
        g.request_id = request_id
        g.request_start_time = time.time()
        g.request_tracked = False  # Flag to prevent duplicate logging
        
        # Log request start with request ID
        logger.info(
            f"[{request_id}] Request started: {request.method} {request.path}",
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', 'Unknown')
            }
        )
    
    @app.after_request
    def track_request_end(response):
        """
        After ALL requests (successful and errors):
        1. Add request ID to response headers
        2. Calculate request duration
        3. Log request completion with timing
        
        This runs for both successful requests and error responses,
        ensuring all responses have tracking headers.
        
        Args:
            response: Flask response object
            
        Returns:
            Flask response object with added headers
        """
        request_id = getattr(g, 'request_id', None)
        start_time = getattr(g, 'request_start_time', None)
        
        # Always add request ID header if available
        if request_id:
            response.headers['X-Request-ID'] = request_id
        
        # Calculate and add timing information
        if start_time:
            duration_ms = int((time.time() - start_time) * 1000)
            response.headers['X-Response-Time'] = f"{duration_ms}ms"
            
            # Only log if not already tracked (errors are logged via signal)
            if not getattr(g, 'request_tracked', False):
                # Log based on status code
                if response.status_code >= 500:
                    # Server errors already logged by got_request_exception
                    pass
                elif response.status_code >= 400:
                    # Client errors already logged by got_request_exception
                    pass
                else:
                    # Success - log completion
                    logger.info(
                        f"[{request_id}] Request completed: {request.method} {request.path} "
                        f"- Status: {response.status_code} - Duration: {duration_ms}ms",
                        extra={
                            'request_id': request_id,
                            'method': request.method,
                            'path': request.path,
                            'status_code': response.status_code,
                            'duration_ms': duration_ms,
                            'response_size': response.content_length
                        }
                    )
                
                # Warn on slow requests (>1 second)
                if duration_ms > 1000:
                    logger.warning(
                        f"[{request_id}] Slow request detected: {request.method} {request.path} "
                        f"took {duration_ms}ms",
                        extra={
                            'request_id': request_id,
                            'method': request.method,
                            'path': request.path,
                            'duration_ms': duration_ms,
                            'slow_request': True
                        }
                    )
                
                # Mark as tracked
                g.request_tracked = True
        
        return response
    
    @app.teardown_request
    def teardown_request_tracking(exception=None):
        """
        Always runs at the end of a request, even if an exception occurred.
        This ensures request tracking happens even on error responses.
        
        Args:
            exception: Exception that occurred during request (None if successful)
        """
        request_id = getattr(g, 'request_id', None)
        start_time = getattr(g, 'request_start_time', None)
        already_tracked = getattr(g, 'request_tracked', False)
        
        # Only log if not already tracked (prevents duplicate logs)
        if request_id and not already_tracked:
            if start_time:
                duration_ms = int((time.time() - start_time) * 1000)
                
                if exception:
                    # Log request failure with exception details
                    logger.error(
                        f"[{request_id}] Request failed: {request.method} {request.path} "
                        f"- Duration: {duration_ms}ms - Exception: {type(exception).__name__}",
                        extra={
                            'request_id': request_id,
                            'method': request.method,
                            'path': request.path,
                            'duration_ms': duration_ms,
                            'exception_type': type(exception).__name__,
                            'exception_message': str(exception)
                        },
                        exc_info=True
                    )
                else:
                    # This shouldn't normally happen (after_request should have logged)
                    # but log it anyway for safety
                    logger.info(
                        f"[{request_id}] Request ended: {request.method} {request.path} "
                        f"- Duration: {duration_ms}ms",
                        extra={
                            'request_id': request_id,
                            'method': request.method,
                            'path': request.path,
                            'duration_ms': duration_ms
                        }
                    )
    
    # Use Flask's got_request_exception signal to log all exceptions
    def log_exception_with_request_id(sender, exception, **extra):
        """
        Logs all exceptions with request ID before Flask's error handling kicks in.
        This runs before error handlers, ensuring all exceptions are logged.
        
        Args:
            sender: The application that sent the signal
            exception: The exception that was raised
        """
        from werkzeug.exceptions import HTTPException
        
        request_id = getattr(g, 'request_id', None)
        start_time = getattr(g, 'request_start_time', None)
        duration_ms = int((time.time() - start_time) * 1000) if start_time else None
        
        # Log HTTP exceptions as warnings, unexpected exceptions as errors
        if isinstance(exception, HTTPException):
            logger.warning(
                f"[{request_id}] HTTP error: {request.method} {request.path} "
                f"- Status: {exception.code} - Duration: {duration_ms}ms",
                extra={
                    'request_id': request_id,
                    'method': request.method,
                    'path': request.path,
                    'status_code': exception.code,
                    'duration_ms': duration_ms,
                    'error_message': exception.description or str(exception)
                }
            )
        else:
            logger.error(
                f"[{request_id}] Unhandled exception: {type(exception).__name__}: {str(exception)} "
                f"- Duration: {duration_ms}ms",
                extra={
                    'request_id': request_id,
                    'method': request.method,
                    'path': request.path,
                    'exception_type': type(exception).__name__,
                    'exception_message': str(exception),
                    'duration_ms': duration_ms
                },
                exc_info=True
            )
    
    # Connect the signal handler
    from flask import got_request_exception
    got_request_exception.connect(log_exception_with_request_id, app)
    
    logger.info("Request tracking middleware initialized - using got_request_exception signal for error logging")


def with_request_id(func):
    """
    Decorator to add request ID context to function execution.
    
    This decorator ensures the function has access to the current request ID
    and automatically logs function execution with the request ID.
    
    Usage:
        @with_request_id
        def process_order(order_id):
            logger.info(f"Processing order {order_id}")
            # request ID is automatically included in logs
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        request_id = get_request_id()
        
        if request_id:
            logger.debug(
                f"[{request_id}] Executing {func.__name__}",
                extra={'request_id': request_id, 'function': func.__name__}
            )
        
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            if request_id:
                logger.error(
                    f"[{request_id}] Error in {func.__name__}: {str(e)}",
                    extra={'request_id': request_id, 'function': func.__name__, 'error': str(e)},
                    exc_info=True
                )
            raise
    
    return wrapper


class RequestIDFormatter(logging.Formatter):
    """
    Custom log formatter that includes request ID in log messages.
    
    This formatter automatically adds the request ID to log records
    when available, making it easy to trace all logs related to a specific request.
    
    Usage:
        formatter = RequestIDFormatter(
            '%(asctime)s [%(request_id)s] %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
    """
    
    def format(self, record):
        """
        Format the log record with request ID if available.
        
        Args:
            record: LogRecord instance
            
        Returns:
            Formatted log string
        """
        # Add request ID to record if available
        if not hasattr(record, 'request_id'):
            record.request_id = get_request_id() or 'NO-REQUEST-ID'
        
        return super().format(record)


def get_trace_context():
    """
    Get current trace context for distributed tracing.
    
    Returns a dictionary containing request ID and timing information
    that can be passed to external services for distributed tracing.
    
    Returns:
        dict: Trace context with request_id, start_time, and headers for forwarding
    """
    request_id = get_request_id()
    start_time = getattr(g, 'request_start_time', None)
    
    return {
        'request_id': request_id,
        'start_time': start_time,
        'headers': {
            'X-Request-ID': request_id or generate_request_id(),
            'X-Correlation-ID': request_id or generate_request_id()
        }
    }


def log_with_context(message, level='info', **kwargs):
    """
    Log a message with automatic request ID context.
    
    Args:
        message: Log message
        level: Log level (debug, info, warning, error, critical)
        **kwargs: Additional context to include in the log
    """
    request_id = get_request_id()
    
    # Add request ID to extra context
    extra = kwargs.copy()
    if request_id:
        extra['request_id'] = request_id
        message = f"[{request_id}] {message}"
    
    # Get logger function based on level
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(message, extra=extra)


# Export main functions
__all__ = [
    'setup_request_tracking',
    'get_request_id',
    'generate_request_id',
    'with_request_id',
    'RequestIDFormatter',
    'get_trace_context',
    'log_with_context'
]

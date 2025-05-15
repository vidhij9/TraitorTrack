"""
Database utility functions for TraceTrack.
Providing connection pooling optimizations and database health checks.
"""
import logging
import time
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError, OperationalError, TimeoutError
from app import db

logger = logging.getLogger(__name__)

# Constants for database health checking
DEFAULT_QUERY_TIMEOUT = 10  # seconds
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 0.5  # seconds

def check_database_connection():
    """
    Check if the database connection is healthy.
    
    Returns:
        tuple: (is_connected, error_message)
    """
    try:
        # Simple, fast query to check database connectivity
        from sqlalchemy import text
        db.session.execute(text("SELECT 1")).scalar()
        return True, None
    except SQLAlchemyError as e:
        error_message = f"Database connection error: {str(e)}"
        logger.error(error_message)
        return False, error_message
    finally:
        db.session.close()

def get_connection_pool_stats():
    """
    Get statistics about the database connection pool.
    
    Returns:
        dict: Connection pool statistics
    """
    try:
        # Access the engine's pool to get statistics
        engine = db.engine
        pool = engine.pool
        return {
            'size': pool.size(),
            'checkedin': pool.checkedin(),
            'checkedout': pool.checkedout(),
            'overflow': pool.overflow(),
            'checkedout_overflow': pool.checkedout_overflow()
        }
    except Exception as e:
        logger.error(f"Error getting connection pool stats: {str(e)}")
        return {
            'error': str(e)
        }

def retry_on_db_error(max_attempts=MAX_RETRY_ATTEMPTS, delay=RETRY_DELAY):
    """
    Decorator to retry a function when a database error occurs.
    
    Args:
        max_attempts (int): Maximum number of retry attempts
        delay (float): Delay between retries in seconds
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, TimeoutError) as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"Database error, retrying ({attempt+1}/{max_attempts}): {str(e)}")
                        time.sleep(delay * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        logger.error(f"Database error, max retries reached: {str(e)}")
                        raise
            raise last_error
        return wrapper
    return decorator

def create_scoped_session():
    """
    Create a scoped session optimized for high concurrency.
    
    Returns:
        Session: SQLAlchemy session
    """
    # Create a session that's optimized for high concurrency
    return db.create_scoped_session({
        "query_cls": db.Query,
        "expire_on_commit": False,  # Prevent expired objects issues
    })

def execute_with_retry(query_func, max_attempts=MAX_RETRY_ATTEMPTS):
    """
    Execute a database query with retry logic for high concurrency.
    
    Args:
        query_func: Function that performs the query
        max_attempts: Maximum number of retry attempts
        
    Returns:
        Query result
    """
    session = create_scoped_session()
    last_error = None
    
    try:
        for attempt in range(max_attempts):
            try:
                # Execute the query function with our session
                result = query_func(session)
                
                # Detach objects from session to prevent session conflicts
                session.expunge_all()
                return result
            except (OperationalError, TimeoutError) as e:
                last_error = e
                if attempt < max_attempts - 1:
                    logger.warning(f"Database query error, retrying ({attempt+1}/{max_attempts}): {str(e)}")
                    # Rollback to release locks
                    session.rollback()
                    time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    logger.error(f"Database query error, max retries reached: {str(e)}")
                    raise
    except Exception as e:
        # Make sure to rollback on any error
        session.rollback()
        raise
    finally:
        # Always close the session to release resources
        session.close()
        
    if last_error:
        raise last_error
    return None
"""
Database Query Performance Tracker
Integrates with SQLAlchemy to track query execution times
"""

import time
import logging
from functools import wraps
from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# Global reference to performance monitor
performance_monitor = None

def init_query_tracking(db, monitor=None):
    """Initialize database query tracking with performance monitor integration"""
    global performance_monitor
    performance_monitor = monitor
    
    # Track query start times
    query_times = {}
    
    @event.listens_for(Engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Track when query starts"""
        conn.info.setdefault('query_start_time', []).append(time.perf_counter())
        
    @event.listens_for(Engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Track when query completes and record metrics"""
        total = time.perf_counter() - conn.info['query_start_time'].pop(-1)
        execution_time_ms = total * 1000
        
        # Log slow queries
        if execution_time_ms > 100:
            logger.debug(f"Slow query ({execution_time_ms:.2f}ms): {statement[:100]}")
        
        # Record to performance monitor if available
        if performance_monitor:
            try:
                performance_monitor.record_db_query(statement[:200], execution_time_ms)
            except Exception as e:
                logger.debug(f"Failed to record query metrics: {e}")
    
    logger.info("✅ Database query tracking initialized")
    
def track_db_operation(func):
    """Decorator to track database operation performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            
            # Record to performance monitor if available
            if performance_monitor and execution_time_ms > 0:
                performance_monitor.record_db_query(
                    f"{func.__name__}()", 
                    execution_time_ms
                )
            
            return result
        except Exception as e:
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Database operation {func.__name__} failed after {execution_time_ms:.2f}ms: {e}")
            raise
    
    return wrapper
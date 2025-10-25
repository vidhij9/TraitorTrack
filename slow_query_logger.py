"""
Slow Query Logger
Captures and logs slow database queries for performance analysis.
"""

import logging
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class SlowQueryLogger:
    """Tracks and logs slow database queries"""
    
    # Default slow query threshold (milliseconds)
    DEFAULT_THRESHOLD_MS = 100
    
    # Maximum number of slow queries to keep in memory
    MAX_HISTORY_SIZE = 1000
    
    def __init__(self, threshold_ms: int = DEFAULT_THRESHOLD_MS, enabled: bool = True):
        """
        Initialize slow query logger
        
        Args:
            threshold_ms: Query duration threshold in milliseconds
            enabled: Whether slow query logging is enabled
        """
        self.threshold_ms = threshold_ms
        self.enabled = enabled
        self.slow_queries = []
        self.stats = {
            'total_queries': 0,
            'slow_queries': 0,
            'total_slow_time_ms': 0,
            'slowest_query_ms': 0
        }
    
    def log_query(self, duration_ms: float, statement: str, parameters: Optional[dict] = None):
        """
        Log a slow query if it exceeds threshold
        
        Args:
            duration_ms: Query duration in milliseconds
            statement: SQL statement
            parameters: Query parameters (optional)
        """
        if not self.enabled:
            return
        
        # Update stats
        self.stats['total_queries'] += 1
        
        # Check if query is slow
        if duration_ms >= self.threshold_ms:
            self.stats['slow_queries'] += 1
            self.stats['total_slow_time_ms'] += duration_ms
            self.stats['slowest_query_ms'] = max(
                self.stats['slowest_query_ms'],
                duration_ms
            )
            
            # Create query entry
            query_entry = {
                'timestamp': datetime.now(),
                'duration_ms': round(duration_ms, 2),
                'statement': statement[:500],  # Truncate long queries
                'parameters': str(parameters)[:200] if parameters else None,
                'threshold_exceeded': duration_ms - self.threshold_ms
            }
            
            # Add to history
            self.slow_queries.append(query_entry)
            if len(self.slow_queries) > self.MAX_HISTORY_SIZE:
                self.slow_queries.pop(0)  # Remove oldest
            
            # Log the slow query
            logger.warning(
                f"SLOW QUERY ({duration_ms:.2f}ms > {self.threshold_ms}ms): "
                f"{statement[:200]}..."
            )
            
            # Log parameters if available
            if parameters:
                logger.debug(f"Query parameters: {parameters}")
    
    def get_slow_queries(self, minutes: int = 60, limit: int = 100) -> List[Dict]:
        """
        Get recent slow queries
        
        Args:
            minutes: Number of minutes of history to return
            limit: Maximum number of queries to return
            
        Returns:
            List of slow query dictionaries
        """
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        recent_queries = [
            q for q in self.slow_queries
            if q['timestamp'] >= cutoff_time
        ]
        
        # Sort by duration (slowest first) and limit
        recent_queries.sort(key=lambda x: x['duration_ms'], reverse=True)
        return recent_queries[:limit]
    
    def get_stats(self) -> Dict:
        """
        Get slow query statistics
        
        Returns:
            Dictionary with stats
        """
        avg_slow_time = (
            self.stats['total_slow_time_ms'] / self.stats['slow_queries']
            if self.stats['slow_queries'] > 0
            else 0
        )
        
        slow_query_percent = (
            (self.stats['slow_queries'] / self.stats['total_queries'] * 100)
            if self.stats['total_queries'] > 0
            else 0
        )
        
        return {
            'enabled': self.enabled,
            'threshold_ms': self.threshold_ms,
            'total_queries': self.stats['total_queries'],
            'slow_queries': self.stats['slow_queries'],
            'slow_query_percent': round(slow_query_percent, 2),
            'avg_slow_time_ms': round(avg_slow_time, 2),
            'slowest_query_ms': round(self.stats['slowest_query_ms'], 2),
            'history_size': len(self.slow_queries)
        }
    
    def reset_stats(self):
        """Reset all statistics"""
        self.stats = {
            'total_queries': 0,
            'slow_queries': 0,
            'total_slow_time_ms': 0,
            'slowest_query_ms': 0
        }
        self.slow_queries = []
        logger.info("Slow query statistics reset")


# Global logger instance
slow_query_logger: Optional[SlowQueryLogger] = None


def get_slow_query_logger() -> Optional[SlowQueryLogger]:
    """Get the global slow query logger instance"""
    return slow_query_logger


def init_slow_query_logger(
    engine: Engine,
    threshold_ms: int = SlowQueryLogger.DEFAULT_THRESHOLD_MS,
    enabled: bool = True
) -> SlowQueryLogger:
    """
    Initialize slow query logging for SQLAlchemy engine
    
    Args:
        engine: SQLAlchemy engine
        threshold_ms: Slow query threshold in milliseconds
        enabled: Whether logging is enabled
        
    Returns:
        SlowQueryLogger instance
    """
    global slow_query_logger
    
    slow_query_logger = SlowQueryLogger(threshold_ms=threshold_ms, enabled=enabled)
    
    if not enabled:
        logger.info("Slow query logging is disabled")
        return slow_query_logger
    
    # Register SQLAlchemy event listeners
    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Capture query start time"""
        conn.info.setdefault('query_start_time', []).append(time.time())
    
    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Calculate query duration and log if slow"""
        try:
            start_times = conn.info.get('query_start_time', [])
            if not start_times:
                return
            
            start_time = start_times.pop()
            duration_ms = (time.time() - start_time) * 1000
            
            # Log query with duration
            slow_query_logger.log_query(
                duration_ms=duration_ms,
                statement=statement,
                parameters=parameters
            )
        except Exception as e:
            logger.error(f"Error logging query duration: {e}")
    
    logger.info(f"Slow query logging initialized - threshold: {threshold_ms}ms")
    
    return slow_query_logger


# Helper function for analyzing slow queries
def analyze_slow_queries(minutes: int = 60) -> Dict:
    """
    Analyze recent slow queries and provide insights
    
    Args:
        minutes: Number of minutes of history to analyze
        
    Returns:
        Dictionary with analysis results
    """
    logger_inst = get_slow_query_logger()
    
    if not logger_inst or not logger_inst.enabled:
        return {
            'error': 'Slow query logging not enabled'
        }
    
    slow_queries = logger_inst.get_slow_queries(minutes=minutes)
    
    if not slow_queries:
        return {
            'status': 'healthy',
            'message': f'No slow queries in the last {minutes} minutes',
            'stats': logger_inst.get_stats()
        }
    
    # Analyze patterns
    query_patterns = {}
    for query in slow_queries:
        # Extract query type (SELECT, INSERT, UPDATE, DELETE)
        statement = query['statement'].strip().upper()
        query_type = statement.split()[0] if statement else 'UNKNOWN'
        
        if query_type not in query_patterns:
            query_patterns[query_type] = {
                'count': 0,
                'total_duration_ms': 0,
                'max_duration_ms': 0
            }
        
        query_patterns[query_type]['count'] += 1
        query_patterns[query_type]['total_duration_ms'] += query['duration_ms']
        query_patterns[query_type]['max_duration_ms'] = max(
            query_patterns[query_type]['max_duration_ms'],
            query['duration_ms']
        )
    
    # Calculate averages
    for pattern in query_patterns.values():
        pattern['avg_duration_ms'] = round(
            pattern['total_duration_ms'] / pattern['count'], 2
        )
    
    # Get top slowest queries
    top_slowest = slow_queries[:10]
    
    return {
        'status': 'needs_attention' if len(slow_queries) > 100 else 'warning',
        'message': f'Found {len(slow_queries)} slow queries in the last {minutes} minutes',
        'total_slow_queries': len(slow_queries),
        'query_patterns': query_patterns,
        'top_slowest': top_slowest,
        'stats': logger_inst.get_stats()
    }

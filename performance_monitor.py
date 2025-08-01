"""
Performance monitoring and optimization utilities
Replaces and consolidates performance-related code
"""
import time
import logging
from functools import wraps
from flask import request, g
from app_clean import db
import threading

logger = logging.getLogger(__name__)

class QueryTracker:
    """Track and optimize database queries"""
    
    def __init__(self):
        self.queries = []
        self.slow_queries = []
        self.query_count = 0
        self.total_time = 0
        self._lock = threading.Lock()
    
    def track_query(self, query, duration):
        """Track a database query"""
        with self._lock:
            self.query_count += 1
            self.total_time += duration
            
            if duration > 0.1:  # Slow query threshold: 100ms
                self.slow_queries.append({
                    'query': str(query)[:200],
                    'duration': duration,
                    'timestamp': time.time()
                })
                
                # Keep only last 100 slow queries
                if len(self.slow_queries) > 100:
                    self.slow_queries = self.slow_queries[-100:]
    
    def get_stats(self):
        """Get query statistics"""
        with self._lock:
            return {
                'total_queries': self.query_count,
                'total_time': self.total_time,
                'avg_time': self.total_time / max(self.query_count, 1),
                'slow_queries_count': len(self.slow_queries),
                'recent_slow_queries': self.slow_queries[-10:]
            }
    
    def reset(self):
        """Reset statistics"""
        with self._lock:
            self.queries.clear()
            self.slow_queries.clear()
            self.query_count = 0
            self.total_time = 0

# Global query tracker
query_tracker = QueryTracker()

def monitor_performance(f):
    """Decorator to monitor request performance"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = f(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
            
            # Log slow requests
            if duration > 1.0:  # 1 second threshold
                logger.warning(f"Slow request: {request.path} took {duration:.2f}s")
            
            # Store performance data
            g.request_duration = duration
    
    return decorated_function

def optimize_database_session():
    """Optimize database session settings for performance"""
    try:
        # Set optimal connection parameters
        db.session.execute("SET statement_timeout = '30s'")
        db.session.execute("SET lock_timeout = '10s'") 
        db.session.execute("SET idle_in_transaction_session_timeout = '1min'")
        
        # Enable query plan caching
        db.session.execute("SET plan_cache_mode = 'force_generic_plan'")
        
        logger.info("Database session optimized")
    except Exception as e:
        logger.warning(f"Database optimization failed: {e}")

def batch_insert_optimized(model_class, data_list, batch_size=1000):
    """Optimized batch insert for large datasets"""
    try:
        total_inserted = 0
        
        for i in range(0, len(data_list), batch_size):
            batch = data_list[i:i + batch_size]
            
            # Use bulk insert for better performance
            db.session.bulk_insert_mappings(model_class, batch)
            db.session.commit()
            
            total_inserted += len(batch)
            logger.info(f"Batch inserted {len(batch)} records ({total_inserted}/{len(data_list)})")
        
        return total_inserted
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Batch insert failed: {e}")
        return 0

def cleanup_old_data():
    """Clean up old data to maintain performance"""
    try:
        from datetime import datetime, timedelta
        from models import Scan
        
        # Remove scans older than 1 year
        cutoff_date = datetime.utcnow() - timedelta(days=365)
        old_scans = Scan.query.filter(Scan.timestamp < cutoff_date).count()
        
        if old_scans > 0:
            Scan.query.filter(Scan.timestamp < cutoff_date).delete()
            db.session.commit()
            logger.info(f"Cleaned up {old_scans} old scan records")
        
        return old_scans
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Data cleanup failed: {e}")
        return 0

def get_performance_report():
    """Generate comprehensive performance report"""
    try:
        query_stats = query_tracker.get_stats()
        
        # Database statistics
        db_stats = db.session.execute("""
            SELECT 
                schemaname,
                tablename,
                n_tup_ins as inserts,
                n_tup_upd as updates, 
                n_tup_del as deletes,
                n_live_tup as live_tuples,
                n_dead_tup as dead_tuples
            FROM pg_stat_user_tables 
            ORDER BY n_live_tup DESC
            LIMIT 10
        """).fetchall()
        
        return {
            'query_performance': query_stats,
            'database_tables': [
                {
                    'schema': row[0],
                    'table': row[1], 
                    'inserts': row[2],
                    'updates': row[3],
                    'deletes': row[4],
                    'live_tuples': row[5],
                    'dead_tuples': row[6]
                } for row in db_stats
            ],
            'timestamp': time.time()
        }
        
    except Exception as e:
        logger.error(f"Performance report failed: {e}")
        return {'error': str(e), 'timestamp': time.time()}
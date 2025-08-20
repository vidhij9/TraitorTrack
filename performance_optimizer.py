"""
Performance Optimization Module for TraceTrack
Provides caching, connection pooling, and query optimization
"""

import time
import hashlib
import json
from functools import wraps
from flask import g
import redis
from sqlalchemy import text

# Initialize Redis with connection pooling
redis_pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    db=0,
    max_connections=50,
    socket_keepalive=True,
    socket_keepalive_options={
        1: 1,  # TCP_KEEPIDLE
        2: 1,  # TCP_KEEPINTVL
        3: 3,  # TCP_KEEPCNT
    }
)

redis_client = redis.Redis(connection_pool=redis_pool)

def cache_key(*args, **kwargs):
    """Generate a cache key from function arguments"""
    key_data = str(args) + str(sorted(kwargs.items()))
    return hashlib.md5(key_data.encode()).hexdigest()

def cached(expire_time=300):
    """Decorator to cache function results in Redis"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key = f"cache:{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            try:
                cached_data = redis_client.get(key)
                if cached_data:
                    return json.loads(cached_data)
            except:
                pass  # Fallback to executing function
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            try:
                redis_client.setex(key, expire_time, json.dumps(result))
            except:
                pass  # Continue even if cache fails
            
            return result
        return wrapper
    return decorator

def batch_query(query_func):
    """Decorator to batch database queries"""
    @wraps(query_func)
    def wrapper(*args, **kwargs):
        if not hasattr(g, 'batch_queries'):
            g.batch_queries = []
        
        # Add query to batch
        g.batch_queries.append((query_func, args, kwargs))
        
        # Execute batch if it reaches threshold
        if len(g.batch_queries) >= 10:
            execute_batch_queries()
        
        return query_func(*args, **kwargs)
    return wrapper

def execute_batch_queries():
    """Execute all batched queries at once"""
    if hasattr(g, 'batch_queries') and g.batch_queries:
        # Process all queries
        for func, args, kwargs in g.batch_queries:
            func(*args, **kwargs)
        g.batch_queries = []

def optimize_session():
    """Optimize database session for performance"""
    from app import db
    
    # Set session options for better performance
    db.session.execute(text("SET LOCAL statement_timeout = '30s'"))
    db.session.execute(text("SET LOCAL lock_timeout = '10s'"))
    db.session.execute(text("SET LOCAL idle_in_transaction_session_timeout = '30s'"))
    
def bulk_insert(model_class, records):
    """Efficiently insert multiple records"""
    from app import db
    
    if not records:
        return
    
    # Use bulk_insert_mappings for better performance
    db.session.bulk_insert_mappings(model_class, records)
    db.session.commit()

def get_cached_user(user_id):
    """Get user data with caching"""
    key = f"user:{user_id}"
    
    # Try cache first
    try:
        cached = redis_client.get(key)
        if cached:
            return json.loads(cached)
    except:
        pass
    
    # Get from database
    from models import User
    user = User.query.get(user_id)
    if user:
        user_data = {
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'dispatch_area': user.dispatch_area
        }
        
        # Cache for 5 minutes
        try:
            redis_client.setex(key, 300, json.dumps(user_data))
        except:
            pass
        
        return user_data
    
    return None

def invalidate_cache(pattern):
    """Invalidate cache entries matching pattern"""
    try:
        for key in redis_client.scan_iter(match=pattern):
            redis_client.delete(key)
    except:
        pass

class QueryOptimizer:
    """Optimize database queries"""
    
    @staticmethod
    def get_bag_with_children(qr_id):
        """Get bag with all children in one query"""
        from models import Bag
        from sqlalchemy.orm import joinedload
        
        return Bag.query.options(
            joinedload(Bag.children)
        ).filter_by(qr_id=qr_id).first()
    
    @staticmethod
    def get_recent_scans(limit=10):
        """Get recent scans with optimized query"""
        from models import Scan
        from sqlalchemy import desc
        
        return Scan.query.order_by(
            desc(Scan.timestamp)
        ).limit(limit).all()
    
    @staticmethod
    def count_bags_by_type(type_filter=None):
        """Count bags efficiently"""
        from models import Bag
        from sqlalchemy import func
        
        query = Bag.query
        if type_filter:
            query = query.filter_by(type=type_filter)
        
        return query.with_entities(
            func.count(Bag.id)
        ).scalar()

# Response time tracking
class ResponseTimer:
    """Track and log response times"""
    
    def __init__(self):
        self.start_time = None
    
    def start(self):
        self.start_time = time.time()
    
    def stop(self, operation_name):
        if self.start_time:
            elapsed = time.time() - self.start_time
            
            # Log slow operations
            if elapsed > 2.0:
                import logging
                logging.warning(f"Slow operation: {operation_name} took {elapsed:.2f}s")
            
            # Store metrics
            try:
                redis_client.lpush(f"metrics:{operation_name}", elapsed)
                redis_client.ltrim(f"metrics:{operation_name}", 0, 100)
            except:
                pass
            
            return elapsed
        return 0

def get_performance_metrics():
    """Get performance metrics from Redis"""
    metrics = {}
    
    try:
        for key in redis_client.scan_iter(match="metrics:*"):
            operation = key.decode().replace("metrics:", "")
            times = redis_client.lrange(key, 0, -1)
            
            if times:
                float_times = [float(t) for t in times]
                metrics[operation] = {
                    'avg': sum(float_times) / len(float_times),
                    'min': min(float_times),
                    'max': max(float_times),
                    'count': len(float_times)
                }
    except:
        pass
    
    return metrics
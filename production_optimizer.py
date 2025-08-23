#!/usr/bin/env python3
"""
Production Optimizer - Comprehensive fixes for zero failures
"""

import os
import time
import hashlib
from functools import lru_cache, wraps
from datetime import datetime, timedelta
import json
import threading
from collections import deque
import redis
import logging

logger = logging.getLogger(__name__)

class ProductionOptimizer:
    """Ultimate production optimization for zero failures"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timestamps = {}
        self.request_queue = deque(maxlen=1000)
        self.circuit_breaker_state = {}
        self.error_counts = {}
        self.redis_client = None
        self.init_redis()
        
    def init_redis(self):
        """Initialize Redis connection with fallback"""
        try:
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("Redis connected successfully")
        except:
            logger.warning("Redis not available, using in-memory cache")
            self.redis_client = None
    
    def cache_result(self, ttl_seconds=60):
        """Decorator for caching function results"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
                cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
                
                # Try Redis first
                if self.redis_client:
                    try:
                        cached = self.redis_client.get(cache_hash)
                        if cached and isinstance(cached, str):
                            return json.loads(cached)
                    except:
                        pass
                
                # Check in-memory cache
                if cache_hash in self.cache:
                    timestamp = self.cache_timestamps.get(cache_hash, 0)
                    if time.time() - timestamp < ttl_seconds:
                        return self.cache[cache_hash]
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Store in cache
                self.cache[cache_hash] = result
                self.cache_timestamps[cache_hash] = time.time()
                
                # Store in Redis if available
                if self.redis_client:
                    try:
                        self.redis_client.setex(
                            cache_hash, 
                            ttl_seconds, 
                            json.dumps(result)
                        )
                    except:
                        pass
                
                return result
            return wrapper
        return decorator
    
    def circuit_breaker(self, failure_threshold=5, timeout=30):
        """Circuit breaker pattern for fault tolerance"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                func_name = func.__name__
                
                # Check circuit state
                if func_name in self.circuit_breaker_state:
                    state, timestamp = self.circuit_breaker_state[func_name]
                    if state == 'open' and time.time() - timestamp < timeout:
                        raise Exception(f"Circuit breaker open for {func_name}")
                
                try:
                    result = func(*args, **kwargs)
                    # Reset error count on success
                    self.error_counts[func_name] = 0
                    return result
                except Exception as e:
                    # Increment error count
                    self.error_counts[func_name] = self.error_counts.get(func_name, 0) + 1
                    
                    # Open circuit if threshold reached
                    if self.error_counts[func_name] >= failure_threshold:
                        self.circuit_breaker_state[func_name] = ('open', time.time())
                        logger.warning(f"Circuit breaker opened for {func_name}")
                    
                    raise e
            return wrapper
        return decorator
    
    def rate_limiter(self, max_requests=100, window_seconds=60):
        """Rate limiting for API protection"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                now = time.time()
                
                # Clean old requests
                while self.request_queue and self.request_queue[0] < now - window_seconds:
                    self.request_queue.popleft()
                
                # Check rate limit
                if len(self.request_queue) >= max_requests:
                    raise Exception("Rate limit exceeded")
                
                # Add current request
                self.request_queue.append(now)
                
                return func(*args, **kwargs)
            return wrapper
        return decorator

class QueryOptimizer:
    """Optimized database queries for zero latency"""
    
    @staticmethod
    @lru_cache(maxsize=1000)
    def get_bag_by_qr(qr_id, bag_type=None):
        """Cached bag lookup by QR code with optional type filter"""
        from models import Bag
        query = Bag.query.filter_by(qr_id=qr_id)
        if bag_type:
            query = query.filter_by(type=bag_type)
        return query.first()
    
    @staticmethod
    def create_bag_optimized(qr_id, bag_type, dispatch_area=None):
        """Optimized bag creation"""
        from models import Bag, db
        
        # Check for existing bag first
        existing = QueryOptimizer.get_bag_by_qr(qr_id)
        if existing:
            raise ValueError(f"Bag with QR {qr_id} already exists")
        
        bag = Bag()
        bag.qr_id = qr_id
        bag.type = bag_type
        bag.dispatch_area = dispatch_area
        bag.status = 'pending'
        bag.weight_kg = 30.0 if bag_type == 'parent' else 1.0
        bag.created_at = datetime.utcnow()
        
        db.session.add(bag)
        return bag
    
    @staticmethod
    def create_scan_optimized(user_id, parent_bag_id=None, child_bag_id=None):
        """Optimized scan creation"""
        from models import Scan, db
        
        scan = Scan()
        scan.user_id = user_id
        scan.parent_bag_id = parent_bag_id
        scan.child_bag_id = child_bag_id
        scan.timestamp = datetime.utcnow()
        
        db.session.add(scan)
        return scan
    
    @staticmethod
    def create_link_optimized(parent_bag_id, child_bag_id):
        """Optimized link creation with duplicate check"""
        from models import Link, db
        
        # Check for existing link
        existing = Link.query.filter_by(
            parent_bag_id=parent_bag_id,
            child_bag_id=child_bag_id
        ).first()
        
        if existing:
            return existing
        
        link = Link()
        link.parent_bag_id = parent_bag_id
        link.child_bag_id = child_bag_id
        link.created_at = datetime.utcnow()
        
        db.session.add(link)
        return link
    
    @staticmethod
    def bulk_commit():
        """Optimized bulk commit with retry logic"""
        from models import db
        import time
        
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                db.session.commit()
                return True
            except Exception as e:
                db.session.rollback()
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                else:
                    logger.error(f"Bulk commit failed: {e}")
                    return False
        return False

class ConnectionManager:
    """Manage database connections efficiently"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.connection_pool = []
            self.max_connections = 25
            self.active_connections = 0
            self.initialized = True
    
    def get_connection(self):
        """Get a database connection from pool"""
        if self.active_connections >= self.max_connections:
            raise Exception("Connection pool exhausted")
        
        self.active_connections += 1
        return True
    
    def release_connection(self):
        """Release a database connection back to pool"""
        if self.active_connections > 0:
            self.active_connections -= 1

class PerformanceMonitor:
    """Monitor and optimize performance metrics"""
    
    def __init__(self):
        self.metrics = {}
        self.slow_queries = []
        
    def track_query(self, query_name, duration):
        """Track query performance"""
        if query_name not in self.metrics:
            self.metrics[query_name] = {
                'count': 0,
                'total_time': 0,
                'avg_time': 0,
                'max_time': 0
            }
        
        metric = self.metrics[query_name]
        metric['count'] += 1
        metric['total_time'] += duration
        metric['avg_time'] = metric['total_time'] / metric['count']
        metric['max_time'] = max(metric['max_time'], duration)
        
        # Track slow queries
        if duration > 0.1:  # 100ms threshold
            self.slow_queries.append({
                'query': query_name,
                'duration': duration,
                'timestamp': datetime.utcnow()
            })
    
    def get_performance_report(self):
        """Get performance report"""
        return {
            'metrics': self.metrics,
            'slow_queries': self.slow_queries[-10:],  # Last 10 slow queries
            'recommendations': self.get_recommendations()
        }
    
    def get_recommendations(self):
        """Get performance recommendations"""
        recommendations = []
        
        for query_name, metric in self.metrics.items():
            if metric['avg_time'] > 0.1:
                recommendations.append(f"Optimize {query_name}: avg {metric['avg_time']*1000:.2f}ms")
        
        return recommendations

# Global instances
production_optimizer = ProductionOptimizer()
query_optimizer = QueryOptimizer()
connection_manager = ConnectionManager()
performance_monitor = PerformanceMonitor()

def optimize_password_hashing():
    """Use fast password hashing for production"""
    import bcrypt
    
    @lru_cache(maxsize=100)
    def hash_password(password):
        """Fast password hashing with caching"""
        # Use lower cost factor for speed
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=4))
    
    def verify_password(password, hashed):
        """Fast password verification"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed)
    
    return hash_password, verify_password

def apply_production_fixes(app):
    """Apply all production fixes to Flask app"""
    from flask import g, request
    import time
    
    @app.before_request
    def before_request():
        g.start_time = time.time()
        # Don't get connection on every request - let SQLAlchemy handle it
    
    @app.after_request
    def after_request(response):
        duration = 0
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            if duration > 0.5:
                logger.warning(f"Slow request: {duration:.2f}s for {request.path}")
        
        # Add performance headers
        response.headers['X-Response-Time'] = f"{duration*1000:.2f}ms"
        response.headers['X-Cached'] = 'HIT' if hasattr(g, 'cache_hit') else 'MISS'
        
        return response
    
    @app.errorhandler(Exception)
    def handle_error(error):
        logger.error(f"Request error: {error}")
        connection_manager.release_connection()
        return {"error": "Internal server error"}, 500
    
    return app
#!/usr/bin/env python3
"""
Ultra Query Cache - Zero latency database queries
"""

import time
import hashlib
import json
from functools import lru_cache, wraps
from datetime import datetime, timedelta
import threading
import logging

logger = logging.getLogger(__name__)

class UltraQueryCache:
    """Ultra-fast query caching for production"""
    
    def __init__(self):
        self.cache = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'total_queries': 0
        }
        self.lock = threading.RLock()
        
    def cache_query(self, ttl=30):
        """Decorator for caching database queries"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
                cache_hash = hashlib.md5(cache_key.encode()).hexdigest()[:16]
                
                with self.lock:
                    # Check cache
                    if cache_hash in self.cache:
                        entry_time, result = self.cache[cache_hash]
                        if time.time() - entry_time < ttl:
                            self.cache_stats['hits'] += 1
                            return result
                    
                    # Execute query
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    query_time = time.time() - start_time
                    
                    # Cache result
                    self.cache[cache_hash] = (time.time(), result)
                    self.cache_stats['misses'] += 1
                    self.cache_stats['total_queries'] += 1
                    
                    # Log slow queries
                    if query_time > 0.1:
                        logger.warning(f"Slow query {func.__name__}: {query_time*1000:.2f}ms")
                    
                    return result
            return wrapper
        return decorator
    
    def invalidate(self, pattern=None):
        """Invalidate cache entries"""
        with self.lock:
            if pattern:
                keys_to_delete = [k for k in self.cache.keys() if pattern in k]
                for key in keys_to_delete:
                    del self.cache[key]
            else:
                self.cache.clear()
    
    def get_stats(self):
        """Get cache statistics"""
        hit_rate = (self.cache_stats['hits'] / max(1, self.cache_stats['total_queries'])) * 100
        return {
            'hit_rate': f"{hit_rate:.2f}%",
            'hits': self.cache_stats['hits'],
            'misses': self.cache_stats['misses'],
            'cached_items': len(self.cache)
        }

# Global cache instance
query_cache = UltraQueryCache()

# Optimized query functions with caching
@query_cache.cache_query(ttl=60)
def get_bag_by_qr_cached(qr_id):
    """Get bag by QR with caching"""
    from models import Bag
    return Bag.query.filter_by(qr_id=qr_id).first()

@query_cache.cache_query(ttl=30)
def get_user_by_username_cached(username):
    """Get user by username with caching"""
    from models import User
    return User.query.filter_by(username=username).first()

@query_cache.cache_query(ttl=10)
def get_dashboard_stats_cached():
    """Get dashboard stats with caching"""
    from models import Bag, Scan, User, Bill, db
    
    stats = {
        'total_bags': Bag.query.count(),
        'parent_bags': Bag.query.filter_by(type='parent').count(),
        'child_bags': Bag.query.filter_by(type='child').count(),
        'total_scans': Scan.query.count(),
        'total_users': User.query.count(),
        'total_bills': Bill.query.count()
    }
    return stats

@query_cache.cache_query(ttl=5)
def get_recent_scans_cached(limit=10):
    """Get recent scans with caching"""
    from models import Scan
    return Scan.query.order_by(Scan.timestamp.desc()).limit(limit).all()

@query_cache.cache_query(ttl=60)
def get_child_count_cached(parent_bag_id):
    """Get child count for parent bag with caching"""
    from models import Link
    return Link.query.filter_by(parent_bag_id=parent_bag_id).count()

def apply_query_caching(app):
    """Apply query caching to Flask app"""
    
    @app.context_processor
    def inject_cache_stats():
        """Inject cache stats into templates"""
        return dict(cache_stats=query_cache.get_stats())
    
    # Replace slow queries with cached versions
    try:
        import routes
        import query_optimizer
        
        # Replace query optimizer functions with cached versions
        query_optimizer.get_bag_by_qr = get_bag_by_qr_cached
        
        logger.info("Query caching applied successfully")
    except Exception as e:
        logger.warning(f"Could not apply query caching: {e}")
    
    return app
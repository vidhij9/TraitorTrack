"""
Ultra-fast caching system for TraceTrack
Designed for 50+ concurrent users and 800,000+ bags
"""

import time
import json
import hashlib
from functools import wraps
from threading import Lock
import logging

logger = logging.getLogger(__name__)

class UltraCache:
    """High-performance in-memory cache with TTL support"""
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
        self._locks = {}
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
        self._global_lock = Lock()
    
    def _get_lock(self, key):
        """Get or create a lock for a specific key"""
        if key not in self._locks:
            with self._global_lock:
                if key not in self._locks:
                    self._locks[key] = Lock()
        return self._locks[key]
    
    def get(self, key, default=None, ttl=60):
        """Get value from cache with TTL check"""
        with self._get_lock(key):
            if key in self._cache:
                timestamp = self._timestamps.get(key, 0)
                if time.time() - timestamp < ttl:
                    self._stats['hits'] += 1
                    return self._cache[key]
                else:
                    # Expired, remove it
                    del self._cache[key]
                    del self._timestamps[key]
            
            self._stats['misses'] += 1
            return default
    
    def set(self, key, value):
        """Set value in cache"""
        with self._get_lock(key):
            self._cache[key] = value
            self._timestamps[key] = time.time()
            self._stats['sets'] += 1
    
    def delete(self, key):
        """Delete value from cache"""
        with self._get_lock(key):
            if key in self._cache:
                del self._cache[key]
                del self._timestamps[key]
                self._stats['deletes'] += 1
    
    def clear(self):
        """Clear entire cache"""
        with self._global_lock:
            self._cache.clear()
            self._timestamps.clear()
            self._locks.clear()
    
    def get_stats(self):
        """Get cache statistics"""
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'size': len(self._cache),
            'hits': self._stats['hits'],
            'misses': self._stats['misses'],
            'hit_rate': hit_rate,
            'sets': self._stats['sets'],
            'deletes': self._stats['deletes']
        }

# Global cache instance
_cache = UltraCache()

def cache_key(*args, **kwargs):
    """Generate a cache key from arguments"""
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()

def cached_result(ttl=60, key_prefix=None):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_prefix:
                cache_key_val = f"{key_prefix}:{cache_key(*args, **kwargs)}"
            else:
                cache_key_val = f"{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            result = _cache.get(cache_key_val, ttl=ttl)
            if result is not None:
                return result
            
            # Call function and cache result
            result = func(*args, **kwargs)
            _cache.set(cache_key_val, result)
            return result
        
        return wrapper
    return decorator

def invalidate_pattern(pattern):
    """Invalidate all cache keys matching a pattern"""
    keys_to_delete = []
    for key in _cache._cache.keys():
        if pattern in key:
            keys_to_delete.append(key)
    
    for key in keys_to_delete:
        _cache.delete(key)
    
    return len(keys_to_delete)

# Specific cache functions for different data types

@cached_result(ttl=300, key_prefix='user')
def get_cached_user(user_id):
    """Get cached user data"""
    from models import User
    from app_clean import db
    return db.session.query(User).filter_by(id=user_id).first()

@cached_result(ttl=600, key_prefix='bag')
def get_cached_bag(bag_id):
    """Get cached bag data"""
    from models import Bag
    from app_clean import db
    return db.session.query(Bag).filter_by(id=bag_id).first()

@cached_result(ttl=60, key_prefix='scan_count')
def get_cached_scan_count(user_id=None):
    """Get cached scan count"""
    from models import Scan
    from app_clean import db
    query = db.session.query(Scan)
    if user_id:
        query = query.filter_by(user_id=user_id)
    return query.count()

@cached_result(ttl=120, key_prefix='bill')
def get_cached_bill(bill_id):
    """Get cached bill data"""
    from models import Bill
    from app_clean import db
    return db.session.query(Bill).filter_by(id=bill_id).first()

@cached_result(ttl=30, key_prefix='stats')
def get_cached_system_stats():
    """Get cached system statistics"""
    from models import User, Bag, Scan, Bill
    from app_clean import db
    
    return {
        'total_users': db.session.query(User).count(),
        'total_bags': db.session.query(Bag).count(),
        'total_scans': db.session.query(Scan).count(),
        'total_bills': db.session.query(Bill).count()
    }

# Batch operations for better performance

def batch_cache_set(items, key_prefix=''):
    """Set multiple items in cache at once"""
    for key, value in items.items():
        full_key = f"{key_prefix}:{key}" if key_prefix else key
        _cache.set(full_key, value)

def batch_cache_get(keys, key_prefix='', ttl=60):
    """Get multiple items from cache at once"""
    results = {}
    for key in keys:
        full_key = f"{key_prefix}:{key}" if key_prefix else key
        results[key] = _cache.get(full_key, ttl=ttl)
    return results

# Query result caching

class CachedQuery:
    """Cache database query results"""
    
    @staticmethod
    @cached_result(ttl=120, key_prefix='query')
    def execute(query_string, params=None):
        """Execute and cache query results"""
        from app_clean import db
        from sqlalchemy import text
        
        result = db.session.execute(text(query_string), params or {})
        return result.fetchall()
    
    @staticmethod
    def invalidate_queries(table_name):
        """Invalidate all cached queries for a table"""
        return invalidate_pattern(f"query:*{table_name}*")

# Performance monitoring

def get_cache_performance():
    """Get cache performance metrics"""
    stats = _cache.get_stats()
    
    return {
        'cache_size': stats['size'],
        'hit_rate': f"{stats['hit_rate']:.2f}%",
        'total_hits': stats['hits'],
        'total_misses': stats['misses'],
        'total_sets': stats['sets'],
        'total_deletes': stats['deletes'],
        'performance': 'EXCELLENT' if stats['hit_rate'] > 80 else 'GOOD' if stats['hit_rate'] > 60 else 'NEEDS_IMPROVEMENT'
    }

# Clear cache on startup
def initialize_cache():
    """Initialize cache system"""
    _cache.clear()
    logger.info("Ultra-fast cache system initialized")

# Export main cache instance
cache = _cache
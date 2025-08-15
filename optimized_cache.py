"""
Optimized In-Memory Caching System for 4+ Million Bags
Simplified, fast, and efficient without Redis dependency
"""

import time
import hashlib
from functools import wraps
from threading import RLock
import logging

logger = logging.getLogger(__name__)

class OptimizedCache:
    """High-performance in-memory cache optimized for large scale"""
    
    def __init__(self):
        self.cache = {}
        self.timestamps = {}
        self.lock = RLock()
        self.max_size = 10000  # Maximum cache entries
        self.stats = {'hits': 0, 'misses': 0}
        
    def _make_key(self, prefix, *args, **kwargs):
        """Generate cache key from arguments"""
        key_str = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_str.encode()).hexdigest()[:16]
    
    def get(self, key):
        """Get value from cache with TTL check"""
        with self.lock:
            if key in self.cache:
                timestamp, ttl, value = self.cache[key]
                if time.time() - timestamp < ttl:
                    self.stats['hits'] += 1
                    return value
                else:
                    del self.cache[key]
            self.stats['misses'] += 1
            return None
    
    def set(self, key, value, ttl=60):
        """Set value in cache with TTL"""
        with self.lock:
            # Clean old entries if cache is too large
            if len(self.cache) >= self.max_size:
                self._cleanup()
            
            self.cache[key] = (time.time(), ttl, value)
    
    def _cleanup(self):
        """Remove expired entries and oldest 20% if still too large"""
        now = time.time()
        # Remove expired entries
        expired_keys = [k for k, (ts, ttl, _) in self.cache.items() if now - ts >= ttl]
        for key in expired_keys:
            del self.cache[key]
        
        # If still too large, remove oldest 20%
        if len(self.cache) >= self.max_size:
            sorted_keys = sorted(self.cache.keys(), key=lambda k: self.cache[k][0])
            remove_count = len(self.cache) // 5
            for key in sorted_keys[:remove_count]:
                del self.cache[key]
    
    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.stats = {'hits': 0, 'misses': 0}
    
    def get_stats(self):
        """Get cache statistics"""
        with self.lock:
            total = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0
            return {
                'size': len(self.cache),
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'hit_rate': f"{hit_rate:.1f}%"
            }

# Global cache instance
cache = OptimizedCache()

def cached(ttl=60, prefix='default'):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Skip caching for certain arguments
            if kwargs.get('skip_cache', False):
                return func(*args, **kwargs)
            
            cache_key = cache._make_key(f"{prefix}:{func.__name__}", *args, **kwargs)
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result, ttl)
            
            return result
        
        wrapper.clear_cache = lambda: cache.clear()
        return wrapper
    return decorator

def invalidate_cache(prefix=None):
    """Invalidate cache entries by prefix or all"""
    if prefix:
        with cache.lock:
            keys_to_delete = [k for k in cache.cache.keys() if k.startswith(prefix)]
            for key in keys_to_delete:
                del cache.cache[key]
    else:
        cache.clear()
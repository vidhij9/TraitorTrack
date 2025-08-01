"""
Optimized cache management - replaces cache_utils.py with better performance
"""
import time
import logging
from functools import wraps
from flask import request, jsonify

logger = logging.getLogger(__name__)

class OptimizedCache:
    """In-memory cache with TTL and size limits for optimal performance"""
    
    def __init__(self, max_size=1000, default_ttl=300):
        self.cache = {}
        self.timestamps = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
    
    def _is_expired(self, key):
        """Check if cache entry is expired"""
        if key not in self.timestamps:
            return True
        return time.time() - self.timestamps[key] > self.default_ttl
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.timestamps.items()
            if current_time - timestamp > self.default_ttl
        ]
        for key in expired_keys:
            self.cache.pop(key, None)
            self.timestamps.pop(key, None)
    
    def _make_room(self):
        """Remove oldest entries if cache is full"""
        if len(self.cache) >= self.max_size:
            # Remove 20% of oldest entries
            remove_count = int(self.max_size * 0.2)
            oldest_keys = sorted(self.timestamps.items(), key=lambda x: x[1])[:remove_count]
            for key, _ in oldest_keys:
                self.cache.pop(key, None)
                self.timestamps.pop(key, None)
    
    def get(self, key):
        """Get value from cache"""
        if key in self.cache and not self._is_expired(key):
            return self.cache[key]
        return None
    
    def set(self, key, value, ttl=None):
        """Set value in cache"""
        self._cleanup_expired()
        self._make_room()
        
        self.cache[key] = value
        self.timestamps[key] = time.time()
    
    def delete(self, key):
        """Delete key from cache"""
        self.cache.pop(key, None)
        self.timestamps.pop(key, None)
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()
        self.timestamps.clear()
    
    def stats(self):
        """Get cache statistics"""
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hit_ratio': getattr(self, '_hits', 0) / max(getattr(self, '_requests', 1), 1)
        }

# Global cache instance
cache = OptimizedCache()

def cached_response(timeout=300, key_func=None):
    """Decorator for caching API responses"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{f.__name__}:{request.full_path}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result:
                cache._hits = getattr(cache, '_hits', 0) + 1
                if isinstance(cached_result, dict):
                    cached_result['cached'] = True
                return cached_result
            
            # Execute function and cache result
            cache._requests = getattr(cache, '_requests', 0) + 1
            result = f(*args, **kwargs)
            
            # Cache successful responses
            if hasattr(result, 'status_code') and result.status_code == 200:
                cache.set(cache_key, result, timeout)
            elif isinstance(result, (dict, list)):
                cache.set(cache_key, result, timeout)
            
            return result
        return decorated_function
    return decorator

def invalidate_cache(pattern=None):
    """Invalidate cache entries matching pattern"""
    if pattern:
        keys_to_remove = [key for key in cache.cache.keys() if pattern in key]
        for key in keys_to_remove:
            cache.delete(key)
    else:
        cache.clear()

def cache_stats():
    """Get cache statistics"""
    return cache.stats()
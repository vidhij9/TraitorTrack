
import time
import json
from functools import wraps
import hashlib

class UltraFastCache:
    '''Ultra-fast in-memory caching for high performance'''
    
    def __init__(self):
        self.cache = {}
        self.timestamps = {}
        self.hit_count = 0
        self.miss_count = 0
    
    def get_key(self, prefix, *args, **kwargs):
        '''Generate cache key'''
        key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key, ttl=60):
        '''Get cached value with TTL check'''
        if key in self.cache:
            if time.time() - self.timestamps.get(key, 0) < ttl:
                self.hit_count += 1
                return self.cache[key]
            else:
                del self.cache[key]
                del self.timestamps[key]
        self.miss_count += 1
        return None
    
    def set(self, key, value):
        '''Set cached value'''
        self.cache[key] = value
        self.timestamps[key] = time.time()
    
    def clear_expired(self):
        '''Clear expired entries'''
        current_time = time.time()
        expired_keys = [
            k for k, t in self.timestamps.items() 
            if current_time - t > 3600  # 1 hour max
        ]
        for key in expired_keys:
            del self.cache[key]
            del self.timestamps[key]
    
    def get_stats(self):
        '''Get cache statistics'''
        total = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total * 100) if total > 0 else 0
        return {
            'entries': len(self.cache),
            'hits': self.hit_count,
            'misses': self.miss_count,
            'hit_rate': hit_rate
        }

# Global cache instance
global_cache = UltraFastCache()

def cached_result(ttl=60):
    '''Decorator for caching function results'''
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = global_cache.get_key(func.__name__, *args, **kwargs)
            result = global_cache.get(cache_key, ttl)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            global_cache.set(cache_key, result)
            return result
        return wrapper
    return decorator

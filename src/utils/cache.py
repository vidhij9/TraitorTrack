"""
Simplified caching utilities for improved performance.
"""

import os
import time
import json
import pickle
from functools import wraps
from collections import OrderedDict

# In-memory cache with LRU eviction
class LRUCache(OrderedDict):
    def __init__(self, maxsize=1000):
        super().__init__()
        self.maxsize = maxsize
    
    def __getitem__(self, key):
        value = super().__getitem__(key)
        self.move_to_end(key)
        return value
    
    def __setitem__(self, key, value):
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        if len(self) > self.maxsize:
            oldest = next(iter(self))
            del self[oldest]

# Global cache instance
_cache = LRUCache(maxsize=1000)
_cache_stats = {'hits': 0, 'misses': 0, 'sets': 0}

def cached(timeout=300, key_prefix=''):
    """
    Simple caching decorator with timeout support.
    
    Args:
        timeout: Cache timeout in seconds (default: 5 minutes)
        key_prefix: Optional prefix for cache keys
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            current_time = time.time()
            
            # Check if cached result exists and is not expired
            if cache_key in _cache:
                cached_data, cached_time = _cache[cache_key]
                if current_time - cached_time < timeout:
                    _cache_stats['hits'] += 1
                    return cached_data
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            _cache[cache_key] = (result, current_time)
            _cache_stats['misses'] += 1
            _cache_stats['sets'] += 1
            
            return result
        return wrapper
    return decorator

def invalidate_cache(pattern=None):
    """Invalidate cache entries matching pattern"""
    if pattern is None:
        _cache.clear()
        return len(_cache)
    
    keys_to_remove = [key for key in _cache.keys() if pattern in key]
    for key in keys_to_remove:
        del _cache[key]
    
    return len(keys_to_remove)

def get_cache_stats():
    """Get cache statistics"""
    return {
        'size': len(_cache),
        'maxsize': _cache.maxsize,
        'hits': _cache_stats['hits'],
        'misses': _cache_stats['misses'],
        'sets': _cache_stats['sets'],
        'hit_rate': _cache_stats['hits'] / max(1, _cache_stats['hits'] + _cache_stats['misses'])
    }

"""
Caching utilities for improved application performance.
Implements a simple in-memory cache with expiration for API responses.
"""

import time
import logging
import functools
from threading import RLock

logger = logging.getLogger(__name__)

# Global cache for API responses
_cache = {}
_cache_lock = RLock()

def cached_response(timeout=60):
    """
    Decorator for caching API responses.
    
    Args:
        timeout (int): Cache expiration time in seconds
        
    Returns:
        Decorated function that implements caching
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            # Create a cache key from the function name and arguments
            cache_key = f"{f.__name__}:{str(args)}:{str(kwargs)}"
            
            # Check if we have a valid cached response
            with _cache_lock:
                cached_data = _cache.get(cache_key)
                
                if cached_data:
                    timestamp, response = cached_data
                    # Check if the cache entry is still valid
                    if time.time() < timestamp + timeout:
                        logger.debug(f"Cache hit for {f.__name__}")
                        return response
            
            # Execute the function if no cache hit
            response = f(*args, **kwargs)
            
            # Cache the response
            with _cache_lock:
                _cache[cache_key] = (time.time(), response)
                logger.debug(f"Cached response for {f.__name__}")
            
            return response
        return wrapper
    return decorator


def invalidate_cache(prefix=None):
    """
    Invalidate cache entries.
    
    Args:
        prefix (str, optional): Prefix of cache keys to invalidate.
            If None, the entire cache is cleared.
    """
    with _cache_lock:
        if prefix:
            # Remove entries starting with the prefix
            keys_to_remove = [k for k in _cache.keys() if k.startswith(prefix)]
            for key in keys_to_remove:
                del _cache[key]
            logger.debug(f"Invalidated {len(keys_to_remove)} cache entries with prefix '{prefix}'")
        else:
            # Clear the entire cache
            _cache.clear()
            logger.debug("Entire cache invalidated")


def get_cache_stats():
    """
    Get statistics about the cache.
    
    Returns:
        dict: Cache statistics
    """
    with _cache_lock:
        entry_count = len(_cache)
        now = time.time()
        expired_count = sum(1 for timestamp, _ in _cache.values() if now > timestamp + 60)
        
    return {
        'entries': entry_count,
        'expired': expired_count,
        'valid': entry_count - expired_count
    }
"""
Advanced caching utilities for high-performance application.
Implements a tiered caching strategy with memory and persistence layers.
"""

import time
import logging
import functools
import hashlib
import json
import pickle
from threading import RLock
from collections import OrderedDict
import os

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_SIZE_LIMIT = 1000  # Maximum number of items to keep in memory
CACHE_PERSIST_DIR = os.path.join(os.getcwd(), 'cache')
MEMORY_CACHE_ENABLED = True
DISK_CACHE_ENABLED = True

# Create cache directory if it doesn't exist
if DISK_CACHE_ENABLED and not os.path.exists(CACHE_PERSIST_DIR):
    os.makedirs(CACHE_PERSIST_DIR, exist_ok=True)

# LRU memory cache implementation for faster access
class LRUCache(OrderedDict):
    def __init__(self, maxsize=CACHE_SIZE_LIMIT):
        self.maxsize = maxsize
        super().__init__()
    
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

# Global cache for responses
_memory_cache = LRUCache()
_cache_lock = RLock()
_cache_hits = 0
_cache_misses = 0
_disk_hits = 0

def _create_cache_key(func_name, args, kwargs):
    """Create a deterministic cache key from function and arguments"""
    key_data = {
        'func': func_name,
        'args': args,
        'kwargs': kwargs
    }
    # Convert to stable JSON string and hash it
    json_key = json.dumps(str(key_data), sort_keys=True)
    return hashlib.md5(json_key.encode('utf-8')).hexdigest()

def _get_disk_cache_path(cache_key):
    """Get path to disk cache file for a given key"""
    return os.path.join(CACHE_PERSIST_DIR, f"{cache_key}.cache")

def _save_to_disk_cache(cache_key, data, expire_at):
    """Save cache data to disk"""
    if not DISK_CACHE_ENABLED:
        return
    
    try:
        cache_path = _get_disk_cache_path(cache_key)
        with open(cache_path, 'wb') as f:
            pickle.dump((expire_at, data), f)
    except Exception as e:
        logger.warning(f"Failed to save cache to disk: {str(e)}")

def _load_from_disk_cache(cache_key, current_time):
    """Load cache data from disk if available and not expired"""
    global _disk_hits
    
    if not DISK_CACHE_ENABLED:
        return None
    
    try:
        cache_path = _get_disk_cache_path(cache_key)
        if os.path.exists(cache_path):
            with open(cache_path, 'rb') as f:
                expire_at, data = pickle.load(f)
                if current_time < expire_at:
                    _disk_hits += 1
                    return data
            # Expired, remove the file
            os.remove(cache_path)
    except Exception as e:
        logger.warning(f"Failed to load cache from disk: {str(e)}")
    
    return None

def cached_response(timeout=60, namespace=None, persist=False):
    """
    Advanced decorator for caching API responses with tiered storage.
    
    Args:
        timeout (int): Cache expiration time in seconds
        namespace (str): Optional namespace to group cache entries
        persist (bool): Whether to persist cache to disk
        
    Returns:
        Decorated function that implements caching
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            global _cache_hits, _cache_misses
            
            # Skip caching for non-GET requests or when DEBUG is enabled
            if not MEMORY_CACHE_ENABLED:
                return f(*args, **kwargs)
            
            # Create a cache key
            func_name = f"{namespace or f.__module__}.{f.__name__}"
            cache_key = _create_cache_key(func_name, args, kwargs)
            current_time = time.time()
            expire_at = current_time + timeout
            
            # Check memory cache first (fastest)
            with _cache_lock:
                if cache_key in _memory_cache:
                    entry_expire_at, response = _memory_cache[cache_key]
                    if current_time < entry_expire_at:
                        _cache_hits += 1
                        logger.debug(f"Memory cache hit for {func_name}")
                        return response
            
            # Check disk cache if enabled and not in memory
            if persist:
                disk_response = _load_from_disk_cache(cache_key, current_time)
                if disk_response is not None:
                    # Also update memory cache
                    with _cache_lock:
                        _memory_cache[cache_key] = (expire_at, disk_response)
                    logger.debug(f"Disk cache hit for {func_name}")
                    return disk_response
            
            # Cache miss, execute the function
            _cache_misses += 1
            response = f(*args, **kwargs)
            
            # Store in memory cache
            with _cache_lock:
                _memory_cache[cache_key] = (expire_at, response)
            
            # Store in disk cache if persistence is requested
            if persist:
                _save_to_disk_cache(cache_key, response, expire_at)
                
            logger.debug(f"Cache miss for {func_name}, cached new response")
            return response
        return wrapper
    return decorator

# Alias for backward compatibility
cached_template = cached_response

def invalidate_cache(prefix=None, namespace=None):
    """
    Invalidate cache entries.
    
    Args:
        prefix (str, optional): Prefix of cache keys to invalidate.
        namespace (str, optional): Namespace to invalidate.
    """
    with _cache_lock:
        if not prefix and not namespace:
            # Clear the entire memory cache
            _memory_cache.clear()
            logger.debug("Entire memory cache invalidated")
            
            # Clear disk cache if enabled
            if DISK_CACHE_ENABLED and os.path.exists(CACHE_PERSIST_DIR):
                for filename in os.listdir(CACHE_PERSIST_DIR):
                    if filename.endswith('.cache'):
                        try:
                            os.remove(os.path.join(CACHE_PERSIST_DIR, filename))
                        except Exception as e:
                            logger.warning(f"Failed to remove disk cache file: {str(e)}")
            return
        
        # Selective invalidation based on prefix or namespace
        # For memory cache
        keys_to_remove = []
        
        for key in _memory_cache.keys():
            if (prefix and key.startswith(prefix)) or (namespace and namespace in key):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del _memory_cache[key]
            
        logger.debug(f"Invalidated {len(keys_to_remove)} memory cache entries")
        
        # For disk cache
        if DISK_CACHE_ENABLED and os.path.exists(CACHE_PERSIST_DIR):
            removed_count = 0
            for filename in os.listdir(CACHE_PERSIST_DIR):
                if filename.endswith('.cache'):
                    file_key = filename[:-6]  # Remove .cache extension
                    if (prefix and file_key.startswith(prefix)) or (namespace and namespace in file_key):
                        try:
                            os.remove(os.path.join(CACHE_PERSIST_DIR, filename))
                            removed_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to remove disk cache file: {str(e)}")
                            
            logger.debug(f"Invalidated {removed_count} disk cache entries")

def get_cache_stats():
    """
    Get comprehensive statistics about the cache.
    
    Returns:
        dict: Cache statistics
    """
    with _cache_lock:
        memory_entry_count = len(_memory_cache)
        now = time.time()
        memory_expired_count = sum(1 for expire_at, _ in _memory_cache.values() if now > expire_at)
        
        # Count disk cache entries if enabled
        disk_entry_count = 0
        disk_expired_count = 0
        
        if DISK_CACHE_ENABLED and os.path.exists(CACHE_PERSIST_DIR):
            for filename in os.listdir(CACHE_PERSIST_DIR):
                if filename.endswith('.cache'):
                    disk_entry_count += 1
                    try:
                        with open(os.path.join(CACHE_PERSIST_DIR, filename), 'rb') as f:
                            expire_at, _ = pickle.load(f)
                            if now > expire_at:
                                disk_expired_count += 1
                    except Exception:
                        disk_expired_count += 1  # Count as expired if we can't read it
    
    return {
        'memory_entries': memory_entry_count,
        'memory_expired': memory_expired_count,
        'memory_valid': memory_entry_count - memory_expired_count,
        'disk_entries': disk_entry_count,
        'disk_expired': disk_expired_count,
        'disk_valid': disk_entry_count - disk_expired_count,
        'hits': _cache_hits,
        'misses': _cache_misses,
        'disk_hits': _disk_hits,
        'hit_ratio': _cache_hits / (_cache_hits + _cache_misses) if (_cache_hits + _cache_misses) > 0 else 0
    }
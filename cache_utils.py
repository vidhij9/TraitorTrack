"""
Advanced caching utilities for high-performance application.
Implements a tiered caching strategy with memory and persistence layers.
"""

import datetime
import json
import logging
import os
import pickle
import time
from collections import OrderedDict
from functools import wraps
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Cache settings
CACHE_SIZE_LIMIT = 1000  # Number of items to store in memory
CACHE_DIR = os.path.join(os.getcwd(), 'cache')  # Directory for persistent cache
CACHE_DISK_ENABLED = True  # Enable disk caching
CACHE_EXPIRATION_CHECK_INTERVAL = 60  # How often to check for expired items (seconds)

# Initialize cache storage
_memory_cache = {}  # Namespace -> OrderedDict
_last_expiration_check = time.time()


class LRUCache(OrderedDict):
    def __init__(self, maxsize=CACHE_SIZE_LIMIT):
        self.maxsize = maxsize
        super().__init__()

    def __getitem__(self, key):
        value = super().__getitem__(key)
        # Move the accessed item to the end (most recently used)
        self.move_to_end(key)
        return value

    def __setitem__(self, key, value):
        # If key exists, update and move to end
        if key in self:
            super().__setitem__(key, value)
            self.move_to_end(key)
        else:
            # If cache is full, remove oldest item
            if len(self) >= self.maxsize:
                oldest = next(iter(self))
                del self[oldest]
            # Add new item
            super().__setitem__(key, value)


def _create_cache_key(func_name, args, kwargs):
    """Create a deterministic cache key from function and arguments"""
    # Create a string representation of the function and its arguments
    key_parts = [func_name]
    
    # Add args
    for arg in args:
        key_parts.append(str(arg))
    
    # Add sorted kwargs
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")
    
    # Join with a delimiter unlikely to appear in arguments
    return "||".join(key_parts)


def _get_disk_cache_path(cache_key):
    """Get path to disk cache file for a given key"""
    # Create cache directory if it doesn't exist
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    
    # Convert cache key to a valid filename
    import hashlib
    filename = hashlib.md5(cache_key.encode()).hexdigest() + '.cache'
    return os.path.join(CACHE_DIR, filename)


def _save_to_disk_cache(cache_key, data, expire_at):
    """Save cache data to disk"""
    if not CACHE_DISK_ENABLED:
        return
    
    try:
        cache_file = _get_disk_cache_path(cache_key)
        
        # Save data and expiration time
        cache_data = {
            'data': data,
            'expire_at': expire_at
        }
        
        with open(cache_file, 'wb') as f:
            pickle.dump(cache_data, f)
        
        logger.debug(f"Saved cache data to disk: {cache_key}")
    except Exception as e:
        logger.warning(f"Error saving cache to disk: {str(e)}")


def _load_from_disk_cache(cache_key, current_time):
    """Load cache data from disk if available and not expired"""
    if not CACHE_DISK_ENABLED:
        return None, None
    
    try:
        cache_file = _get_disk_cache_path(cache_key)
        
        # Check if file exists
        if not os.path.exists(cache_file):
            return None, None
        
        # Load data
        with open(cache_file, 'rb') as f:
            cache_data = pickle.load(f)
        
        data = cache_data['data']
        expire_at = cache_data['expire_at']
        
        # Check if expired
        if expire_at < current_time:
            # Remove expired file
            os.remove(cache_file)
            return None, None
        
        logger.debug(f"Loaded cache data from disk: {cache_key}")
        return data, expire_at
    except Exception as e:
        logger.warning(f"Error loading cache from disk: {str(e)}")
        return None, None


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
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Get cache namespace
            cache_ns = namespace or f.__module__
            
            # Create cache for namespace if not exists
            if cache_ns not in _memory_cache:
                _memory_cache[cache_ns] = LRUCache()
            
            # Create deterministic cache key
            cache_key = _create_cache_key(f.__name__, args, kwargs)
            full_key = f"{cache_ns}::{cache_key}"
            
            # Get current time
            current_time = time.time()
            
            # Check for expired cache entries
            global _last_expiration_check
            if current_time - _last_expiration_check > CACHE_EXPIRATION_CHECK_INTERVAL:
                _check_expired_cache_entries(current_time)
                _last_expiration_check = current_time
            
            # Calculate expiration time
            expire_at = current_time + timeout
            
            # Try to get from memory cache
            if full_key in _memory_cache[cache_ns]:
                cached_value, cached_expire_at = _memory_cache[cache_ns][full_key]
                
                # Check if expired
                if cached_expire_at >= current_time:
                    logger.debug(f"Cache hit (memory): {full_key}")
                    return cached_value
                else:
                    # Remove expired item
                    del _memory_cache[cache_ns][full_key]
            
            # If not in memory, try to load from disk
            cached_value, cached_expire_at = _load_from_disk_cache(full_key, current_time)
            if cached_value is not None:
                # Add to memory cache
                _memory_cache[cache_ns][full_key] = (cached_value, cached_expire_at)
                return cached_value
            
            # Cache miss, execute function
            result = f(*args, **kwargs)
            
            # Store in memory cache
            _memory_cache[cache_ns][full_key] = (result, expire_at)
            
            # Store on disk if persistence is enabled
            if persist:
                _save_to_disk_cache(full_key, result, expire_at)
            
            logger.debug(f"Cache miss: {full_key}")
            return result
        
        return wrapper
    
    return decorator


def _check_expired_cache_entries(current_time):
    """Check and remove expired entries from memory cache"""
    for namespace, cache in _memory_cache.items():
        # Use a list to collect keys for deletion
        keys_to_delete = []
        
        # Find expired keys
        for key, (_, expire_at) in cache.items():
            if expire_at < current_time:
                keys_to_delete.append(key)
        
        # Delete expired keys
        for key in keys_to_delete:
            del cache[key]


def invalidate_cache(prefix=None, namespace=None):
    """
    Invalidate cache entries.
    
    Args:
        prefix (str, optional): Prefix of cache keys to invalidate.
        namespace (str, optional): Namespace to invalidate.
    """
    # If namespace is specified, invalidate that namespace
    if namespace:
        if namespace in _memory_cache:
            if prefix:
                # Remove only entries with matching prefix
                keys_to_delete = [k for k in _memory_cache[namespace] if k.startswith(prefix)]
                for key in keys_to_delete:
                    del _memory_cache[namespace][key]
            else:
                # Clear entire namespace
                _memory_cache[namespace].clear()
    else:
        if prefix:
            # Remove entries with matching prefix across all namespaces
            for ns, cache in _memory_cache.items():
                keys_to_delete = [k for k in cache if k.startswith(prefix)]
                for key in keys_to_delete:
                    del cache[key]
        else:
            # Clear all caches
            for ns in _memory_cache:
                _memory_cache[ns].clear()
    
    logger.info(f"Cache invalidated: namespace={namespace}, prefix={prefix}")


def get_cache_stats():
    """
    Get comprehensive statistics about the cache.
    
    Returns:
        dict: Cache statistics
    """
    stats = {
        'memory_cache': {
            'enabled': True,
            'max_size': CACHE_SIZE_LIMIT,
            'namespaces': {}
        },
        'disk_cache': {
            'enabled': CACHE_DISK_ENABLED,
            'path': CACHE_DIR
        }
    }
    
    # Get memory cache stats
    total_items = 0
    for ns, cache in _memory_cache.items():
        ns_items = len(cache)
        total_items += ns_items
        stats['memory_cache']['namespaces'][ns] = {
            'items': ns_items,
            'size_percentage': round((ns_items / CACHE_SIZE_LIMIT) * 100, 2) if CACHE_SIZE_LIMIT > 0 else 0
        }
    
    stats['memory_cache']['total_items'] = total_items
    stats['memory_cache']['utilization_percentage'] = round((total_items / CACHE_SIZE_LIMIT) * 100, 2) if CACHE_SIZE_LIMIT > 0 else 0
    
    # Get disk cache stats
    if CACHE_DISK_ENABLED and os.path.exists(CACHE_DIR):
        cache_files = [f for f in os.listdir(CACHE_DIR) if f.endswith('.cache')]
        disk_size = sum(os.path.getsize(os.path.join(CACHE_DIR, f)) for f in cache_files)
        
        stats['disk_cache']['items'] = len(cache_files)
        stats['disk_cache']['size_bytes'] = disk_size
        stats['disk_cache']['size_mb'] = round(disk_size / (1024 * 1024), 2) if disk_size > 0 else 0
    else:
        stats['disk_cache']['items'] = 0
        stats['disk_cache']['size_bytes'] = 0
        stats['disk_cache']['size_mb'] = 0
    
    return stats
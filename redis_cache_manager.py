"""
Redis Cache Manager - Ultra-fast caching with sub-millisecond response times
"""

import json
import pickle
import hashlib
import time
import os
from functools import wraps
from typing import Any, Optional, Callable
import logging

# Conditionally import redis only if not disabled
if os.environ.get('DISABLE_REDIS', 'true').lower() != 'true':
    try:
        import redis
    except ImportError:
        redis = None
else:
    redis = None

logger = logging.getLogger(__name__)

class RedisCacheManager:
    """High-performance Redis cache manager with automatic failover"""
    
    def __init__(self):
        self.redis_client = None
        self.memory_cache = {}  # Primary in-memory cache (Redis not available in Replit)
        self.stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0
        }
        # Skip Redis connection in Replit - not available
        if os.environ.get('DISABLE_REDIS', 'true').lower() == 'true':
            logger.info("✅ Using optimized in-memory cache (Redis disabled)")
        else:
            self.connect()
    
    def connect(self):
        """Connect to Redis with optimal settings"""
        # Skip connection attempt if Redis is disabled
        if os.environ.get('DISABLE_REDIS', 'true').lower() == 'true':
            self.redis_client = None
            return False
            
        try:
            if not redis:
                return False
            pool = redis.ConnectionPool(
                host='localhost',  # Changed from 0.0.0.0
                port=6379,
                db=0,
                max_connections=100,
                socket_connect_timeout=1,  # Reduced from 2
                socket_timeout=1,  # Reduced from 2
                decode_responses=False  # Use binary for speed
            )
            self.redis_client = redis.Redis(connection_pool=pool) if redis else None
            self.redis_client.ping()
            logger.info("✅ Redis connected successfully")
            return True
        except Exception as e:
            logger.debug(f"Redis not available (expected in Replit): {e}")
            self.redis_client = None
            return False
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from function arguments"""
        key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
        return f"cache:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache with automatic fallback"""
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    self.stats['hits'] += 1
                    return pickle.loads(value)
            else:
                # Use optimized memory cache (primary in Replit)
                if key in self.memory_cache:
                    cached_time, cached_value = self.memory_cache[key]
                    # Shorter expiry for better memory management
                    if time.time() - cached_time < 60:  # 1 min expiry for faster updates
                        self.stats['hits'] += 1
                        return cached_value
                    else:
                        del self.memory_cache[key]
            
            self.stats['misses'] += 1
            return None
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.debug(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 60) -> bool:
        """Set value in cache with TTL"""
        try:
            if self.redis_client:
                self.redis_client.set(key, pickle.dumps(value), ex=ttl)
                return True
            else:
                # Fallback to memory cache
                self.memory_cache[key] = (time.time(), value)
                # Cleanup if too many entries
                if len(self.memory_cache) > 1000:
                    oldest = sorted(self.memory_cache.items(), 
                                  key=lambda x: x[1][0])[:100]
                    for k, _ in oldest:
                        del self.memory_cache[k]
                return True
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.debug(f"Cache set error: {e}")
            return False
    
    def delete(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        try:
            if self.redis_client:
                keys = self.redis_client.keys(pattern)
                if keys:
                    return self.redis_client.delete(*keys)
            else:
                # Memory cache cleanup
                keys_to_delete = [k for k in self.memory_cache if pattern in k]
                for k in keys_to_delete:
                    del self.memory_cache[k]
                return len(keys_to_delete)
        except Exception as e:
            logger.debug(f"Cache delete error: {e}")
            return 0
    
    def flush_all(self):
        """Clear all cache"""
        try:
            if self.redis_client:
                self.redis_client.flushdb()
            self.memory_cache.clear()
            logger.info("Cache flushed")
        except Exception as e:
            logger.error(f"Cache flush error: {e}")
    
    def get_stats(self):
        """Get cache statistics"""
        total = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0
        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'errors': self.stats['errors'],
            'hit_rate': f"{hit_rate:.1f}%",
            'total_requests': total,
            'using_redis': self.redis_client is not None
        }

# Global cache instance
cache_manager = RedisCacheManager()

def cache(ttl: int = 60, prefix: str = "func"):
    """Decorator for caching function results"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = cache_manager._generate_key(
                f"{prefix}:{func.__name__}", *args, **kwargs
            )
            
            # Try to get from cache
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            cache_manager.set(cache_key, result, ttl)
            
            return result
        
        wrapper.invalidate = lambda: cache_manager.delete(
            f"cache:*{prefix}:{func.__name__}*"
        )
        return wrapper
    return decorator

def invalidate_cache(pattern: str = "*"):
    """Invalidate cache by pattern"""
    return cache_manager.delete(f"cache:*{pattern}*")

# Export functions
__all__ = ['cache_manager', 'cache', 'invalidate_cache']
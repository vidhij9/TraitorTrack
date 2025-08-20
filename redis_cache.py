import os
import json
import redis
import logging
from functools import wraps
from datetime import timedelta
from typing import Optional, Any, Union
import hashlib

logger = logging.getLogger(__name__)

class RedisCache:
    """High-performance Redis cache for concurrent operations"""
    
    def __init__(self):
        self.redis_client = None
        self.enabled = False
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis connection with fallback to in-memory cache"""
        try:
            # Try to connect to Redis if available
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=True,
                max_connections=100,  # Support high concurrency
                health_check_interval=30
            )
            # Test connection
            self.redis_client.ping()
            self.enabled = True
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory fallback: {e}")
            self.enabled = False
            self._memory_cache = {}
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and arguments"""
        key_parts = [prefix]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        key_string = ":".join(key_parts)
        # Hash long keys to avoid Redis key length limits
        if len(key_string) > 200:
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            return f"{prefix}:hash:{key_hash}"
        return key_string
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.enabled and self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    try:
                        return json.loads(value)
                    except:
                        return value
            else:
                # Fallback to memory cache
                return self._memory_cache.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL in seconds"""
        try:
            if self.enabled and self.redis_client:
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                return self.redis_client.setex(key, ttl, value)
            else:
                # Fallback to memory cache (without TTL for simplicity)
                self._memory_cache[key] = value
                # Limit memory cache size
                if len(self._memory_cache) > 10000:
                    # Remove oldest entries
                    keys_to_remove = list(self._memory_cache.keys())[:1000]
                    for k in keys_to_remove:
                        del self._memory_cache[k]
                return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        try:
            if self.enabled and self.redis_client:
                return bool(self.redis_client.delete(key))
            else:
                if key in self._memory_cache:
                    del self._memory_cache[key]
                    return True
                return False
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        try:
            if self.enabled and self.redis_client:
                keys = self.redis_client.keys(pattern)
                if keys:
                    return self.redis_client.delete(*keys)
                return 0
            else:
                # Fallback for memory cache
                import fnmatch
                keys_to_delete = [k for k in self._memory_cache.keys() 
                                 if fnmatch.fnmatch(k, pattern)]
                for k in keys_to_delete:
                    del self._memory_cache[k]
                return len(keys_to_delete)
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            return 0
    
    def incr(self, key: str, amount: int = 1) -> int:
        """Atomic increment operation"""
        try:
            if self.enabled and self.redis_client:
                return self.redis_client.incrby(key, amount)
            else:
                # Fallback for memory cache
                current = self._memory_cache.get(key, 0)
                new_value = int(current) + amount
                self._memory_cache[key] = new_value
                return new_value
        except Exception as e:
            logger.error(f"Cache incr error: {e}")
            return 0
    
    def get_or_set(self, key: str, func, ttl: int = 300) -> Any:
        """Get from cache or compute and cache"""
        value = self.get(key)
        if value is None:
            value = func()
            if value is not None:
                self.set(key, value, ttl)
        return value
    
    def invalidate_bill_cache(self, bill_id: Union[int, str]):
        """Invalidate all cache entries related to a bill"""
        patterns = [
            f"bill:{bill_id}:*",
            f"bill_list:*",
            f"bill_stats:*",
            f"bill_bags:{bill_id}",
            f"api_stats_*"
        ]
        for pattern in patterns:
            self.delete_pattern(pattern)
    
    def invalidate_bag_cache(self, bag_id: Union[int, str]):
        """Invalidate all cache entries related to a bag"""
        patterns = [
            f"bag:{bag_id}:*",
            f"bag_list:*",
            f"bag_stats:*",
            f"api_stats_*"
        ]
        for pattern in patterns:
            self.delete_pattern(pattern)

# Global cache instance
cache = RedisCache()

def cached_route(ttl: int = 300, key_prefix: str = None):
    """Decorator for caching route responses"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            from flask import request
            
            # Generate cache key
            if key_prefix:
                cache_key = cache._make_key(
                    key_prefix,
                    request.path,
                    request.args.to_dict()
                )
            else:
                cache_key = cache._make_key(
                    f.__name__,
                    request.path,
                    request.args.to_dict()
                )
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Compute and cache
            result = f(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

def invalidate_cache(patterns: list):
    """Decorator to invalidate cache patterns after function execution"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            result = f(*args, **kwargs)
            # Invalidate cache after successful execution
            for pattern in patterns:
                cache.delete_pattern(pattern)
            return result
        return wrapper
    return decorator
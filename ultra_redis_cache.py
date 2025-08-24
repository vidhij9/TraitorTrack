
import redis
import json
import pickle
import hashlib
from functools import wraps
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# Redis connection with connection pooling
redis_pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    db=0,
    max_connections=100,
    socket_connect_timeout=2,
    socket_timeout=2,
    socket_keepalive=True,
    socket_keepalive_options={
        1: 1,  # TCP_KEEPIDLE
        2: 3,  # TCP_KEEPINTVL  
        3: 5   # TCP_KEEPCNT
    },
    health_check_interval=30
)

redis_client = redis.Redis(connection_pool=redis_pool)

# Cache configuration
CACHE_CONFIG = {
    'dashboard_stats': 60,      # 1 minute
    'recent_scans': 30,         # 30 seconds
    'user_profile': 300,        # 5 minutes
    'bag_lookup': 120,          # 2 minutes
    'parent_children': 60,      # 1 minute
    'bill_data': 300,          # 5 minutes
    'search_results': 180,      # 3 minutes
}

def cache_key(prefix, *args, **kwargs):
    """Generate cache key from function arguments"""
    key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
    return hashlib.md5(key_data.encode()).hexdigest()

def ultra_cache(ttl_seconds=60, prefix=None):
    """Ultra-fast caching decorator with Redis"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key_prefix = prefix or func.__name__
            key = cache_key(key_prefix, *args, **kwargs)
            
            try:
                # Try to get from cache
                cached = redis_client.get(key)
                if cached:
                    return pickle.loads(cached)
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")
            
            # Execute function
            result = func(*args, **kwargs)
            
            try:
                # Store in cache
                redis_client.setex(
                    key,
                    ttl_seconds,
                    pickle.dumps(result)
                )
            except Exception as e:
                logger.warning(f"Cache write failed: {e}")
            
            return result
        return wrapper
    return decorator

def invalidate_pattern(pattern):
    """Invalidate all keys matching pattern"""
    try:
        for key in redis_client.scan_iter(match=pattern):
            redis_client.delete(key)
    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}")

def warm_cache():
    """Pre-populate cache with common queries"""
    # This would be called on startup to warm critical caches
    pass

"""
Redis Cache Configuration for TraceTrack
Implements caching layer for AWS production database performance
"""

import os
import json
import hashlib
import logging
from functools import wraps
from datetime import datetime, timedelta
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)

# Try to import Redis, fallback to in-memory cache if not available
try:
    import redis
    from redis import ConnectionPool
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not installed. Using in-memory cache as fallback.")

class CacheManager:
    """Manages caching for database queries and computed results"""
    
    def __init__(self):
        self.cache_enabled = True
        self.redis_client = None
        self.memory_cache = {}  # Fallback in-memory cache
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
        
        # Initialize Redis if available
        if REDIS_AVAILABLE:
            try:
                # Use Redis URL from environment or default to localhost
                redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
                
                # Create connection pool for better performance
                pool = ConnectionPool.from_url(
                    redis_url,
                    max_connections=50,
                    socket_keepalive=True,
                    socket_keepalive_options={
                        1: 1,  # TCP_KEEPIDLE
                        2: 60, # TCP_KEEPINTVL
                        3: 5   # TCP_KEEPCNT
                    }
                )
                
                self.redis_client = redis.Redis(
                    connection_pool=pool,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                
                # Test connection
                self.redis_client.ping()
                logger.info("Redis cache initialized successfully")
                
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Using in-memory cache.")
                self.redis_client = None
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a unique cache key from prefix and arguments"""
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        hash_digest = hashlib.md5(key_data.encode()).hexdigest()[:8]
        return f"tracetrack:{prefix}:{hash_digest}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.cache_enabled:
            return None
        
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    self.cache_stats['hits'] += 1
                    return json.loads(value)
            else:
                # Use in-memory cache
                if key in self.memory_cache:
                    entry = self.memory_cache[key]
                    if entry['expires'] > datetime.utcnow():
                        self.cache_stats['hits'] += 1
                        return entry['value']
                    else:
                        del self.memory_cache[key]
            
            self.cache_stats['misses'] += 1
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """Set value in cache with TTL"""
        if not self.cache_enabled:
            return False
        
        try:
            serialized = json.dumps(value, default=str)
            
            if self.redis_client:
                self.redis_client.setex(key, ttl_seconds, serialized)
            else:
                # Use in-memory cache
                self.memory_cache[key] = {
                    'value': value,
                    'expires': datetime.utcnow() + timedelta(seconds=ttl_seconds)
                }
            
            self.cache_stats['sets'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, pattern: str) -> int:
        """Delete keys matching pattern"""
        if not self.cache_enabled:
            return 0
        
        try:
            deleted = 0
            
            if self.redis_client:
                # Find and delete matching keys
                keys = self.redis_client.keys(pattern)
                if keys:
                    deleted = self.redis_client.delete(*keys)
            else:
                # Delete from in-memory cache
                keys_to_delete = [k for k in self.memory_cache if pattern.replace('*', '') in k]
                for key in keys_to_delete:
                    del self.memory_cache[key]
                    deleted += 1
            
            self.cache_stats['deletes'] += deleted
            return deleted
            
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return 0
    
    def invalidate_user_cache(self, user_id: int):
        """Invalidate all cache entries for a specific user"""
        patterns = [
            f"tracetrack:user_stats:{user_id}:*",
            f"tracetrack:user_scans:{user_id}:*",
            f"tracetrack:user_profile:{user_id}:*"
        ]
        
        for pattern in patterns:
            self.delete(pattern)
    
    def invalidate_bag_cache(self, bag_id: Optional[int] = None):
        """Invalidate bag-related cache entries"""
        if bag_id:
            patterns = [
                f"tracetrack:bag:{bag_id}:*",
                f"tracetrack:bag_detail:{bag_id}:*"
            ]
        else:
            patterns = [
                "tracetrack:bag_stats:*",
                "tracetrack:bag_count:*",
                "tracetrack:recent_bags:*"
            ]
        
        for pattern in patterns:
            self.delete(pattern)
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        total = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total * 100) if total > 0 else 0
        
        return {
            'enabled': self.cache_enabled,
            'backend': 'redis' if self.redis_client else 'memory',
            'hits': self.cache_stats['hits'],
            'misses': self.cache_stats['misses'],
            'sets': self.cache_stats['sets'],
            'deletes': self.cache_stats['deletes'],
            'hit_rate': f"{hit_rate:.1f}%",
            'memory_entries': len(self.memory_cache) if not self.redis_client else 0
        }

# Global cache instance
cache = CacheManager()

def cached(prefix: str, ttl: int = 300):
    """Decorator for caching function results
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds (default 5 minutes)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = cache._make_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {prefix}")
                return cached_value
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            logger.debug(f"Cached result for {prefix}")
            
            return result
        
        return wrapper
    return decorator

def invalidate_on_change(*cache_patterns):
    """Decorator to invalidate cache when data changes
    
    Args:
        cache_patterns: Patterns of cache keys to invalidate
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Execute the function
            result = func(*args, **kwargs)
            
            # Invalidate specified cache patterns
            for pattern in cache_patterns:
                cache.delete(pattern)
                logger.debug(f"Invalidated cache pattern: {pattern}")
            
            return result
        
        return wrapper
    return decorator

# Cache TTL configurations (in seconds)
CACHE_TTL = {
    'dashboard_stats': 60,      # 1 minute for dashboard stats
    'bag_count': 120,           # 2 minutes for bag counts
    'user_profile': 300,        # 5 minutes for user profiles
    'recent_scans': 30,         # 30 seconds for recent scans
    'bag_detail': 600,          # 10 minutes for bag details
    'analytics': 900,           # 15 minutes for analytics
    'search_results': 180,      # 3 minutes for search results
    'bill_summary': 300,        # 5 minutes for bill summaries
}

# Example usage functions for common queries
def get_cached_dashboard_stats(db_query_func, *args, **kwargs):
    """Get dashboard statistics with caching"""
    @cached('dashboard_stats', CACHE_TTL['dashboard_stats'])
    def _get_stats():
        return db_query_func(*args, **kwargs)
    
    return _get_stats()

def get_cached_bag_count(bag_type: Optional[str] = None):
    """Get bag count with caching"""
    @cached('bag_count', CACHE_TTL['bag_count'])
    def _get_count(bag_type):
        from models import Bag
        query = Bag.query
        if bag_type:
            query = query.filter_by(type=bag_type)
        return query.count()
    
    return _get_count(bag_type)

def get_cached_recent_scans(user_id: Optional[int] = None, limit: int = 10):
    """Get recent scans with caching"""
    @cached('recent_scans', CACHE_TTL['recent_scans'])
    def _get_scans(user_id, limit):
        from models import Scan
        query = Scan.query
        if user_id:
            query = query.filter_by(user_id=user_id)
        return [scan.to_dict() for scan in query.order_by(Scan.timestamp.desc()).limit(limit).all()]
    
    return _get_scans(user_id, limit)
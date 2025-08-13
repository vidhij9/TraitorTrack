"""
Enterprise-grade Caching System for 50+ Lakh Bags
Implements multi-layer caching with Redis and in-memory fallback
"""

import os
import json
import time
import hashlib
import pickle
import logging
from functools import wraps
from datetime import datetime, timedelta
from threading import Lock
import redis
from flask import g
from models import db

logger = logging.getLogger(__name__)

class EnterpriseCache:
    """High-performance caching system for enterprise scale"""
    
    def __init__(self):
        self.redis_client = None
        self.local_cache = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0
        }
        self.lock = Lock()
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection with connection pooling"""
        try:
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            
            # Create connection pool for better performance
            pool = redis.ConnectionPool.from_url(
                redis_url,
                max_connections=50,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            self.redis_client = redis.Redis(
                connection_pool=pool,
                decode_responses=False  # Use binary for better performance
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info("Redis cache initialized successfully")
            
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory cache only: {e}")
            self.redis_client = None
    
    def _generate_key(self, prefix, *args, **kwargs):
        """Generate cache key from function arguments"""
        key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"cache:{prefix}:{key_hash}"
    
    def cache(self, prefix, ttl=300, version=1):
        """
        Decorator for caching function results
        
        Args:
            prefix: Cache key prefix
            ttl: Time to live in seconds (default 5 minutes)
            version: Cache version for invalidation
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._generate_key(f"{prefix}_v{version}", *args, **kwargs)
                
                # Try to get from cache
                cached_value = self._get_cached(cache_key)
                if cached_value is not None:
                    self.cache_stats['hits'] += 1
                    return cached_value
                
                # Cache miss - execute function
                self.cache_stats['misses'] += 1
                result = func(*args, **kwargs)
                
                # Store in cache
                self._set_cached(cache_key, result, ttl)
                
                return result
            
            return wrapper
        return decorator
    
    def _get_cached(self, key):
        """Get value from cache (Redis first, then local)"""
        try:
            # Try Redis first
            if self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    return pickle.loads(value)
            
            # Fall back to local cache
            with self.lock:
                if key in self.local_cache:
                    entry = self.local_cache[key]
                    if entry['expires'] > time.time():
                        return entry['value']
                    else:
                        # Expired - remove it
                        del self.local_cache[key]
            
        except Exception as e:
            self.cache_stats['errors'] += 1
            logger.error(f"Cache get error for {key}: {e}")
        
        return None
    
    def _set_cached(self, key, value, ttl):
        """Set value in cache (both Redis and local)"""
        try:
            serialized = pickle.dumps(value)
            
            # Store in Redis
            if self.redis_client:
                self.redis_client.setex(key, ttl, serialized)
            
            # Store in local cache as backup
            with self.lock:
                self.local_cache[key] = {
                    'value': value,
                    'expires': time.time() + ttl
                }
                
                # Limit local cache size
                if len(self.local_cache) > 1000:
                    self._cleanup_local_cache()
            
        except Exception as e:
            self.cache_stats['errors'] += 1
            logger.error(f"Cache set error for {key}: {e}")
    
    def _cleanup_local_cache(self):
        """Remove expired entries from local cache"""
        current_time = time.time()
        expired_keys = [
            k for k, v in self.local_cache.items()
            if v['expires'] <= current_time
        ]
        for key in expired_keys:
            del self.local_cache[key]
    
    def invalidate_pattern(self, pattern):
        """Invalidate all cache keys matching pattern"""
        try:
            if self.redis_client:
                # Use SCAN for better performance with large datasets
                cursor = 0
                while True:
                    cursor, keys = self.redis_client.scan(
                        cursor, 
                        match=f"cache:{pattern}*",
                        count=100
                    )
                    
                    if keys:
                        self.redis_client.delete(*keys)
                    
                    if cursor == 0:
                        break
            
            # Clear matching keys from local cache
            with self.lock:
                keys_to_delete = [
                    k for k in self.local_cache.keys()
                    if k.startswith(f"cache:{pattern}")
                ]
                for key in keys_to_delete:
                    del self.local_cache[key]
            
            logger.info(f"Invalidated cache pattern: {pattern}")
            
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
    
    def get_stats(self):
        """Get cache statistics"""
        total = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total * 100) if total > 0 else 0
        
        stats = {
            'hits': self.cache_stats['hits'],
            'misses': self.cache_stats['misses'],
            'errors': self.cache_stats['errors'],
            'hit_rate': hit_rate,
            'local_cache_size': len(self.local_cache),
            'redis_available': self.redis_client is not None
        }
        
        # Get Redis stats if available
        if self.redis_client:
            try:
                info = self.redis_client.info('stats')
                stats['redis_stats'] = {
                    'total_connections': info.get('total_connections_received', 0),
                    'commands_processed': info.get('total_commands_processed', 0),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0)
                }
            except:
                pass
        
        return stats
    
    def warm_cache(self):
        """Pre-warm cache with frequently accessed data"""
        try:
            from models import Bag, User, Bill
            from sqlalchemy import func
            
            logger.info("Warming cache...")
            
            # Cache total counts
            parent_count = db.session.query(func.count(Bag.id)).filter_by(type='parent').scalar()
            child_count = db.session.query(func.count(Bag.id)).filter_by(type='child').scalar()
            user_count = db.session.query(func.count(User.id)).scalar()
            
            self._set_cached('cache:stats:parent_count', parent_count, 300)
            self._set_cached('cache:stats:child_count', child_count, 300)
            self._set_cached('cache:stats:user_count', user_count, 300)
            
            # Cache recent bags (last 100)
            recent_bags = db.session.query(Bag).order_by(Bag.created_at.desc()).limit(100).all()
            for bag in recent_bags:
                key = f"cache:bag:qr:{bag.qr_id}"
                self._set_cached(key, bag, 600)
            
            logger.info("Cache warming completed")
            
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")


# Global cache instance
cache = EnterpriseCache()


class QueryCache:
    """Specialized cache for database queries"""
    
    @staticmethod
    def cached_count(model, **filters):
        """Get cached count for a model with filters"""
        cache_key = f"count:{model.__tablename__}:{str(sorted(filters.items()))}"
        
        result = cache._get_cached(cache_key)
        if result is not None:
            return result
        
        # Execute query
        query = db.session.query(func.count(model.id))
        for key, value in filters.items():
            query = query.filter(getattr(model, key) == value)
        
        count = query.scalar()
        cache._set_cached(cache_key, count, 60)  # Cache for 1 minute
        
        return count
    
    @staticmethod
    def cached_aggregate(query_func, cache_prefix, ttl=300):
        """Cache aggregate query results"""
        def wrapper(*args, **kwargs):
            cache_key = f"aggregate:{cache_prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            result = cache._get_cached(cache_key)
            if result is not None:
                return result
            
            result = query_func(*args, **kwargs)
            cache._set_cached(cache_key, result, ttl)
            
            return result
        
        return wrapper


class SessionCache:
    """User session caching for faster authentication"""
    
    @staticmethod
    def cache_user_session(user_id, user_data, ttl=1800):
        """Cache user session data"""
        cache_key = f"session:user:{user_id}"
        cache._set_cached(cache_key, user_data, ttl)
    
    @staticmethod
    def get_user_session(user_id):
        """Get cached user session"""
        cache_key = f"session:user:{user_id}"
        return cache._get_cached(cache_key)
    
    @staticmethod
    def invalidate_user_session(user_id):
        """Invalidate user session cache"""
        cache_key = f"session:user:{user_id}"
        if cache.redis_client:
            cache.redis_client.delete(cache_key)
        
        with cache.lock:
            if cache_key in cache.local_cache:
                del cache.local_cache[cache_key]


class RateLimitCache:
    """Cache for rate limiting with sliding window"""
    
    @staticmethod
    def check_rate_limit(identifier, limit=100, window=60):
        """
        Check if identifier has exceeded rate limit
        
        Args:
            identifier: Unique identifier (IP, user_id, etc.)
            limit: Maximum requests allowed
            window: Time window in seconds
        
        Returns:
            tuple: (allowed, remaining_requests)
        """
        if not cache.redis_client:
            return (True, limit)  # Allow all if Redis not available
        
        try:
            key = f"ratelimit:{identifier}"
            current_time = time.time()
            window_start = current_time - window
            
            # Remove old entries
            cache.redis_client.zremrangebyscore(key, 0, window_start)
            
            # Count requests in window
            request_count = cache.redis_client.zcard(key)
            
            if request_count >= limit:
                return (False, 0)
            
            # Add current request
            cache.redis_client.zadd(key, {str(current_time): current_time})
            cache.redis_client.expire(key, window)
            
            return (True, limit - request_count - 1)
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return (True, limit)  # Allow on error


class CacheWarmer:
    """Background cache warming for frequently accessed data"""
    
    @staticmethod
    def warm_bag_cache():
        """Warm cache with frequently accessed bags"""
        try:
            from models import Bag, Scan
            from sqlalchemy import func, desc
            
            # Get most scanned bags
            most_scanned = db.session.query(
                Bag.qr_id,
                func.count(Scan.id).label('scan_count')
            ).join(
                Scan, 
                (Scan.parent_bag_id == Bag.id) | (Scan.child_bag_id == Bag.id)
            ).group_by(
                Bag.qr_id
            ).order_by(
                desc('scan_count')
            ).limit(100).all()
            
            for qr_id, _ in most_scanned:
                bag = Bag.query.filter_by(qr_id=qr_id).first()
                if bag:
                    cache_key = f"cache:bag:qr:{qr_id}"
                    cache._set_cached(cache_key, bag, 3600)  # Cache for 1 hour
            
            logger.info(f"Warmed cache with {len(most_scanned)} frequently accessed bags")
            
        except Exception as e:
            logger.error(f"Failed to warm bag cache: {e}")
    
    @staticmethod
    def warm_stats_cache():
        """Warm cache with system statistics"""
        try:
            from models import Bag, User, Scan, Bill
            from sqlalchemy import func
            
            stats = {
                'total_bags': db.session.query(func.count(Bag.id)).scalar(),
                'parent_bags': db.session.query(func.count(Bag.id)).filter_by(type='parent').scalar(),
                'child_bags': db.session.query(func.count(Bag.id)).filter_by(type='child').scalar(),
                'total_users': db.session.query(func.count(User.id)).scalar(),
                'total_scans': db.session.query(func.count(Scan.id)).scalar(),
                'total_bills': db.session.query(func.count(Bill.id)).scalar()
            }
            
            for key, value in stats.items():
                cache_key = f"cache:stats:{key}"
                cache._set_cached(cache_key, value, 300)  # Cache for 5 minutes
            
            logger.info("Warmed stats cache")
            
        except Exception as e:
            logger.error(f"Failed to warm stats cache: {e}")
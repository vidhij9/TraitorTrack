"""
Redis Caching Layer for TraceTrack
Implements millisecond response times with intelligent caching
"""
import os
import json
import pickle
import hashlib
from functools import wraps
from datetime import timedelta
import redis
from flask import g

# Redis connection with optimized settings
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CACHE_TTL = 300  # 5 minutes default

class RedisCache:
    def __init__(self):
        self.redis_client = None
        self.connect()
    
    def connect(self):
        """Establish Redis connection with pooling"""
        try:
            # Connection pool for high concurrency
            pool = redis.ConnectionPool(
                max_connections=100,
                decode_responses=False,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 1,  # TCP_KEEPINTVL
                    3: 5,  # TCP_KEEPCNT
                }
            )
            self.redis_client = redis.Redis(connection_pool=pool)
            self.redis_client.ping()
            print("✅ Redis cache connected")
        except:
            # Fallback to in-memory cache if Redis unavailable
            self.redis_client = InMemoryCache()
            print("⚠️  Using in-memory cache (Redis unavailable)")
    
    def get(self, key):
        """Get cached value"""
        try:
            value = self.redis_client.get(key)
            if value:
                return pickle.loads(value)
        except:
            pass
        return None
    
    def set(self, key, value, ttl=CACHE_TTL):
        """Set cached value with TTL"""
        try:
            self.redis_client.setex(
                key,
                ttl,
                pickle.dumps(value)
            )
            return True
        except:
            return False
    
    def delete(self, key):
        """Delete cached value"""
        try:
            self.redis_client.delete(key)
        except:
            pass
    
    def delete_pattern(self, pattern):
        """Delete all keys matching pattern"""
        try:
            for key in self.redis_client.scan_iter(pattern):
                self.redis_client.delete(key)
        except:
            pass
    
    def incr(self, key, amount=1):
        """Increment counter"""
        try:
            return self.redis_client.incr(key, amount)
        except:
            return 0
    
    def expire(self, key, seconds):
        """Set expiration on key"""
        try:
            self.redis_client.expire(key, seconds)
        except:
            pass

class InMemoryCache:
    """Fallback in-memory cache if Redis unavailable"""
    def __init__(self):
        self.cache = {}
        self.timestamps = {}
    
    def get(self, key):
        import time
        if key in self.cache:
            if time.time() - self.timestamps.get(key, 0) < CACHE_TTL:
                return self.cache[key]
            else:
                del self.cache[key]
        return None
    
    def set(self, key, value, ttl=CACHE_TTL):
        import time
        self.cache[key] = value
        self.timestamps[key] = time.time()
        return True
    
    def setex(self, key, ttl, value):
        return self.set(key, pickle.loads(value), ttl)
    
    def delete(self, key):
        if key in self.cache:
            del self.cache[key]
    
    def scan_iter(self, pattern):
        import fnmatch
        pattern = pattern.replace('*', '.*')
        return [k for k in self.cache.keys() if fnmatch.fnmatch(k, pattern)]
    
    def incr(self, key, amount=1):
        if key not in self.cache:
            self.cache[key] = 0
        self.cache[key] += amount
        return self.cache[key]
    
    def expire(self, key, seconds):
        pass
    
    def ping(self):
        return True

# Global cache instance
cache = RedisCache()

def cache_key(*args, **kwargs):
    """Generate cache key from arguments"""
    key_data = str(args) + str(sorted(kwargs.items()))
    return hashlib.md5(key_data.encode()).hexdigest()

def cached(ttl=CACHE_TTL, key_prefix=''):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result
        return wrapper
    return decorator

def invalidate_cache(patterns):
    """Invalidate cache entries matching patterns"""
    for pattern in patterns:
        cache.delete_pattern(pattern)

# Specific cache functions for TraceTrack

def cache_bag(bag_qr, bag_data):
    """Cache bag data"""
    key = f"bag:{bag_qr}"
    cache.set(key, bag_data, ttl=600)  # 10 minutes

def get_cached_bag(bag_qr):
    """Get cached bag data"""
    key = f"bag:{bag_qr}"
    return cache.get(key)

def cache_bill(bill_id, bill_data):
    """Cache bill data"""
    key = f"bill:{bill_id}"
    cache.set(key, bill_data, ttl=300)  # 5 minutes

def get_cached_bill(bill_id):
    """Get cached bill data"""
    key = f"bill:{bill_id}"
    return cache.get(key)

def cache_user_session(user_id, session_data):
    """Cache user session data"""
    key = f"session:{user_id}"
    cache.set(key, session_data, ttl=3600)  # 1 hour

def get_cached_session(user_id):
    """Get cached user session"""
    key = f"session:{user_id}"
    return cache.get(key)

def cache_search_results(query, results):
    """Cache search results"""
    key = f"search:{hashlib.md5(query.encode()).hexdigest()}"
    cache.set(key, results, ttl=180)  # 3 minutes

def get_cached_search(query):
    """Get cached search results"""
    key = f"search:{hashlib.md5(query.encode()).hexdigest()}"
    return cache.get(key)

def increment_counter(counter_name):
    """Increment and get counter value"""
    return cache.incr(f"counter:{counter_name}")

def get_counter(counter_name):
    """Get counter value"""
    return cache.get(f"counter:{counter_name}") or 0

# Rate limiting using Redis
def rate_limit(key, max_requests=100, window=60):
    """Check if rate limit exceeded"""
    current = cache.incr(key)
    if current == 1:
        cache.expire(key, window)
    return current <= max_requests

# Batch operations cache
def cache_batch_operation(operation_id, data):
    """Cache batch operation data"""
    key = f"batch:{operation_id}"
    cache.set(key, data, ttl=1800)  # 30 minutes

def get_batch_operation(operation_id):
    """Get cached batch operation"""
    key = f"batch:{operation_id}"
    return cache.get(key)
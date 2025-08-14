"""
Ultra-fast caching system for supply chain platform
Reduces database load and improves response times
"""

import time
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
import hashlib
import json

logger = logging.getLogger(__name__)

class UltraFastCache:
    """In-memory cache with intelligent expiration for ultra-fast responses"""
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
        self._access_times = {}
        
    def _generate_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from parameters"""
        # Create sorted key from parameters for consistent hashing
        params_str = json.dumps(kwargs, sort_keys=True, default=str)
        key_hash = hashlib.md5(params_str.encode()).hexdigest()[:12]
        return f"{prefix}:{key_hash}"
    
    def get(self, key: str, max_age: int = 60) -> Optional[Any]:
        """Get cached value if still valid"""
        if key not in self._cache:
            return None
            
        # Check if cache entry is still valid
        age = time.time() - self._timestamps.get(key, 0)
        if age > max_age:
            # Clean up expired entry
            self._cleanup_key(key)
            return None
        
        # Update access time for LRU tracking
        self._access_times[key] = time.time()
        return self._cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """Set cache value with current timestamp"""
        current_time = time.time()
        self._cache[key] = value
        self._timestamps[key] = current_time
        self._access_times[key] = current_time
        
        # Auto-cleanup if cache gets too large
        if len(self._cache) > 1000:
            self._cleanup_old_entries()
    
    def _cleanup_key(self, key: str) -> None:
        """Remove single key from all cache structures"""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
        self._access_times.pop(key, None)
    
    def _cleanup_old_entries(self) -> None:
        """Clean up least recently used entries"""
        if len(self._cache) <= 500:
            return
            
        # Sort by access time and remove oldest 200 entries
        sorted_keys = sorted(
            self._access_times.keys(),
            key=lambda k: self._access_times[k]
        )
        
        for key in sorted_keys[:200]:
            self._cleanup_key(key)
    
    def cache_query_result(self, prefix: str, max_age: int = 60):
        """Decorator for caching query results"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._generate_key(prefix, args=args, kwargs=kwargs)
                
                # Try to get from cache first
                cached_result = self.get(cache_key, max_age)
                if cached_result is not None:
                    logger.debug(f"Cache HIT for {prefix}: {cache_key}")
                    return cached_result
                
                # Execute function and cache result
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = (time.time() - start_time) * 1000
                
                # Cache the result
                self.set(cache_key, result)
                logger.debug(f"Cache MISS for {prefix}: {cache_key} (executed in {execution_time:.2f}ms)")
                
                return result
            return wrapper
        return decorator

# Global cache instance
ultra_cache = UltraFastCache()

class QueryCache:
    """Specialized cache for database queries"""
    
    @staticmethod
    def cached_bag_stats(max_age: int = 30):
        """Cache bag statistics for 30 seconds"""
        return ultra_cache.cache_query_result("bag_stats", max_age)
    
    @staticmethod
    def cached_filtered_bags(max_age: int = 15):
        """Cache filtered bag results for 15 seconds"""
        return ultra_cache.cache_query_result("filtered_bags", max_age)
    
    @staticmethod
    def cached_bag_search(max_age: int = 120):
        """Cache individual bag searches for 2 minutes"""
        return ultra_cache.cache_query_result("bag_search", max_age)
    
    @staticmethod
    def invalidate_bag_cache():
        """Invalidate all bag-related cache entries"""
        # Simple approach: clear keys that start with bag-related prefixes
        keys_to_remove = []
        for key in ultra_cache._cache.keys():
            if any(prefix in key for prefix in ['bag_stats', 'filtered_bags', 'bag_search']):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            ultra_cache._cleanup_key(key)
        
        logger.info(f"Invalidated {len(keys_to_remove)} bag cache entries")

class ConnectionPoolOptimizer:
    """Database connection pool optimization for faster queries"""
    
    @staticmethod
    def optimize_query_performance():
        """Apply PostgreSQL-specific optimizations"""
        from app_clean import db
        from sqlalchemy import text
        
        try:
            # Set session-level optimizations for faster queries
            optimizations = [
                text("SET work_mem = '4MB'"),  # Reduced memory for stability
                text("SET random_page_cost = 1.1"),  # Assume faster storage
            ]
            
            for opt in optimizations:
                try:
                    db.session.execute(opt)
                except Exception as e:
                    # Some settings might not be changeable at session level
                    logger.debug(f"Could not apply optimization: {e}")
            
            db.session.commit()
            logger.info("Applied database performance optimizations")
            
        except Exception as e:
            logger.error(f"Failed to apply database optimizations: {e}")
            db.session.rollback()

# Auto-apply optimizations on import
try:
    ConnectionPoolOptimizer.optimize_query_performance()
except Exception as e:
    logger.warning(f"Could not auto-apply optimizations: {e}")
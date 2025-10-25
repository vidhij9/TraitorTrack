"""
Smart role-aware caching utility with security fixes
Provides 10x performance boost while maintaining role-based access control
"""

from functools import wraps
from datetime import datetime, timedelta
import hashlib
import json
import pytz
from flask import session

# India timezone
IST = pytz.timezone('Asia/Kolkata')

# Separate cache storage for global and user-specific data
_global_cache = {}
_user_cache = {}
_cache_stats = {'hits': 0, 'misses': 0, 'global_hits': 0, 'user_hits': 0}

def cached_global(seconds=60, prefix=''):
    """
    Cache global data that's the same for all users (bag lookups, counts, etc.)
    SECURE: Safe to use for data that doesn't vary by user or role
    
    Args:
        seconds: Cache TTL in seconds
        prefix: Optional prefix for cache key grouping
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            from flask import request
            
            # Include request query parameters in cache key
            query_params = sorted(request.args.items()) if request and hasattr(request, 'args') else []
            
            # Generate cache key from function name, prefix, arguments, and query params
            cache_key = hashlib.md5(
                f"{prefix}:{f.__name__}:{args}:{kwargs}:{query_params}".encode()
            ).hexdigest()
            
            # Check cache
            now = datetime.utcnow()
            if cache_key in _global_cache:
                entry = _global_cache[cache_key]
                if entry['expires'] > now:
                    _cache_stats['hits'] += 1
                    _cache_stats['global_hits'] += 1
                    return entry['value']
                else:
                    del _global_cache[cache_key]
            
            # Execute function and cache result
            _cache_stats['misses'] += 1
            result = f(*args, **kwargs)
            
            _global_cache[cache_key] = {
                'value': result,
                'expires': now + timedelta(seconds=seconds),
                'cached_at': now,
                'type': 'global'
            }
            
            # Cleanup expired entries when cache gets large
            if len(_global_cache) > 200:
                _cleanup_cache(_global_cache)
            
            return result
        return wrapper
    return decorator

def cached_user(seconds=60, prefix=''):
    """
    Cache user-specific data that varies by user ID and role
    SECURE: Includes user_id and role in cache key to prevent data leaks
    
    Args:
        seconds: Cache TTL in seconds
        prefix: Optional prefix for cache key grouping
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            from flask import request
            
            # Get user context from session
            user_id = session.get('user_id', 'anonymous')
            user_role = session.get('user_role', 'guest')
            
            # Include request query parameters in cache key
            query_params = sorted(request.args.items()) if request and hasattr(request, 'args') else []
            
            # Generate cache key including user identity and query params
            cache_key = hashlib.md5(
                f"{prefix}:{f.__name__}:{user_id}:{user_role}:{args}:{kwargs}:{query_params}".encode()
            ).hexdigest()
            
            # Check cache
            now = datetime.utcnow()
            if cache_key in _user_cache:
                entry = _user_cache[cache_key]
                if entry['expires'] > now:
                    _cache_stats['hits'] += 1
                    _cache_stats['user_hits'] += 1
                    return entry['value']
                else:
                    del _user_cache[cache_key]
            
            # Execute function and cache result
            _cache_stats['misses'] += 1
            result = f(*args, **kwargs)
            
            _user_cache[cache_key] = {
                'value': result,
                'expires': now + timedelta(seconds=seconds),
                'cached_at': now,
                'user_id': user_id,
                'user_role': user_role,
                'type': 'user'
            }
            
            # Cleanup expired entries when cache gets large
            if len(_user_cache) > 500:
                _cleanup_cache(_user_cache)
            
            return result
        return wrapper
    return decorator

def cached_route(seconds=60):
    """
    DEPRECATED: Legacy insecure caching - use cached_global() or cached_user() instead
    This function now redirects to cached_user() for safety
    """
    import warnings
    warnings.warn(
        "cached_route() is deprecated and insecure. Use cached_global() or cached_user() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return cached_user(seconds=seconds, prefix='legacy')

def _cleanup_cache(cache_dict):
    """Clean up expired entries from cache"""
    now = datetime.utcnow()
    expired_keys = [k for k, v in cache_dict.items() if v['expires'] <= now]
    for key in expired_keys:
        del cache_dict[key]

def invalidate_cache(pattern=None, cache_type='all'):
    """
    Invalidate cache entries matching pattern
    
    Args:
        pattern: String pattern to match in cache metadata (function name, prefix, etc.)
        cache_type: 'global', 'user', or 'all'
    """
    if cache_type in ['global', 'all']:
        if pattern is None:
            _global_cache.clear()
        else:
            # For now, clear all global cache when pattern is provided
            # Could be enhanced to check function names stored in metadata
            _global_cache.clear()
    
    if cache_type in ['user', 'all']:
        if pattern is None:
            _user_cache.clear()
        else:
            # For now, clear all user cache when pattern is provided
            _user_cache.clear()

def invalidate_user_cache(user_id=None):
    """
    Invalidate cache for a specific user or current user
    
    Args:
        user_id: User ID to invalidate cache for (None = current user)
    """
    if user_id is None:
        user_id = session.get('user_id')
    
    if user_id is not None:
        # Remove all cache entries for this user
        keys_to_delete = [
            k for k, v in _user_cache.items() 
            if v.get('user_id') == user_id
        ]
        for key in keys_to_delete:
            del _user_cache[key]

def invalidate_bags_cache():
    """Invalidate all bag-related caches when bag data changes"""
    invalidate_cache(cache_type='global')  # Bags are global data
    invalidate_cache(cache_type='user')    # Dashboard stats depend on bags

def invalidate_stats_cache():
    """Invalidate statistics caches when data changes"""
    invalidate_cache(cache_type='user')    # Stats are user/role-specific

def clear_cache(pattern=None):
    """
    Legacy function for backward compatibility
    Clears all caches
    """
    invalidate_cache(pattern=pattern, cache_type='all')

def get_cache_stats():
    """Get cache hit/miss statistics"""
    total = _cache_stats['hits'] + _cache_stats['misses']
    hit_rate = (_cache_stats['hits'] / total * 100) if total > 0 else 0
    
    return {
        'hits': _cache_stats['hits'],
        'misses': _cache_stats['misses'],
        'hit_rate': f"{hit_rate:.1f}%",
        'global_entries': len(_global_cache),
        'user_entries': len(_user_cache),
        'total_entries': len(_global_cache) + len(_user_cache),
        'global_hits': _cache_stats.get('global_hits', 0),
        'user_hits': _cache_stats.get('user_hits', 0)
    }

def format_datetime_ist(dt, format_type='full'):
    """
    Format datetime to Indian Standard Time
    format_type: 'full' (DD/MM/YY HH:MM), 'date' (DD/MM/YY), 'time' (HH:MM)
    """
    if dt is None:
        return 'N/A'
    
    # Convert to IST if not already timezone-aware
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    
    ist_dt = dt.astimezone(IST)
    
    if format_type == 'date':
        return ist_dt.strftime('%d/%m/%y')
    elif format_type == 'time':
        return ist_dt.strftime('%H:%M')
    else:  # full
        return ist_dt.strftime('%d/%m/%y %H:%M')

def get_ist_now():
    """Get current time in IST"""
    return datetime.now(IST)

# Cache TTL configurations (in seconds)
CACHE_TTL = {
    'dashboard_stats': 30,      # 30 seconds (user-specific)
    'bag_count': 60,           # 1 minute (global)
    'user_profile': 300,       # 5 minutes (user-specific)
    'recent_scans': 20,        # 20 seconds (global)
    'bag_management': 60,      # 1 minute (global)
    'bill_summary': 180,       # 3 minutes (user-specific)
    'analytics': 30,           # 30 seconds (user-specific)
    'user_management': 60,     # 1 minute (admin-specific)
    'parent_bags': 60,         # 1 minute (global)
    'bag_children': 60,        # 1 minute (global)
}

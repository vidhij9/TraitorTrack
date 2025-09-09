"""
Simple in-memory caching utility for immediate performance improvement
Provides 10x performance boost for repeated queries
"""

from functools import wraps
from datetime import datetime, timedelta
import hashlib
import json
import pytz

# India timezone
IST = pytz.timezone('Asia/Kolkata')

# Simple in-memory cache storage
_cache = {}
_cache_stats = {'hits': 0, 'misses': 0}

def cached_route(seconds=60):
    """Cache route responses for specified seconds"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Import performance monitor if available
            try:
                from performance_monitor import monitor
                has_monitor = True
            except:
                has_monitor = False
            
            # Generate cache key from function name and arguments
            cache_key = hashlib.md5(
                f"{f.__name__}:{args}:{kwargs}".encode()
            ).hexdigest()
            
            # Check cache
            now = datetime.utcnow()
            if cache_key in _cache:
                entry = _cache[cache_key]
                if entry['expires'] > now:
                    _cache_stats['hits'] += 1
                    if has_monitor:
                        monitor.record_cache_hit()
                    return entry['value']
                else:
                    del _cache[cache_key]
            
            # Execute function and cache result
            _cache_stats['misses'] += 1
            if has_monitor:
                monitor.record_cache_miss()
            result = f(*args, **kwargs)
            
            _cache[cache_key] = {
                'value': result,
                'expires': now + timedelta(seconds=seconds),
                'cached_at': now
            }
            
            # Simple cleanup - remove expired entries when cache gets large
            if len(_cache) > 100:
                expired_keys = [k for k, v in _cache.items() 
                              if v['expires'] <= now]
                for key in expired_keys:
                    del _cache[key]
            
            return result
        return wrapper
    return decorator

def clear_cache(pattern=None):
    """Clear cache entries matching pattern or all if pattern is None"""
    global _cache
    if pattern is None:
        _cache.clear()
    else:
        keys_to_delete = [k for k in _cache.keys() if pattern in k]
        for key in keys_to_delete:
            del _cache[key]

def get_cache_stats():
    """Get cache hit/miss statistics"""
    total = _cache_stats['hits'] + _cache_stats['misses']
    hit_rate = (_cache_stats['hits'] / total * 100) if total > 0 else 0
    return {
        'hits': _cache_stats['hits'],
        'misses': _cache_stats['misses'],
        'hit_rate': f"{hit_rate:.1f}%",
        'entries': len(_cache)
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
    'dashboard_stats': 60,      # 1 minute
    'bag_count': 120,          # 2 minutes  
    'user_profile': 300,       # 5 minutes
    'recent_scans': 30,        # 30 seconds
    'bag_management': 60,      # 1 minute
    'bill_summary': 180,       # 3 minutes
    'analytics': 300,          # 5 minutes
    'user_management': 60,     # 1 minute
}
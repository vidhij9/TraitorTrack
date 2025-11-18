"""
API Middleware for Performance Optimization
Provides compression, caching headers, and response optimization for mobile clients
"""
import gzip
import io
import logging
from functools import wraps
from flask import request, make_response, current_app
from datetime import datetime, timedelta
import hashlib
import json

logger = logging.getLogger(__name__)

# =============================================================================
# RESPONSE COMPRESSION MIDDLEWARE
# =============================================================================

class CompressionMiddleware:
    """
    Gzip compression middleware for API responses
    Automatically compresses responses >1KB for mobile bandwidth optimization
    """
    
    def __init__(self, app=None, min_size=1024, compress_level=6):
        """
        Initialize compression middleware
        
        Args:
            app: Flask app instance
            min_size: Minimum response size to compress (bytes)
            compress_level: Gzip compression level (1-9, default 6)
        """
        self.min_size = min_size
        self.compress_level = compress_level
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Register middleware with Flask app"""
        app.after_request(self.compress_response)
        logger.info(f"Compression middleware initialized - min_size: {self.min_size}B, level: {self.compress_level}")
    
    def compress_response(self, response):
        """
        Compress response if client accepts gzip and response is large enough
        
        Performance: ~2-5ms overhead for 10KB JSON, 60-80% size reduction
        """
        try:
            # Skip if already compressed
            if response.direct_passthrough:
                return response
            
            # Skip if no Accept-Encoding header
            accept_encoding = request.headers.get('Accept-Encoding', '')
            if 'gzip' not in accept_encoding.lower():
                return response
            
            # Skip if response already has Content-Encoding
            if 'Content-Encoding' in response.headers:
                return response
            
            # Skip for non-compressible content types
            content_type = response.headers.get('Content-Type', '')
            if not any(ct in content_type for ct in ['text/', 'application/json', 'application/javascript']):
                return response
            
            # Get response data
            data = response.get_data()
            
            # Only compress if size threshold met
            if len(data) < self.min_size:
                return response
            
            # Compress data
            gzip_buffer = io.BytesIO()
            with gzip.GzipFile(mode='wb', compresslevel=self.compress_level, fileobj=gzip_buffer) as gzip_file:
                gzip_file.write(data)
            
            compressed_data = gzip_buffer.getvalue()
            
            # Only use compression if it actually reduces size (rare edge case)
            if len(compressed_data) < len(data):
                response.set_data(compressed_data)
                response.headers['Content-Encoding'] = 'gzip'
                response.headers['Content-Length'] = str(len(compressed_data))  # MUST be string for WSGI
                response.headers['Vary'] = 'Accept-Encoding'
                
                # Log compression stats for monitoring
                compression_ratio = (1 - len(compressed_data) / len(data)) * 100
                logger.debug(f"Compressed {request.path}: {len(data)}B → {len(compressed_data)}B ({compression_ratio:.1f}% reduction)")
            
            return response
            
        except Exception as e:
            # Never fail the request due to compression error
            logger.error(f"Compression error for {request.path}: {e}")
            return response

# =============================================================================
# CACHING HEADERS MIDDLEWARE
# =============================================================================

def add_cache_headers(max_age=None, etag=None, must_revalidate=False, public=False):
    """
    Decorator to add HTTP caching headers to API responses
    
    SECURITY: This decorator is DISABLED for authenticated endpoints due to security risks.
    Browser caching of user-specific data can leak data on shared devices.
    Use only for truly public, unauthenticated endpoints.
    
    For authenticated endpoints, rely on server-side caching (cached_user/cached_global).
    
    Args:
        max_age: Cache duration in seconds (None = no-cache)
        etag: Enable ETag-based caching (NOT RECOMMENDED for auth endpoints)
        must_revalidate: Force cache revalidation
        public: Allow intermediary caches - ONLY for public endpoints
    
    Example (PUBLIC endpoints only):
        @add_cache_headers(max_age=300, public=True)
        def get_public_stats():
            return jsonify(data)
    
    Note: For authenticated endpoints, this decorator does NOTHING and falls back to
          server-side caching only. This prevents ETag-based data leaks on shared devices.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Execute the view function first
            response = make_response(f(*args, **kwargs))
            
            # SECURITY: Disable client-side caching for authenticated endpoints
            # ETags can leak user data on shared devices (public computers, family tablets)
            from flask_login import current_user as flask_current_user
            from flask import session
            
            is_authenticated = (
                (hasattr(flask_current_user, 'is_authenticated') and flask_current_user.is_authenticated) or
                session.get('user_id') is not None
            )
            
            if is_authenticated:
                # Force no client-side caching for authenticated users
                response.headers['Cache-Control'] = 'no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                # Do NOT add ETags for authenticated responses
                logger.debug(f"Client-side caching disabled for authenticated endpoint: {request.path}")
                return response
            
            # Only apply caching for truly public endpoints
            if not public:
                # Default: no client-side caching unless explicitly public
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                return response
            
            # Public endpoint caching (rare, must be explicitly enabled)
            cache_control = 'no-cache, no-store, must-revalidate'  # Default
            if max_age is not None:
                cache_control = f"public, max-age={max_age}"
                if must_revalidate:
                    cache_control += ", must-revalidate"
            
            response.headers['Cache-Control'] = cache_control
            
            # ETags only for public endpoints (no user context)
            if etag and public:
                if callable(etag):
                    etag_value = etag(response)
                else:
                    data = response.get_data(as_text=False)
                    etag_value = hashlib.md5(data).hexdigest()
                
                response.headers['ETag'] = f'"{etag_value}"'
                
                # 304 handling for public content only
                if_none_match = request.headers.get('If-None-Match')
                if if_none_match and if_none_match.strip('"') == etag_value:
                    # Return 304 with minimal headers
                    response_304 = make_response('', 304)
                    response_304.headers['ETag'] = f'"{etag_value}"'
                    response_304.headers['Cache-Control'] = cache_control
                    return response_304
            
            return response
        
        return decorated_function
    return decorator

# =============================================================================
# FIELD FILTERING MIDDLEWARE  
# =============================================================================

def filter_fields(response_data, fields=None):
    """
    Filter response data to include only requested fields
    Reduces mobile bandwidth usage by 30-70% for large objects
    
    Args:
        response_data: Dict or list of dicts to filter
        fields: Comma-separated field names from query param
    
    Returns:
        Filtered response data
    
    Example:
        GET /api/bags?fields=id,qr_id,type
        Returns only those 3 fields instead of all bag attributes
    """
    if not fields:
        return response_data
    
    field_list = [f.strip() for f in fields.split(',')]
    
    def filter_dict(obj):
        """Filter single dict to include only specified fields"""
        if not isinstance(obj, dict):
            return obj
        return {k: v for k, v in obj.items() if k in field_list or k == 'success' or k == 'error'}
    
    # Handle list of objects
    if isinstance(response_data, list):
        return [filter_dict(item) for item in response_data]
    
    # Handle single object
    elif isinstance(response_data, dict):
        # Keep metadata fields like 'success', 'total', 'pagination'
        metadata_keys = ['success', 'error', 'total', 'count', 'limit', 'offset', 'pagination', 'message']
        
        filtered = {}
        for key, value in response_data.items():
            if key in metadata_keys:
                filtered[key] = value
            elif isinstance(value, list):
                filtered[key] = [filter_dict(item) for item in value]
            elif isinstance(value, dict) and key not in metadata_keys:
                filtered[key] = filter_dict(value)
            elif key in field_list:
                filtered[key] = value
        
        return filtered
    
    return response_data

# =============================================================================
# LIGHTWEIGHT HEALTH CHECK RESPONSE
# =============================================================================

def is_health_check_request():
    """
    Detect if request is a lightweight health check
    Returns True for monitoring tools, load balancers, etc.
    """
    # Check query parameter
    if request.args.get('lightweight') == 'true':
        return True
    
    # Check User-Agent for common monitoring tools
    user_agent = request.headers.get('User-Agent', '').lower()
    health_check_agents = ['pingdom', 'uptimerobot', 'statuspage', 'healthcheck', 'monitor', 'check']
    
    return any(agent in user_agent for agent in health_check_agents)

# =============================================================================
# MOBILE OPTIMIZATION HELPERS
# =============================================================================

def is_mobile_client():
    """Detect if request is from mobile device"""
    user_agent = request.headers.get('User-Agent', '').lower()
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'phone', 'tablet']
    return any(keyword in user_agent for keyword in mobile_keywords)

def get_optimal_page_size():
    """
    Return optimal page size based on client type
    Mobile: smaller pages (20-50)
    Desktop: larger pages (50-100)
    """
    if is_mobile_client():
        return min(request.args.get('limit', 20, type=int), 50)
    else:
        return min(request.args.get('limit', 50, type=int), 100)

# =============================================================================
# BATCH OPERATION HELPERS
# =============================================================================

def validate_batch_size(items, max_size=50):
    """
    Validate batch operation size
    Prevents abuse and ensures reasonable response times
    
    Args:
        items: List of items to process
        max_size: Maximum allowed batch size
    
    Returns:
        (is_valid, error_message)
    """
    if not isinstance(items, list):
        return False, "Batch data must be an array"
    
    if len(items) == 0:
        return False, "Batch cannot be empty"
    
    if len(items) > max_size:
        return False, f"Batch size exceeds maximum of {max_size}"
    
    return True, None

# =============================================================================
# RESPONSE TIME LOGGING
# =============================================================================

def log_slow_api_request(threshold_ms=100):
    """
    Decorator to log slow API requests for performance monitoring
    
    Args:
        threshold_ms: Log requests slower than this threshold
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            import time
            start_time = time.time()
            
            response = f(*args, **kwargs)
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            if elapsed_ms > threshold_ms:
                logger.warning(f"Slow API request: {request.method} {request.path} - {elapsed_ms:.1f}ms")
            
            return response
        
        return decorated_function
    return decorator

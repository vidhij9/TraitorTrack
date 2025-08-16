"""
Security Configuration for Production Environment
Optimized for 4+ Million Bags and 1000+ Concurrent Users
"""

from flask import request
from werkzeug.security import generate_password_hash
import logging
import re

logger = logging.getLogger(__name__)

# Security Headers Configuration
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; font-src 'self' data: https://cdnjs.cloudflare.com https://fonts.gstatic.com; img-src 'self' data: blob: https:; connect-src 'self';",
    'Referrer-Policy': 'strict-origin-when-cross-origin'
}

# Rate Limiting Configuration (per IP)
RATE_LIMITS = {
    'api_default': '100 per minute',
    'api_auth': '10 per minute',
    'api_search': '200 per minute',
    'api_create': '50 per minute',
    'web_default': '60 per minute',
    'web_auth': '5 per minute'
}

# Input Validation Patterns
VALIDATION_PATTERNS = {
    'qr_id': r'^[A-Za-z0-9\-_]{1,50}$',
    'username': r'^[a-zA-Z0-9_]{3,30}$',
    'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    'bag_name': r'^[A-Za-z0-9\s\-_]{1,100}$',
    'dispatch_area': r'^[A-Za-z0-9\s\-]{1,50}$'
}

# Session Security Configuration
SESSION_CONFIG = {
    'SESSION_COOKIE_SECURE': True,  # HTTPS only in production
    'SESSION_COOKIE_HTTPONLY': True,  # No JS access
    'SESSION_COOKIE_SAMESITE': 'Lax',  # CSRF protection
    'PERMANENT_SESSION_LIFETIME': 86400,  # 24 hours
    'SESSION_REFRESH_EACH_REQUEST': True
}

def validate_input(input_type, value):
    """Validate input against predefined patterns"""
    if input_type not in VALIDATION_PATTERNS:
        return False
    
    pattern = VALIDATION_PATTERNS[input_type]
    return bool(re.match(pattern, str(value)))

def sanitize_input(value):
    """Basic input sanitization"""
    if not value:
        return value
    
    # Remove dangerous characters
    value = str(value)
    value = re.sub(r'[<>\"\'%;()&+]', '', value)
    value = value.strip()
    
    # Limit length
    max_length = 200
    if len(value) > max_length:
        value = value[:max_length]
    
    return value

def apply_security_headers(response):
    """Apply security headers to response"""
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    return response

def check_request_safety(request):
    """Check if request appears safe"""
    # Check for SQL injection patterns
    dangerous_patterns = [
        r'(\bunion\b.*\bselect\b|\bselect\b.*\bunion\b)',
        r'(;|\-\-|\/\*|\*\/|xp_|sp_|0x)',
        r'(\bdrop\b|\bdelete\b|\btruncate\b|\balter\b)',
        r'(<script|javascript:|onerror=|onload=)',
    ]
    
    request_data = str(request.args) + str(request.form) + str(request.get_json(silent=True))
    
    for pattern in dangerous_patterns:
        if re.search(pattern, request_data, re.IGNORECASE):
            logger.warning(f"Potentially dangerous request detected: {request.remote_addr}")
            return False
    
    return True

def hash_password(password):
    """Generate secure password hash"""
    return generate_password_hash(password)

def get_client_ip(request):
    """Get real client IP considering proxy headers"""
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
    elif request.environ.get('HTTP_X_REAL_IP'):
        return request.environ['HTTP_X_REAL_IP']
    else:
        return request.environ.get('REMOTE_ADDR', 'unknown')

# Connection limits for database
DB_CONNECTION_LIMITS = {
    'pool_size': 20,  # Optimized for stability
    'max_overflow': 30,
    'pool_timeout': 10,
    'pool_recycle': 1800,  # 30 minutes
    'max_connections': 200  # Total database connections
}

# API Security Configuration
API_SECURITY = {
    'require_api_key': False,  # Can be enabled for additional security
    'max_request_size': 10 * 1024 * 1024,  # 10MB max request size
    'allowed_origins': ['*'],  # Configure for production
    'max_batch_size': 100,  # Maximum items in batch operations
}

def init_security(app):
    """Initialize security configuration for Flask app"""
    # Apply session configuration
    app.config.update(SESSION_CONFIG)
    
    # Set maximum content length
    app.config['MAX_CONTENT_LENGTH'] = API_SECURITY['max_request_size']
    
    # Add security headers to all responses
    @app.after_request
    def add_security_headers(response):
        return apply_security_headers(response)
    
    # Log security initialization
    logger.info("Security configuration initialized for production")
    
    return app
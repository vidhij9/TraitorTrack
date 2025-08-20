"""
Production Configuration for TraceTrack
Optimized for 50+ concurrent users with CDN and monitoring
"""

import os
from datetime import timedelta

class ProductionConfig:
    """Production configuration settings"""
    
    # Flask Settings
    DEBUG = False
    TESTING = False
    PROPAGATE_EXCEPTIONS = True
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Database Pool Configuration
    SQLALCHEMY_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', 50))
    SQLALCHEMY_MAX_OVERFLOW = int(os.environ.get('DB_MAX_OVERFLOW', 100))
    SQLALCHEMY_POOL_RECYCLE = 300
    SQLALCHEMY_POOL_TIMEOUT = 30
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'connect_args': {
            'connect_timeout': 10,
            'application_name': 'tracetrack_prod',
            'options': '-c statement_timeout=60000 -c idle_in_transaction_session_timeout=30000'
        }
    }
    
    # Performance Settings
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1 year for static files
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = False
    
    # Cache Configuration
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_THRESHOLD = 1000
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = 'memory://'
    RATELIMIT_DEFAULT = '500 per minute'
    RATELIMIT_HEADERS_ENABLED = True
    
    # Security Headers
    SECURITY_HEADERS = {
        'X-Frame-Options': 'SAMEORIGIN',
        'X-Content-Type-Options': 'nosniff',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net"
    }
    
    # CDN Configuration
    CDN_DOMAIN = os.environ.get('CDN_DOMAIN', '')
    USE_CDN = bool(CDN_DOMAIN)
    STATIC_URL = f'https://{CDN_DOMAIN}/static' if USE_CDN else '/static'
    
    # Monitoring
    ENABLE_MONITORING = True
    LOG_LEVEL = 'INFO'
    
    @staticmethod
    def init_app(app):
        """Initialize production application"""
        # Add security headers
        @app.after_request
        def add_security_headers(response):
            for header, value in ProductionConfig.SECURITY_HEADERS.items():
                response.headers[header] = value
            return response
        
        # Enable CDN for static files
        if ProductionConfig.USE_CDN:
            app.config['STATIC_URL'] = ProductionConfig.STATIC_URL
        
        # Configure logging
        import logging
        logging.basicConfig(
            level=getattr(logging, ProductionConfig.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Add performance monitoring
        if ProductionConfig.ENABLE_MONITORING:
            @app.before_request
            def log_request_info():
                app.logger.info('Request: %s %s', request.method, request.url)
            
            @app.after_request
            def log_response_info(response):
                app.logger.info('Response: %s', response.status)
                return response

# Apply configuration on import
def apply_production_config(app):
    """Apply production configuration to Flask app"""
    app.config.from_object(ProductionConfig)
    ProductionConfig.init_app(app)
    print("✅ Production configuration applied")
    print(f"  - Database pool: {ProductionConfig.SQLALCHEMY_POOL_SIZE} + {ProductionConfig.SQLALCHEMY_MAX_OVERFLOW} overflow")
    print(f"  - CDN: {'Enabled' if ProductionConfig.USE_CDN else 'Disabled'}")
    print(f"  - Security headers: Enabled")
    print(f"  - Rate limiting: {ProductionConfig.RATELIMIT_DEFAULT}")
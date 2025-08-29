"""
Production-ready configuration for handling 20+ concurrent users
with intensive operations across all APIs
"""
import os
from datetime import timedelta

class ProductionConfig:
    """Optimized configuration for production deployment"""
    
    # Database configuration for high concurrency
    DATABASE_CONFIG = {
        # Connection pool settings optimized for 50+ concurrent users
        "pool_size": 60,  # Increased base pool size for more concurrent connections
        "max_overflow": 40,  # Additional connections for peak load
        "pool_recycle": 3600,  # Recycle connections every hour
        "pool_pre_ping": True,  # Test connections before use
        "pool_timeout": 30,  # Wait up to 30 seconds for connection
        "echo": False,  # Disable SQL logging for performance
        "echo_pool": False,
        "pool_use_lifo": True,  # LIFO for better connection reuse
        
        # PostgreSQL specific optimizations
        "connect_args": {
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
            "connect_timeout": 10,
            "application_name": "TraceTrack_Production",
            "options": "-c statement_timeout=60000 -c idle_in_transaction_session_timeout=60000"  # 60 second timeouts
        },
        
        # Query execution settings
        "execution_options": {
            "isolation_level": "READ COMMITTED",
            "postgresql_readonly": False,
            "postgresql_deferrable": False
        }
    }
    
    # Flask configuration
    FLASK_CONFIG = {
        # Session configuration
        "SESSION_COOKIE_SECURE": True,  # Use HTTPS in production
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "PERMANENT_SESSION_LIFETIME": timedelta(hours=24),
        "SESSION_REFRESH_EACH_REQUEST": False,
        
        # Security
        "WTF_CSRF_TIME_LIMIT": None,
        "WTF_CSRF_SSL_STRICT": False,
        "WTF_CSRF_ENABLED": True,
        
        # Performance
        "SEND_FILE_MAX_AGE_DEFAULT": 3600,  # Cache static files
        "MAX_CONTENT_LENGTH": 16 * 1024 * 1024,  # 16MB max upload
        
        # Database
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_ECHO": False,
        "SQLALCHEMY_RECORD_QUERIES": False,
        
        # Request handling
        "PROPAGATE_EXCEPTIONS": False,
        "PRESERVE_CONTEXT_ON_EXCEPTION": False
    }
    
    # Gunicorn worker configuration
    WORKER_CONFIG = {
        "bind": "0.0.0.0:5000",
        "workers": 4,  # 4 worker processes
        "threads": 2,  # 2 threads per worker
        "worker_class": "gthread",  # Threaded workers
        "worker_connections": 1000,
        "timeout": 60,
        "graceful_timeout": 30,
        "keepalive": 5,
        "max_requests": 2000,
        "max_requests_jitter": 100,
        "preload_app": True,
        "accesslog": "-",
        "errorlog": "-",
        "loglevel": "warning",
        "capture_output": True
    }
    
    # Rate limiting for API endpoints
    RATE_LIMITS = {
        "default": "10000 per hour",  # Default for all endpoints
        "api": "5000 per hour",  # API endpoints
        "auth": "100 per hour",  # Authentication endpoints
        "scanning": "2000 per hour"  # Scanning operations
    }
    
    # Caching configuration
    CACHE_CONFIG = {
        "CACHE_TYPE": "simple",  # Use simple in-memory cache
        "CACHE_DEFAULT_TIMEOUT": 300,  # 5 minutes default
        "CACHE_THRESHOLD": 1000,  # Max cached items
        "CACHE_KEY_PREFIX": "tracetrack_"
    }
    
    @classmethod
    def apply_to_app(cls, app):
        """Apply production configuration to Flask app"""
        # Apply Flask configuration
        app.config.update(cls.FLASK_CONFIG)
        
        # Apply database configuration
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = cls.DATABASE_CONFIG
        
        # Set environment-specific settings
        if os.environ.get("ENVIRONMENT") == "production":
            app.config["SESSION_COOKIE_SECURE"] = True
            app.config["PREFERRED_URL_SCHEME"] = "https"
        else:
            app.config["SESSION_COOKIE_SECURE"] = False
            app.config["PREFERRED_URL_SCHEME"] = "http"
        
        return app
    
    @classmethod
    def get_gunicorn_config(cls):
        """Get Gunicorn configuration for production deployment"""
        return cls.WORKER_CONFIG
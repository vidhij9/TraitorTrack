"""
Configuration module for Traitor Track application.
Centralizes all configuration settings with environment variable support.
"""
import os
from datetime import timedelta


class Config:
    """Base configuration class with settings common to all environments."""
    # Flask settings
    SECRET_KEY = os.environ.get("SESSION_SECRET") or "development-key-not-for-production"
    DEBUG = False
    TESTING = False
    
    # SQLAlchemy settings - Optimized for high-performance
    # Default database URI (will be overridden by specific environments)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 50,                # Larger connection pool for better concurrent performance
        "max_overflow": 60,             # Allow more overflow connections during peak loads
        "pool_recycle": 300,            # Recycle connections every 5 minutes to prevent stale connections
        "pool_pre_ping": True,          # Test connections before use to detect broken connections
        "pool_timeout": 20,             # Faster timeout for connection pool requests
        "pool_use_lifo": True,          # LIFO queue to maximize connection reuse and performance
        "connect_args": {               # PostgreSQL specific optimizations
            "keepalives": 1,            # Enable TCP keepalives
            "keepalives_idle": 60,      # Idle time before sending keepalive probes
            "keepalives_interval": 10,  # Time between keepalive probes
            "keepalives_count": 3,      # Number of probes before connection is considered dead
            "options": "-c statement_timeout=90000"  # 90-second statement timeout
        }
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Disable unnecessary event tracking
    SQLALCHEMY_ECHO = False                 # Disable SQL echoing in production for better performance
    
    # Security settings
    SESSION_COOKIE_SECURE = True            # Only send cookies over HTTPS
    SESSION_COOKIE_HTTPONLY = True          # Prevent JavaScript access to session cookie
    SESSION_COOKIE_SAMESITE = 'Lax'         # Restrict cookie sending to same-site requests
    PERMANENT_SESSION_LIFETIME = 1800       # Session timeout after 30 minutes
    SESSION_REFRESH_EACH_REQUEST = True     # Update session with each request
    
    # Security features
    SECURITY_STRICT_MODE = False            # If True, block suspicious requests instead of just logging
    PREFERRED_URL_SCHEME = 'https'          # Use HTTPS for generated URLs
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024   # Limit upload size to 10MB
    SEND_FILE_MAX_AGE_DEFAULT = 31536000    # Cache static files for 1 year
    JSON_SORT_KEYS = False                  # Don't sort JSON keys for better performance
    
    # Rate limiting settings
    RATELIMIT_DEFAULT = "200 per day"
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_STRATEGY = "fixed-window"
    
    # Application settings
    QR_VALIDATION_ENABLED = True
    CHILD_BAGS_PER_PARENT = 5
    
    # Account security
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION = 15 * 60  # 15 minutes
    
    # Password requirements
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGITS = True
    PASSWORD_REQUIRE_SPECIAL = True


class DevelopmentConfig(Config):
    """Configuration for development environment."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False  # Allow non-HTTPS for development
    SECURITY_STRICT_MODE = False   # More lenient security in development
    
    # Development-specific database
    SQLALCHEMY_DATABASE_URI = os.environ.get("DEV_DATABASE_URL") or os.environ.get("DATABASE_URL")
    
    # Smaller connection pool for development
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_timeout": 10,
        "pool_use_lifo": True,
        "connect_args": {
            "keepalives": 1,
            "keepalives_idle": 60,
            "keepalives_interval": 10,
            "keepalives_count": 3
        }
    }
    
    # Faster development with more instant feedback
    SEND_FILE_MAX_AGE_DEFAULT = 0  # Don't cache static files
    TEMPLATES_AUTO_RELOAD = True   # Auto-reload templates on change
    SQLALCHEMY_ECHO = True         # Enable SQL echoing for development debugging


class TestingConfig(Config):
    """Configuration for testing environment."""
    TESTING = True
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False  # Disable CSRF for testing
    
    # Use in-memory database for testing
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    """Configuration for production environment."""
    # More strict production settings
    SESSION_COOKIE_SECURE = True
    SECURITY_STRICT_MODE = True
    
    # Production-specific database
    SQLALCHEMY_DATABASE_URI = os.environ.get("PROD_DATABASE_URL") or os.environ.get("DATABASE_URL")
    
    # Optimized production database settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 50,
        "max_overflow": 60,
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_timeout": 20,
        "pool_use_lifo": True,
        "connect_args": {
            "keepalives": 1,
            "keepalives_idle": 60,
            "keepalives_interval": 10,
            "keepalives_count": 3,
            "options": "-c statement_timeout=90000"
        }
    }
    
    # Ensure these are set in production
    def __init__(self):
        if not os.environ.get("SESSION_SECRET"):
            raise ValueError("SESSION_SECRET must be set in production")
        # Check for production database URL first, then fallback to generic
        if not (os.environ.get("PROD_DATABASE_URL") or os.environ.get("DATABASE_URL")):
            raise ValueError("PROD_DATABASE_URL or DATABASE_URL must be set in production")


# Create a mapping of environment names to configuration classes
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}

# Default to development if not specified
active_config = config_by_name.get(os.environ.get('FLASK_ENV', 'development'))

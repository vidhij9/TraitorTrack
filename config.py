"""
Configuration module for TraceTrack application.
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
    
    # SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 30,                # Increase connection pool size for high concurrency
        "max_overflow": 40,             # Allow additional connections when pool is full
        "pool_recycle": 300,            # Recycle connections every 5 minutes
        "pool_pre_ping": True,          # Verify connections before using them
        "pool_timeout": 30,             # Maximum time to wait for connection from pool
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
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
    
    # Faster development with more instant feedback
    SEND_FILE_MAX_AGE_DEFAULT = 0  # Don't cache static files
    TEMPLATES_AUTO_RELOAD = True   # Auto-reload templates on change


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
    
    # Ensure these are set in production
    def __init__(self):
        if not os.environ.get("SESSION_SECRET"):
            raise ValueError("SESSION_SECRET must be set in production")
        if not os.environ.get("DATABASE_URL"):
            raise ValueError("DATABASE_URL must be set in production")


# Create a mapping of environment names to configuration classes
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}

# Default to development if not specified
active_config = config_by_name.get(os.environ.get('FLASK_ENV', 'development'))
"""
Unified configuration for the restructured TraceTrack application.
Consolidates all configuration settings in one place.
"""

import os
from datetime import timedelta

class Config:
    """Base configuration with common settings"""
    
    # Application Settings
    SECRET_KEY = os.environ.get('SESSION_SECRET', 'dev-key-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    TESTING = False
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 50,
        'max_overflow': 60,
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'pool_timeout': 20,
        'pool_use_lifo': True,
        'connect_args': {
            'keepalives': 1,
            'keepalives_idle': 60,
            'keepalives_interval': 10,
            'keepalives_count': 3,
            'options': '-c statement_timeout=90000'
        }
    }
    
    # Security Settings
    SESSION_COOKIE_SECURE = os.environ.get('ENVIRONMENT') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    
    # Authentication Settings
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION = 900  # 15 minutes in seconds
    PASSWORD_MIN_LENGTH = 8
    
    # Rate Limiting
    RATELIMIT_DEFAULT = "200 per day"
    RATELIMIT_STORAGE_URI = "memory://"
    
    # Application Features
    QR_VALIDATION_ENABLED = True
    CHILD_BAGS_PER_PARENT = 5
    
    # File Upload
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
    
    # Cache Settings
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    LOG_LEVEL = 'WARNING'

class TestingConfig(Config):
    """Testing environment configuration"""
    TESTING = True
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Configuration mapping
config_mapping = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('ENVIRONMENT', 'development')
    return config_mapping.get(env, DevelopmentConfig)
"""
Deployment configuration for TraceTrack.
Optimizes application settings for production deployment.
"""

import os

# Set production mode
os.environ['FLASK_ENV'] = 'production'

# Security settings
CSRF_ENABLED = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
PERMANENT_SESSION_LIFETIME = 3600  # 1 hour

# Performance optimizations
SQLALCHEMY_POOL_SIZE = 100
SQLALCHEMY_MAX_OVERFLOW = 20
SQLALCHEMY_POOL_RECYCLE = 300
SQLALCHEMY_POOL_TIMEOUT = 10

# Cache settings
CACHE_SIZE_LIMIT = 5000
CACHE_DISK_ENABLED = True

# Task queue settings
MAX_QUEUE_SIZE = 5000
MAX_TASK_HISTORY = 1000

# Mobile app settings
MOBILE_API_KEY_HEADER = "X-TraceTrack-Api-Key"
ENABLE_MOBILE_API = True
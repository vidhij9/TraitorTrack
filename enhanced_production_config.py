#!/usr/bin/env python3
"""
Enhanced Production Configuration for TraceTrack
Optimized for scalability and high user load
"""

import os
import multiprocessing
import logging
from datetime import datetime

# =============================================================================
# GUNICORN CONFIGURATION
# =============================================================================

# Server configuration
bind = "0.0.0.0:5000"
workers = min(multiprocessing.cpu_count() * 2 + 1, 8)  # Cap at 8 workers
worker_class = "gevent"  # Async worker for high concurrency
worker_connections = 2000  # Connections per worker
threads = 4  # Threads per worker

# Connection handling
backlog = 2048  # Maximum pending connections
keepalive = 5  # Seconds to keep connections alive

# Timeouts
timeout = 60  # Worker timeout
graceful_timeout = 30  # Graceful shutdown timeout

# Performance tuning
max_requests = 10000  # Restart workers after this many requests
max_requests_jitter = 1000  # Randomize worker restarts
preload_app = True  # Load app before forking workers

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"  # Log to stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'tracetrack-production-enhanced'

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Enhanced features
enable_stdio_inheritance = True
capture_output = True
reload = False
daemon = False

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# Database connection pool settings
DB_POOL_SIZE = 20
DB_MAX_OVERFLOW = 30
DB_POOL_TIMEOUT = 30
DB_POOL_RECYCLE = 3600
DB_POOL_PRE_PING = True

# =============================================================================
# CACHE CONFIGURATION
# =============================================================================

# Redis cache settings
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
REDIS_SSL = os.getenv('REDIS_SSL', 'false').lower() == 'true'

# Cache TTL settings
CACHE_TTL_DEFAULT = 300  # 5 minutes
CACHE_TTL_DASHBOARD = 60  # 1 minute
CACHE_TTL_USER_DATA = 1800  # 30 minutes
CACHE_TTL_BILL_DATA = 600  # 10 minutes

# =============================================================================
# PERFORMANCE MONITORING
# =============================================================================

# Performance monitoring settings
ENABLE_PERFORMANCE_MONITORING = True
PERFORMANCE_LOG_INTERVAL = 60  # seconds
SLOW_QUERY_THRESHOLD = 1000  # milliseconds
ERROR_LOG_ENABLED = True

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

# Security settings
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
PERMANENT_SESSION_LIFETIME = 3600  # 1 hour

# Rate limiting
RATE_LIMIT_DEFAULT = "100 per minute"
RATE_LIMIT_API = "200 per minute"
RATE_LIMIT_AUTH = "10 per minute"

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Logging settings
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = os.getenv('LOG_FILE', '/var/log/tracetrack/app.log')

# =============================================================================
# WORKER LIFECYCLE HOOKS
# =============================================================================

def on_starting(server):
    """Called just before the master process is initialized"""
    server.log.info("🚀 Starting Enhanced TraceTrack Production Server")
    server.log.info(f"Workers: {workers}, Worker Class: {worker_class}")
    server.log.info(f"CPU Count: {multiprocessing.cpu_count()}")

def on_reload(server):
    """Called to recycle workers during a reload"""
    server.log.info("🔄 Reloading Enhanced TraceTrack workers")

def when_ready(server):
    """Called just after the server is started"""
    server.log.info("✅ Enhanced TraceTrack server is ready")
    server.log.info(f"Listening on: {server.address}")
    server.log.info(f"Process ID: {os.getpid()}")

def worker_int(worker):
    """Called when a worker receives the INT or QUIT signal"""
    worker.log.info("⚠️ Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked"""
    server.log.info(f"🔧 Pre-fork worker {worker.pid}")

def post_fork(server, worker):
    """Called just after a worker has been forked"""
    worker.log.info(f"✅ Post-fork worker {worker.pid}")
    
    # Initialize worker-specific configurations
    try:
        # Import and apply enhancements
        from enhancement_features import apply_all_enhancements
        worker.log.info("🔧 Applying enhancements to worker")
        apply_all_enhancements()
        worker.log.info("✅ Enhancements applied successfully")
    except Exception as e:
        worker.log.error(f"❌ Failed to apply enhancements: {e}")

def worker_exit(server, worker):
    """Called just after a worker has been exited"""
    server.log.info(f"👋 Worker {worker.pid} exited")

# =============================================================================
# HEALTH CHECK CONFIGURATION
# =============================================================================

# Health check settings
HEALTH_CHECK_ENABLED = True
HEALTH_CHECK_INTERVAL = 30  # seconds
HEALTH_CHECK_TIMEOUT = 10  # seconds

# =============================================================================
# AUTO-SCALING CONFIGURATION
# =============================================================================

# Auto-scaling settings
AUTO_SCALE_ENABLED = os.getenv('AUTO_SCALE_ENABLED', 'false').lower() == 'true'
AUTO_SCALE_MIN_WORKERS = 2
AUTO_SCALE_MAX_WORKERS = 8
AUTO_SCALE_CPU_THRESHOLD = 70  # percentage
AUTO_SCALE_MEMORY_THRESHOLD = 80  # percentage

# =============================================================================
# MONITORING AND METRICS
# =============================================================================

# Metrics collection
METRICS_ENABLED = True
METRICS_INTERVAL = 60  # seconds
METRICS_RETENTION = 24 * 60 * 60  # 24 hours in seconds

# Performance thresholds
RESPONSE_TIME_WARNING = 1000  # milliseconds
RESPONSE_TIME_CRITICAL = 5000  # milliseconds
ERROR_RATE_WARNING = 5  # percentage
ERROR_RATE_CRITICAL = 10  # percentage

# =============================================================================
# BACKUP AND RECOVERY
# =============================================================================

# Backup settings
BACKUP_ENABLED = os.getenv('BACKUP_ENABLED', 'true').lower() == 'true'
BACKUP_INTERVAL = 24 * 60 * 60  # 24 hours in seconds
BACKUP_RETENTION_DAYS = 7

# =============================================================================
# ENVIRONMENT-SPECIFIC SETTINGS
# =============================================================================

# Environment detection
ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')

if ENVIRONMENT == 'development':
    # Development settings
    workers = 1
    reload = True
    loglevel = "debug"
    CACHE_TTL_DEFAULT = 60
    PERFORMANCE_MONITORING = False
    
elif ENVIRONMENT == 'staging':
    # Staging settings
    workers = min(multiprocessing.cpu_count(), 4)
    loglevel = "info"
    CACHE_TTL_DEFAULT = 300
    
elif ENVIRONMENT == 'production':
    # Production settings (default)
    pass

# =============================================================================
# CONFIGURATION VALIDATION
# =============================================================================

def validate_configuration():
    """Validate the configuration settings"""
    errors = []
    
    # Validate worker count
    if workers < 1:
        errors.append("Workers must be at least 1")
    
    # Validate timeouts
    if timeout < graceful_timeout:
        errors.append("Timeout must be greater than graceful_timeout")
    
    # Validate database settings
    if DB_POOL_SIZE < 1:
        errors.append("Database pool size must be at least 1")
    
    # Validate cache settings
    if CACHE_TTL_DEFAULT < 0:
        errors.append("Cache TTL must be non-negative")
    
    if errors:
        raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    return True

# Validate configuration on import
try:
    validate_configuration()
    print(f"✅ Enhanced production configuration loaded successfully")
    print(f"Environment: {ENVIRONMENT}")
    print(f"Workers: {workers}")
    print(f"Worker Class: {worker_class}")
    print(f"Database Pool Size: {DB_POOL_SIZE}")
except Exception as e:
    print(f"❌ Configuration validation failed: {e}")
    raise

# =============================================================================
# CONFIGURATION EXPORT
# =============================================================================

def get_configuration_summary():
    """Get a summary of the current configuration"""
    return {
        'environment': ENVIRONMENT,
        'workers': workers,
        'worker_class': worker_class,
        'worker_connections': worker_connections,
        'timeout': timeout,
        'max_requests': max_requests,
        'database_pool_size': DB_POOL_SIZE,
        'cache_ttl_default': CACHE_TTL_DEFAULT,
        'rate_limit_default': RATE_LIMIT_DEFAULT,
        'performance_monitoring': ENABLE_PERFORMANCE_MONITORING,
        'auto_scale_enabled': AUTO_SCALE_ENABLED,
        'health_check_enabled': HEALTH_CHECK_ENABLED,
        'backup_enabled': BACKUP_ENABLED
    }

if __name__ == "__main__":
    # Print configuration summary when run directly
    import json
    config_summary = get_configuration_summary()
    print("Enhanced Production Configuration Summary:")
    print(json.dumps(config_summary, indent=2))
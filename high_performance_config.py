"""
High-performance configuration for TraceTrack
Optimized for 50+ concurrent users and 800,000+ bags
"""

import os
import logging
from datetime import timedelta

# Disable unnecessary logging for performance
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)
logging.getLogger('sqlalchemy.pool').setLevel(logging.ERROR)

class HighPerformanceConfig:
    """Configuration optimized for high load and concurrent users"""
    
    # Database Configuration for 50+ concurrent users
    DATABASE_CONFIG = {
        "pool_size": 200,                    # Base connections for 50+ users
        "max_overflow": 400,                 # Allow up to 600 total connections
        "pool_recycle": 600,                 # Recycle every 10 minutes
        "pool_pre_ping": True,               # Test connections before use
        "pool_timeout": 60,                  # Wait up to 60 seconds
        "echo": False,                       # Disable SQL logging
        "echo_pool": False,                  # Disable pool logging
        "pool_use_lifo": True,               # Use LIFO for better cache locality
        "connect_args": {
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 10,
            "connect_timeout": 30,
            "application_name": "TraceTrack_HighPerf",
            "options": "-c statement_timeout=60000 -c idle_in_transaction_session_timeout=30000 -c jit=on -c random_page_cost=1.1"
        }
    }
    
    # Redis Configuration for caching
    REDIS_CONFIG = {
        'REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
        'REDIS_MAX_CONNECTIONS': 100,
        'REDIS_DECODE_RESPONSES': True,
        'REDIS_HEALTH_CHECK_INTERVAL': 30
    }
    
    # Session Configuration
    SESSION_CONFIG = {
        'SESSION_TYPE': 'filesystem',        # Use filesystem for better performance
        'SESSION_FILE_DIR': '/tmp/flask_session',
        'SESSION_PERMANENT': False,
        'PERMANENT_SESSION_LIFETIME': timedelta(hours=24),
        'SESSION_USE_SIGNER': True,
        'SESSION_KEY_PREFIX': 'tracetrack:',
        'SESSION_COOKIE_SECURE': False,      # Set True for production HTTPS
        'SESSION_COOKIE_HTTPONLY': True,
        'SESSION_COOKIE_SAMESITE': 'Lax'
    }
    
    # Rate Limiting Configuration
    RATE_LIMIT_CONFIG = {
        'default': ["1000000 per day", "100000 per hour", "10000 per minute"],
        'api': ["50000 per hour", "5000 per minute"],
        'auth': ["1000 per hour", "100 per minute"],
        'scan': ["100000 per hour", "10000 per minute"]
    }
    
    # Query Optimization Settings
    QUERY_CONFIG = {
        'batch_size': 1000,                  # Process in batches of 1000
        'query_timeout': 30000,               # 30 seconds
        'max_results': 10000,                # Maximum results per query
        'use_prepared_statements': True,
        'enable_query_cache': True
    }
    
    # Cache TTL Settings (in seconds)
    CACHE_TTL = {
        'user_data': 300,                    # 5 minutes
        'bag_data': 600,                     # 10 minutes
        'scan_data': 60,                     # 1 minute
        'bill_data': 1800,                   # 30 minutes
        'stats': 30,                         # 30 seconds
        'search_results': 120                # 2 minutes
    }
    
    # Application Performance Settings
    APP_CONFIG = {
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB max request size
        'SEND_FILE_MAX_AGE_DEFAULT': 31536000,   # 1 year for static files
        'JSONIFY_PRETTYPRINT_REGULAR': False,    # Disable pretty print for performance
        'JSON_SORT_KEYS': False,                 # Don't sort JSON keys
        'PROPAGATE_EXCEPTIONS': False,           # Don't propagate exceptions in production
        'TRAP_HTTP_EXCEPTIONS': False            # Don't trap HTTP exceptions
    }
    
    @classmethod
    def apply_to_app(cls, app):
        """Apply high-performance configuration to Flask app"""
        # Apply database configuration
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = cls.DATABASE_CONFIG
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SQLALCHEMY_RECORD_QUERIES'] = False
        
        # Apply session configuration
        for key, value in cls.SESSION_CONFIG.items():
            app.config[key] = value
        
        # Apply app configuration
        for key, value in cls.APP_CONFIG.items():
            app.config[key] = value
        
        # Optimize JSON encoder
        app.json.compact = True
        
        return app
    
    @classmethod
    def get_worker_config(cls):
        """Get optimized Gunicorn worker configuration"""
        import multiprocessing
        
        # Calculate optimal workers for 50+ concurrent users
        cpu_count = multiprocessing.cpu_count()
        
        return {
            'workers': min(cpu_count * 4, 16),     # 4 workers per CPU, max 16
            'worker_class': 'sync',                # Use sync workers for stability
            'worker_connections': 1000,            # High connection count
            'max_requests': 10000,                 # Restart workers after 10k requests
            'max_requests_jitter': 1000,          # Add jitter to prevent simultaneous restarts
            'timeout': 60,                         # 60 second timeout
            'graceful_timeout': 30,               # 30 second graceful shutdown
            'keepalive': 5,                        # Keep connections alive for 5 seconds
            'threads': 4,                          # 4 threads per worker
            'backlog': 2048,                       # Large backlog for high load
            'preload_app': True,                   # Preload app for faster worker starts
            'daemon': False
        }

# Fast authentication optimizations
class OptimizedAuth:
    """Optimized authentication for high concurrency"""
    
    @staticmethod
    def create_session_pool():
        """Create a session pool for authentication"""
        from werkzeug.local import LocalStack
        return LocalStack()
    
    @staticmethod
    def optimize_password_hashing():
        """Use faster password hashing for high load"""
        import hashlib
        import hmac
        
        def fast_hash(password, salt=None):
            if salt is None:
                salt = os.urandom(32)
            pwdhash = hashlib.pbkdf2_hmac('sha256', 
                                          password.encode('utf-8'), 
                                          salt, 
                                          100000,  # Reduced iterations for speed
                                          dklen=32)
            return salt + pwdhash
        
        def fast_verify(password, stored):
            salt = stored[:32]
            stored_hash = stored[32:]
            pwdhash = hashlib.pbkdf2_hmac('sha256',
                                          password.encode('utf-8'),
                                          salt,
                                          100000,
                                          dklen=32)
            return hmac.compare_digest(stored_hash, pwdhash)
        
        return fast_hash, fast_verify

# Query optimization utilities
class QueryOptimizer:
    """Optimize database queries for large datasets"""
    
    @staticmethod
    def batch_insert(session, model, data, batch_size=1000):
        """Batch insert for better performance"""
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            session.bulk_insert_mappings(model, batch)
            session.commit()
    
    @staticmethod
    def paginated_query(query, page_size=1000):
        """Paginate large queries"""
        offset = 0
        while True:
            results = query.limit(page_size).offset(offset).all()
            if not results:
                break
            yield results
            offset += page_size
    
    @staticmethod
    def optimized_count(session, model, filters=None):
        """Optimized count query"""
        from sqlalchemy import func
        query = session.query(func.count(model.id))
        if filters:
            query = query.filter(filters)
        return query.scalar()

# Connection pool manager
class ConnectionPoolManager:
    """Manage database connections efficiently"""
    
    _pools = {}
    
    @classmethod
    def get_pool(cls, name='default'):
        """Get or create a connection pool"""
        if name not in cls._pools:
            from sqlalchemy import create_engine
            from sqlalchemy.pool import QueuePool
            
            database_url = os.environ.get('DATABASE_URL')
            cls._pools[name] = create_engine(
                database_url,
                poolclass=QueuePool,
                **HighPerformanceConfig.DATABASE_CONFIG
            )
        return cls._pools[name]
    
    @classmethod
    def cleanup_pools(cls):
        """Clean up all connection pools"""
        for pool in cls._pools.values():
            pool.dispose()
        cls._pools.clear()

# Cache manager for high-performance caching
class CacheManager:
    """Manage caching for high performance"""
    
    _cache = {}
    _timestamps = {}
    
    @classmethod
    def get(cls, key, default=None):
        """Get cached value"""
        import time
        
        if key in cls._cache:
            timestamp = cls._timestamps.get(key, 0)
            ttl = HighPerformanceConfig.CACHE_TTL.get(key.split(':')[0], 60)
            
            if time.time() - timestamp < ttl:
                return cls._cache[key]
            else:
                del cls._cache[key]
                del cls._timestamps[key]
        
        return default
    
    @classmethod
    def set(cls, key, value):
        """Set cached value"""
        import time
        cls._cache[key] = value
        cls._timestamps[key] = time.time()
    
    @classmethod
    def delete(cls, key):
        """Delete cached value"""
        if key in cls._cache:
            del cls._cache[key]
            del cls._timestamps[key]
    
    @classmethod
    def clear(cls):
        """Clear all cache"""
        cls._cache.clear()
        cls._timestamps.clear()
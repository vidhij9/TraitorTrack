"""
Production Optimization Configuration
Optimizes database pooling, caching, and worker configuration for high concurrency
"""

from app_clean import app, db
from sqlalchemy import event, text
from sqlalchemy.pool import Pool
import logging

logger = logging.getLogger(__name__)

def optimize_production_config():
    """Apply production optimizations for better performance"""
    
    # 1. Database Pool Configuration
    app.config.update({
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'pool_size': 100,           # Increased from 50
            'max_overflow': 200,         # Increased from 100
            'pool_timeout': 10,          # Reduced from 30
            'pool_recycle': 300,         # Keep at 5 minutes
            'pool_pre_ping': True,       # Verify connections
            'connect_args': {
                'connect_timeout': 5,
                'options': '-c statement_timeout=15000'  # 15 second statement timeout
            }
        },
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SQLALCHEMY_ECHO': False  # Disable SQL logging for performance
    })
    
    # 2. Apply configuration to existing engine
    if hasattr(db.engine, 'pool'):
        db.engine.pool._size = 100
        db.engine.pool._max_overflow = 200
        db.engine.pool._timeout = 10
    
    # 3. Connection Pool Events for Better Performance
    @event.listens_for(Pool, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """Optimize database connection settings"""
        cursor = dbapi_conn.cursor()
        try:
            # PostgreSQL optimizations
            cursor.execute("SET work_mem = '256MB'")
            cursor.execute("SET effective_cache_size = '4GB'")
            cursor.execute("SET random_page_cost = 1.0")
            cursor.execute("SET jit = on")
            cursor.execute("SET max_parallel_workers_per_gather = 4")
            cursor.execute("SET statement_timeout = 15000")  # 15 seconds
            cursor.execute("SET idle_in_transaction_session_timeout = 30000")  # 30 seconds
            cursor.close()
        except Exception as e:
            logger.warning(f"Could not set connection parameters: {e}")
            cursor.close()
    
    # 4. Gunicorn Worker Configuration (for reference)
    gunicorn_config = {
        'workers': 8,  # Increased from 4
        'worker_class': 'gevent',  # Async workers
        'worker_connections': 2000,
        'backlog': 2048,
        'max_requests': 5000,  # Reduced from 10000 for more frequent recycling
        'max_requests_jitter': 500,
        'timeout': 30,  # Reduced from 60
        'graceful_timeout': 30,
        'keepalive': 5,
        'threads': 4  # If using gthread worker class
    }
    
    logger.info(f"Production optimizations applied:")
    logger.info(f"  - Database pool: 100 base + 200 overflow connections")
    logger.info(f"  - Statement timeout: 15 seconds")
    logger.info(f"  - Worker configuration optimized for high concurrency")
    
    return gunicorn_config

# Apply optimizations when imported within app context
def initialize():
    """Initialize production optimizations within app context"""
    try:
        optimize_production_config()
        logger.info("✅ Production configuration optimized")
    except Exception as e:
        logger.error(f"Failed to apply production optimizations: {e}")
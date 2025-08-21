
import os
from sqlalchemy import create_engine, pool
from sqlalchemy.pool import NullPool, QueuePool
import logging

logger = logging.getLogger(__name__)

class OptimizedDatabasePool:
    '''Optimized database connection pooling for high concurrency'''
    
    @staticmethod
    def get_engine_config():
        '''Get optimized engine configuration'''
        return {
            "pool_size": 300,  # Increased for 50+ users
            "max_overflow": 500,  # Allow up to 800 total connections
            "pool_recycle": 300,  # Recycle every 5 minutes
            "pool_pre_ping": True,  # Test connections
            "pool_timeout": 30,  # Wait up to 30 seconds
            "echo": False,
            "echo_pool": False,
            "pool_use_lifo": True,  # Better cache locality
            "connect_args": {
                "keepalives": 1,
                "keepalives_idle": 10,
                "keepalives_interval": 5,
                "keepalives_count": 5,
                "connect_timeout": 10,
                "application_name": "TraceTrack_Optimized",
                "options": "-c statement_timeout=30000 -c idle_in_transaction_session_timeout=15000 -c jit=on"
            }
        }
    
    @staticmethod
    def create_engine(database_url):
        '''Create optimized database engine'''
        config = OptimizedDatabasePool.get_engine_config()
        
        # Use QueuePool for better concurrency
        engine = create_engine(
            database_url,
            poolclass=QueuePool,
            **config
        )
        
        logger.info(f"Created optimized database engine with pool_size={config['pool_size']}")
        return engine

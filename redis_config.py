"""
Redis Configuration for Session Storage and Caching
Reduces database load by moving sessions to Redis
"""

import os
import redis
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class RedisConfig:
    """Redis configuration for session storage and caching"""
    
    # Redis connection settings
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
    REDIS_DB = int(os.environ.get("REDIS_DB", 0))
    REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None)
    
    # Session configuration
    SESSION_TYPE = "redis"
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = "tracetrack:session:"
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # Cache configuration
    CACHE_TYPE = "redis"
    CACHE_KEY_PREFIX = "tracetrack:cache:"
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    
    # Connection pooling for Redis
    REDIS_MAX_CONNECTIONS = 150  # Support 100+ concurrent users
    REDIS_SOCKET_KEEPALIVE = True
    REDIS_SOCKET_KEEPALIVE_OPTIONS = {
        1: 1,  # TCP_KEEPIDLE
        2: 1,  # TCP_KEEPINTVL
        3: 3,  # TCP_KEEPCNT
    }
    REDIS_CONNECTION_POOL_KWARGS = {
        'max_connections': 150,
        'socket_keepalive': True,
        'socket_connect_timeout': 5,
        'retry_on_timeout': True,
        'health_check_interval': 30,
    }

class RedisSessionStore:
    """Redis-based session storage to reduce database load"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.connection_pool: Optional[redis.ConnectionPool] = None
    
    def init_redis(self):
        """Initialize Redis connection pool"""
        try:
            # Create connection pool
            self.connection_pool = redis.ConnectionPool(
                host=RedisConfig.REDIS_HOST,
                port=RedisConfig.REDIS_PORT,
                db=RedisConfig.REDIS_DB,
                password=RedisConfig.REDIS_PASSWORD,
                max_connections=RedisConfig.REDIS_MAX_CONNECTIONS,
                socket_keepalive=RedisConfig.REDIS_SOCKET_KEEPALIVE,
                socket_keepalive_options=RedisConfig.REDIS_SOCKET_KEEPALIVE_OPTIONS,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
                decode_responses=True,  # Decode bytes to str
            )
            
            # Create Redis client
            self.redis_client = redis.Redis(
                connection_pool=self.connection_pool,
                decode_responses=True
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info("✅ Redis connection pool initialized successfully (150 max connections)")
            return True
            
        except redis.ConnectionError as e:
            logger.warning(f"⚠️ Redis connection failed: {e}. Falling back to file-based sessions.")
            return False
        except Exception as e:
            logger.error(f"❌ Redis initialization error: {e}")
            return False
    
    def get_client(self) -> Optional[redis.Redis]:
        """Get Redis client"""
        if not self.redis_client:
            self.init_redis()
        return self.redis_client
    
    def close(self):
        """Close Redis connections"""
        if self.connection_pool:
            self.connection_pool.disconnect()
            logger.info("Redis connection pool closed")

# Global Redis store instance
redis_store = RedisSessionStore()

def get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client for session storage"""
    return redis_store.get_client()

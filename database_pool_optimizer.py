"""
Database Connection Pool Optimizer for High Concurrency
Designed to handle 1000+ concurrent users with 40+ lakh bags
"""

import logging
from sqlalchemy import create_engine, event, pool
from sqlalchemy.pool import NullPool, QueuePool, StaticPool
import os
from typing import Optional

logger = logging.getLogger(__name__)

class DatabasePoolOptimizer:
    """Advanced database connection pooling for enterprise scale"""
    
    @staticmethod
    def create_optimized_engine(database_url: str, app_config: dict = None):
        """
        Create an optimized database engine with advanced pooling
        
        Args:
            database_url: Database connection URL
            app_config: Optional Flask app configuration
        
        Returns:
            Optimized SQLAlchemy engine
        """
        
        # Parse environment for optimization hints
        is_production = os.environ.get('ENVIRONMENT') == 'production'
        max_connections = int(os.environ.get('DB_MAX_CONNECTIONS', '100'))
        
        # Configure pool based on expected load
        if is_production:
            # Production: Use QueuePool with high limits
            pool_config = {
                'poolclass': QueuePool,
                'pool_size': 20,                # Base pool size
                'max_overflow': 80,              # Additional connections when needed
                'pool_timeout': 30,              # Wait up to 30 seconds for connection
                'pool_recycle': 3600,           # Recycle connections after 1 hour
                'pool_pre_ping': True,          # Test connections before use
                'echo_pool': False,             # Don't log pool checkouts
            }
            logger.info(f"Using production pool: size={pool_config['pool_size']}, overflow={pool_config['max_overflow']}")
        else:
            # Development: Use smaller pool
            pool_config = {
                'poolclass': QueuePool,
                'pool_size': 5,
                'max_overflow': 10,
                'pool_timeout': 10,
                'pool_recycle': 300,
                'pool_pre_ping': True,
                'echo_pool': False,
            }
            logger.info(f"Using development pool: size={pool_config['pool_size']}, overflow={pool_config['max_overflow']}")
        
        # Create engine with optimized settings
        engine = create_engine(
            database_url,
            **pool_config,
            connect_args={
                'connect_timeout': 10,
                'application_name': 'TraceTrack-Ultra',
                'options': '-c statement_timeout=30000'  # 30 second statement timeout
            },
            # Performance optimizations
            execution_options={
                'isolation_level': 'READ COMMITTED',  # Prevent lock contention
                'postgresql_readonly': False,
                'postgresql_deferrable': False
            }
        )
        
        # Add connection pool listeners for monitoring and optimization
        @event.listens_for(engine, "connect")
        def set_connection_parameters(dbapi_conn, connection_record):
            """Set connection-level parameters for optimization"""
            with dbapi_conn.cursor() as cursor:
                # Optimize for web application workload
                cursor.execute("SET jit = off")  # Disable JIT for consistent performance
                cursor.execute("SET random_page_cost = 1.1")  # Optimize for SSD
                cursor.execute("SET effective_cache_size = '4GB'")
                cursor.execute("SET work_mem = '16MB'")  # Per-operation memory
                cursor.execute("SET maintenance_work_mem = '256MB'")
                
                # Set connection info for monitoring
                connection_record.info['pid'] = dbapi_conn.get_backend_pid()
        
        @event.listens_for(engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Track connection checkouts for monitoring"""
            pid = connection_record.info.get('pid', 'unknown')
            logger.debug(f"Connection checked out: PID={pid}")
        
        @event.listens_for(engine, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            """Reset connection state on checkin"""
            try:
                # Reset any session-level settings
                with dbapi_conn.cursor() as cursor:
                    cursor.execute("RESET ALL")
            except Exception as e:
                logger.warning(f"Failed to reset connection: {e}")
        
        return engine
    
    @staticmethod
    def optimize_app_config(app):
        """
        Optimize Flask-SQLAlchemy configuration for high concurrency
        
        Args:
            app: Flask application instance
        """
        
        # Core SQLAlchemy optimizations
        app.config.update({
            # Connection pool settings
            'SQLALCHEMY_ENGINE_OPTIONS': {
                'pool_size': 20,
                'max_overflow': 80,
                'pool_timeout': 30,
                'pool_recycle': 3600,
                'pool_pre_ping': True,
                'echo': False,
                'echo_pool': False,
                'connect_args': {
                    'connect_timeout': 10,
                    'application_name': 'TraceTrack-Ultra',
                    'options': '-c statement_timeout=30000'
                }
            },
            
            # Flask-SQLAlchemy settings
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,  # Disable event system
            'SQLALCHEMY_RECORD_QUERIES': False,       # Don't record queries in debug
            
            # Query optimizations
            'SQLALCHEMY_ECHO': False,                 # Don't log SQL statements
            'SQLALCHEMY_COMMIT_ON_TEARDOWN': False,   # Manual transaction control
        })
        
        logger.info("Flask-SQLAlchemy optimized for high concurrency")
        return app
    
    @staticmethod
    def get_pool_status(engine):
        """
        Get current connection pool status
        
        Args:
            engine: SQLAlchemy engine instance
        
        Returns:
            Dict with pool statistics
        """
        pool = engine.pool
        
        if isinstance(pool, QueuePool):
            return {
                'size': pool.size(),
                'checked_in': pool.checkedin(),
                'overflow': pool.overflow(),
                'total': pool.size() + pool.overflow(),
                'checked_out': pool.checkedout()
            }
        elif isinstance(pool, NullPool):
            return {
                'type': 'NullPool',
                'message': 'No connection pooling'
            }
        else:
            return {
                'type': type(pool).__name__,
                'message': 'Pool statistics not available'
            }
    
    @staticmethod
    def monitor_connections(engine, threshold=0.8):
        """
        Monitor connection pool usage and log warnings
        
        Args:
            engine: SQLAlchemy engine instance
            threshold: Warning threshold (0.0 to 1.0)
        
        Returns:
            Pool usage ratio (0.0 to 1.0)
        """
        try:
            status = DatabasePoolOptimizer.get_pool_status(engine)
            
            if 'checked_out' in status and 'total' in status:
                usage = status['checked_out'] / max(status['total'], 1)
                
                if usage > threshold:
                    logger.warning(
                        f"High connection pool usage: {status['checked_out']}/{status['total']} "
                        f"({usage:.1%}) connections in use"
                    )
                
                return usage
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Failed to monitor connections: {e}")
            return 0.0
    
    @staticmethod
    def emergency_pool_reset(engine):
        """
        Emergency connection pool reset in case of issues
        
        Args:
            engine: SQLAlchemy engine instance
        """
        try:
            logger.warning("Performing emergency connection pool reset")
            
            # Dispose of current pool
            engine.dispose()
            
            # Recreate pool connections
            engine.pool.recreate()
            
            logger.info("Connection pool reset completed")
            
        except Exception as e:
            logger.error(f"Failed to reset connection pool: {e}")

# Initialize optimizer
db_pool_optimizer = DatabasePoolOptimizer()

# Export for app integration
__all__ = ['DatabasePoolOptimizer', 'db_pool_optimizer']
"""
Database connection pool manager for high concurrency
"""
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import DBAPIError, OperationalError
import time
import os

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages database connections with retry logic and health checks"""
    
    def __init__(self, app=None):
        self.app = app
        self.engine = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize connection manager with Flask app"""
        self.app = app
        self.setup_engine()
    
    def setup_engine(self):
        """Setup SQLAlchemy engine with optimized pool settings"""
        if not self.app:
            return
            
        database_url = self.app.config.get('SQLALCHEMY_DATABASE_URI')
        if not database_url:
            logger.error("No database URL configured")
            return
            
        # Create engine with optimized settings for high concurrency
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=50,  # Base pool size
            max_overflow=100,  # Allow up to 150 total connections
            pool_recycle=300,  # Recycle connections every 5 minutes
            pool_pre_ping=True,  # Check connections before using
            pool_timeout=30,  # Wait up to 30 seconds for a connection
            echo=False,
            connect_args={
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
                "connect_timeout": 5,
                "application_name": "TraceTrack_HighConcurrency",
                "options": "-c statement_timeout=60000 -c idle_in_transaction_session_timeout=30000"
            }
        )
        logger.info("Database engine configured for high concurrency")
    
    @contextmanager
    def get_connection(self, max_retries=3):
        """Get a database connection with retry logic"""
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                conn = self.engine.connect()
                try:
                    yield conn
                    conn.commit()
                finally:
                    conn.close()
                return
            except (DBAPIError, OperationalError) as e:
                retry_count += 1
                last_error = e
                logger.warning(f"Database connection attempt {retry_count} failed: {str(e)}")
                
                if retry_count < max_retries:
                    # Exponential backoff
                    wait_time = min(2 ** retry_count, 10)
                    time.sleep(wait_time)
                    
                    # Check if we need to recreate the engine
                    if "connection" in str(e).lower() or "pool" in str(e).lower():
                        logger.info("Recreating database engine due to connection issues")
                        self.setup_engine()
            except Exception as e:
                logger.error(f"Unexpected database error: {str(e)}")
                raise
        
        # If we've exhausted retries, raise the last error
        if last_error:
            logger.error(f"Failed to connect to database after {max_retries} attempts")
            raise last_error
    
    def check_health(self):
        """Check database connection health"""
        try:
            with self.get_connection(max_retries=1) as conn:
                result = conn.execute("SELECT 1").scalar()
                return result == 1
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False
    
    def get_pool_status(self):
        """Get current connection pool status"""
        if not self.engine or not hasattr(self.engine.pool, 'status'):
            return {
                'size': 0,
                'checked_in': 0,
                'checked_out': 0,
                'overflow': 0,
                'total': 0
            }
        
        pool = self.engine.pool
        return {
            'size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'total': pool.size() + pool.overflow()
        }

# Global connection manager instance
connection_manager = ConnectionManager()
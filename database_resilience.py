"""
Enhanced database configuration with DNS retry and connection resilience
"""
import os
import socket
import time
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import DBAPIError, OperationalError
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)

class ResilientDatabaseConfig:
    """Database configuration with enhanced resilience for production issues"""
    
    @staticmethod
    def resolve_hostname_with_retry(hostname, max_retries=3, delay=1):
        """Attempt to resolve hostname with retries"""
        for attempt in range(max_retries):
            try:
                # Try to resolve the hostname
                result = socket.gethostbyname(hostname)
                logger.info(f"Successfully resolved {hostname} to {result}")
                return result
            except socket.gaierror as e:
                logger.warning(f"DNS resolution attempt {attempt + 1} failed for {hostname}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(delay * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"Failed to resolve {hostname} after {max_retries} attempts")
                    raise
        return None
    
    @staticmethod
    def create_resilient_engine(database_url, **kwargs):
        """Create a database engine with enhanced resilience"""
        
        # Parse the database URL
        parsed = urlparse(database_url)
        
        # If it's a Neon database, try to resolve DNS first
        if 'neon.tech' in parsed.hostname:
            try:
                # Attempt to resolve the hostname
                resolved_ip = ResilientDatabaseConfig.resolve_hostname_with_retry(parsed.hostname)
                if resolved_ip:
                    # Replace hostname with IP temporarily for connection
                    logger.info(f"Using resolved IP {resolved_ip} for database connection")
                    # Keep the original hostname in connect_args for SSL verification
                    kwargs.setdefault('connect_args', {})
                    kwargs['connect_args']['host'] = parsed.hostname  # Original hostname for SSL
            except Exception as e:
                logger.error(f"DNS resolution failed, using original URL: {e}")
        
        # Enhanced connection settings
        engine_config = {
            'poolclass': QueuePool,
            'pool_size': 50,
            'max_overflow': 100,
            'pool_recycle': 300,
            'pool_pre_ping': True,
            'pool_timeout': 30,
            'echo': False,
            'connect_args': {
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5,
                'connect_timeout': 10,
                'application_name': 'TraceTrack_Production',
                'options': '-c statement_timeout=60000 -c idle_in_transaction_session_timeout=30000'
            }
        }
        
        # Merge with provided kwargs
        engine_config.update(kwargs)
        
        # Create the engine
        engine = create_engine(database_url, **engine_config)
        
        # Add event listeners for connection resilience
        @event.listens_for(engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Configure connection on connect"""
            connection_record.info['pid'] = os.getpid()
            logger.debug(f"New database connection established (PID: {os.getpid()})")
        
        @event.listens_for(engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Verify connection on checkout"""
            pid = os.getpid()
            if connection_record.info['pid'] != pid:
                connection_record.connection = None
                raise DBAPIError(
                    "Connection record belongs to different PID",
                    None, None, None
                )
        
        return engine
    
    @staticmethod
    def get_enhanced_config():
        """Get enhanced database configuration for Flask-SQLAlchemy"""
        return {
            "pool_size": 50,
            "max_overflow": 100,
            "pool_recycle": 300,
            "pool_pre_ping": True,
            "pool_timeout": 30,
            "echo": False,
            "echo_pool": False,
            "connect_args": {
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
                "connect_timeout": 10,
                "application_name": "TraceTrack_Production",
                "options": "-c statement_timeout=60000 -c idle_in_transaction_session_timeout=30000"
            }
        }
    
    @staticmethod
    def test_connection(database_url):
        """Test database connection with detailed error reporting"""
        try:
            engine = ResilientDatabaseConfig.create_resilient_engine(database_url)
            with engine.connect() as conn:
                from sqlalchemy import text
                result = conn.execute(text("SELECT 1"))
                logger.info("Database connection test successful")
                return True
        except OperationalError as e:
            logger.error(f"Database operational error: {e}")
            # Check for specific DNS error
            if "could not translate host name" in str(e):
                logger.error("DNS resolution failure detected - check network configuration")
            elif "timeout" in str(e).lower():
                logger.error("Connection timeout - check network connectivity and firewall rules")
            elif "password authentication failed" in str(e):
                logger.error("Authentication failure - check database credentials")
            else:
                logger.error(f"Unknown operational error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected database connection error: {e}")
            return False

# Helper function to integrate with Flask app
def configure_resilient_database(app):
    """Configure Flask app with resilient database settings"""
    from database_resilience import ResilientDatabaseConfig
    
    # Get the database URL
    database_url = app.config.get('SQLALCHEMY_DATABASE_URI')
    
    # Test the connection first
    if not ResilientDatabaseConfig.test_connection(database_url):
        logger.warning("Initial database connection test failed - proceeding with caution")
    
    # Apply enhanced configuration
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = ResilientDatabaseConfig.get_enhanced_config()
    
    logger.info("Resilient database configuration applied")
    return app
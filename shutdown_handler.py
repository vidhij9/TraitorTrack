"""
Graceful Shutdown Handler for TraceTrack
Ensures zero-downtime deployments by properly cleaning up resources
"""

import logging
import os
import signal
import sys
import threading
import time
from typing import Callable, List

logger = logging.getLogger(__name__)


class GracefulShutdownHandler:
    """Handles graceful shutdown of the application"""
    
    # Default shutdown timeout (seconds)
    DEFAULT_TIMEOUT = 30
    
    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        """
        Initialize graceful shutdown handler
        
        Args:
            timeout: Maximum time to wait for graceful shutdown (seconds)
        """
        self.timeout = timeout
        self.shutdown_in_progress = False
        self.cleanup_callbacks = []
        self.shutdown_event = threading.Event()
    
    def register_cleanup(self, callback: Callable, name: str = None):
        """
        Register a cleanup callback to be called during shutdown
        
        Args:
            callback: Function to call during shutdown
            name: Optional name for the callback (for logging)
        """
        callback_name = name or callback.__name__
        self.cleanup_callbacks.append((callback, callback_name))
        logger.debug(f"Registered cleanup callback: {callback_name}")
    
    def _handle_shutdown_signal(self, signum, frame):
        """
        Handle shutdown signals (SIGTERM, SIGINT)
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        logger.info(f"Received {signal_name} signal - initiating graceful shutdown")
        
        if self.shutdown_in_progress:
            logger.warning("Shutdown already in progress - ignoring duplicate signal")
            return
        
        self.shutdown_in_progress = True
        self.shutdown_event.set()
        
        # Perform graceful shutdown in a separate thread to avoid blocking signal handler
        shutdown_thread = threading.Thread(target=self._perform_shutdown, name="GracefulShutdown")
        shutdown_thread.daemon = False
        shutdown_thread.start()
    
    def _perform_shutdown(self):
        """Perform graceful shutdown sequence"""
        logger.info(f"Starting graceful shutdown - timeout: {self.timeout}s")
        start_time = time.time()
        
        # Execute cleanup callbacks in reverse order (LIFO)
        for callback, name in reversed(self.cleanup_callbacks):
            try:
                elapsed = time.time() - start_time
                remaining = self.timeout - elapsed
                
                if remaining <= 0:
                    logger.warning(f"Shutdown timeout reached - skipping remaining cleanup callbacks")
                    break
                
                logger.info(f"Executing cleanup callback: {name}")
                callback()
                logger.info(f"Completed cleanup callback: {name}")
                
            except Exception as e:
                logger.error(f"Error in cleanup callback {name}: {e}", exc_info=True)
        
        elapsed = time.time() - start_time
        logger.info(f"Graceful shutdown completed in {elapsed:.2f}s")
        
        # DON'T call sys.exit() or os._exit() here!
        # Gunicorn handles graceful shutdown by:
        # 1. Stopping new connections when SIGTERM received
        # 2. Waiting for in-flight requests to complete
        # 3. Then terminating the worker process
        # Our cleanup has run - let Gunicorn finish its own shutdown
        logger.info("Cleanup complete - allowing Gunicorn to complete graceful shutdown")
    
    def setup_signal_handlers(self):
        """Register signal handlers for graceful shutdown"""
        # Handle SIGTERM (sent by Kubernetes, systemd, etc. for graceful shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        logger.info("Registered SIGTERM handler for graceful shutdown")
        
        # Handle SIGINT (Ctrl+C)
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)
        logger.info("Registered SIGINT handler for graceful shutdown")
    
    def is_shutting_down(self) -> bool:
        """Check if shutdown is in progress"""
        return self.shutdown_in_progress
    
    def wait_for_shutdown(self, timeout: float = None):
        """
        Wait for shutdown signal
        
        Args:
            timeout: Maximum time to wait (None = wait forever)
            
        Returns:
            True if shutdown signal received, False if timeout
        """
        return self.shutdown_event.wait(timeout)


# Global shutdown handler instance
_shutdown_handler = None


def get_shutdown_handler() -> GracefulShutdownHandler:
    """Get or create the global shutdown handler instance"""
    global _shutdown_handler
    if _shutdown_handler is None:
        _shutdown_handler = GracefulShutdownHandler()
    return _shutdown_handler


def init_graceful_shutdown(app, db, timeout: int = GracefulShutdownHandler.DEFAULT_TIMEOUT):
    """
    Initialize graceful shutdown handling for Flask application
    
    Args:
        app: Flask application instance
        db: SQLAlchemy database instance
        timeout: Shutdown timeout in seconds
        
    Returns:
        GracefulShutdownHandler instance
    """
    global _shutdown_handler
    
    # Reset singleton to avoid callback accumulation on reloads
    _shutdown_handler = GracefulShutdownHandler(timeout=timeout)
    
    # Register database connection pool cleanup
    def cleanup_database():
        """Close all database connections gracefully"""
        try:
            logger.info("Closing database connections...")
            
            # Get connection pool
            pool = db.engine.pool
            
            # Log current pool state
            pool_size = pool.size()
            checked_out = pool.checkedout()
            logger.info(f"Database pool state: {checked_out}/{pool_size} connections in use")
            
            # Dispose of the connection pool
            # This will close all connections and wait for checked-out connections to be returned
            db.engine.dispose()
            
            logger.info("Database connections closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")
    
    _shutdown_handler.register_cleanup(cleanup_database, "database_cleanup")
    
    # Register pool monitor cleanup
    def cleanup_pool_monitor():
        """Stop pool monitoring background thread"""
        try:
            from pool_monitor import get_pool_monitor
            
            monitor = get_pool_monitor()
            if monitor and monitor.monitor_thread and monitor.monitor_thread.is_alive():
                logger.info("Stopping pool monitor...")
                monitor.stop()
                logger.info("Pool monitor stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping pool monitor: {e}")
    
    _shutdown_handler.register_cleanup(cleanup_pool_monitor, "pool_monitor_cleanup")
    
    # Register session cleanup
    def cleanup_sessions():
        """Clean up any remaining Flask sessions"""
        try:
            logger.info("Cleaning up Flask sessions...")
            db.session.remove()
            logger.info("Flask sessions cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
    
    _shutdown_handler.register_cleanup(cleanup_sessions, "session_cleanup")
    
    # Register audit log flush
    def flush_audit_logs():
        """Ensure all audit logs are written to database"""
        try:
            logger.info("Flushing audit logs...")
            db.session.commit()
            logger.info("Audit logs flushed")
        except Exception as e:
            logger.error(f"Error flushing audit logs: {e}")
    
    _shutdown_handler.register_cleanup(flush_audit_logs, "audit_log_flush")
    
    # Setup signal handlers
    _shutdown_handler.setup_signal_handlers()
    
    logger.info(f"Graceful shutdown initialized - timeout: {timeout}s, {len(_shutdown_handler.cleanup_callbacks)} cleanup callbacks registered")
    
    return _shutdown_handler


def register_cleanup_callback(callback: Callable, name: str = None):
    """
    Register a custom cleanup callback
    
    Args:
        callback: Function to call during shutdown
        name: Optional name for the callback
    """
    handler = get_shutdown_handler()
    handler.register_cleanup(callback, name)

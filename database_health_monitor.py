"""
Database health monitoring and recovery system for production stability
"""
import logging
import time
import threading
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, DBAPIError
from flask import jsonify

logger = logging.getLogger(__name__)

class DatabaseHealthMonitor:
    """Monitor database health and perform automatic recovery"""
    
    def __init__(self, app=None, db=None):
        self.app = app
        self.db = db
        self.is_healthy = True
        self.last_check = time.time()
        self.consecutive_failures = 0
        self.max_failures = 3
        self.check_interval = 30  # Check every 30 seconds
        self.monitor_thread = None
        self.running = False
        
    def init_app(self, app, db):
        """Initialize with Flask app and database"""
        self.app = app
        self.db = db
        self.start_monitoring()
        
    def check_health(self):
        """Check database health status"""
        try:
            # Use app context for health check
            with self.app.app_context():
                # Simple health check query
                result = self.db.session.execute(
                    text("SELECT 1 as health_check")
                ).scalar()
            
            if result == 1:
                self.is_healthy = True
                self.consecutive_failures = 0
                return True
                
        except (OperationalError, DBAPIError) as e:
            logger.warning(f"Database health check failed: {str(e)}")
            self.consecutive_failures += 1
            
            if self.consecutive_failures >= self.max_failures:
                self.is_healthy = False
                self.attempt_recovery()
                
        except Exception as e:
            logger.error(f"Unexpected error in health check: {str(e)}")
            self.consecutive_failures += 1
            
        return False
        
    def attempt_recovery(self):
        """Attempt to recover database connection"""
        logger.warning("Attempting database recovery...")
        
        try:
            # Use app context for recovery
            with self.app.app_context():
                # Close existing connections
                self.db.session.remove()
                self.db.engine.dispose()
                
                # Wait a moment
                time.sleep(2)
                
                # Recreate engine and test
                self.db.engine.connect().close()
                
                # Test with a query
                result = self.db.session.execute(
                    text("SELECT 1 as recovery_check")
                ).scalar()
                
                if result == 1:
                    self.is_healthy = True
                    self.consecutive_failures = 0
                    logger.info("Database recovery successful!")
                    return True
                
        except Exception as e:
            logger.error(f"Database recovery failed: {str(e)}")
            
        return False
        
    def monitor_loop(self):
        """Background monitoring loop"""
        while self.running:
            try:
                time.sleep(self.check_interval)
                self.check_health()
                self.last_check = time.time()
                
            except Exception as e:
                logger.error(f"Monitor loop error: {str(e)}")
                
    def start_monitoring(self):
        """Start background monitoring"""
        if not self.running:
            self.running = True
            self.monitor_thread = threading.Thread(
                target=self.monitor_loop,
                daemon=True
            )
            self.monitor_thread.start()
            logger.info("Database health monitoring started")
            
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
            
    def get_status(self):
        """Get current health status"""
        return {
            'healthy': self.is_healthy,
            'consecutive_failures': self.consecutive_failures,
            'last_check': time.time() - self.last_check,
            'status': 'healthy' if self.is_healthy else 'unhealthy'
        }

# Global health monitor instance
db_health_monitor = DatabaseHealthMonitor()

def register_health_endpoints(app, db):
    """Register health check endpoints"""
    
    # Initialize monitor
    db_health_monitor.init_app(app, db)
    
    @app.route('/api/db/health', methods=['GET'])
    def database_health():
        """Database health check endpoint"""
        status = db_health_monitor.get_status()
        
        if status['healthy']:
            return jsonify({
                'status': 'healthy',
                'message': 'Database connection is healthy',
                'details': status
            }), 200
        else:
            return jsonify({
                'status': 'unhealthy',
                'message': 'Database connection issues detected',
                'details': status,
                'recovery_attempted': db_health_monitor.consecutive_failures >= db_health_monitor.max_failures
            }), 503
            
    @app.route('/api/db/recover', methods=['POST'])
    def force_database_recovery():
        """Force database recovery attempt"""
        success = db_health_monitor.attempt_recovery()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Database recovery successful'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Database recovery failed - manual intervention may be required'
            }), 500
            
    logger.info("Database health endpoints registered")
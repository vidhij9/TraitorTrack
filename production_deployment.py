"""
Production Deployment Optimization for Replit Autoscale
Handles database connection issues and port opening requirements
"""

import os
import time
import logging
from functools import wraps
from threading import Thread

logger = logging.getLogger(__name__)

class LazyDatabaseInitializer:
    """Lazy database initialization to prevent startup blocking"""
    
    def __init__(self, app, db):
        self.app = app
        self.db = db
        self.initialized = False
        self.initialization_error = None
        
    def initialize_database(self):
        """Initialize database connection with retry logic"""
        if self.initialized:
            return True
            
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                with self.app.app_context():
                    # Test connection
                    from sqlalchemy import text
                    self.db.session.execute(text("SELECT 1")).scalar()
                    
                    # Create tables if needed
                    import models
                    self.db.create_all()
                    
                    self.initialized = True
                    logger.info(f"Database initialized successfully on attempt {attempt + 1}")
                    return True
                    
            except Exception as e:
                self.initialization_error = e
                logger.warning(f"Database initialization attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                    
        logger.error(f"Database initialization failed after {max_retries} attempts")
        return False
        
    def ensure_initialized(self):
        """Ensure database is initialized before use"""
        if not self.initialized:
            self.initialize_database()
        return self.initialized


def apply_production_deployment_fixes(app, db):
    """Apply production deployment fixes for Replit Autoscale"""
    
    # Create lazy database initializer
    db_initializer = LazyDatabaseInitializer(app, db)
    
    # Store initializer on app for access in routes
    app.db_initializer = db_initializer
    
    # Add production health check endpoint (no database required)
    @app.route('/health')
    def health_check():
        """Simple health check that doesn't require database"""
        return {'status': 'healthy', 'service': 'tracetrack'}, 200
    
    # Add readiness check endpoint
    @app.route('/ready')
    def readiness_check():
        """Readiness check that verifies database connection"""
        if db_initializer.initialized:
            try:
                from sqlalchemy import text
                db.session.execute(text("SELECT 1")).scalar()
                return {'status': 'ready', 'database': 'connected'}, 200
            except Exception as e:
                return {'status': 'not_ready', 'database': 'error', 'error': str(e)}, 503
        else:
            # Try to initialize
            if db_initializer.initialize_database():
                return {'status': 'ready', 'database': 'connected'}, 200
            else:
                error_msg = str(db_initializer.initialization_error) if db_initializer.initialization_error else 'Unknown error'
                return {'status': 'not_ready', 'database': 'not_connected', 'error': error_msg}, 503
    
    # Add liveness check endpoint
    @app.route('/live')
    def liveness_check():
        """Liveness check for Kubernetes/Autoscale"""
        return {'status': 'alive', 'timestamp': time.time()}, 200
    
    # Wrap database-dependent routes with lazy initialization
    def ensure_db_initialized(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not db_initializer.ensure_initialized():
                # Return service unavailable if database isn't ready
                from flask import jsonify
                return jsonify({
                    'error': 'Service temporarily unavailable',
                    'message': 'Database connection is being established. Please try again in a few moments.'
                }), 503
            return f(*args, **kwargs)
        return decorated_function
    
    # Apply wrapper to all database-dependent routes
    for endpoint in app.url_map._rules:
        if endpoint.endpoint and endpoint.endpoint not in ['health_check', 'readiness_check', 'liveness_check', 'static']:
            view_func = app.view_functions.get(endpoint.endpoint)
            if view_func and not getattr(view_func, '_db_check_applied', False):
                wrapped = ensure_db_initialized(view_func)
                wrapped._db_check_applied = True
                app.view_functions[endpoint.endpoint] = wrapped
    
    # Initialize database in background thread after app starts
    def background_db_init():
        """Initialize database in background to not block startup"""
        time.sleep(2)  # Give app time to start
        logger.info("Starting background database initialization...")
        db_initializer.initialize_database()
    
    # Start background initialization
    init_thread = Thread(target=background_db_init, daemon=True)
    init_thread.start()
    
    # Configure for production deployment
    app.config.update({
        'PROPAGATE_EXCEPTIONS': True,
        'TRAP_HTTP_EXCEPTIONS': True,
        'TRAP_BAD_REQUEST_ERRORS': True,
        'PRESERVE_CONTEXT_ON_EXCEPTION': False,
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'pool_size': 10,  # Reduced for initial connection
            'max_overflow': 20,
            'pool_recycle': 300,
            'pool_pre_ping': True,
            'pool_timeout': 30,  # Increased timeout
            'echo': False,
            'connect_args': {
                'connect_timeout': 30,  # Increased connection timeout
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 5,
                'options': '-c statement_timeout=60000'  # 60 second statement timeout
            }
        }
    })
    
    logger.info("Production deployment optimizations applied")
    return app


def configure_for_cloud_run(app):
    """Configure app specifically for Cloud Run / Autoscale deployment"""
    
    # Get port from environment or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Cloud Run specific configurations
    app.config.update({
        'SERVER_NAME': None,  # Let Cloud Run handle this
        'APPLICATION_ROOT': '/',
        'PREFERRED_URL_SCHEME': 'https',
        'SESSION_COOKIE_SECURE': True,  # Use secure cookies in production
        'SESSION_COOKIE_HTTPONLY': True,
        'SESSION_COOKIE_SAMESITE': 'Lax',
    })
    
    return app


def create_minimal_app():
    """Create a minimal Flask app that starts quickly for production"""
    from flask import Flask, jsonify
    
    minimal_app = Flask(__name__)
    
    @minimal_app.route('/health')
    def health():
        return jsonify({'status': 'healthy'}), 200
    
    @minimal_app.route('/')
    def index():
        return jsonify({'message': 'TraceTrack is starting up...'}), 200
    
    return minimal_app
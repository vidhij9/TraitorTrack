"""
AWS RDS optimized main.py - starts immediately and connects to database in background
This ensures the app opens port 5000 quickly for Replit Autoscale deployment
"""

import os
import logging
import time
from threading import Thread, Event
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress noisy loggers
for noisy_logger in ['werkzeug', 'sqlalchemy.engine', 'sqlalchemy.pool']:
    logging.getLogger(noisy_logger).setLevel(logging.ERROR)

# Global flag for database readiness
db_ready = Event()
db_error = None
db_initialized = False

def lazy_db_check(f):
    """Decorator to check database readiness before executing routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not db_ready.is_set():
            # Wait up to 2 seconds for database
            if not db_ready.wait(timeout=2):
                from flask import jsonify
                error_msg = str(db_error) if db_error else "Database connection in progress"
                return jsonify({
                    'error': 'Service temporarily unavailable',
                    'message': f'Database is initializing. {error_msg}',
                    'retry_after': 5
                }), 503
        return f(*args, **kwargs)
    return decorated_function

def initialize_database_async(app, db):
    """Initialize database connection in background with retries"""
    global db_error, db_initialized
    
    max_retries = 30  # More retries for AWS RDS
    retry_delay = 2
    
    logger.info("Starting background database initialization for AWS RDS...")
    
    for attempt in range(max_retries):
        try:
            with app.app_context():
                # Test connection
                from sqlalchemy import text
                result = db.session.execute(text("SELECT 1")).scalar()
                logger.info(f"Database connection test successful (attempt {attempt + 1})")
                
                # Initialize tables if needed
                if hasattr(app, 'initialize_database'):
                    app.initialize_database()
                else:
                    import models
                    db.create_all()
                
                db_initialized = True
                db_ready.set()
                logger.info("✅ AWS RDS database initialized successfully!")
                return True
                
        except Exception as e:
            db_error = e
            logger.warning(f"Database connection attempt {attempt + 1}/{max_retries} failed: {e}")
            
            if attempt < max_retries - 1:
                # Exponential backoff with max delay of 30 seconds
                delay = min(retry_delay * (2 ** min(attempt, 5)), 30)
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.error(f"Failed to connect to AWS RDS after {max_retries} attempts")
                # Set ready anyway to allow app to function with errors
                db_ready.set()
                
    return False

# Import Flask app WITHOUT immediate database initialization
from flask import Flask, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Create minimal app first
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-for-tracetrack-2024")

# Basic health check - no database required
@app.route('/health')
def health():
    """Health check for Autoscale - always returns healthy"""
    return jsonify({'status': 'healthy', 'service': 'tracetrack'}), 200

@app.route('/ready')
def ready():
    """Readiness check - reports database status"""
    if db_ready.is_set() and db_initialized:
        return jsonify({'status': 'ready', 'database': 'connected'}), 200
    else:
        error_msg = str(db_error) if db_error else "Connecting to AWS RDS..."
        return jsonify({
            'status': 'not_ready',
            'database': 'connecting',
            'message': error_msg
        }), 503

@app.route('/')
def index():
    """Root page that works without database"""
    if db_ready.is_set():
        # Database is ready, redirect to login
        return '''
        <html>
            <head>
                <title>TraceTrack</title>
                <meta http-equiv="refresh" content="0; url=/login">
            </head>
            <body>
                <h1>TraceTrack Ready</h1>
                <p>Redirecting to login...</p>
            </body>
        </html>
        '''
    else:
        # Database still connecting
        return '''
        <html>
            <head>
                <title>TraceTrack - Starting</title>
                <meta http-equiv="refresh" content="5">
            </head>
            <body style="font-family: Arial, sans-serif; padding: 50px; text-align: center;">
                <h1>🚀 TraceTrack is Starting Up</h1>
                <p>Connecting to AWS RDS database...</p>
                <p style="color: #666;">This page will refresh automatically.</p>
                <div style="margin: 30px auto; width: 200px; height: 4px; background: #f0f0f0; border-radius: 2px; overflow: hidden;">
                    <div style="width: 100%; height: 100%; background: #4CAF50; animation: loading 2s linear infinite;">
                        <style>
                            @keyframes loading {
                                0% { transform: translateX(-100%); }
                                100% { transform: translateX(100%); }
                            }
                        </style>
                    </div>
                </div>
                <p><small>If this takes too long, check your AWS RDS configuration.</small></p>
            </body>
        </html>
        '''

# Now import the full app configuration AFTER basic routes are set
logger.info("Loading full application configuration...")

try:
    # Import the configured app with database settings
    from app_clean import app as configured_app, db, login_manager, csrf, limiter
    
    # Copy configurations from configured app
    app.config.update(configured_app.config)
    
    # Initialize extensions with our app
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    
    # Import all routes and apply lazy database check
    import routes
    import api
    
    # Apply lazy database check to all database-dependent routes
    for endpoint_name, view_func in app.view_functions.items():
        if endpoint_name not in ['health', 'ready', 'index', 'static']:
            if not hasattr(view_func, '_db_check_applied'):
                wrapped = lazy_db_check(view_func)
                wrapped._db_check_applied = True
                app.view_functions[endpoint_name] = wrapped
    
    logger.info("✅ Application configured successfully")
    
    # Start database initialization in background
    db_thread = Thread(target=initialize_database_async, args=(app, db), daemon=True)
    db_thread.start()
    
except Exception as e:
    logger.error(f"Failed to load full application: {e}")
    # App will still work with basic routes

# Import optimizers if available (non-blocking)
try:
    from production_deployment import apply_production_deployment_fixes
    app = apply_production_deployment_fixes(app, db)
except:
    pass

# For Gunicorn
application = app

if __name__ == "__main__":
    logger.info("🚀 Starting TraceTrack with AWS RDS support on port 5000...")
    logger.info("App will start immediately - database connection happens in background")
    app.run(host="0.0.0.0", port=5000, debug=False)
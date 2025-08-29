"""
Production-optimized main.py for Replit Autoscale deployment
Ensures port 5000 opens immediately and handles database connection gracefully
"""

import os
import logging
import time
from threading import Thread

# Configure minimal logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress noisy loggers
for noisy_logger in ['werkzeug', 'sqlalchemy', 'flask_limiter']:
    logging.getLogger(noisy_logger).setLevel(logging.ERROR)

def initialize_app():
    """Initialize the Flask application with lazy database loading"""
    
    # Import Flask app with database NOT initialized
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    from sqlalchemy.orm import DeclarativeBase
    
    # Create base Flask app
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-for-tracetrack-2024")
    
    # Basic configuration
    app.config.update({
        'SQLALCHEMY_DATABASE_URI': os.environ.get('DATABASE_URL', 'sqlite:///tracetrack.db'),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'pool_size': 5,  # Start small
            'max_overflow': 10,
            'pool_recycle': 300,
            'pool_pre_ping': True,
            'pool_timeout': 30,
            'connect_args': {
                'connect_timeout': 30,
            }
        }
    })
    
    # Create database instance but don't initialize yet
    class Base(DeclarativeBase):
        pass
    
    db = SQLAlchemy(model_class=Base)
    
    # Add health check endpoint immediately (no database required)
    @app.route('/health')
    def health():
        """Health check endpoint for Autoscale"""
        return {'status': 'healthy', 'service': 'tracetrack'}, 200
    
    @app.route('/')
    def index():
        """Root endpoint that works without database"""
        return '''
        <html>
            <head><title>TraceTrack</title></head>
            <body>
                <h1>TraceTrack is starting up...</h1>
                <p>Please wait while the application initializes.</p>
                <script>
                    setTimeout(function() {
                        window.location.href = '/login';
                    }, 5000);
                </script>
            </body>
        </html>
        '''
    
    # Initialize database connection in background
    def init_database():
        """Initialize database connection with retries"""
        time.sleep(2)  # Let the app start first
        
        max_retries = 10
        retry_delay = 3
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Database initialization attempt {attempt + 1}/{max_retries}")
                
                with app.app_context():
                    db.init_app(app)
                    
                    # Test connection
                    from sqlalchemy import text
                    db.session.execute(text("SELECT 1")).scalar()
                    
                    # Import models and create tables
                    import models
                    db.create_all()
                    
                    logger.info("✅ Database initialized successfully")
                    
                    # Now import and register all routes
                    import routes
                    import api
                    
                    # Import optimizers if available
                    try:
                        from production_deployment import apply_production_deployment_fixes
                        apply_production_deployment_fixes(app, db)
                    except ImportError:
                        pass
                    
                    logger.info("✅ All routes registered successfully")
                    return True
                    
            except Exception as e:
                logger.warning(f"Database initialization failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    
        logger.error("Failed to initialize database after all retries")
        return False
    
    # Start database initialization in background
    db_thread = Thread(target=init_database, daemon=True)
    db_thread.start()
    
    return app, db

# Create app instance
app, db = initialize_app()

# For Gunicorn
application = app

if __name__ == "__main__":
    # Start the app immediately on port 5000
    logger.info("Starting TraceTrack on port 5000...")
    app.run(host="0.0.0.0", port=5000, debug=False)
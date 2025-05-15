import os
import logging
import time
import sys

from flask import Flask, request, g, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, current_user, logout_user
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Import custom logging configuration
from logging_config import setup_logging

# Setup advanced logging configuration
setup_logging()
logger = logging.getLogger(__name__)

# Set application version
VERSION = "1.2.0"

class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with the Base class
db = SQLAlchemy(model_class=Base)

# Create the Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # Needed for url_for to generate with https

# Configure secure session and security settings
app.config.update(
    # Session security
    SESSION_COOKIE_SECURE=True,            # Only send cookies over HTTPS
    SESSION_COOKIE_HTTPONLY=True,          # Prevent JavaScript access to session cookie
    SESSION_COOKIE_SAMESITE='Lax',         # Restrict cookie sending to same-site requests
    PERMANENT_SESSION_LIFETIME=1800,       # Session timeout after 30 minutes
    SESSION_REFRESH_EACH_REQUEST=True,     # Update session with each request
    
    # General security settings
    SECURITY_STRICT_MODE=False,            # If True, block suspicious requests instead of just logging
    PREFERRED_URL_SCHEME='https',          # Use HTTPS for generated URLs
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,   # Limit upload size to 10MB
    SEND_FILE_MAX_AGE_DEFAULT=31536000,    # Cache static files for 1 year
    JSON_SORT_KEYS=False                   # Don't sort JSON keys for better performance
)

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    strategy="fixed-window"
)

# Configure the database connection
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 30,  # Increase connection pool size for high concurrency
    "max_overflow": 40,  # Allow additional connections when pool is full
    "pool_recycle": 300,  # Recycle connections every 5 minutes
    "pool_pre_ping": True,  # Verify connections before using them
    "pool_timeout": 30,  # Maximum time to wait for connection from pool
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the database with the app
db.init_app(app)

# Add request timing middleware for performance monitoring and security
@app.before_request
def before_request():
    # Record request start time for performance monitoring
    g.start_time = time.time()
    
    # Session security monitoring for authenticated users
    if current_user.is_authenticated and not request.path.startswith('/static/'):
        # Check for potential session hijacking by comparing user agent
        current_ua = request.user_agent.string if request.user_agent else 'Unknown'
        
        try:
            stored_ua = session.get('user_agent')
            
            # Store user agent if it's not already stored
            if not stored_ua:
                session['user_agent'] = current_ua
            
            # If user agent changed dramatically, this might be a session hijacking attempt
            elif stored_ua != current_ua:
                # Log the suspicious activity
                logger.warning(
                    f"Potential session hijacking detected. User ID: {current_user.id}, "
                    f"Old UA: {stored_ua}, New UA: {current_ua}, IP: {request.remote_addr}"
                )
                
                # For extra security, force logout and session reset
                from flask import flash, redirect, url_for
                logout_user()
                session.clear()
                flash('Your session was terminated for security reasons. Please log in again.', 'warning')
                return redirect(url_for('login'))
        except Exception as e:
            # Log any session-related errors without crashing
            logger.error(f"Session security check error: {str(e)}")
    
@app.after_request
def after_request(response):
    if hasattr(g, 'start_time'):
        elapsed = time.time() - g.start_time
        logger.info(f"Request to {request.path} completed in {elapsed:.4f}s")
        # Add Server-Timing header for client-side monitoring
        response.headers['Server-Timing'] = f'total;dur={elapsed*1000:.0f}'
    
    # Add security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Content Security Policy - Updated to allow more sources and inline scripts for compatibility
    csp = "default-src 'self'; " \
          "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://code.jquery.com https://*; " \
          "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.replit.com https://*; " \
          "img-src 'self' data: https://* blob:; " \
          "font-src 'self' https://cdn.jsdelivr.net https://*; " \
          "connect-src 'self' https://*; " \
          "manifest-src 'self'; " \
          "media-src 'self' blob:; " \
          "worker-src 'self' blob:;"
    
    response.headers['Content-Security-Policy'] = csp
    return response

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # type: ignore # LSP incorrectly flags this as an error

# Configure additional app settings for performance
app.config['TEMPLATES_AUTO_RELOAD'] = False  # Disable in production for better performance

with app.app_context():
    # Import models to ensure they're registered with SQLAlchemy
    import models  # noqa: F401
    
    # Create all database tables
    db.create_all()
    
    # Set up security middleware
    from security_middleware import setup_security_middleware
    setup_security_middleware(app)
    
    # Import and register routes
    import routes  # noqa: F401
    
    # Register API blueprint for advanced API endpoints
    from api_endpoints import api
    app.register_blueprint(api)
    
    # Register mobile API for Android app integration
    from mobile_api import mobile_api
    app.register_blueprint(mobile_api)
    
    # Set mobile API key
    app.config['MOBILE_API_KEY'] = os.environ.get('MOBILE_API_KEY', 'tracetrack-mobile-key')
    
    # Start task queue worker for asynchronous processing
    import task_queue
    task_queue.start_worker()
    
    from models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

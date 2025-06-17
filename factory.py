"""
Application factory module for traitor track.
Improves code organization, testability, and allows for multiple app instances.
"""
import os
import logging
import time

from flask import Flask, request, g, session, flash, redirect, url_for, render_template
from flask_login import LoginManager, current_user, logout_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import active_config
from logging_config import setup_logging
from security_middleware import setup_security_middleware

# Global objects
csrf = CSRFProtect()
login_manager = LoginManager()
limiter = Limiter(get_remote_address)


def create_app(config=None):
    """Create and configure the Flask application using the factory pattern."""
    
    # Initialize Flask app
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(active_config)
    
    # Override with custom config if provided
    if config:
        app.config.from_object(config)
    
    # Set up logging configuration
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Initialize extensions
    init_extensions(app)
    
    # Set up proxy fix for proper URL generation
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Register request handlers
    register_request_handlers(app, logger)
    
    # Set up security middleware
    setup_security_middleware(app)
    
    with app.app_context():
        # Import the database and models
        from app import db
        
        # Create database tables
        db.create_all()
        
        # Import and register routes
        import routes
        import api
        
        # Register error handlers
        register_error_handlers(app)
        
        # Initialize user loader for Flask-Login
        from models import User
        
        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))
    
    return app


def init_extensions(app):
    """Initialize Flask extensions."""
    # Import the database
    from app import db
    
    # Initialize database
    db.init_app(app)
    
    # Initialize CSRF protection
    csrf.init_app(app)
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'login'  # type: ignore
    
    # Initialize rate limiter
    limiter.init_app(app)


def register_request_handlers(app, logger):
    """Register before and after request handlers."""
    
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
        
        # Content Security Policy
        csp = "default-src 'self'; " \
              "script-src 'self' https://cdn.jsdelivr.net https://code.jquery.com; " \
              "style-src 'self' https://cdn.jsdelivr.net https://cdn.replit.com 'unsafe-inline'; " \
              "img-src 'self' data: https://*; " \
              "font-src 'self' https://cdn.jsdelivr.net; " \
              "connect-src 'self'; " \
              "manifest-src 'self'; " \
              "worker-src 'self'"
        
        response.headers['Content-Security-Policy'] = csp
        return response


def register_error_handlers(app):
    """Register error handlers for the application."""
    
    @app.errorhandler(400)
    def bad_request(error):
        return render_template('errors/400.html'), 400
    
    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template('errors/500.html'), 500

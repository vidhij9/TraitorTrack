"""
Core application factory and configuration.
Consolidates app creation and initialization logic.
"""

import os
import logging
from flask import Flask, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy.orm import DeclarativeBase

# Database setup
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

def create_app(config=None):
    """
    Application factory pattern for creating Flask application instances.
    
    Args:
        config: Configuration object or None for default
        
    Returns:
        Flask application instance
    """
    app = Flask(__name__, 
                template_folder='../../templates',
                static_folder='../../static')
    
    # Load configuration
    _configure_app(app, config)
    
    # Initialize extensions
    _init_extensions(app)
    
    # Setup logging
    _setup_logging(app)
    
    # Register blueprints and routes
    _register_routes(app)
    
    # Setup error handlers
    _setup_error_handlers(app)
    
    # Initialize database
    _init_database(app)
    
    return app

def _configure_app(app, config):
    """Configure the Flask application."""
    # Basic configuration
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-key-change-in-production")
    app.config['DEBUG'] = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # Database configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 50,
        "max_overflow": 60,
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_timeout": 20,
        "pool_use_lifo": True,
        "connect_args": {
            "keepalives": 1,
            "keepalives_idle": 60,
            "keepalives_interval": 10,
            "keepalives_count": 3,
            "options": "-c statement_timeout=90000"
        }
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Security configuration
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('ENVIRONMENT') == 'production'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutes
    
    # Rate limiting
    app.config['RATELIMIT_DEFAULT'] = "200 per day"
    app.config['RATELIMIT_STORAGE_URI'] = "memory://"
    
    # Apply proxy fix for deployment
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

def _init_extensions(app):
    """Initialize Flask extensions."""
    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

def _setup_logging(app):
    """Setup application logging."""
    if not app.debug:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(name)s:%(levelname)s: %(message)s'
        )
        app.logger.setLevel(logging.INFO)
        app.logger.info('TraceTrack application startup')

def _register_routes(app):
    """Register application routes and blueprints."""
    # Import and register blueprints
    from ..auth.routes import auth_bp
    from ..api.routes import api_bp
    from ..routes.main import main_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(main_bp)
    
    # Request logging
    @app.before_request
    def log_request_info():
        if app.config.get('DEBUG'):
            app.logger.info(f'Request: {request.method} {request.url} - IP: {request.remote_addr}')
    
    @app.after_request
    def after_request(response):
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Cache control for authenticated pages
        if request.endpoint and 'login' not in request.endpoint:
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        
        return response

def _setup_error_handlers(app):
    """Setup error handlers."""
    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Server Error: {error}')
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html'), 403

def _init_database(app):
    """Initialize database tables."""
    with app.app_context():
        # Import models to ensure they're registered
        from ..models import User, Bag, Scan, Bill, BillBag, Link
        
        # Create tables
        db.create_all()
        
        # Create default admin user if none exists
        _create_default_admin()

def _create_default_admin():
    """Create default admin user if none exists."""
    from ..models.user import User
    from werkzeug.security import generate_password_hash
    
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@tracetrack.com',
            password_hash=generate_password_hash('admin'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        logging.info('Default admin user created')
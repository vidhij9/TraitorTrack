import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define database model base class
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

# Create Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Production-compatible session configuration
app.config.update(
    SESSION_COOKIE_SECURE=False,  # Allow HTTP in development
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_DOMAIN=None,
    SESSION_COOKIE_PATH='/',
    SESSION_COOKIE_NAME='tracetrack_session',
    PERMANENT_SESSION_LIFETIME=86400,  # 24 hours
    SESSION_REFRESH_EACH_REQUEST=True  # Update session on each request
)

# Configure database with environment-specific URLs
def get_database_url():
    """Get appropriate database URL based on environment"""
    flask_env = os.environ.get('FLASK_ENV', 'development')
    
    # Check if we have separate dev/prod URLs configured
    dev_db_url = os.environ.get('DEV_DATABASE_URL')
    prod_db_url = os.environ.get('PROD_DATABASE_URL')
    fallback_db_url = os.environ.get('DATABASE_URL')
    
    if flask_env == 'production' and prod_db_url:
        return prod_db_url
    elif flask_env == 'development' and dev_db_url:
        return dev_db_url
    elif fallback_db_url:
        # Use the main DATABASE_URL but create separate databases based on environment
        if 'neondb' in fallback_db_url:
            if flask_env == 'development':
                # Parse URL components properly to avoid changing username
                from urllib.parse import urlparse, urlunparse
                parsed = urlparse(fallback_db_url)
                
                # Replace only the database name part, keep everything else the same
                new_path = '/tracetrack_dev'
                dev_parsed = parsed._replace(path=new_path)
                dev_url = urlunparse(dev_parsed)
                return dev_url
            else:
                # Production uses the original database
                return fallback_db_url
        else:
            return fallback_db_url
    else:
        raise ValueError("No database URL configured")

# Configure database with environment-specific settings
flask_env = os.environ.get('FLASK_ENV', 'development')
app.config["SQLALCHEMY_DATABASE_URI"] = get_database_url()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Environment-specific database connection pool settings
if flask_env == 'production':
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
else:
    # Development settings - smaller pool, enable SQL logging for debugging
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_timeout": 10,
        "pool_use_lifo": True,
        "connect_args": {
            "keepalives": 1,
            "keepalives_idle": 60,
            "keepalives_interval": 10,
            "keepalives_count": 3
        }
    }
    app.config["SQLALCHEMY_ECHO"] = True  # Enable SQL logging in development

# Security settings - Fix session management for deployment
app.config.update(
    SESSION_COOKIE_SECURE=False,  # Temporarily disable for troubleshooting
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE=None,  # Allow cross-site for deployment
    PERMANENT_SESSION_LIFETIME=1800,
    SESSION_REFRESH_EACH_REQUEST=True,
    PREFERRED_URL_SCHEME='https',
    WTF_CSRF_TIME_LIMIT=None,
    WTF_CSRF_SSL_STRICT=False,
    SESSION_TYPE='filesystem',  # Use filesystem sessions
)

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
csrf.init_app(app)
limiter.init_app(app)

# Configure CSRF exemptions for deployment compatibility
app.config['WTF_CSRF_ENABLED'] = False  # Temporarily disable CSRF for deployment troubleshooting

# Setup error handlers and monitoring
from error_handlers import setup_error_handlers, setup_request_logging, setup_health_monitoring
setup_error_handlers(app)
setup_request_logging(app)
setup_health_monitoring(app)

# Add session validation and cache control
@app.before_request
def before_request():
    """Validate authentication and session before each request"""
    from flask import session, request, redirect, url_for
    from simple_auth import is_authenticated
    
    # Skip validation for login, register, static files, and debug endpoints
    excluded_paths = ['/login', '/register', '/static', '/logout', '/setup', '/debug-deployment', '/test-login', '/session-test']
    if any(request.path.startswith(path) for path in excluded_paths):
        return
    
    # For protected routes, validate authentication
    if request.endpoint and request.endpoint not in ['login', 'register', 'logout', 'setup']:
        if not is_authenticated():
            # Redirect to login for protected routes
            if request.path != '/' and not request.path.startswith('/api'):
                return redirect(url_for('login'))

@app.after_request
def after_request(response):
    """Add cache control headers to authenticated pages"""
    from flask import session, request
    
    # Check if user is authenticated
    if session.get('logged_in') or session.get('auth_session_id'):
        # Add no-cache headers to prevent browser caching of authenticated pages
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['Last-Modified'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
    
    return response

# Setup deployment configuration
from deployment_config import configure_for_deployment, setup_monitoring_alerts
configure_for_deployment(app)
setup_monitoring_alerts(app)

# Add CSRF token to template context
@app.context_processor
def inject_csrf_token():
    from flask_wtf.csrf import generate_csrf
    return dict(csrf_token=generate_csrf)

# Configure login
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Import models for database tables
with app.app_context():
    from models import User, UserRole, Bag, BagType, Link, Scan, Bill, BillBag
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Routes will be imported via main.py to prevent circular imports

# Temporarily comment out API endpoints to fix circular imports
# We'll uncomment and fix these later if needed
# from api_endpoints import api
# app.register_blueprint(api, name='api_endpoints')

# from mobile_api import mobile_api
# app.register_blueprint(mobile_api)

@app.context_processor
def inject_current_user():
    """Make current_user available in all templates"""
    from flask import session
    # Simple session-based authentication check
    is_authenticated = session.get('logged_in', False)
    
    # Create a user object that matches template expectations
    class CurrentUser:
        def __init__(self):
            if is_authenticated:
                self.id = session.get('user_id')
                self.username = session.get('username')
                self.email = session.get('email')
                self.role = session.get('user_role')
                self._is_authenticated = True
            else:
                self.id = None
                self.username = None
                self.email = None
                self.role = None
                self._is_authenticated = False
        
        def is_admin(self):
            return self._is_authenticated and self.role == 'admin'
        
        @property
        def is_authenticated(self):
            return self._is_authenticated
    
    current_user = CurrentUser()
    return dict(current_user=current_user)
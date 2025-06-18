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
def get_current_environment():
    """Detect current environment with improved logic"""
    # Check explicit environment variable first
    env = os.environ.get('ENVIRONMENT', '').lower()
    if env in ['production', 'prod']:
        return 'production'
    elif env in ['development', 'dev']:
        return 'development'
    
    # Check Flask environment
    flask_env = os.environ.get('FLASK_ENV', '').lower()
    if flask_env == 'production':
        return 'production'
    elif flask_env in ['development', 'dev']:
        return 'development'
    
    # Check Replit environment indicators
    replit_env = os.environ.get('REPLIT_ENVIRONMENT', '').lower()
    if replit_env == 'production':
        return 'production'
    
    # Check REPL_SLUG for specific production deployments
    repl_slug = os.environ.get('REPL_SLUG', '')
    if repl_slug == 'traitortrack':
        return 'production'
    
    # Default to development for safety
    return 'development'

def get_database_url():
    """Get appropriate database URL based on environment with complete database isolation"""
    current_env = get_current_environment()
    
    if current_env == 'production':
        # Production environment - try dedicated production database first
        prod_url = os.environ.get('PROD_DATABASE_URL')
        if prod_url:
            logging.info("PRODUCTION: Using dedicated production database")
            return prod_url
        else:
            # Use main database with production schema
            base_url = os.environ.get('DATABASE_URL', '')
            if base_url:
                logging.info("PRODUCTION: Using main database with production schema")
                return base_url
            else:
                raise ValueError("No database URL configured for production")
    else:
        # Development environment - try dedicated development database first
        dev_url = os.environ.get('DEV_DATABASE_URL')
        if dev_url:
            logging.info("DEVELOPMENT: Using dedicated development database")
            return dev_url
        else:
            # Use main database with development schema
            base_url = os.environ.get('DATABASE_URL', '')
            if base_url:
                logging.info("DEVELOPMENT: Using main database with development schema")
                return base_url
            else:
                raise ValueError("No database URL configured for development")

# Configure database with environment-specific settings
flask_env = os.environ.get('FLASK_ENV', 'development')
app.config["SQLALCHEMY_DATABASE_URI"] = get_database_url()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Environment-specific schema configuration
def get_database_schema():
    """Get database schema based on environment"""
    current_env = get_current_environment()
    return current_env

# Configure database engine with schema isolation
database_schema = get_database_schema()
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 5,
    "max_overflow": 10,
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "pool_timeout": 20,
    "connect_args": {
        "connect_timeout": 60,
        "application_name": "tracetrack_app",
        "options": f"-csearch_path={database_schema}"
    }
}

# Disable SQL logging to reduce noise
app.config["SQLALCHEMY_ECHO"] = False

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

# Create tables after app initialization
with app.app_context():
    try:
        # Import models to ensure they're registered
        import models
        # Create all tables
        db.create_all()
        logging.info("Database tables created successfully")
    except Exception as e:
        logging.error(f"Database initialization error: {e}")

# Re-enable CSRF protection with proper configuration
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour
app.config['WTF_CSRF_SSL_STRICT'] = False  # Allow HTTP in development

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
                return redirect('/login')

@app.after_request
def after_request(response):
    """Add security headers and cache control"""
    from flask import session, request
    
    # Add comprehensive security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Add Content Security Policy
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "font-src 'self' https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self';"
    )
    response.headers['Content-Security-Policy'] = csp
    
    # Check if user is authenticated
    if session.get('logged_in') or session.get('auth_session_id'):
        # Add no-cache headers to prevent browser caching of authenticated pages
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['Last-Modified'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
    
    return response

# Basic deployment configuration
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year cache for static files

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
    from simple_auth import is_authenticated
    
    # Create a user object that matches template expectations
    class ProductionUser:
        def __init__(self):
            # Check session directly for better reliability
            authenticated = (
                session.get('authenticated', False) or 
                session.get('logged_in', False)
            )
            user_id = session.get('user_id')
            
            if authenticated and user_id:
                try:
                    from models import User
                    actual_user = User.query.get(user_id)
                    if actual_user:
                        self.id = actual_user.id
                        self.username = actual_user.username
                        self.email = actual_user.email
                        self.role = actual_user.role
                        self._is_authenticated = True
                    else:
                        self._setup_anonymous()
                except Exception:
                    self._setup_anonymous()
            else:
                self._setup_anonymous()
        
        def _setup_anonymous(self):
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
    
    current_user = ProductionUser()
    return dict(current_user=current_user)
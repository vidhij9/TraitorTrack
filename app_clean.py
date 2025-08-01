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

def get_current_environment():
    """Detect current environment - simplified logic"""
    # Check if we're on the production domain
    replit_domains = os.environ.get('REPLIT_DOMAINS', '')
    if 'traitortrack.replit.app' in replit_domains:
        return 'production'
    
    # Check explicit environment variable
    env = os.environ.get('ENVIRONMENT', '').lower()
    if env == 'production':
        return 'production'
    
    # Default to development (Replit preview and local dev)
    return 'development'

def get_database_url():
    """Get appropriate database URL based on environment"""
    current_env = get_current_environment()
    
    if current_env == 'production':
        # Production: use dedicated production database URL
        prod_url = os.environ.get('PRODUCTION_DATABASE_URL')
        if prod_url:
            logging.info("PRODUCTION: Using production database")
            return prod_url
        else:
            raise ValueError("PRODUCTION_DATABASE_URL must be set for production deployment")
    else:
        # Development: use Replit's default DATABASE_URL
        dev_url = os.environ.get('DATABASE_URL')
        if dev_url:
            logging.info("DEVELOPMENT: Using development database")
            return dev_url
        else:
            raise ValueError("DATABASE_URL not available in development environment")

# Configure database with environment-specific settings
flask_env = os.environ.get('FLASK_ENV', 'development')
app.config["SQLALCHEMY_DATABASE_URI"] = get_database_url()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configure database engine options
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 5,
    "max_overflow": 10,
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "pool_timeout": 20,
    "connect_args": {
        "connect_timeout": 60,
        "application_name": "tracetrack_app"
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
    WTF_CSRF_ENABLED=True,
    SECRET_KEY=os.environ.get("SESSION_SECRET", "dev-secret-key"),
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

# CSRF protection configuration moved to main config above

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
    from auth_utils import is_authenticated
    
    # Skip validation for login, register, static files, public pages, and debug endpoints
    excluded_paths = ['/login', '/register', '/static', '/logout', '/setup', '/debug-deployment', '/test-login', '/session-test', '/', '/bill/', '/bag/']
    if any(request.path.startswith(path) for path in excluded_paths):
        return
    
    # Allow public access to the root page
    if request.path == '/':
        return
    
    # For protected routes, validate authentication - but don't redirect admin routes
    if request.endpoint and request.endpoint not in ['login', 'register', 'logout', 'setup', 'index']:
        if not is_authenticated():
            # Only redirect to login for non-API protected routes
            if not request.path.startswith('/api'):
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

# Handle CSRF errors for JSON API endpoints
@app.errorhandler(400)
def handle_csrf_error(e):
    from flask import request, jsonify
    
    # If it's an AJAX request or API endpoint, return JSON
    if (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
        request.headers.get('Accept', '').find('application/json') != -1 or
        request.path.startswith('/process_') or 
        request.path.startswith('/api/')):
        
        if 'CSRF' in str(e) or 'csrf' in str(e.description or '').lower():
            return jsonify({
                'success': False, 
                'message': 'Security token expired. Please refresh the page and try again.'
            }), 400
        
        return jsonify({
            'success': False, 
            'message': 'Bad request. Please check your input and try again.'
        }), 400
    
    # For regular requests, return HTML error page
    return e

# Configure login
# Flask-Login configuration
try:
    login_manager.login_view = 'login'
except Exception:
    # Handle potential Flask-Login configuration issues
    pass
login_manager.login_message = 'Please log in to access this page.'
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
    from auth_utils import is_authenticated
    
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
        
        def is_biller(self):
            return self._is_authenticated and self.role == 'biller'
        
        def can_edit_bills(self):
            """Check if user can edit bills"""
            return self.is_admin() or self.is_biller()
        
        @property
        def is_authenticated(self):
            return self._is_authenticated
    
    current_user = ProductionUser()
    return dict(current_user=current_user)
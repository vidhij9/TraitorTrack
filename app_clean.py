import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Configure logging for production - suppress unnecessary warnings
import warnings
warnings.filterwarnings("ignore", module="flask_limiter")
warnings.filterwarnings("ignore", message=".*flask_limiter.*")
warnings.filterwarnings("ignore", message=".*Redis not available.*")
warnings.filterwarnings("ignore", message=".*Index creation issue.*")
warnings.filterwarnings("ignore", message=".*Statistics update issue.*")
warnings.filterwarnings("ignore", message=".*optimizer not loaded.*")
warnings.filterwarnings("ignore", message=".*No module named.*")

# Initialize logging - suppress noise
logging.basicConfig(
    level=logging.ERROR,  # Only show errors
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True  # Force reconfigure logging
)
logger = logging.getLogger(__name__)

# Suppress noisy loggers
logging.getLogger('production_scale_optimizer').setLevel(logging.ERROR)
logging.getLogger('production_database_optimizer').setLevel(logging.ERROR)
logging.getLogger('production_optimizer').setLevel(logging.ERROR)
logging.getLogger('main').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# Define database model base class
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
csrf = CSRFProtect()

# Configure limiter with Redis backend for distributed rate limiting
try:
    import os
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["2000000 per day", "200000 per hour", "20000 per minute"],  # Ultra-high limits for 50+ concurrent users
        storage_uri=redis_url if 'REDIS_URL' in os.environ else "memory://",
        strategy="fixed-window",  # Use fixed window strategy for better performance
        headers_enabled=True,  # Enable rate limit headers
        swallow_errors=True  # Don't fail on Redis errors
    )
except:
    # Fallback to memory storage
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["2000000 per day", "200000 per hour", "20000 per minute"],  # Ultra-high limits
        storage_uri="memory://",
        strategy="fixed-window"
    )

# Create Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-for-tracetrack-2024")

# Simple and reliable session configuration
app.config.update(
    SESSION_COOKIE_SECURE=False,  # Allow HTTP in development
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_NAME='tracetrack_session',
    PERMANENT_SESSION_LIFETIME=86400,  # 24 hours
    SEND_FILE_MAX_AGE_DEFAULT=0  # Disable caching for development
)

def get_current_environment():
    """Detect current environment - simplified logic"""
    # Check explicit environment variable first
    env = os.environ.get('ENVIRONMENT', '').lower()
    if env == 'production':
        return 'production'
    
    # Check if we're on the actual production domain (not Replit preview)
    replit_domains = os.environ.get('REPLIT_DOMAINS', '')
    if 'traitor-track.replit.app' in replit_domains and not 'replit.dev' in replit_domains:
        return 'production'
    
    # Default to development for Replit testing and local dev
    return 'development'

def get_database_url():
    """Get appropriate database URL based on environment"""
    current_env = get_current_environment()
    
    if current_env == 'production':
        # Production: use PRODUCTION_DATABASE_URL if available, fallback to DATABASE_URL
        prod_url = os.environ.get('PRODUCTION_DATABASE_URL')
        if prod_url:
            logging.info("PRODUCTION: Using production database")
            return prod_url
        else:
            dev_url = os.environ.get('DATABASE_URL')
            if dev_url:
                logging.info("PRODUCTION: Using fallback development database")
                return dev_url
            else:
                raise ValueError("No database URL available for production")
    else:
        # Development: use DATABASE_URL (Replit Neon database)
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

# Import production-ready configuration
try:
    from production_config import ProductionConfig
    # Apply production configuration
    ProductionConfig.apply_to_app(app)
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = ProductionConfig.DATABASE_CONFIG
    logger.info("Using PRODUCTION configuration for 20+ concurrent users with heavy operations")
except ImportError:
    try:
        from high_performance_config import HighPerformanceConfig, ConnectionPoolManager
        # Apply high-performance configuration
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = HighPerformanceConfig.DATABASE_CONFIG
        HighPerformanceConfig.apply_to_app(app)
        logger.info("Using HIGH-PERFORMANCE configuration for 50+ concurrent users")
    except ImportError:
        # Fallback to inline optimized configuration
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_size": 30,  # Increased for heavy operations
            "max_overflow": 20,  # Additional connections for peaks
            "pool_recycle": 300,
            "pool_pre_ping": True,
            "pool_timeout": 20,  # Increased timeout for heavy queries
            "echo": False,
            "echo_pool": False,
            "pool_use_lifo": True,
            "connect_args": {
                "keepalives": 1,
                "keepalives_idle": 10,
                "keepalives_interval": 5,
                "keepalives_count": 5,
                "connect_timeout": 10,
                "application_name": "TraceTrack_Production",
                "options": "-c statement_timeout=30000"  # 30 second query timeout
            }
        }
        logger.info("Using optimized database configuration for high concurrency")

# Disable SQL logging to reduce noise
app.config["SQLALCHEMY_ECHO"] = False

# Security settings - Fix session management for deployment
app.config.update(
    SESSION_COOKIE_SECURE=False,  # False for HTTP development
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',  # Changed from None to Lax for proper session handling
    PERMANENT_SESSION_LIFETIME=1800,
    SESSION_REFRESH_EACH_REQUEST=False,  # Changed to False to prevent session loss
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

# Make CSRF available for route decorators
# CSRF exemption will be handled in routes.py for specific endpoints
limiter.init_app(app)

# Apply performance optimizations
try:
    from performance_patches import apply_performance_patches
    apply_performance_patches(app)
    logging.info("Performance patches applied successfully")
except Exception as e:
    logging.warning(f"Performance patches not applied: {e}")

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

# Security headers and optimizations are built into the application
# No additional modules needed - security is handled in the main app configuration

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
    """Add security headers and cache control with header limit check"""
    from flask import session, request
    
    # Limit total headers to prevent issues with concurrent requests
    if len(response.headers) > 50:
        # Keep only essential headers
        essential = ['Content-Type', 'Content-Length', 'Cache-Control', 'Set-Cookie', 'Location']
        headers_to_keep = {k: v for k, v in response.headers.items() if k in essential}
        response.headers.clear()
        for k, v in headers_to_keep.items():
            response.headers[k] = v
    
    # Security headers - only add if not exceeding limit
    if len(response.headers) < 40:
        if 'X-Content-Type-Options' not in response.headers:
            response.headers['X-Content-Type-Options'] = 'nosniff'
        if 'X-Frame-Options' not in response.headers:
            response.headers['X-Frame-Options'] = 'DENY'
        if 'X-XSS-Protection' not in response.headers:
            response.headers['X-XSS-Protection'] = '1; mode=block'
    
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

# Add CSRF token and current_user to template context
@app.context_processor
def inject_csrf_token():
    from flask_wtf.csrf import generate_csrf
    from auth_utils import current_user
    return dict(csrf_token=generate_csrf, current_user=current_user)

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

# Configure login after app initialization
def configure_login_manager():
    """Configure Flask-Login after app is created"""
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

# Call configuration after app is ready
configure_login_manager()

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
        
        def is_dispatcher(self):
            return self._is_authenticated and self.role == 'dispatcher'
        
        def can_edit_bills(self):
            """Check if user can edit bills"""
            return self.is_admin() or self.is_biller()
        
        @property
        def is_authenticated(self):
            return self._is_authenticated
    
    current_user = ProductionUser()
    return dict(current_user=current_user)
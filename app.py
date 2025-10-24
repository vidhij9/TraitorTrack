import os
import logging
import secrets
from flask import Flask, session, request, redirect, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_session import Session
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging properly
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define database model base class
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
csrf = CSRFProtect()

# Create CSRF exemption decorator for compatibility
class CSRFExempt:
    @staticmethod
    def exempt(f):
        """CSRF exemption decorator"""
        if hasattr(csrf, 'exempt'):
            return csrf.exempt(f)
        else:
            return f

csrf_compat = CSRFExempt()

# Configure rate limiter with memory storage
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["2000 per day", "500 per hour"],
    storage_uri="memory://",
    strategy="fixed-window",
    swallow_errors=True
)

# Create Flask application
app = Flask(__name__)

# Proxy fix for correct URL generation
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# SECURITY: Require SESSION_SECRET environment variable
session_secret = os.environ.get("SESSION_SECRET")
if not session_secret:
    raise ValueError("SESSION_SECRET environment variable is required for security")
app.secret_key = session_secret

# Session configuration - using filesystem for compatibility
app.config.update(
    SESSION_TYPE='filesystem',
    SESSION_FILE_DIR='/tmp/flask_session',
    SESSION_PERMANENT=False,
    SESSION_USE_SIGNER=True,
    SESSION_FILE_THRESHOLD=500,
    SESSION_COOKIE_SECURE=False,  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_NAME='tracetrack_session',
    PERMANENT_SESSION_LIFETIME=3600,  # 1 hour
    SEND_FILE_MAX_AGE_DEFAULT=0,
    WTF_CSRF_ENABLED=True,
    WTF_CSRF_TIME_LIMIT=None,
    WTF_CSRF_CHECK_DEFAULT=True,
    WTF_CSRF_SSL_STRICT=False,
    PREFERRED_URL_SCHEME='https'
)

# Initialize Flask-Session
os.makedirs('/tmp/flask_session', exist_ok=True)
Session(app)

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
if not app.config["SQLALCHEMY_DATABASE_URI"]:
    raise ValueError("DATABASE_URL environment variable is required")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = False

# Optimized connection pool settings
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 20,
    "max_overflow": 10,
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "pool_timeout": 30,
    "echo": False,
    "echo_pool": False
}

logger.info("Database connection pool configured: 20 base + 10 overflow")

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
csrf.init_app(app)
limiter.init_app(app)

# Configure login manager
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Initialize database tables and admin user
with app.app_context():
    try:
        # Import models to ensure they're registered
        import models
        # Create all tables
        db.create_all()
        
        # Create or update admin user
        from models import User
        
        admin = User.query.filter_by(username='admin').first()
        
        # SECURITY: Admin password must be provided via environment variable
        admin_password = os.environ.get('ADMIN_PASSWORD')
        
        if not admin:
            # Create new admin user
            if not admin_password:
                # Generate a secure random password
                admin_password = secrets.token_urlsafe(16)
                print('=' * 80)
                print('WARNING: No ADMIN_PASSWORD environment variable set!')
                print('Generated secure random password for admin user:')
                print(f'USERNAME: admin')
                print(f'PASSWORD: {admin_password}')
                print('IMPORTANT: Save this password NOW! It will not be displayed again.')
                print('=' * 80)
            
            admin = User()
            admin.username = 'admin'
            admin.email = 'admin@tracetrack.com'
            admin.set_password(admin_password)
            admin.role = 'admin'
            admin.verified = True
            db.session.add(admin)
            db.session.commit()
            logger.info("Admin user created successfully")
        elif admin_password:
            # Update existing admin password if ADMIN_PASSWORD is set
            admin.set_password(admin_password)
            admin.role = 'admin'
            admin.verified = True
            db.session.commit()
            logger.info("Admin password synchronized with ADMIN_PASSWORD environment variable")
        
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise

# Setup error handlers
from error_handlers import setup_error_handlers, setup_request_logging, setup_health_monitoring
setup_error_handlers(app)
setup_request_logging(app)
setup_health_monitoring(app)

# Add before_request handler for authentication
@app.before_request
def before_request():
    """Validate authentication before each request"""
    from auth_utils import is_authenticated
    
    # Skip validation for public paths
    excluded_paths = ['/login', '/register', '/static', '/logout', '/health', '/api/health']
    if any(request.path.startswith(path) for path in excluded_paths):
        return
    
    # Allow public access to root
    if request.path == '/':
        return
    
    # For protected routes, validate authentication
    if request.endpoint and request.endpoint not in ['login', 'register', 'logout']:
        if not is_authenticated():
            if not request.path.startswith('/api'):
                return redirect('/login')

# Add after_request handler for security headers
@app.after_request
def after_request(response):
    """Add security headers and cache control"""
    
    # Security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Cache control for authenticated pages
    if session.get('logged_in') or session.get('auth_session_id'):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    return response

# Add CSRF token and current_user to template context
@app.context_processor
def inject_csrf_token():
    from flask_wtf.csrf import generate_csrf
    from auth_utils import current_user
    return dict(csrf_token=generate_csrf, current_user=current_user)

@app.context_processor
def inject_current_user():
    """Make current_user available in all templates"""
    from auth_utils import is_authenticated
    
    class TemplateUser:
        def __init__(self):
            user_id = session.get('user_id')
            if is_authenticated() and user_id:
                try:
                    from models import User
                    actual_user = User.query.get(user_id)
                    if actual_user:
                        self.id = actual_user.id
                        self.username = actual_user.username
                        self.email = actual_user.email
                        self.role = actual_user.role
                        self.is_authenticated = True
                        return
                except Exception as e:
                    logger.error(f"Error loading user: {e}")
            
            # Anonymous user
            self.id = None
            self.username = None
            self.email = None
            self.role = None
            self.is_authenticated = False
        
        def is_admin(self):
            return self.role == 'admin' if self.is_authenticated else False
        
        def is_biller(self):
            return self.role == 'biller' if self.is_authenticated else False
        
        def is_dispatcher(self):
            return self.role == 'dispatcher' if self.is_authenticated else False
        
        def can_edit_bills(self):
            """Check if user can edit bills (billers and admins)"""
            return self.role in ('biller', 'admin') if self.is_authenticated else False
    
    return dict(current_user=TemplateUser())

# Handle CSRF errors
@app.errorhandler(400)
def handle_csrf_error(e):
    from flask import jsonify
    
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
    
    return e

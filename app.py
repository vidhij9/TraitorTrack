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
from flask_migrate import Migrate
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
migrate = Migrate()
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

# Configure rate limiter - fallback to memory if Redis unavailable
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["2000 per day", "500 per hour"],
    storage_uri="memory://",  # Using memory for now due to Redis connection pool limits
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

# Detect production environment - only actual deployments, not dev workspaces
is_production = (
    os.environ.get('REPLIT_DEPLOYMENT') == '1' or
    os.environ.get('ENVIRONMENT') == 'production'
)

# Session configuration - using filesystem (Redis causes port exhaustion under load)
app.config.update(
    SESSION_TYPE='filesystem',
    SESSION_FILE_DIR='/tmp/flask_session',
    SESSION_PERMANENT=False,
    SESSION_USE_SIGNER=True,
    SESSION_FILE_THRESHOLD=500,
    SESSION_COOKIE_SECURE=is_production,  # Auto-enable HTTPS in production
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_NAME='tracetrack_session',
    PERMANENT_SESSION_LIFETIME=3600,  # 1 hour
    SEND_FILE_MAX_AGE_DEFAULT=0,
    WTF_CSRF_ENABLED=True,
    WTF_CSRF_TIME_LIMIT=None,
    WTF_CSRF_CHECK_DEFAULT=True,
    WTF_CSRF_SSL_STRICT=False,
    PREFERRED_URL_SCHEME='https' if is_production else 'http'
)

logger.info(f"Environment: {'production' if is_production else 'development'} - HTTPS cookies: {is_production}")

# Initialize Flask-Session
os.makedirs('/tmp/flask_session', exist_ok=True)
Session(app)
logger.info("Filesystem session storage configured")

# Database configuration - auto-select based on environment
# Production deployments use PRODUCTION_DATABASE_URL (AWS RDS)
# Development workspace uses DATABASE_URL (Replit PostgreSQL)
if is_production:
    # Production: Use AWS RDS
    database_url = os.environ.get("PRODUCTION_DATABASE_URL")
    if not database_url:
        # Fallback to DATABASE_URL if PRODUCTION_DATABASE_URL not set
        database_url = os.environ.get("DATABASE_URL")
        logger.warning("PRODUCTION_DATABASE_URL not set, falling back to DATABASE_URL")
    db_source = "AWS RDS (PRODUCTION_DATABASE_URL)"
else:
    # Development: Use Replit database
    database_url = os.environ.get("DATABASE_URL")
    db_source = "Replit PostgreSQL (DATABASE_URL)"

if not database_url:
    raise ValueError("Database URL not found. Set DATABASE_URL (dev) or PRODUCTION_DATABASE_URL (prod)")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
logger.info(f"Database: {db_source}")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = False

# Optimized connection pool settings - SCALED FOR 100+ CONCURRENT USERS
# CRITICAL: Pool size must account for multiple Gunicorn workers
# Formula: (pool_size + max_overflow) * num_workers < postgres max_connections
# With 2 workers: (25 + 15) * 2 = 80 connections (safe for max_connections=100)
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 25,  # Per-worker pool (25 * 2 workers = 50 base connections)
    "max_overflow": 15,  # Per-worker overflow (15 * 2 = 30 overflow connections)
    "pool_recycle": 300,  # Recycle connections every 5 minutes
    "pool_pre_ping": True,  # Verify connections before use
    "pool_timeout": 30,  # Wait up to 30s for connection
    "echo": False,
    "echo_pool": False,
    "connect_args": {
        "connect_timeout": 10,  # Database connection timeout
        "application_name": "tracetrack_web"  # For monitoring
    }
}

logger.info("Database connection pool configured: 25 base + 15 overflow per worker (80 total for 2 workers)")

# Add database pool monitoring function
def get_db_pool_stats():
    """Get current database connection pool statistics for monitoring"""
    try:
        pool = db.engine.pool
        return {
            'size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'total_connections': pool.checkedout() + pool.checkedin()
        }
    except Exception as e:
        logger.error(f"Error getting pool stats: {e}")
        return {}

# Initialize extensions
db.init_app(app)
migrate.init_app(app, db)
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
        
        # NOTE: Schema management is now handled by Alembic migrations
        # db.create_all() is disabled to avoid conflicts with migration system
        # To initialize database schema on fresh deployment, run: flask db upgrade
        # db.create_all()  # DISABLED: Use Flask-Migrate instead
        
        # Create or update admin user (only if tables exist)
        try:
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
            
            # Initialize pool monitoring with alerts (inside app context)
            try:
                from pool_monitor import init_pool_monitor
                pool_monitoring_enabled = os.environ.get('POOL_MONITORING_ENABLED', 'true').lower() == 'true'
                init_pool_monitor(db.engine, enabled=pool_monitoring_enabled)
                if pool_monitoring_enabled:
                    logger.info("Database connection pool monitoring started with alert thresholds: 70%/85%/95%")
                else:
                    logger.info("Database connection pool monitoring disabled")
            except Exception as e:
                logger.error(f"Failed to initialize pool monitoring: {e}")
            
            # Initialize slow query logging (inside app context)
            try:
                from slow_query_logger import init_slow_query_logger
                slow_query_threshold = int(os.environ.get('SLOW_QUERY_THRESHOLD_MS', '100'))
                slow_query_enabled = os.environ.get('SLOW_QUERY_LOGGING_ENABLED', 'true').lower() == 'true'
                init_slow_query_logger(db.engine, threshold_ms=slow_query_threshold, enabled=slow_query_enabled)
                if slow_query_enabled:
                    logger.info(f"Slow query logging initialized - threshold: {slow_query_threshold}ms")
                else:
                    logger.info("Slow query logging disabled")
            except Exception as e:
                logger.error(f"Failed to initialize slow query logging: {e}")
            
        except Exception as e:
            # Tables might not exist yet if this is a fresh deployment
            # In that case, run: flask db upgrade
            if 'does not exist' in str(e) or 'relation' in str(e).lower():
                logger.warning("Database tables not found. Run 'flask db upgrade' to initialize schema.")
            else:
                logger.error(f"Database initialization error: {e}")
                raise
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise

# Setup error handlers
from error_handlers import setup_error_handlers, setup_request_logging, setup_health_monitoring
setup_error_handlers(app)
setup_request_logging(app)
setup_health_monitoring(app)

# Setup request tracking for distributed tracing
from request_tracking import setup_request_tracking
setup_request_tracking(app)
logger.info("Request tracking middleware initialized - all requests now have unique IDs")

# Setup session timeout middleware
@app.before_request
def check_session_timeout_middleware():
    """Check session timeout on every request and auto-logout if expired"""
    from flask import request, flash, redirect, url_for
    from auth_utils import check_session_timeout, update_session_activity, clear_session, is_authenticated
    
    # Skip timeout check for static files, login, logout, and API endpoints
    if request.endpoint in ['static', 'login', 'logout', 'register']:
        return None
    
    # Skip for API health checks
    if request.path and (request.path.startswith('/static/') or request.path == '/health'):
        return None
    
    # Check if session has expired
    is_valid, reason = check_session_timeout()
    
    if not is_valid and is_authenticated():
        # Session expired - clear it and redirect to login
        username = session.get('username', 'unknown')
        clear_session()
        
        # Set appropriate flash message
        if reason == 'absolute':
            flash('Your session has expired after 1 hour. Please log in again.', 'warning')
            logger.info(f"Session expired (absolute timeout) for user {username}")
        elif reason == 'inactivity':
            flash('Your session has expired due to inactivity. Please log in again.', 'warning')
            logger.info(f"Session expired (inactivity timeout) for user {username}")
        
        return redirect(url_for('login'))
    
    # Update last activity timestamp for valid sessions
    if is_valid and is_authenticated():
        update_session_activity()
    
    return None

logger.info("Session timeout middleware initialized - checking timeout on every request")

# Add before_request handler for authentication
@app.before_request
def before_request():
    """Validate authentication before each request"""
    from auth_utils import is_authenticated
    
    # Skip validation for public paths
    excluded_paths = ['/login', '/register', '/static', '/logout', '/health', '/api/health', '/forgot_password', '/reset_password']
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

# Initialize high-performance query optimizer
from query_optimizer import init_query_optimizer
query_optimizer = init_query_optimizer(db)
logger.info("Query optimizer initialized for high-performance operations")

# Add teardown handler for proper database session cleanup
@app.teardown_appcontext
def shutdown_session(exception=None):
    """Ensure database session is properly closed after each request"""
    try:
        db.session.remove()
        # Log session cleanup errors for monitoring
        if exception:
            logger.warning(f"Session cleanup after exception: {exception}")
    except Exception as e:
        logger.error(f"Error during session cleanup: {e}")

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

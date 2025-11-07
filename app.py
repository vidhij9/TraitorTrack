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

# Create Flask application (moved before Redis configuration)
app = Flask(__name__)

# SECURITY: Enable Jinja2 autoescape for XSS protection
# This ensures all template variables are HTML-escaped by default
app.jinja_env.autoescape = True

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

# Redis Configuration - for sessions and rate limiting
# REDIS_URL format: redis://[[username]:[password]]@host:port/db
# Default: redis://localhost:6379/0
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
redis_available = False
redis_client = None

# Try to connect to Redis if URL is provided
if redis_url and redis_url != 'redis://localhost:6379/0':
    try:
        import redis
        redis_client = redis.from_url(redis_url, socket_connect_timeout=2)
        # Test connection
        redis_client.ping()
        redis_available = True
        logger.info(f"✅ Redis connected successfully: {redis_url.split('@')[-1] if '@' in redis_url else redis_url}")
    except Exception as e:
        # In production, log error but allow fallback for resilience (deploy.sh verifies REDIS_URL is set)
        if is_production:
            logger.error(f"❌ CRITICAL: Redis connection failed in production: {str(e)}")
            logger.error(f"⚠️  WARNING: Falling back to filesystem sessions (may cause issues with multiple workers)")
            logger.error(f"⚠️  Please verify REDIS_URL is correct and Redis service is accessible")
        else:
            logger.warning(f"⚠️  Redis connection failed, falling back to filesystem/memory: {str(e)}")
        redis_available = False
        redis_client = None
else:
    # Log warning if REDIS_URL not configured
    if is_production:
        logger.error(f"❌ CRITICAL: REDIS_URL not configured in production environment")
        logger.error(f"⚠️  deploy.sh should have caught this - check deployment configuration")
    else:
        logger.info("ℹ️  REDIS_URL not configured, using filesystem/memory storage (development mode)")

# Session configuration - Redis with filesystem fallback
# SECURITY: SESSION_COOKIE_SECURE=True in production for HTTPS-only session cookies
# In development, it's set to True but the after_request handler strips the Secure flag
# to allow session persistence across HTTP (Gunicorn serves HTTP internally)
if redis_available:
    # Production: Use Redis for multi-worker session sharing
    app.config.update(
        SESSION_TYPE='redis',
        SESSION_REDIS=redis_client,
        SESSION_PERMANENT=False,
        SESSION_USE_SIGNER=True,
        SESSION_KEY_PREFIX='traitortrack:session:',
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_NAME='traitortrack_session',
        PERMANENT_SESSION_LIFETIME=3600,  # 1 hour
        SEND_FILE_MAX_AGE_DEFAULT=0,
        WTF_CSRF_ENABLED=True,
        WTF_CSRF_TIME_LIMIT=None,
        WTF_CSRF_CHECK_DEFAULT=True,
        WTF_CSRF_SSL_STRICT=False,
        PREFERRED_URL_SCHEME='https' if is_production else 'http'
    )
    session_backend = "Redis (multi-worker ready)"
else:
    # Development: Use filesystem for single-worker development
    app.config.update(
        SESSION_TYPE='filesystem',
        SESSION_FILE_DIR='/tmp/flask_session',
        SESSION_PERMANENT=False,
        SESSION_USE_SIGNER=True,
        SESSION_FILE_THRESHOLD=500,
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_NAME='traitortrack_session',
        PERMANENT_SESSION_LIFETIME=3600,  # 1 hour
        SEND_FILE_MAX_AGE_DEFAULT=0,
        WTF_CSRF_ENABLED=True,
        WTF_CSRF_TIME_LIMIT=None,
        WTF_CSRF_CHECK_DEFAULT=True,
        WTF_CSRF_SSL_STRICT=False,
        PREFERRED_URL_SCHEME='https' if is_production else 'http'
    )
    os.makedirs('/tmp/flask_session', exist_ok=True)
    session_backend = "Filesystem (single-worker only)"

# File upload size limits (for security and performance)
# MAX_FILE_UPLOAD_SIZE must be in bytes (integer). Default: 16MB
try:
    max_upload_size = int(os.environ.get('MAX_FILE_UPLOAD_SIZE', str(16 * 1024 * 1024)))
    if max_upload_size < 1024:  # Minimum 1KB
        raise ValueError("MAX_FILE_UPLOAD_SIZE must be at least 1024 bytes")
    if max_upload_size > 100 * 1024 * 1024:  # Maximum 100MB
        raise ValueError("MAX_FILE_UPLOAD_SIZE cannot exceed 100MB (104857600 bytes)")
    app.config['MAX_CONTENT_LENGTH'] = max_upload_size
    logger.info(f"File upload size limit: {max_upload_size / (1024 * 1024):.1f}MB")
except ValueError as e:
    raise ValueError(f"Invalid MAX_FILE_UPLOAD_SIZE environment variable. Must be an integer in bytes. Error: {e}")

logger.info(f"Environment: {'production' if is_production else 'development'} - HTTPS cookies: {is_production}")

# Initialize Flask-Session
Session(app)
logger.info(f"Session storage: {session_backend}")

# Configure rate limiter - Redis with in-memory fallback
if redis_available:
    # Production: Use Redis for multi-worker rate limiting
    limiter_storage_uri = redis_url
    limiter_backend = "Redis (multi-worker ready)"
else:
    # Development: Use in-memory for single-worker development
    limiter_storage_uri = "memory://"
    limiter_backend = "In-memory (single-worker only)"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["2000 per day", "500 per hour"],
    storage_uri=limiter_storage_uri,
    strategy="fixed-window",
    swallow_errors=True
)

logger.info(f"Rate limiting storage: {limiter_backend}")

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
        "application_name": "traitortrack_web"  # For monitoring
    }
}

logger.info("Database connection pool configured: 25 base + 15 overflow per worker (80 total for 2 workers)")

# Add database pool monitoring function
def get_db_pool_stats():
    """Get current database connection pool statistics for monitoring"""
    try:
        pool = db.engine.pool
        # Note: pool methods require proper type annotation for LSP
        return {
            'size': pool.size(),  # type: ignore
            'checked_in': pool.checkedin(),  # type: ignore
            'checked_out': pool.checkedout(),  # type: ignore
            'overflow': pool.overflow(),  # type: ignore
            'total_connections': pool.checkedout() + pool.checkedin()  # type: ignore
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
login_manager.login_view = 'login'  # type: ignore
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    """
    Optimized user loader with request-level caching.
    
    Caches user object in Flask's request context (g) to avoid
    repeated database queries within the same request lifecycle.
    This is critical for performance as Flask-Login calls this function
    on every authenticated request to check user session validity.
    """
    from flask import g
    from models import User
    
    # Check if user is already cached in request context
    cached_user = getattr(g, '_login_user', None)
    if cached_user is not None and str(cached_user.id) == str(user_id):
        return cached_user
    
    # Load user from database (only if not cached)
    user = User.query.get(int(user_id))
    
    # Cache in request context for subsequent auth checks in same request
    if user:
        g._login_user = user
    
    return user

# Run database migrations automatically on startup
with app.app_context():
    try:
        # Import models to ensure they're registered
        import models
        
        # AUTOMATIC MIGRATIONS: Run pending migrations on application startup
        # This ensures database schema is always up-to-date without manual intervention
        try:
            from flask_migrate import upgrade as flask_migrate_upgrade
            from alembic.script import ScriptDirectory
            from alembic.config import Config as AlembicConfig
            import alembic.command
            
            logger.info("🔄 Checking for pending database migrations...")
            
            # Get Alembic config
            migrations_path = os.path.join(os.path.dirname(__file__), 'migrations')
            alembic_cfg = AlembicConfig(os.path.join(migrations_path, 'alembic.ini'))
            alembic_cfg.set_main_option('script_location', migrations_path)
            
            # Check current migration version
            from alembic.migration import MigrationContext
            from sqlalchemy import create_engine
            
            engine = db.engine
            conn = engine.connect()
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()
            conn.close()
            
            # Get latest migration version
            script = ScriptDirectory.from_config(alembic_cfg)
            head_rev = script.get_current_head()
            
            if current_rev == head_rev:
                logger.info(f"✅ Database schema is up-to-date (revision: {current_rev or 'base'})")
            else:
                logger.info(f"📝 Applying pending migrations: {current_rev or 'base'} → {head_rev}")
                
                # Run migrations
                flask_migrate_upgrade()
                
                logger.info(f"✅ Database migrations applied successfully! Current revision: {head_rev}")
        
        except Exception as migration_error:
            # Log migration errors but don't crash the app
            # This allows the app to start even if migrations fail (e.g., schema already up-to-date manually)
            logger.error(f"⚠️  Migration check failed (non-critical): {str(migration_error)}")
            logger.info("📌 App will continue startup - database may already be up-to-date")
        
        # NOTE: Schema management is now handled by Alembic migrations above
        # db.create_all() is disabled to avoid conflicts with migration system
        # db.create_all()  # DISABLED: Use Flask-Migrate for automatic migrations
        
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
                admin.email = 'admin@traitortrack.com'
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

# Setup graceful shutdown handling for zero-downtime deployments
from shutdown_handler import init_graceful_shutdown
shutdown_timeout = int(os.environ.get('GRACEFUL_SHUTDOWN_TIMEOUT', '30'))
shutdown_handler = init_graceful_shutdown(app, db, timeout=shutdown_timeout)
logger.info(f"Graceful shutdown handler initialized - timeout: {shutdown_timeout}s")

# Setup session timeout middleware
@app.before_request
def check_session_timeout_middleware():
    """Check session timeout on every request and auto-logout if expired"""
    from flask import request, flash, redirect, url_for
    from auth_utils import check_session_timeout, update_session_activity, clear_session, is_authenticated
    
    # Skip timeout check for static files, login, logout, and API endpoints
    if request.endpoint in ['static', 'login', 'logout', 'register']:
        return None
    
    # Skip for health check endpoints and static files
    if request.path and (request.path.startswith('/static/') or request.path == '/health' or request.path == '/status'):
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
    
    # Skip validation for public paths (including health check endpoints)
    excluded_paths = ['/login', '/register', '/static', '/logout', '/health', '/status', '/api/health', '/forgot_password', '/reset_password']
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
    """Add comprehensive security headers including CSP"""
    
    # Content Security Policy (CSP) - Comprehensive XSS protection
    csp_directives = [
        "default-src 'self'",
        # Allow scripts from self, CDN, and inline (for Bootstrap functionality)
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
        # Allow styles from self, CDNs, and inline
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
        # Allow fonts from self, CDN, and data URIs
        "font-src 'self' https://cdnjs.cloudflare.com data:",
        # Allow images from self and data URIs (for inline SVG/base64)
        "img-src 'self' data:",
        # Restrict AJAX/fetch to self only
        "connect-src 'self'",
        # Prevent framing (clickjacking protection)
        "frame-ancestors 'none'",
        # Restrict base tag (prevents base tag injection attacks)
        "base-uri 'self'",
        # Restrict form submissions to self only
        "form-action 'self'",
        # Upgrade insecure requests in production
        "upgrade-insecure-requests" if os.environ.get('REPLIT_DEPLOYMENT') == '1' or os.environ.get('ENVIRONMENT') == 'production' else ""
    ]
    # Filter out empty directives and join with semicolons
    csp_policy = "; ".join([directive for directive in csp_directives if directive])
    response.headers['Content-Security-Policy'] = csp_policy
    
    # Strict Transport Security (HSTS) - Force HTTPS in production
    # Tells browsers to only connect via HTTPS for 1 year (31536000 seconds)
    if os.environ.get('REPLIT_DEPLOYMENT') == '1' or os.environ.get('ENVIRONMENT') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    
    # Referrer Policy - Control referrer information leakage
    # 'strict-origin-when-cross-origin' sends full URL for same-origin, only origin for cross-origin
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Permissions Policy - Disable unnecessary browser features
    # Restricts camera, microphone, geolocation, payment, and other sensitive APIs
    permissions_policies = [
        "camera=()",
        "microphone=()",
        "geolocation=()",
        "payment=()",
        "usb=()",
        "magnetometer=()",
        "accelerometer=()",
        "gyroscope=()"
    ]
    response.headers['Permissions-Policy'] = ", ".join(permissions_policies)
    
    # X-Download-Options - Prevent IE from executing downloads in site context
    response.headers['X-Download-Options'] = 'noopen'
    
    # Basic security headers (existing)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Cache control for authenticated pages
    if session.get('logged_in') or session.get('auth_session_id'):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    # CRITICAL FIX: Force session cookies to NOT be Secure in development
    # Flask overrides SESSION_COOKIE_SECURE based on X-Forwarded-Proto from Replit proxy
    # This causes cookies to be Secure=true even though gunicorn serves HTTP
    # Browsers then refuse to send Secure cookies over HTTP, breaking session persistence
    if not (os.environ.get('REPLIT_DEPLOYMENT') == '1' or os.environ.get('ENVIRONMENT') == 'production'):
        # Get all Set-Cookie headers
        cookies = response.headers.getlist('Set-Cookie')
        if cookies:
            # Filter out old session cookies and rebuild without Secure flag
            new_cookies = []
            for cookie in cookies:
                if 'traitortrack_session=' in cookie:
                    # Remove Secure flag from session cookie
                    cookie = cookie.replace('; Secure', '').replace(';Secure', '')
                new_cookies.append(cookie)
            # Replace all Set-Cookie headers
            response.headers.remove('Set-Cookie')
            for cookie in new_cookies:
                response.headers.add('Set-Cookie', cookie)
    
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

# Note: Comprehensive error handlers are defined in error_handlers.py
# and registered via setup_error_handlers(app) call above

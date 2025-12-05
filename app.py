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

# Create Flask application
app = Flask(__name__)

# SECURITY: Enable Jinja2 autoescape for XSS protection
# This ensures all template variables are HTML-escaped by default
app.jinja_env.autoescape = True

# Add Python built-in functions to Jinja2 globals for template convenience
app.jinja_env.globals.update({
    'min': min,
    'max': max,
    'len': len,
    'sum': sum,
    'abs': abs,
    'int': int,
    'str': str,
    'float': float
})

# Proxy fix for correct URL generation
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# SECURITY: Require SESSION_SECRET environment variable
session_secret = os.environ.get("SESSION_SECRET")
if not session_secret:
    raise ValueError("SESSION_SECRET environment variable is required for security")
app.secret_key = session_secret

# ==================================================================================
# ENVIRONMENT DETECTION - Determines which database to use
# ==================================================================================
# PUBLISHED DEPLOYMENT: Uses AWS RDS (PRODUCTION_DATABASE_URL) or Replit PostgreSQL
# DEVELOPMENT/TESTING: Always uses Replit PostgreSQL (DATABASE_URL)
#
# Safety: To prevent tests from accidentally using production database:
# - Only REPLIT_DEPLOYMENT='1' triggers production mode (actual published app)
# - REPLIT_ENVIRONMENT='production' alone is NOT sufficient
# - Tests and development ALWAYS use Replit's built-in PostgreSQL
# - Override with FORCE_DEV_DB=1 to force Replit DB even in deployment
# ==================================================================================

# Detect if we're in an actual published deployment (not just testing/preview)
is_published_deployment = os.environ.get('REPLIT_DEPLOYMENT') == '1'

# Safety flag: Allow forcing development database for testing
force_dev_db = os.environ.get('FORCE_DEV_DB', '').lower() in ('1', 'true', 'yes')

# Determine production mode (for security settings, rate limits, etc.)
# This affects HTTPS-only cookies, rate limiting strictness, etc.
is_production = (
    is_published_deployment or 
    os.environ.get('REPLIT_ENVIRONMENT') == 'production'
) and not force_dev_db

# ==================================================================================
# SESSION CONFIGURATION - True stateless signed cookie sessions (Autoscale-ready)
# ==================================================================================
# Uses Flask's built-in client-side signed cookie sessions - NO server-side storage.
# Session data is cryptographically signed and stored entirely in the client cookie.
# This is truly stateless and works across any number of workers/instances.
# SECURITY: SESSION_COOKIE_SECURE=True in production for HTTPS-only cookies
# ==================================================================================
app.config.update(
    SESSION_COOKIE_SECURE=is_production,
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

logger.info("Session storage: Stateless signed cookies (true Autoscale-ready)")

# ==================================================================================
# RATE LIMITING CONFIGURATION - Environment-driven with production-safe defaults
# ==================================================================================
# Uses in-memory storage (per-worker). For high-traffic production, rate limits
# are per-worker which provides effective protection without external dependencies.
#
# Configure via environment variables:
# - RATE_LIMIT_PER_DAY: Daily limit per IP (default: 50000 for production workloads)
# - RATE_LIMIT_PER_HOUR: Hourly limit per IP (default: 10000)
# - RATE_LIMIT_PER_MINUTE: Per-minute limit per IP (default: 500)
# ==================================================================================
rate_limit_day = os.environ.get('RATE_LIMIT_PER_DAY', '50000')
rate_limit_hour = os.environ.get('RATE_LIMIT_PER_HOUR', '10000')
rate_limit_minute = os.environ.get('RATE_LIMIT_PER_MINUTE', '500')

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{rate_limit_day} per day", f"{rate_limit_hour} per hour", f"{rate_limit_minute} per minute"],
    storage_uri="memory://",
    strategy="fixed-window",
    swallow_errors=True
)

def get_admin_rate_limit_key():
    """Get rate limit key for admin operations - uses user_id for authenticated users.
    This ensures rate limits apply per-admin, not per-IP, preventing shared-proxy bypass.
    """
    from flask import session
    user_id = session.get('user_id')
    if user_id:
        return f"admin_user:{user_id}"
    # Fallback to IP for unauthenticated requests (shouldn't happen for admin endpoints)
    return get_remote_address()

# Custom rate limit error handler
@app.errorhandler(429)
def ratelimit_handler(e):
    """Custom error handler for rate limit exceeded"""
    from flask import render_template, request, flash
    
    # Get the retry-after header if available
    retry_after = getattr(e, 'description', '').split('Retry after ')[1].split(' ')[0] if 'Retry after' in str(getattr(e, 'description', '')) else 'soon'
    
    # Check if this is a login rate limit
    if '/login' in request.path:
        # Import LoginForm to provide context for template
        from forms import LoginForm
        form = LoginForm()
        flash(f'Too many login attempts. Please try again in {retry_after} seconds. If you need immediate access, contact your administrator.', 'error')
        return render_template('login.html', form=form), 429
    
    # Generic rate limit message for other endpoints
    return render_template('error.html', 
                         error_code=429,
                         error_message=f'Too many requests. Please try again in {retry_after} seconds.',
                         error_title='Rate Limit Exceeded'), 429

logger.info(f"Rate limiting: {rate_limit_day}/day, {rate_limit_hour}/hour, {rate_limit_minute}/minute per IP")

# ==================================================================================
# DATABASE CONFIGURATION - Safe environment-based routing
# ==================================================================================
# PUBLISHED DEPLOYMENT: Uses AWS RDS (PRODUCTION_DATABASE_URL) if available
# DEVELOPMENT/TESTING: ALWAYS uses Replit PostgreSQL (DATABASE_URL)
#
# Safety Rules:
# 1. Tests NEVER connect to AWS RDS production database
# 2. Only actual published deployments (REPLIT_DEPLOYMENT='1') use AWS RDS
# 3. Force Replit DB with FORCE_DEV_DB=1 for testing in deployed environments
# ==================================================================================

# Determine which database to use
if is_published_deployment and not force_dev_db:
    # Published deployment: Try PRODUCTION_DATABASE_URL first, fall back to DATABASE_URL
    database_url = os.environ.get("PRODUCTION_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("❌ CRITICAL: No database configured in production environment")
        logger.error("❌ Set DATABASE_URL (Replit PostgreSQL) or PRODUCTION_DATABASE_URL (external)")
        raise ValueError("Database URL is required in production")
    
    # Determine database source for logging
    if os.environ.get("PRODUCTION_DATABASE_URL"):
        db_source = "AWS RDS Production Database (PRODUCTION_DATABASE_URL)"
        db_host = database_url.split('@')[-1].split('/')[0] if '@' in database_url else 'configured'
        logger.info(f"✅ Production deployment using AWS RDS: {db_host}")
    else:
        db_source = "Replit PostgreSQL (DATABASE_URL)"
        logger.info("✅ Production deployment using Replit built-in PostgreSQL")
        logger.info("ℹ️  For dedicated production database, set PRODUCTION_DATABASE_URL")
else:
    # Development/Testing: ALWAYS use Replit PostgreSQL for safety
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not found - required for development/testing")
    
    db_source = "Replit PostgreSQL (DATABASE_URL) - Development/Testing"
    if force_dev_db:
        logger.info("🔒 FORCE_DEV_DB enabled - using Replit PostgreSQL (safe mode)")
    logger.info(f"✅ Development/Testing using Replit PostgreSQL")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
logger.info(f"📊 Database: {db_source}")

# Log safety information
if not is_published_deployment:
    logger.info("🛡️  Database Safety: Tests and development use Replit PostgreSQL only")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = False

# ==================================================================================
# DATABASE CONNECTION POOL - Environment-driven configuration for scalable load handling
# ==================================================================================
# Configure via environment variables for different deployment scales:
#   - DB_POOL_SIZE: Base pool size per worker (default: 10)
#   - DB_MAX_OVERFLOW: Overflow connections per worker (default: 5)
#   - DB_POOL_RECYCLE: Seconds before connection recycle (default: 300)
#   - DB_POOL_TIMEOUT: Seconds to wait for connection (default: 30)
#   - DB_CONNECT_TIMEOUT: Database connection timeout (default: 10)
#
# Formula: (pool_size + max_overflow) × workers < postgres_max_connections
# ==================================================================================
db_pool_size = int(os.environ.get('DB_POOL_SIZE', '10'))
db_max_overflow = int(os.environ.get('DB_MAX_OVERFLOW', '5'))
db_pool_recycle = int(os.environ.get('DB_POOL_RECYCLE', '300'))
db_pool_timeout = int(os.environ.get('DB_POOL_TIMEOUT', '30'))
db_connect_timeout = int(os.environ.get('DB_CONNECT_TIMEOUT', '10'))

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": db_pool_size,
    "max_overflow": db_max_overflow,
    "pool_recycle": db_pool_recycle,
    "pool_pre_ping": True,
    "pool_timeout": db_pool_timeout,
    "echo": False,
    "echo_pool": False,
    "connect_args": {
        "connect_timeout": db_connect_timeout,
        "application_name": "traitortrack_web"
    }
}

logger.info(f"Database pool: {db_pool_size} base + {db_max_overflow} overflow per worker")

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

# ==================================================================================
# EARLY HEALTH ENDPOINT - Opens port 5000 immediately for Autoscale health checks
# ==================================================================================
# This endpoint responds BEFORE heavy initialization completes, ensuring the app
# passes Autoscale's port-open check within the 2-minute timeout.
# ==================================================================================
@app.route('/health')
@app.route('/status')
def early_health_check():
    """Lightweight health check - responds immediately, no DB required"""
    return {'status': 'ok', 'service': 'traitortrack'}, 200

@app.route('/ready')
def readiness_check():
    """Readiness check - verifies DB connection is available"""
    try:
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        return {'status': 'ready', 'database': 'connected'}, 200
    except Exception as e:
        return {'status': 'not_ready', 'database': str(e)}, 503

logger.info("Early health endpoints registered: /health, /status, /ready")

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

# ==================================================================================
# LAZY INITIALIZATION (Autoscale-ready - no blocking on startup)
# ==================================================================================
# Heavy initialization is deferred to after first request to ensure port 5000
# opens immediately. This prevents Autoscale timeout failures.
# ==================================================================================
_lazy_init_done = False

def _run_lazy_initialization():
    """Run deferred initialization tasks after first request"""
    global _lazy_init_done
    if _lazy_init_done:
        return
    _lazy_init_done = True
    
    try:
        # Admin user check/creation (deferred)
        from models import User
        admin_password = os.environ.get('ADMIN_PASSWORD')
        
        admin = User.query.filter_by(username='admin').first()
        if not admin and admin_password:
            admin = User()
            admin.username = 'admin'
            admin.email = 'admin@traitortrack.com'
            admin.set_password(admin_password)
            admin.role = 'admin'
            admin.verified = True
            db.session.add(admin)
            db.session.commit()
            logger.info("Admin user created (lazy init)")
        elif admin and admin_password and os.environ.get('FORCE_ADMIN_PASSWORD_RESET') == '1':
            admin.set_password(admin_password)
            admin.role = 'admin'
            admin.verified = True
            db.session.commit()
            logger.info("Admin password reset (lazy init)")
        
        # Pool monitoring (deferred)
        try:
            from pool_monitor import init_pool_monitor
            pool_enabled = os.environ.get('POOL_MONITORING_ENABLED', 'true').lower() == 'true'
            init_pool_monitor(db.engine, enabled=pool_enabled)
            if pool_enabled:
                logger.info("Pool monitoring initialized (lazy)")
        except Exception as e:
            logger.debug(f"Pool monitoring skipped: {e}")
        
        # Slow query logging (deferred)
        try:
            from slow_query_logger import init_slow_query_logger
            threshold = int(os.environ.get('SLOW_QUERY_THRESHOLD_MS', '100'))
            enabled = os.environ.get('SLOW_QUERY_LOGGING_ENABLED', 'true').lower() == 'true'
            init_slow_query_logger(db.engine, threshold_ms=threshold, enabled=enabled)
            if enabled:
                logger.info(f"Slow query logging initialized (lazy) - {threshold}ms")
        except Exception as e:
            logger.debug(f"Slow query logging skipped: {e}")
            
        logger.info("Lazy initialization completed")
        
    except Exception as e:
        if 'does not exist' in str(e) or 'relation' in str(e).lower():
            logger.warning("Database tables not found - run migrations first")
        else:
            logger.error(f"Lazy initialization error: {e}")

# Minimal startup - just import models to register them
with app.app_context():
    try:
        import models
        logger.info("Models imported - database ready for connections")
    except Exception as e:
        logger.warning(f"Model import warning: {e}")

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

# Trigger lazy initialization on first real request (not health checks)
@app.before_request
def trigger_lazy_init():
    """Trigger lazy initialization on first non-health-check request"""
    if request.path in ['/health', '/status', '/ready']:
        return None
    if request.path.startswith('/static/'):
        return None
    _run_lazy_initialization()

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
    excluded_paths = ['/login', '/register', '/static', '/logout', '/health', '/status', '/ready', '/api/health', '/forgot_password', '/reset_password']
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
        "upgrade-insecure-requests" if (os.environ.get('REPLIT_DEPLOYMENT') == '1' or os.environ.get('REPLIT_ENVIRONMENT') == 'production') else ""
    ]
    # Filter out empty directives and join with semicolons
    csp_policy = "; ".join([directive for directive in csp_directives if directive])
    response.headers['Content-Security-Policy'] = csp_policy
    
    # Strict Transport Security (HSTS) - Force HTTPS in production
    # Tells browsers to only connect via HTTPS for 1 year (31536000 seconds)
    if os.environ.get('REPLIT_DEPLOYMENT') == '1' or os.environ.get('REPLIT_ENVIRONMENT') == 'production':
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
    if not (os.environ.get('REPLIT_DEPLOYMENT') == '1' or os.environ.get('REPLIT_ENVIRONMENT') == 'production'):
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

# Initialize compression middleware for mobile bandwidth optimization
# This reduces API response sizes by 60-80% for JSON responses
try:
    from api_middleware import CompressionMiddleware
    compression = CompressionMiddleware(app, min_size=1024, compress_level=6)
    logger.info("✅ Compression middleware initialized for mobile optimization")
except Exception as e:
    logger.warning(f"⚠️  Compression middleware failed to initialize: {e}")

# Note: Comprehensive error handlers are defined in error_handlers.py
# and registered via setup_error_handlers(app) call above

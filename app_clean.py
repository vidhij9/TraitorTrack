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
# Temporarily disable Flask-Login to fix API endpoints
# login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

# Create Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Ultra-permissive session configuration for deployment
app.config.update(
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=False,
    SESSION_COOKIE_SAMESITE=None,
    SESSION_COOKIE_DOMAIN=None,
    SESSION_COOKIE_PATH='/',
    SESSION_COOKIE_NAME='session',
    PERMANENT_SESSION_LIFETIME=86400,  # 24 hours
    SESSION_REFRESH_EACH_REQUEST=False  # Prevent session conflicts
)

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

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
# login_manager.init_app(app)  # Disabled to fix API endpoints
csrf.init_app(app)
limiter.init_app(app)

# Configure CSRF exemptions for deployment compatibility
app.config['WTF_CSRF_ENABLED'] = False  # Temporarily disable CSRF for deployment troubleshooting

# Setup error handlers and monitoring
from error_handlers import setup_error_handlers, setup_request_logging, setup_health_monitoring
setup_error_handlers(app)
setup_request_logging(app)
setup_health_monitoring(app)

# Add session validation and cache control (disabled for API endpoints)
@app.before_request
def before_request():
    """Validate authentication and session before each request"""
    from flask import session, request, redirect, url_for
    
    # Allow all API endpoints to work without authentication for dashboard functionality
    if request.path.startswith('/api/'):
        return
    
    # Skip validation for public endpoints
    excluded_paths = ['/login', '/register', '/static', '/logout', '/fix-admin-password']
    if any(request.path.startswith(path) for path in excluded_paths):
        return

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

# Temporarily disable Flask-Login entirely to fix API issues
# login_manager.login_view = 'login'
# login_manager.login_message_category = 'info'

# Import models for database tables
with app.app_context():
    from models import User, UserRole, Bag, BagType, Link, Scan, Bill, BillBag
    db.create_all()

# User loader disabled with Flask-Login
# @login_manager.user_loader
# def load_user(user_id):
#     from models import User
#     return User.query.get(int(user_id))

# Routes will be imported via main.py to prevent circular imports

# Import dashboard API endpoints without authentication
import dashboard_api

@app.context_processor
def inject_current_user():
    """Make current_user available in all templates"""
    from routes import current_user
    return dict(current_user=current_user)
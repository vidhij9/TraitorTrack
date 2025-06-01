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
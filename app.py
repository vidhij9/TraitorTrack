import os
import logging
import time

from flask import Flask, request, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix

# Import custom logging configuration
from logging_config import setup_logging

# Setup advanced logging configuration
setup_logging()
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with the Base class
db = SQLAlchemy(model_class=Base)

# Create the Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # Needed for url_for to generate with https

# Configure the database connection
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 30,  # Increase connection pool size for high concurrency
    "max_overflow": 40,  # Allow additional connections when pool is full
    "pool_recycle": 300,  # Recycle connections every 5 minutes
    "pool_pre_ping": True,  # Verify connections before using them
    "pool_timeout": 30,  # Maximum time to wait for connection from pool
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the database with the app
db.init_app(app)

# Add request timing middleware for performance monitoring
@app.before_request
def before_request():
    g.start_time = time.time()
    
@app.after_request
def after_request(response):
    if hasattr(g, 'start_time'):
        elapsed = time.time() - g.start_time
        logger.info(f"Request to {request.path} completed in {elapsed:.4f}s")
        # Add Server-Timing header for client-side monitoring
        response.headers['Server-Timing'] = f'total;dur={elapsed*1000:.0f}'
    return response

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configure additional app settings for performance
app.config['TEMPLATES_AUTO_RELOAD'] = False  # Disable in production for better performance

with app.app_context():
    # Import models to ensure they're registered with SQLAlchemy
    import models  # noqa: F401
    
    # Create all database tables
    db.create_all()
    
    # Import and register routes
    import routes  # noqa: F401
    import api  # noqa: F401
    
    from models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

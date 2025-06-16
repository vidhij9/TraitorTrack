"""
TraceTrack Application with Complete Database Environment Isolation
This version ensures development and production databases are completely separate.
"""

import os
import logging
from flask import Flask, request, session, g
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Import our environment management system
from environment_manager import get_environment_manager


class Base(DeclarativeBase):
    pass


# Global database and login manager instances
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()


def create_app():
    """
    Application factory with environment-specific database isolation.
    """
    app = Flask(__name__)
    
    # Get environment manager for configuration
    env_manager = get_environment_manager()
    
    # Configure Flask with environment-specific settings
    flask_config = env_manager.get_flask_config()
    for key, value in flask_config.items():
        app.config[key] = value
    
    # Configure database with environment isolation
    db_config = env_manager.get_database_config()
    for key, value in db_config.items():
        app.config[key] = value
    
    # Apply proxy fix for deployment
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'  # type: ignore
    login_manager.login_message = 'Please log in to access this page.'
    
    # Set up logging based on environment
    setup_logging(env_manager)
    
    # Register before/after request handlers
    register_request_handlers(app, env_manager)
    
    # Log environment information
    log_environment_info(env_manager)
    
    # Create database tables
    with app.app_context():
        # Make sure to import models here
        import models  # noqa: F401
        
        try:
            db.create_all()
            logging.info("Database tables created successfully")
        except Exception as e:
            logging.error(f"Error creating database tables: {e}")
            if env_manager.is_production():
                raise  # Don't continue in production with DB errors
    
    return app


def setup_logging(env_manager):
    """Set up logging based on environment."""
    log_level = getattr(logging, env_manager.config.get('log_level', 'INFO'))
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/app.log') if os.path.exists('logs') else logging.NullHandler()
        ]
    )
    
    # Set SQLAlchemy logging
    if env_manager.config.get('sqlalchemy_echo', False):
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    else:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)


def register_request_handlers(app, env_manager):
    """Register request handlers for security and logging."""
    
    @app.before_request
    def before_request():
        """Execute before each request."""
        # Log request info in development
        if env_manager.is_development():
            logging.debug(f"Request: {request.method} {request.url} - IP: {request.remote_addr}")
        
        # Store environment info in Flask's g object
        g.environment = env_manager.current_env
        g.is_development = env_manager.is_development()
        g.is_production = env_manager.is_production()
        
        # Validate database connection periodically
        if hasattr(g, 'validate_db_connection'):
            try:
                db.session.execute(db.text('SELECT 1'))
            except Exception as e:
                logging.error(f"Database connection lost: {e}")
                if env_manager.is_production():
                    # In production, this is critical
                    raise
    
    @app.after_request
    def after_request(response):
        """Execute after each request."""
        # Add security headers in production
        if env_manager.is_production():
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Add cache control for authenticated pages
        if request.endpoint and not request.endpoint.startswith('static'):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        
        return response
    
    @app.context_processor
    def inject_environment_info():
        """Inject environment information into templates."""
        return {
            'current_environment': env_manager.current_env,
            'is_development': env_manager.is_development(),
            'is_production': env_manager.is_production(),
            'debug_mode': env_manager.config.get('debug', False)
        }


def log_environment_info(env_manager):
    """Log environment configuration information."""
    env_info = env_manager.get_environment_info()
    
    logging.info("=" * 50)
    logging.info("TraceTrack Application Starting")
    logging.info("=" * 50)
    logging.info(f"Environment: {env_info['environment']}")
    logging.info(f"Database: {env_info['database_url_preview']}")
    logging.info(f"Debug Mode: {env_info['debug_mode']}")
    logging.info(f"Pool Size: {env_info['pool_size']}")
    logging.info(f"SQL Logging: {env_info['sql_logging']}")
    logging.info("=" * 50)
    
    # Validate database isolation
    from database_environment_switcher import DatabaseEnvironmentSwitcher
    switcher = DatabaseEnvironmentSwitcher()
    validation = switcher.validate_environment_isolation()
    
    if not validation['is_isolated']:
        logging.warning("DATABASE ISOLATION ISSUES DETECTED:")
        for error in validation['errors']:
            logging.error(f"  - {error}")
        for warning in validation['warnings']:
            logging.warning(f"  - {warning}")
    else:
        logging.info("✓ Database isolation validated successfully")


@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login."""
    from models import User
    return User.query.get(int(user_id))


# Create the application instance
app = create_app()


# Add environment diagnostic endpoints
@app.route('/environment-info')
def environment_info():
    """Get environment information for debugging."""
    env_manager = get_environment_manager()
    env_info = env_manager.get_environment_info()
    
    from database_environment_switcher import DatabaseEnvironmentSwitcher
    switcher = DatabaseEnvironmentSwitcher()
    status = switcher.get_current_environment_status()
    
    html = f"""
    <h1>TraceTrack Environment Information</h1>
    
    <h2>Current Environment</h2>
    <ul>
        <li><strong>Environment:</strong> {env_info['environment']}</li>
        <li><strong>Debug Mode:</strong> {env_info['debug_mode']}</li>
        <li><strong>Testing Mode:</strong> {env_info['testing_mode']}</li>
        <li><strong>Database URL:</strong> {env_info['database_url_preview']}</li>
        <li><strong>Pool Size:</strong> {env_info['pool_size']}</li>
        <li><strong>SQL Logging:</strong> {env_info['sql_logging']}</li>
    </ul>
    
    <h2>Database Status</h2>
    <ul>
        <li><strong>Database Configured:</strong> {'✓' if status['database_configured'] else '✗'}</li>
        <li><strong>Database Accessible:</strong> {'✓' if status['database_accessible'] else '✗'}</li>
        <li><strong>Isolation Valid:</strong> {'✓' if status['isolation_valid'] else '✗'}</li>
    </ul>
    """
    
    if 'connectivity_message' in status:
        html += f"<p><strong>Connectivity:</strong> {status['connectivity_message']}</p>"
    
    if status.get('isolation_errors'):
        html += "<h3>Isolation Errors</h3><ul>"
        for error in status['isolation_errors']:
            html += f"<li style='color: red;'>{error}</li>"
        html += "</ul>"
    
    if status.get('isolation_warnings'):
        html += "<h3>Isolation Warnings</h3><ul>"
        for warning in status['isolation_warnings']:
            html += f"<li style='color: orange;'>{warning}</li>"
        html += "</ul>"
    
    if status.get('recommendations'):
        html += "<h3>Recommendations</h3><ul>"
        for rec in status['recommendations']:
            html += f"<li>{rec}</li>"
        html += "</ul>"
    
    html += """
    <h2>Available Environments</h2>
    <ul>
    """
    
    environments = switcher.list_available_environments()
    for name, config in environments.items():
        status_symbol = "✓" if config['status'] == 'configured' else "✗"
        html += f"""
        <li>
            <strong>{status_symbol} {name.upper()}</strong><br>
            URL: {config['database_url']}<br>
            Description: {config['description']}
        </li>
        """
    
    html += """
    </ul>
    
    <p><a href="/">Back to Dashboard</a></p>
    """
    
    return html


@app.route('/validate-database-isolation')
def validate_database_isolation():
    """Validate database isolation and provide recommendations."""
    from database_environment_switcher import DatabaseEnvironmentSwitcher
    switcher = DatabaseEnvironmentSwitcher()
    validation = switcher.validate_environment_isolation()
    
    html = "<h1>Database Isolation Validation</h1>"
    
    if validation['is_isolated']:
        html += "<h2 style='color: green;'>✓ Database environments are properly isolated</h2>"
    else:
        html += "<h2 style='color: red;'>✗ Database isolation issues detected</h2>"
    
    if validation['errors']:
        html += "<h3>Errors</h3><ul>"
        for error in validation['errors']:
            html += f"<li style='color: red;'>{error}</li>"
        html += "</ul>"
    
    if validation['warnings']:
        html += "<h3>Warnings</h3><ul>"
        for warning in validation['warnings']:
            html += f"<li style='color: orange;'>{warning}</li>"
        html += "</ul>"
    
    if validation['recommendations']:
        html += "<h3>Recommendations</h3><ul>"
        for rec in validation['recommendations']:
            html += f"<li>{rec}</li>"
        html += "</ul>"
    
    html += "<p><a href='/environment-info'>Environment Info</a> | <a href='/'>Dashboard</a></p>"
    
    return html


if __name__ == "__main__":
    # This should only be used for development
    env_manager = get_environment_manager()
    if env_manager.is_production():
        logging.warning("Direct app.run() should not be used in production. Use gunicorn or similar WSGI server.")
    
    app.run(
        host="0.0.0.0", 
        port=5000, 
        debug=env_manager.is_development()
    )
"""
Production-ready main application file for TraceTrack
Updated with latest development bug fixes and improvements
"""

import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize logging for production
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
limiter = Limiter(key_func=get_remote_address)

def create_production_app():
    """Create production Flask application with latest bug fixes"""
    app = Flask(__name__)
    
    # Production security configuration
    app.secret_key = os.environ.get("SESSION_SECRET", "production-change-me")
    
    # Enhanced session configuration for production
    app.config.update(
        SESSION_COOKIE_SECURE=True,  # HTTPS only in production
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Strict',
        SESSION_COOKIE_DOMAIN=None,
        SESSION_COOKIE_PATH='/',
        SESSION_COOKIE_NAME='tracetrack_prod_session',
        PERMANENT_SESSION_LIFETIME=28800,  # 8 hours for production
        SESSION_REFRESH_EACH_REQUEST=True
    )
    
    # Production database configuration with connection pooling
    database_url = os.environ.get('DATABASE_URL', os.environ.get('PROD_DATABASE_URL'))
    if not database_url:
        raise ValueError("DATABASE_URL or PROD_DATABASE_URL must be set for production")
    
    app.config.update(
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_ENGINE_OPTIONS={
            "pool_size": 50,  # Larger pool for production
            "pool_recycle": 300,
            "pool_pre_ping": True,
            "pool_timeout": 30,
            "max_overflow": 100
        },
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ECHO=False  # Disable SQL logging in production
    )
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    
    # Production-specific login manager configuration
    login_manager.login_view = None  # Handle redirects manually
    login_manager.login_message = None
    login_manager.session_protection = "strong"
    
    with app.app_context():
        # Import models to ensure tables are created
        import models
        
        # Create all database tables
        db.create_all()
        
        # Import and register all routes
        import routes
        import api
        import optimized_api
        import high_performance_api
        
        # Register production-specific error handlers
        @app.errorhandler(404)
        def not_found(error):
            return {"error": "Not found"}, 404
        
        @app.errorhandler(500)
        def internal_error(error):
            db.session.rollback()
            return {"error": "Internal server error"}, 500
        
        @app.errorhandler(403)
        def forbidden(error):
            return {"error": "Access forbidden"}, 403
    
    # Production routes
    @app.route('/')
    def index():
        """Main dashboard page"""
        from production_auth_fix import is_production_authenticated
        from flask import render_template, session
        
        if is_production_authenticated():
            return render_template('dashboard.html')
        else:
            return render_template('landing.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Enhanced user login with production security"""
        from flask import request, redirect, flash, render_template
        from production_auth_fix import production_login_handler, create_production_session
        from models import User
        
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            if not username or not password:
                flash('Username and password are required', 'error')
                return render_template('login.html')
            
            # Use production login handler with enhanced security
            success, message = production_login_handler(username, password)
            
            if success:
                user = User.query.filter_by(username=username).first()
                if user and create_production_session(user):
                    logger.info(f"Successful production login: {username}")
                    return redirect('/')
                else:
                    flash('Login failed - session error', 'error')
            else:
                flash(message, 'error')
                logger.warning(f"Failed login attempt: {username}")
        
        return render_template('login.html')
    
    @app.route('/logout')
    def logout():
        """Enhanced user logout"""
        from flask import session, redirect, flash
        username = session.get('username', 'unknown')
        session.clear()
        flash('You have been logged out successfully', 'info')
        logger.info(f"User logged out: {username}")
        return redirect('/')
    
    @app.route('/production-setup')
    def setup():
        """Production setup and optimization endpoint"""
        try:
            from werkzeug.security import generate_password_hash
            from models import User
            
            # Create admin user if doesn't exist
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    email='admin@tracetrack.com',
                    password_hash=generate_password_hash('admin'),
                    role='admin'
                )
                db.session.add(admin)
                db.session.commit()
                result = "✓ Admin user created (admin/admin)"
            else:
                result = "✓ Admin user exists"
            
            # Run database optimizations
            try:
                import database_optimizer
                optimization_results = database_optimizer.run_full_optimization()
                optimizations_text = ", ".join([k for k, v in optimization_results.items() if v])
                result += f"<br>✓ Database optimizations: {optimizations_text}"
            except Exception as e:
                result += f"<br>⚠ Database optimization warning: {str(e)}"
            
            # Clear cache for fresh start
            try:
                from cache_utils import invalidate_cache
                invalidate_cache()
                result += "<br>✓ Application cache cleared"
            except Exception as e:
                result += f"<br>⚠ Cache warning: {str(e)}"
            
            result += """
            <br><br>
            <h3>Production Deployment Ready</h3>
            <p>✓ TraceTrack is optimized and ready for production deployment</p>
            <p><a href="/login">Go to Login</a> | <a href="/">Dashboard</a></p>
            """
            
            return result
            
        except Exception as e:
            logger.error(f"Production setup error: {str(e)}")
            return f"Setup error: {str(e)}", 500
    
    @app.route('/health')
    def health_check():
        """Production health check for monitoring"""
        try:
            from sqlalchemy import text
            db.session.execute(text("SELECT 1")).scalar()
            
            return {
                'status': 'healthy',
                'database': 'connected',
                'version': '2.0.0',
                'deployment': 'production-ready',
                'environment': 'production'
            }
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {'status': 'unhealthy', 'error': str(e)}, 500
    
    return app

# Create the production application
app = create_production_app()

# Expose for gunicorn
application = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
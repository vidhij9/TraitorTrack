"""
Production-ready main application file for TraceTrack
Integrates all components for production deployment
"""
import os
import logging
from flask import Flask, request, session, redirect, url_for, render_template, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

# Initialize database
db = SQLAlchemy(model_class=Base)

def create_production_app():
    """Create production Flask application"""
    app = Flask(__name__)
    
    # Production configuration
    app.secret_key = os.environ.get("SESSION_SECRET", "production-secret-key-change-me")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Database configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 20,
        "max_overflow": 30,
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_timeout": 30,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Security configuration
    app.config.update(
        SESSION_COOKIE_SECURE=False,  # Set to True in HTTPS production
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=1800,
        SESSION_REFRESH_EACH_REQUEST=True,
    )
    
    # Initialize database with app
    db.init_app(app)
    
    # Import models to ensure tables are created
    with app.app_context():
        import models
        db.create_all()
        
        # Setup admin user
        from models import User
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
            logger.info("Admin user created")
    
    # Production authentication
    from production_auth_fix import production_login_handler, is_production_authenticated, production_logout, require_production_auth
    
    @app.route('/')
    def index():
        """Main dashboard page"""
        if not is_production_authenticated():
            return render_template('landing.html')
        
        from datetime import datetime
        from sqlalchemy import func, desc
        from models import Scan, Bag
        
        today = datetime.now().date()
        user_id = session.get('user_id')
        
        # Dashboard data
        user_scans_today = Scan.query.filter(
            Scan.user_id == user_id,
            func.date(Scan.timestamp) == today
        ).count()
        
        recent_scans = Scan.query.filter(Scan.user_id == user_id)\
                                 .order_by(desc(Scan.timestamp))\
                                 .limit(5).all()
        
        total_scans_today = Scan.query.filter(func.date(Scan.timestamp) == today).count()
        total_bags = Bag.query.count()
        
        return render_template('dashboard.html',
                             user_scans_today=user_scans_today,
                             recent_scans=recent_scans,
                             total_scans_today=total_scans_today,
                             total_bags=total_bags)
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """User login"""
        if is_production_authenticated() and request.method == 'GET':
            next_url = session.pop('next_url', None)
            return redirect(next_url or url_for('index'))
        
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            if not username or not password:
                return render_template('login.html', error='Please enter both username and password.')
            
            success, message = production_login_handler(username, password)
            
            if success:
                next_url = session.pop('next_url', None)
                return redirect(next_url or url_for('index'))
            else:
                return render_template('login.html', error=message)
        
        return render_template('login.html')
    
    @app.route('/logout')
    def logout():
        """User logout"""
        production_logout()
        return redirect(url_for('login'))
    
    @app.route('/setup')
    def setup():
        """Setup and optimization endpoint"""
        try:
            # Run database optimizations
            from database_optimizer import run_full_optimization
            optimization_results = run_full_optimization()
            optimizations_text = ", ".join([k for k, v in optimization_results.items() if v])
            
            return f"""
            <h2>TraceTrack Production Setup Complete</h2>
            <p>✓ Admin user: admin / admin</p>
            <p>✓ Database optimizations: {optimizations_text}</p>
            <p>✓ Production configuration applied</p>
            <p><a href="/login">Go to Login</a></p>
            """
        except Exception as e:
            return f"Setup error: {str(e)}"
    
    @app.route('/health')
    def health_check():
        """Health check for deployment monitoring"""
        try:
            # Test database connection
            from sqlalchemy import text
            db.session.execute(text("SELECT 1")).scalar()
            
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'version': '1.0.0'
            })
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 500
    
    # Import and register routes - moved outside function scope
    pass
    
    # Register API blueprints
    try:
        from api_endpoints import api
        app.register_blueprint(api)
    except Exception as e:
        logger.warning(f"Could not register API blueprint: {e}")
    
    try:
        from mobile_api import mobile_api
        app.register_blueprint(mobile_api)
    except Exception as e:
        logger.warning(f"Could not register mobile API blueprint: {e}")
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return render_template('error.html', 
                             error_code=404, 
                             error_message="Page not found"), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('error.html', 
                             error_code=500, 
                             error_message="Internal server error"), 500
    
    return app

# Create the application
app = create_production_app()

# For gunicorn
application = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

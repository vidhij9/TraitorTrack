# Import the working application with environment isolation
from app_clean import app, db
import logging

# Setup logging for production
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import database optimizer (available)
import database_optimizer

# Import all the main routes to ensure they're registered
import routes
import optimized_api  # Import optimized API v2 routes

# Import enterprise monitoring and optimization systems
from performance_monitoring import monitor, alert_manager
from enterprise_cache import cache, CacheWarmer
from database_scaling import db_scaler
from analytics_routes import analytics_bp

# Register analytics blueprint
app.register_blueprint(analytics_bp)

# Initialize enterprise systems
db_scaler.init_app(app)

# Setup monitoring for all routes
@app.before_request
def before_request():
    """Track all requests for monitoring"""
    monitor.track_request(lambda: None)()

# Warm cache on startup
with app.app_context():
    try:
        cache.warm_cache()
        CacheWarmer.warm_stats_cache()
        logger.info("Cache warmed successfully")
    except Exception as e:
        logger.warning(f"Cache warming failed: {e}")
    
    # Setup database optimizations
    try:
        db_scaler.optimize_indexes()
        db_scaler.setup_monitoring()
        logger.info("Database optimizations applied")
    except Exception as e:
        logger.warning(f"Database optimization failed: {e}")

# Emergency navigation route
@app.route('/nav')
def emergency_nav():
    """Emergency navigation page to bypass navbar issues"""
    from flask import render_template
    return render_template('emergency_nav.html')

# Add test data creation endpoint
@app.route('/create-test-data')
def create_test_data():
    """Create sample test data for ultra-fast search testing"""
    try:
        from create_test_data import create_sample_data
        create_sample_data()
        return "✓ Sample test data created successfully! Try searching for P000001 or C000001"
    except Exception as e:
        return f"Error creating test data: {str(e)}"

# Add production deployment setup endpoint
@app.route('/production-setup')
def production_setup():
    """Setup and optimize for production deployment"""
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
        return f"Setup error: {str(e)}"

# Production health check endpoint for monitoring
@app.route('/production-health')
def production_health():
    """Health check for production monitoring"""
    try:
        from sqlalchemy import text
        db.session.execute(text("SELECT 1")).scalar()
        
        return {
            'status': 'healthy',
            'database': 'connected',
            'version': '1.0.0',
            'deployment': 'production-ready'
        }
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}, 500

# Expose app for gunicorn
application = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
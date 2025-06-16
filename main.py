# Import the working application with environment isolation
from app_clean import app, db
import logging

# Setup logging for production
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import optimized components for production
import optimized_api
import database_optimizer
import high_performance_api

# Import all the main routes to ensure they're registered
import routes

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
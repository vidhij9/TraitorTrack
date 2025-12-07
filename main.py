# Import the application
from app import app, db
import logging
import time
from flask import request, g

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import all the main routes to ensure they're registered
import routes
import api  # Import consolidated API endpoints
import api_optimized  # Import optimized v2 API endpoints

# Import and register IPT blueprint for Inter Party Transfer
from ipt_routes import ipt_bp
app.register_blueprint(ipt_bp)

# Setup monitoring for all routes
@app.before_request
def before_request():
    """Track all requests for monitoring"""
    g.request_start = time.time()

@app.after_request
def after_request(response):
    """Skip performance logging for speed"""
    return response

# Warm cache on startup
with app.app_context():
    try:
        # Warm up critical caches
        from sqlalchemy import text
        db.session.execute(text("SELECT 1")).scalar()
        logger.info("Database connection verified")
    except Exception as e:
        logger.warning(f"Database warmup failed: {e}")

# Expose app for gunicorn
application = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

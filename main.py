# TraceTrack - Production Deployment
import os
import logging

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from app_clean import app, db
    logger.info("Successfully imported app_clean")
    
    # Try to import working modules one by one
    try:
        import api
        logger.info("Successfully imported api")
    except Exception as e:
        logger.error(f"Failed to import api: {e}")
    
    try:
        import optimized_api
        logger.info("Successfully imported optimized_api")
    except Exception as e:
        logger.error(f"Failed to import optimized_api: {e}")
    
    try:
        import cache_utils
        logger.info("Successfully imported cache_utils")
    except Exception as e:
        logger.error(f"Failed to import cache_utils: {e}")
    
    # Import production-safe routes
    try:
        import routes_production
        logger.info("Successfully imported routes_production")
    except Exception as e:
        logger.error(f"Failed to import routes_production: {e}")
    
except Exception as e:
    logger.error(f"Critical error importing app_clean: {e}")
    # Fallback to minimal Flask app
    from flask import Flask, jsonify
    app = Flask(__name__)
    
    @app.route('/')
    def health():
        return jsonify({'status': 'error', 'message': 'Import failed', 'error': str(e)})

# Export for gunicorn
application = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
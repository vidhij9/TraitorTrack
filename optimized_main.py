"""
Optimized main application entry point
Consolidates initialization and reduces startup time
"""
from app_clean import app
from performance_monitor import optimize_database_session
import logging

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

def initialize_optimizations():
    """Initialize all optimizations on startup"""
    try:
        with app.app_context():
            # Optimize database session
            optimize_database_session()
            
            # Import routes and APIs
            import routes  # noqa
            import api  # noqa  
            import optimized_routes  # noqa
            
            logging.info("Application optimizations initialized successfully")
    except Exception as e:
        logging.error(f"Optimization initialization failed: {e}")

# Initialize on import
initialize_optimizations()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
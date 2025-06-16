# TraceTrack - Deploy Development Codebase to Production
from app_clean import app, db

# Import all your tested routes and features
import routes
import api
import optimized_api
import cache_utils
import database_optimizer

# Export both app and application for gunicorn compatibility
application = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
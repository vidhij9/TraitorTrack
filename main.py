# TraceTrack Production Deployment - Complete Application
from app_production import app, db

# Export for gunicorn
application = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
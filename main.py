from app_clean import app, db
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import all routes
import routes
import api

# Health endpoint
@app.route('/health')
def health():
    return {'status': 'healthy', 'service': 'TraceTrack'}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

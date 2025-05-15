from app import app  # noqa: F401
import multiprocessing
import os
from gevent.pywsgi import WSGIServer

# Import routes and other modules
import routes  # noqa: F401
import api_endpoints  # noqa: F401
import mobile_api  # noqa: F401
import db_monitoring  # Load database monitoring module

def run_with_gevent(app):
    """Run the application with gevent's WSGIServer for better performance"""
    http_server = WSGIServer(('0.0.0.0', 5000), app)
    http_server.serve_forever()

if __name__ == "__main__":
    # In development, use Flask's built-in server
    if os.environ.get('FLASK_ENV') == 'development':
        app.run(host="0.0.0.0", port=5000, debug=True)
    else:
        # In production, use gevent's WSGIServer
        print("Starting high-performance server with gevent...")
        run_with_gevent(app)

"""
Gunicorn configuration for high-concurrency deployment
"""
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes - automatically scale based on CPU cores
workers = multiprocessing.cpu_count() * 2 + 1  # Optimal for production
worker_class = "gevent"  # Use async workers for maximum concurrency
worker_connections = 1000
threads = 4  # 4 threads per worker = 16 concurrent requests
max_requests = 1000  # Restart workers after 1000 requests to prevent memory leaks
max_requests_jitter = 50  # Add randomness to prevent all workers restarting at once
timeout = 120  # Increase timeout for slow database operations
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"  # Log to stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "tracetrack"

# Server mechanics
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
keyfile = None
certfile = None

# Debugging
reload = os.environ.get('FLASK_ENV', 'production') == 'development'  # Only reload in dev
reload_engine = "auto"
reload_extra_files = []
spew = False
check_config = False

# Pre-fork settings
preload_app = True  # Preload for better memory usage in production
reuse_port = True  # Allow multiple workers to bind to the same port

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info("Worker received SIGABRT signal")
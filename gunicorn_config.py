"""
Gunicorn configuration for high-concurrency deployment
"""
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = 4  # Fixed number for consistent performance
worker_class = "gthread"  # Use threaded workers for better concurrency
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
reload = True  # Auto-reload on code changes (disable in production)
reload_engine = "auto"
reload_extra_files = []
spew = False
check_config = False

# Pre-fork settings
preload_app = False  # Don't preload to avoid database connection issues
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
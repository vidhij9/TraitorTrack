"""
Gunicorn configuration optimized for 20+ concurrent scanning users
Target: Handle 20-30 simultaneous scanning operations smoothly
"""
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker configuration for 20+ concurrent scanning users
# Use threaded workers for better session handling
workers = 8  # 8 workers to handle concurrent requests
worker_class = "gthread"  # Threaded workers for session management
threads = 4  # 4 threads per worker = 32 concurrent threads total
worker_connections = 1000  # High connection limit per worker

# Memory management
max_requests = 2000  # Recycle workers after 2000 requests
max_requests_jitter = 200  # Add randomness to prevent simultaneous restarts

# Timeouts optimized for scanning operations
timeout = 60  # 60 seconds for database operations
graceful_timeout = 30  # Grace period for worker shutdown
keepalive = 5  # Keep connections alive

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"  # Log errors to stdout
loglevel = "info"
access_log_format = '%(t)s %(p)s %(h)s "%(r)s" %(s)s %(L)s %(b)s "%(a)s"'

# Process naming
proc_name = "tracetrack_scanner"

# Server mechanics
daemon = False
pidfile = None
worker_tmp_dir = "/dev/shm"  # Use RAM for worker heartbeat
user = None
group = None
tmp_upload_dir = None

# SSL (disabled for internal use)
keyfile = None
certfile = None

# Performance tuning
preload_app = True  # Preload app for better memory usage
reuse_port = True  # Allow multiple workers to bind to same port

# Hooks for monitoring
def when_ready(server):
    """Called when server is ready"""
    server.log.info(f"Server ready with {workers} workers, {threads} threads each")
    server.log.info(f"Total concurrent capacity: {workers * threads} simultaneous requests")

def worker_init(worker):
    """Called when worker is initialized"""
    worker.log.info(f"Worker {worker.pid} initialized")

def pre_request(worker, req):
    """Called before a worker processes a request"""
    worker.log.debug(f"Worker {worker.pid} processing {req.method} {req.path}")

def post_request(worker, req, environ, resp):
    """Called after a worker processes a request"""
    worker.log.debug(f"Worker {worker.pid} completed {req.method} {req.path}")

def worker_exit(server, worker):
    """Called just after a worker has been exited"""
    server.log.info(f"Worker {worker.pid} exited")
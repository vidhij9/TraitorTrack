"""
Gunicorn configuration for production deployment
Optimized for handling 50+ concurrent users with 800,000+ bags
"""
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1  # Dynamic based on CPU cores
worker_class = "gevent"  # Async worker for high concurrency
worker_connections = 1000  # Max concurrent connections per worker
max_requests = 5000  # Restart workers after this many requests to prevent memory leaks
max_requests_jitter = 500  # Add randomness to prevent all workers restarting at once
timeout = 120  # Worker timeout for long-running requests
graceful_timeout = 30  # Time to wait for workers to finish during restart
keepalive = 5  # Keep connections alive for 5 seconds

# Threading (for gthread worker class as fallback)
threads = 4

# Process naming
proc_name = "tracetrack_production"

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"  # Log errors to stdout
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process management
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = None
# certfile = None

# Server mechanics
preload_app = True  # Load app before forking workers
reload = False  # Don't auto-reload in production
reload_engine = "auto"
reload_extra_files = []
spew = False
check_config = False
print_config = False

# Server hooks for monitoring and optimization
def on_starting(server):
    """Called just before the master process is initialized"""
    server.log.info("Starting TraceTrack production server...")
    server.log.info(f"Master process PID: {os.getpid()}")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP"""
    server.log.info("Reloading TraceTrack workers...")

def when_ready(server):
    """Called just after the server is started"""
    server.log.info("TraceTrack server is ready. Listening at: {}".format(bind))
    server.log.info(f"Using {workers} workers with {worker_class} worker class")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT"""
    worker.log.info(f"Worker {worker.pid} interrupted")

def pre_fork(server, worker):
    """Called just before a worker is forked"""
    server.log.info(f"Forking worker {worker.pid}")

def post_fork(server, worker):
    """Called just after a worker has been forked"""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def pre_exec(server):
    """Called just before a new master process is forked"""
    server.log.info("Forking new master process...")

def pre_request(worker, req):
    """Called just before a worker processes the request"""
    worker.log.debug(f"{req.method} {req.path}")

def post_request(worker, req, environ, resp):
    """Called after a worker processes the request"""
    worker.log.debug(f"Request completed: {req.method} {req.path} - {resp.status}")

def child_exit(server, worker):
    """Called just after a worker has been exited"""
    server.log.info(f"Worker {worker.pid} exited")

def worker_exit(server, worker):
    """Called just after a worker has been exited"""
    server.log.info(f"Worker {worker.pid} exited")

def nworkers_changed(server, new_value, old_value):
    """Called when num_workers has been changed"""
    server.log.info(f"Number of workers changed from {old_value} to {new_value}")

def on_exit(server):
    """Called just before exiting"""
    server.log.info("Shutting down TraceTrack server...")

# Environment-specific configurations
if os.environ.get("ENVIRONMENT") == "production":
    # For AWS ECS with 1024 CPU units, use conservative settings
    workers = 2  # Conservative for 1024 CPU units
    worker_class = "sync"  # More stable than gevent for initial deployment
    timeout = 60  # Standard timeout
    loglevel = "info"  # Balanced logging
    accesslog = "-"  # Always log to stdout for CloudWatch
    errorlog = "-"  # Always log to stdout for CloudWatch
else:
    workers = 2  # Fewer workers in development
    loglevel = "debug"  # More verbose in development
    reload = True  # Enable auto-reload in development
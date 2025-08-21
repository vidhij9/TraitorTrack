"""
High-performance Gunicorn configuration
Optimized for 50+ concurrent users and 800,000+ bags
"""

import multiprocessing
import os

# Calculate optimal workers
cpu_count = multiprocessing.cpu_count()

# Worker configuration for high concurrency
workers = min(cpu_count * 4, 16)  # 4 workers per CPU, max 16
worker_class = 'sync'  # Sync workers for stability
worker_connections = 2000  # High connection count per worker
threads = 4  # 4 threads per worker for better concurrency

# Request handling
max_requests = 50000  # Restart workers after 50k requests
max_requests_jitter = 5000  # Add jitter to prevent simultaneous restarts
timeout = 120  # 2 minute timeout for complex operations
graceful_timeout = 30  # 30 second graceful shutdown
keepalive = 5  # Keep connections alive for 5 seconds

# Server socket
bind = '0.0.0.0:5000'
backlog = 4096  # Large backlog for high load
reuse_port = True  # Enable port reuse for better load distribution

# Process naming
proc_name = 'tracetrack-highperf'

# Server mechanics
daemon = False
pidfile = '/tmp/tracetrack.pid'
user = None
group = None
tmp_upload_dir = None

# Logging
errorlog = '-'  # Log to stderr
loglevel = 'error'  # Only log errors for performance
accesslog = None  # Disable access log for performance
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process lifecycle
preload_app = True  # Preload app for faster worker starts
reload = True  # Enable reload for development
reload_engine = 'auto'
reload_extra_files = []
capture_output = False
spew = False

# Server hooks for optimization
def on_starting(server):
    """Called just before the master process is initialized"""
    server.log.info("Starting TraceTrack high-performance server")
    server.log.info(f"Configuration: {workers} workers, {threads} threads per worker")
    server.log.info(f"Maximum capacity: {workers * worker_connections} concurrent connections")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP"""
    server.log.info("Reloading workers for zero-downtime deployment")

def when_ready(server):
    """Called just after the server is started"""
    server.log.info("TraceTrack server is ready to handle requests")
    server.log.info(f"Listening on {bind}")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT"""
    worker.log.info(f"Worker {worker.pid} interrupted")

def pre_fork(server, worker):
    """Called just before a worker is forked"""
    server.log.info(f"Forking worker {worker.pid}")

def post_fork(server, worker):
    """Called just after a worker has been forked"""
    # Initialize per-worker resources
    worker.log.info(f"Worker {worker.pid} spawned")
    
    # Import and initialize cache for this worker
    try:
        from ultra_cache import initialize_cache
        initialize_cache()
        worker.log.info(f"Worker {worker.pid}: Cache initialized")
    except ImportError:
        pass
    
    # Patch performance optimizations
    try:
        from performance_patches import patch_all
        patch_all()
        worker.log.info(f"Worker {worker.pid}: Performance patches applied")
    except ImportError:
        pass

def pre_exec(server):
    """Called just before a new master process is forked"""
    server.log.info("Forking new master process")

def pre_request(worker, req):
    """Called just before a worker processes the request"""
    worker.log.debug(f"{req.method} {req.path}")

def post_request(worker, req, environ, resp):
    """Called after a worker processes the request"""
    pass

def child_exit(server, worker):
    """Called just after a worker has been exited"""
    server.log.info(f"Worker {worker.pid} exited")

def worker_exit(server, worker):
    """Called just after a worker has been exited"""
    server.log.info(f"Worker {worker.pid} cleanup complete")

def nworkers_changed(server, new_value, old_value):
    """Called just after num_workers has been changed"""
    server.log.info(f"Worker count changed from {old_value} to {new_value}")

def on_exit(server):
    """Called just before exiting"""
    server.log.info("TraceTrack server shutting down")

# Performance optimizations
def post_worker_init(worker):
    """Initialize worker-specific optimizations"""
    # Set process priority
    try:
        import os
        os.nice(-5)  # Increase priority slightly
    except:
        pass
    
    # Set CPU affinity if possible
    try:
        import psutil
        p = psutil.Process()
        cpu_count = psutil.cpu_count()
        cpu_id = worker.age % cpu_count
        p.cpu_affinity([cpu_id])
        worker.log.info(f"Worker {worker.pid} bound to CPU {cpu_id}")
    except:
        pass

# Environment-specific optimizations
if os.environ.get('ENVIRONMENT') == 'production':
    # Production optimizations
    accesslog = None  # No access log in production
    errorlog = '/var/log/tracetrack/error.log'
    loglevel = 'error'
    reload = False  # No auto-reload in production
    preload_app = True  # Always preload in production
else:
    # Development settings
    loglevel = 'info'
    reload = True
    accesslog = '-'
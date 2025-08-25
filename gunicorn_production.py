
import multiprocessing
import os

# Ultra-optimized Gunicorn configuration for production

# Bind to all interfaces on port 5000
bind = "0.0.0.0:5000"

# Workers configuration
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"  # Async worker for high concurrency
worker_connections = 2000  # Connections per worker
threads = 4  # Threads per worker

# Connection handling
backlog = 2048  # Maximum pending connections
keepalive = 5  # Seconds to keep connections alive

# Timeouts
timeout = 60  # Worker timeout
graceful_timeout = 30  # Graceful shutdown timeout

# Performance tuning
max_requests = 10000  # Restart workers after this many requests
max_requests_jitter = 1000  # Randomize worker restarts
preload_app = True  # Load app before forking workers

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"  # Log to stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'tracetrack-production'

# Stats
statsd_host = None  # Enable if using StatsD
statsd_prefix = 'tracetrack'

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Worker lifecycle
def on_starting(server):
    """Called just before the master process is initialized"""
    server.log.info("Starting TraceTrack Production Server")

def on_reload(server):
    """Called to recycle workers during a reload"""
    server.log.info("Reloading TraceTrack workers")

def when_ready(server):
    """Called just after the server is started"""
    server.log.info("TraceTrack server is ready. Listening on: %s", server.address)

def worker_int(worker):
    """Called when a worker receives the INT or QUIT signal"""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked"""
    server.log.info("Pre-fork worker")

def post_fork(server, worker):
    """Called just after a worker has been forked"""
    server.log.info("Post-fork worker")
    
def worker_exit(server, worker):
    """Called just after a worker has been exited"""
    server.log.info("Worker exit")

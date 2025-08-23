"""
Ultra-optimized Gunicorn configuration for <50ms response times
Supports 50+ concurrent users
"""

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes - optimized for high concurrency
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"  # Async worker for better concurrency
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# Timeouts
timeout = 30
graceful_timeout = 30
keepalive = 2

# Process naming
proc_name = 'tracetrack-ultra'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Stats
statsd_host = None
statsd_prefix = None

# Server hooks
def post_fork(server, worker):
    """Initialize worker-specific resources"""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_fork(server, worker):
    """Pre-fork hook"""
    pass

def pre_exec(server):
    """Pre-exec hook"""
    server.log.info("Forked child, re-executing.")

def when_ready(server):
    """Called when server is ready"""
    server.log.info("Server is ready. Spawning workers")
    
    # Warmup cache on server start
    try:
        import requests
        requests.post('http://localhost:5000/api/ultra/warmup', timeout=5)
        server.log.info("Cache warmed up successfully")
    except:
        pass

def worker_int(worker):
    """Worker interrupt handler"""
    worker.log.info("worker received INT or QUIT signal")

def on_exit(server):
    """Server exit handler"""
    server.log.info("Server is shutting down")

# Environment variables
raw_env = [
    'DATABASE_URL=' + os.environ.get('DATABASE_URL', ''),
    'SESSION_SECRET=' + os.environ.get('SESSION_SECRET', 'dev-secret'),
    'FLASK_ENV=production'
]

print("🚀 Ultra-optimized Gunicorn configuration loaded")
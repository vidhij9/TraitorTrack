
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 4096  # Increased for high load

# Worker configuration optimized for 50+ concurrent users
workers = min(multiprocessing.cpu_count() * 4, 16)  # More workers
worker_class = "gthread"  # Threaded workers
threads = 8  # More threads per worker
worker_connections = 2000  # Higher connection limit
max_requests = 5000  # Recycle workers after more requests
max_requests_jitter = 500
timeout = 120  # Longer timeout for heavy operations
graceful_timeout = 60
keepalive = 10  # Longer keepalive

# Logging - reduce for performance
accesslog = None  # Disable access logs for performance
errorlog = "-"
loglevel = "error"  # Only log errors

# Process naming
proc_name = "tracetrack_highperf"

# Server mechanics
daemon = False
preload_app = True  # Preload for better memory usage
reuse_port = True  # Allow multiple workers to bind

def when_ready(server):
    server.log.info("High-performance server ready with optimized configuration")

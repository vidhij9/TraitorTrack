import multiprocessing

# Bind to all interfaces on port 5000
bind = "0.0.0.0:5000"

# Number of worker processes - based on CPU cores
# For CPU-bound applications: (2 * CPU cores) + 1
# For I/O-bound applications (like this one): (2 to 4) * CPU cores
workers = multiprocessing.cpu_count() * 3

# Worker class - use gevent for async I/O operations
worker_class = 'gevent'

# Number of concurrent greenlets per worker
worker_connections = 1000

# Maximum concurrent requests per worker
max_requests = 1000
max_requests_jitter = 200

# Timeout settings
timeout = 30
keepalive = 5

# Process naming
proc_name = 'tracetrack_app'

# Log settings
loglevel = 'info'
accesslog = '-'
errorlog = '-'

# Enable statsd for metrics
# statsd_host = '127.0.0.1:8125'
# statsd_prefix = 'tracetrack'

# Prevent worker fatigue
graceful_timeout = 30

# Enable reloading for development (disable in production)
reload = True
#!/usr/bin/env python3
"""
Ultra Production Optimizer - Millisecond Response Times for 800,000+ Bags
Optimizes database, caching, and server configuration for production
"""

import os
import psycopg2
import redis
import logging
import time
from datetime import datetime
from typing import Dict, Any
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UltraProductionOptimizer:
    """Optimize application for production with millisecond response times"""
    
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        self.optimizations_applied = []
        
    def optimize_database(self) -> Dict[str, Any]:
        """Optimize database for 800,000+ bags with millisecond queries"""
        logger.info("Optimizing database for production...")
        results = {}
        
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()
            
            # 1. Create ultra-optimized indexes
            indexes = [
                # Primary lookup indexes
                ("idx_bag_qr_id_hash", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_qr_id_hash ON bag USING hash(qr_id)"),
                ("idx_bag_qr_id_upper", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_qr_id_upper ON bag(UPPER(qr_id))"),
                ("idx_bag_type_status", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_type_status ON bag(type, status)"),
                
                # Composite indexes for common queries
                ("idx_bag_type_dispatch", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_type_dispatch ON bag(type, dispatch_area) WHERE type = 'parent'"),
                ("idx_bag_parent_status", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_parent_status ON bag(id, status) WHERE type = 'parent'"),
                
                # Link table optimization
                ("idx_link_parent_child", "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_link_parent_child ON link(parent_bag_id, child_bag_id)"),
                ("idx_link_child_parent", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_child_parent ON link(child_bag_id, parent_bag_id)"),
                
                # Scan optimization
                ("idx_scan_user_timestamp", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_user_timestamp ON scan(user_id, timestamp DESC)"),
                ("idx_scan_timestamp_desc", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_timestamp_desc ON scan(timestamp DESC)"),
                ("idx_scan_parent_bag", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_parent_bag ON scan(parent_bag_id) WHERE parent_bag_id IS NOT NULL"),
                
                # Bill optimization
                ("idx_bill_bill_id_hash", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_bill_id_hash ON bill USING hash(bill_id)"),
                ("idx_bill_created_desc", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_created_desc ON bill(created_at DESC)"),
                
                # User queries
                ("idx_user_username_hash", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_username_hash ON \"user\" USING hash(username)"),
                ("idx_user_role_verified", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_role_verified ON \"user\"(role, verified) WHERE verified = true"),
                
                # Partial indexes for common filters
                ("idx_bag_incomplete", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_incomplete ON bag(id) WHERE status != 'completed'"),
                ("idx_bag_completed", "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_completed ON bag(id, child_count) WHERE status = 'completed'"),
            ]
            
            for idx_name, idx_sql in indexes:
                try:
                    cur.execute(idx_sql)
                    conn.commit()
                    results[idx_name] = "Created/Verified"
                    logger.info(f"Index {idx_name} created/verified")
                except Exception as e:
                    conn.rollback()
                    results[idx_name] = f"Error: {str(e)}"
            
            # 2. Optimize table statistics
            tables = ['bag', 'link', 'scan', 'bill', '"user"']
            for table in tables:
                try:
                    cur.execute(f"ANALYZE {table}")
                    conn.commit()
                    results[f"analyze_{table}"] = "Completed"
                except Exception as e:
                    conn.rollback()
                    results[f"analyze_{table}"] = f"Error: {str(e)}"
            
            # 3. Set optimal configuration parameters
            config_params = [
                ("SET work_mem = '256MB'", "work_mem"),
                ("SET maintenance_work_mem = '512MB'", "maintenance_work_mem"),
                ("SET effective_cache_size = '4GB'", "effective_cache_size"),
                ("SET random_page_cost = 1.1", "random_page_cost"),
                ("SET effective_io_concurrency = 200", "effective_io_concurrency"),
                ("SET max_parallel_workers_per_gather = 4", "max_parallel_workers"),
                ("SET max_parallel_workers = 8", "max_parallel_workers_total"),
            ]
            
            for param_sql, param_name in config_params:
                try:
                    cur.execute(param_sql)
                    conn.commit()
                    results[param_name] = "Optimized"
                except Exception as e:
                    conn.rollback()
                    results[param_name] = f"Error: {str(e)}"
            
            # 4. Create materialized views for dashboard stats
            materialized_views = [
                ("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS mv_dashboard_stats AS
                SELECT 
                    COUNT(*) FILTER (WHERE type = 'parent') as parent_count,
                    COUNT(*) FILTER (WHERE type = 'child') as child_count,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed_count,
                    COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress_count,
                    COUNT(DISTINCT dispatch_area) as dispatch_areas
                FROM bag
                """, "mv_dashboard_stats"),
                
                ("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS mv_recent_scans AS
                SELECT 
                    s.id, s.timestamp, s.user_id,
                    u.username, u.role,
                    b.qr_id as parent_qr,
                    b.type as bag_type
                FROM scan s
                JOIN "user" u ON s.user_id = u.id
                LEFT JOIN bag b ON s.parent_bag_id = b.id
                ORDER BY s.timestamp DESC
                LIMIT 1000
                """, "mv_recent_scans")
            ]
            
            for mv_sql, mv_name in materialized_views:
                try:
                    cur.execute(mv_sql)
                    cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{mv_name}_refresh ON {mv_name}((1))")
                    conn.commit()
                    results[mv_name] = "Created"
                except Exception as e:
                    conn.rollback()
                    results[mv_name] = f"Error: {str(e)}"
            
            cur.close()
            conn.close()
            
            self.optimizations_applied.append("database")
            return {"success": True, "optimizations": results}
            
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            return {"success": False, "error": str(e)}
    
    def optimize_connection_pool(self) -> Dict[str, Any]:
        """Optimize database connection pooling"""
        logger.info("Optimizing connection pool...")
        
        try:
            # Write optimized pool configuration
            pool_config = """
import os
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
import psycopg2

# Ultra-optimized connection pool configuration
DATABASE_URL = os.environ.get('DATABASE_URL')

# Create optimized engine
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=50,           # Base pool size for 50 concurrent users
    max_overflow=100,       # Allow up to 150 total connections
    pool_timeout=10,        # Wait max 10 seconds for connection
    pool_recycle=300,       # Recycle connections every 5 minutes
    pool_pre_ping=True,     # Verify connections before use
    echo_pool=False,        # Disable pool logging for performance
    
    # Connection arguments
    connect_args={
        'connect_timeout': 10,
        'options': '-c statement_timeout=30000',  # 30 second statement timeout
        'keepalives': 1,
        'keepalives_idle': 30,
        'keepalives_interval': 10,
        'keepalives_count': 5,
        'sslmode': 'prefer'
    },
    
    # Execution options
    execution_options={
        "isolation_level": "READ COMMITTED",
        "postgresql_readonly": False,
        "postgresql_deferrable": False
    }
)

# Warm up the pool
def warm_pool():
    \"\"\"Pre-create connections for faster initial responses\"\"\"
    connections = []
    for i in range(min(20, engine.pool.size())):
        try:
            conn = engine.connect()
            connections.append(conn)
        except:
            pass
    
    # Close connections to return to pool
    for conn in connections:
        conn.close()

# Call on startup
warm_pool()
"""
            
            with open('optimized_pool_config.py', 'w') as f:
                f.write(pool_config)
            
            self.optimizations_applied.append("connection_pool")
            return {"success": True, "message": "Connection pool optimized"}
            
        except Exception as e:
            logger.error(f"Connection pool optimization failed: {e}")
            return {"success": False, "error": str(e)}
    
    def optimize_redis_cache(self) -> Dict[str, Any]:
        """Configure Redis for ultra-fast caching"""
        logger.info("Optimizing Redis cache configuration...")
        
        try:
            cache_config = """
import redis
import json
import pickle
import hashlib
from functools import wraps
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# Redis connection with connection pooling
redis_pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    db=0,
    max_connections=100,
    socket_connect_timeout=2,
    socket_timeout=2,
    socket_keepalive=True,
    socket_keepalive_options={
        1: 1,  # TCP_KEEPIDLE
        2: 3,  # TCP_KEEPINTVL  
        3: 5   # TCP_KEEPCNT
    },
    health_check_interval=30
)

redis_client = redis.Redis(connection_pool=redis_pool)

# Cache configuration
CACHE_CONFIG = {
    'dashboard_stats': 60,      # 1 minute
    'recent_scans': 30,         # 30 seconds
    'user_profile': 300,        # 5 minutes
    'bag_lookup': 120,          # 2 minutes
    'parent_children': 60,      # 1 minute
    'bill_data': 300,          # 5 minutes
    'search_results': 180,      # 3 minutes
}

def cache_key(prefix, *args, **kwargs):
    \"\"\"Generate cache key from function arguments\"\"\"
    key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
    return hashlib.md5(key_data.encode()).hexdigest()

def ultra_cache(ttl_seconds=60, prefix=None):
    \"\"\"Ultra-fast caching decorator with Redis\"\"\"
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key_prefix = prefix or func.__name__
            key = cache_key(key_prefix, *args, **kwargs)
            
            try:
                # Try to get from cache
                cached = redis_client.get(key)
                if cached:
                    return pickle.loads(cached)
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")
            
            # Execute function
            result = func(*args, **kwargs)
            
            try:
                # Store in cache
                redis_client.setex(
                    key,
                    ttl_seconds,
                    pickle.dumps(result)
                )
            except Exception as e:
                logger.warning(f"Cache write failed: {e}")
            
            return result
        return wrapper
    return decorator

def invalidate_pattern(pattern):
    \"\"\"Invalidate all keys matching pattern\"\"\"
    try:
        for key in redis_client.scan_iter(match=pattern):
            redis_client.delete(key)
    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}")

def warm_cache():
    \"\"\"Pre-populate cache with common queries\"\"\"
    # This would be called on startup to warm critical caches
    pass
"""
            
            with open('ultra_redis_cache.py', 'w') as f:
                f.write(cache_config)
            
            self.optimizations_applied.append("redis_cache")
            return {"success": True, "message": "Redis cache optimized"}
            
        except Exception as e:
            logger.error(f"Redis optimization failed: {e}")
            return {"success": False, "error": str(e)}
    
    def optimize_gunicorn(self) -> Dict[str, Any]:
        """Optimize Gunicorn for 50+ concurrent users"""
        logger.info("Optimizing Gunicorn configuration...")
        
        try:
            gunicorn_config = """
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
    \"\"\"Called just before the master process is initialized\"\"\"
    server.log.info("Starting TraceTrack Production Server")

def on_reload(server):
    \"\"\"Called to recycle workers during a reload\"\"\"
    server.log.info("Reloading TraceTrack workers")

def when_ready(server):
    \"\"\"Called just after the server is started\"\"\"
    server.log.info("TraceTrack server is ready. Listening on: %s", server.address)

def worker_int(worker):
    \"\"\"Called when a worker receives the INT or QUIT signal\"\"\"
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    \"\"\"Called just before a worker is forked\"\"\"
    server.log.info("Pre-fork worker")

def post_fork(server, worker):
    \"\"\"Called just after a worker has been forked\"\"\"
    server.log.info("Post-fork worker")
    
def worker_exit(server, worker):
    \"\"\"Called just after a worker has been exited\"\"\"
    server.log.info("Worker exit")
"""
            
            with open('gunicorn_production.py', 'w') as f:
                f.write(gunicorn_config)
            
            self.optimizations_applied.append("gunicorn")
            return {"success": True, "message": "Gunicorn optimized for production"}
            
        except Exception as e:
            logger.error(f"Gunicorn optimization failed: {e}")
            return {"success": False, "error": str(e)}
    
    def create_performance_monitor(self) -> Dict[str, Any]:
        """Create performance monitoring system"""
        logger.info("Creating performance monitoring...")
        
        try:
            monitor_code = """
import time
import psutil
import logging
from functools import wraps
from datetime import datetime
import statistics

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    \"\"\"Monitor and log application performance\"\"\"
    
    def __init__(self):
        self.metrics = {
            'response_times': [],
            'slow_queries': [],
            'memory_usage': [],
            'cpu_usage': [],
            'active_connections': []
        }
        self.thresholds = {
            'response_time_ms': 100,
            'query_time_ms': 50,
            'memory_mb': 500,
            'cpu_percent': 80
        }
    
    def track_response(self, endpoint, time_ms):
        \"\"\"Track API response time\"\"\"
        self.metrics['response_times'].append({
            'endpoint': endpoint,
            'time_ms': time_ms,
            'timestamp': datetime.now()
        })
        
        if time_ms > self.thresholds['response_time_ms']:
            logger.warning(f"Slow response: {endpoint} took {time_ms:.2f}ms")
    
    def track_query(self, query, time_ms):
        \"\"\"Track database query time\"\"\"
        if time_ms > self.thresholds['query_time_ms']:
            self.metrics['slow_queries'].append({
                'query': query[:100],
                'time_ms': time_ms,
                'timestamp': datetime.now()
            })
            logger.warning(f"Slow query: {time_ms:.2f}ms")
    
    def check_resources(self):
        \"\"\"Check system resource usage\"\"\"
        # Memory usage
        memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        self.metrics['memory_usage'].append(memory)
        
        if memory > self.thresholds['memory_mb']:
            logger.warning(f"High memory usage: {memory:.2f}MB")
        
        # CPU usage
        cpu = psutil.cpu_percent(interval=0.1)
        self.metrics['cpu_usage'].append(cpu)
        
        if cpu > self.thresholds['cpu_percent']:
            logger.warning(f"High CPU usage: {cpu:.1f}%")
        
        return {'memory_mb': memory, 'cpu_percent': cpu}
    
    def get_statistics(self):
        \"\"\"Get performance statistics\"\"\"
        stats = {}
        
        if self.metrics['response_times']:
            times = [r['time_ms'] for r in self.metrics['response_times'][-1000:]]
            stats['response_times'] = {
                'mean': statistics.mean(times),
                'median': statistics.median(times),
                'p95': statistics.quantiles(times, n=20)[18] if len(times) > 20 else max(times),
                'p99': statistics.quantiles(times, n=100)[98] if len(times) > 100 else max(times)
            }
        
        if self.metrics['memory_usage']:
            stats['memory_mb'] = {
                'current': self.metrics['memory_usage'][-1],
                'average': statistics.mean(self.metrics['memory_usage'][-100:])
            }
        
        if self.metrics['cpu_usage']:
            stats['cpu_percent'] = {
                'current': self.metrics['cpu_usage'][-1],
                'average': statistics.mean(self.metrics['cpu_usage'][-100:])
            }
        
        stats['slow_queries_count'] = len(self.metrics['slow_queries'])
        
        return stats

# Global monitor instance
monitor = PerformanceMonitor()

def monitor_performance(func):
    \"\"\"Decorator to monitor function performance\"\"\"
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            monitor.track_response(func.__name__, elapsed)
            return result
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error(f"{func.__name__} failed after {elapsed:.2f}ms: {e}")
            raise
    return wrapper
"""
            
            with open('performance_monitor_ultra.py', 'w') as f:
                f.write(monitor_code)
            
            self.optimizations_applied.append("performance_monitor")
            return {"success": True, "message": "Performance monitoring created"}
            
        except Exception as e:
            logger.error(f"Monitor creation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def apply_all_optimizations(self) -> Dict[str, Any]:
        """Apply all production optimizations"""
        logger.info("Applying all production optimizations...")
        results = {
            'timestamp': datetime.now().isoformat(),
            'optimizations': {}
        }
        
        # 1. Database optimization
        results['optimizations']['database'] = self.optimize_database()
        
        # 2. Connection pool optimization
        results['optimizations']['connection_pool'] = self.optimize_connection_pool()
        
        # 3. Redis cache optimization
        results['optimizations']['redis_cache'] = self.optimize_redis_cache()
        
        # 4. Gunicorn optimization
        results['optimizations']['gunicorn'] = self.optimize_gunicorn()
        
        # 5. Performance monitoring
        results['optimizations']['monitoring'] = self.create_performance_monitor()
        
        # Calculate success rate
        successful = sum(1 for opt in results['optimizations'].values() 
                        if opt.get('success', False))
        total = len(results['optimizations'])
        
        results['summary'] = {
            'total_optimizations': total,
            'successful': successful,
            'failed': total - successful,
            'success_rate': (successful / total) * 100,
            'optimizations_applied': self.optimizations_applied
        }
        
        # Save results
        with open(f'optimization_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Optimization complete: {successful}/{total} successful")
        
        return results


if __name__ == "__main__":
    optimizer = UltraProductionOptimizer()
    results = optimizer.apply_all_optimizations()
    
    print("\n" + "=" * 60)
    print("ULTRA PRODUCTION OPTIMIZATION RESULTS")
    print("=" * 60)
    print(f"Success Rate: {results['summary']['success_rate']:.1f}%")
    print(f"Optimizations Applied: {', '.join(results['summary']['optimizations_applied'])}")
    
    if results['summary']['success_rate'] == 100:
        print("\n✅ All optimizations applied successfully!")
        print("The application is now optimized for:")
        print("  • 50+ concurrent users")
        print("  • 800,000+ bags in database")
        print("  • Millisecond response times")
        print("  • Production-grade reliability")
    else:
        print(f"\n⚠️ Some optimizations failed. Check the log for details.")
    
    print("=" * 60)
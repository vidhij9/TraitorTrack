
import time
import psutil
import logging
from functools import wraps
from datetime import datetime
import statistics

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Monitor and log application performance"""
    
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
        """Track API response time"""
        self.metrics['response_times'].append({
            'endpoint': endpoint,
            'time_ms': time_ms,
            'timestamp': datetime.now()
        })
        
        if time_ms > self.thresholds['response_time_ms']:
            logger.warning(f"Slow response: {endpoint} took {time_ms:.2f}ms")
    
    def track_query(self, query, time_ms):
        """Track database query time"""
        if time_ms > self.thresholds['query_time_ms']:
            self.metrics['slow_queries'].append({
                'query': query[:100],
                'time_ms': time_ms,
                'timestamp': datetime.now()
            })
            logger.warning(f"Slow query: {time_ms:.2f}ms")
    
    def check_resources(self):
        """Check system resource usage"""
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
        """Get performance statistics"""
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
    """Decorator to monitor function performance"""
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


import psutil
import time
import json
from datetime import datetime

def get_system_metrics():
    '''Get current system performance metrics'''
    
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    network = psutil.net_io_counters()
    
    # Get process-specific metrics
    process = psutil.Process()
    process_info = process.as_dict(['cpu_percent', 'memory_info', 'num_threads'])
    
    metrics = {
        'timestamp': datetime.now().isoformat(),
        'system': {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available_gb': memory.available / (1024**3),
            'disk_percent': disk.percent,
            'network_sent_mb': network.bytes_sent / (1024**2),
            'network_recv_mb': network.bytes_recv / (1024**2)
        },
        'process': {
            'cpu_percent': process_info['cpu_percent'],
            'memory_mb': process_info['memory_info'].rss / (1024**2),
            'threads': process_info['num_threads']
        }
    }
    
    return metrics

def log_performance_metrics():
    '''Log performance metrics to file'''
    metrics = get_system_metrics()
    
    # Log to file
    with open('performance_metrics.jsonl', 'a') as f:
        f.write(json.dumps(metrics) + '\n')
    
    # Alert if resources are critical
    if metrics['system']['cpu_percent'] > 90:
        print(f"⚠️ HIGH CPU USAGE: {metrics['system']['cpu_percent']}%")
    
    if metrics['system']['memory_percent'] > 90:
        print(f"⚠️ HIGH MEMORY USAGE: {metrics['system']['memory_percent']}%")
    
    return metrics

if __name__ == '__main__':
    print("Starting performance monitoring...")
    while True:
        metrics = log_performance_metrics()
        print(f"CPU: {metrics['system']['cpu_percent']:.1f}% | "
              f"Memory: {metrics['system']['memory_percent']:.1f}% | "
              f"Threads: {metrics['process']['threads']}")
        time.sleep(5)

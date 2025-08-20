"""
Production Monitoring Script for TraceTrack
Monitors health, performance, and alerts on issues
"""

import requests
import time
import psutil
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ProductionMonitor:
    """Monitor production system health and performance"""
    
    def __init__(self, base_url='http://localhost:5000'):
        self.base_url = base_url
        self.alerts = []
        
    def check_health(self):
        """Check application health endpoint"""
        try:
            response = requests.get(f'{self.base_url}/health', timeout=5)
            data = response.json()
            
            if response.status_code == 200:
                logging.info(f"✅ Health check passed: {data['status']}")
                return True
            else:
                logging.error(f"❌ Health check failed: {response.status_code}")
                self.alerts.append(f"Health check failed at {datetime.now()}")
                return False
        except Exception as e:
            logging.error(f"❌ Health check error: {e}")
            self.alerts.append(f"Health check error: {e}")
            return False
    
    def check_performance(self):
        """Test response times for key operations"""
        operations = {
            'login_page': '/login',
            'dashboard': '/dashboard',
            'api_endpoint': '/health'
        }
        
        results = {}
        for name, endpoint in operations.items():
            try:
                start = time.time()
                response = requests.get(f'{self.base_url}{endpoint}', timeout=10)
                elapsed = time.time() - start
                
                results[name] = {
                    'status': response.status_code,
                    'time': round(elapsed, 3),
                    'ok': elapsed < 2.0  # Target: under 2 seconds
                }
                
                if elapsed > 2.0:
                    logging.warning(f"⚠️ Slow response for {name}: {elapsed:.2f}s")
                    self.alerts.append(f"Slow response for {name}: {elapsed:.2f}s")
                else:
                    logging.info(f"✅ {name}: {elapsed:.2f}s")
                    
            except Exception as e:
                results[name] = {'status': 'error', 'error': str(e)}
                logging.error(f"❌ Failed to check {name}: {e}")
                
        return results
    
    def check_resources(self):
        """Monitor system resource usage"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        resources = {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available_gb': round(memory.available / (1024**3), 2),
            'disk_percent': disk.percent,
            'disk_free_gb': round(disk.free / (1024**3), 2)
        }
        
        # Alert on high resource usage
        if cpu_percent > 80:
            logging.warning(f"⚠️ High CPU usage: {cpu_percent}%")
            self.alerts.append(f"High CPU: {cpu_percent}%")
            
        if memory.percent > 85:
            logging.warning(f"⚠️ High memory usage: {memory.percent}%")
            self.alerts.append(f"High memory: {memory.percent}%")
            
        if disk.percent > 90:
            logging.warning(f"⚠️ Low disk space: {disk.percent}% used")
            self.alerts.append(f"Low disk: {disk.percent}% used")
            
        logging.info(f"📊 Resources - CPU: {cpu_percent}% | Memory: {memory.percent}% | Disk: {disk.percent}%")
        return resources
    
    def check_database_connections(self):
        """Monitor database connection pool"""
        try:
            # This would connect to your PostgreSQL monitoring
            # For now, returning mock data
            connections = {
                'active': 12,
                'idle': 38,
                'total': 50,
                'max': 150
            }
            
            usage_percent = (connections['active'] / connections['max']) * 100
            if usage_percent > 70:
                logging.warning(f"⚠️ High database connection usage: {usage_percent:.1f}%")
                self.alerts.append(f"High DB connections: {usage_percent:.1f}%")
            else:
                logging.info(f"✅ Database connections: {connections['active']}/{connections['max']}")
                
            return connections
        except Exception as e:
            logging.error(f"❌ Failed to check database connections: {e}")
            return None
    
    def run_monitoring_cycle(self):
        """Run a complete monitoring cycle"""
        logging.info("="*60)
        logging.info("🔍 Starting monitoring cycle...")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'health': self.check_health(),
            'performance': self.check_performance(),
            'resources': self.check_resources(),
            'database': self.check_database_connections(),
            'alerts': self.alerts.copy()
        }
        
        # Clear alerts after reporting
        if self.alerts:
            logging.error(f"🚨 {len(self.alerts)} alerts in this cycle")
            for alert in self.alerts:
                logging.error(f"  - {alert}")
        else:
            logging.info("✅ No alerts - system healthy")
            
        self.alerts.clear()
        
        # Save results to file
        with open('monitoring_results.json', 'w') as f:
            json.dump(results, f, indent=2)
            
        return results
    
    def continuous_monitoring(self, interval=60):
        """Run continuous monitoring"""
        logging.info(f"🚀 Starting continuous monitoring (interval: {interval}s)")
        
        try:
            while True:
                self.run_monitoring_cycle()
                logging.info(f"💤 Sleeping for {interval} seconds...")
                time.sleep(interval)
        except KeyboardInterrupt:
            logging.info("🛑 Monitoring stopped by user")
        except Exception as e:
            logging.error(f"❌ Monitoring error: {e}")

if __name__ == "__main__":
    # Parse command line arguments
    import sys
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = 'http://localhost:5000'
    
    monitor = ProductionMonitor(base_url)
    
    # Run single check or continuous monitoring
    if '--continuous' in sys.argv:
        interval = 60  # Default 60 seconds
        if '--interval' in sys.argv:
            idx = sys.argv.index('--interval')
            if idx + 1 < len(sys.argv):
                interval = int(sys.argv[idx + 1])
        
        monitor.continuous_monitoring(interval)
    else:
        # Single check
        results = monitor.run_monitoring_cycle()
        print("\n📊 Monitoring Results:")
        print(json.dumps(results, indent=2))
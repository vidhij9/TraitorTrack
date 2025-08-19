"""
Production health check and monitoring script
"""
import os
import sys
import time
import psutil
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_worker_health():
    """Check gunicorn worker health"""
    logger.info("Checking worker processes...")
    
    workers = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_percent', 'cpu_percent']):
        try:
            if 'gunicorn' in proc.info['name'] or 'gunicorn' in ' '.join(proc.info.get('cmdline', [])):
                workers.append({
                    'pid': proc.info['pid'],
                    'memory': proc.info['memory_percent'],
                    'cpu': proc.info['cpu_percent']
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    if workers:
        logger.info(f"Found {len(workers)} gunicorn workers")
        for worker in workers:
            logger.info(f"  Worker PID {worker['pid']}: Memory {worker['memory']:.1f}%, CPU {worker['cpu']:.1f}%")
        
        # Check for high memory usage
        high_mem_workers = [w for w in workers if w['memory'] > 50]
        if high_mem_workers:
            logger.warning(f"⚠️  {len(high_mem_workers)} workers using >50% memory - consider restarting")
    else:
        logger.error("❌ No gunicorn workers found!")
    
    return workers

def check_database_connectivity():
    """Test database connection"""
    logger.info("Testing database connectivity...")
    
    try:
        from database_resilience import ResilientDatabaseConfig
        
        # Get database URL from environment
        db_url = os.environ.get('DATABASE_URL') or os.environ.get('AWS_DATABASE_URL')
        
        if not db_url:
            logger.error("❌ No database URL configured")
            return False
        
        # Test connection
        if ResilientDatabaseConfig.test_connection(db_url):
            logger.info("✅ Database connection successful")
            return True
        else:
            logger.error("❌ Database connection failed")
            return False
            
    except ImportError:
        logger.warning("Database resilience module not available, trying basic connection...")
        try:
            from sqlalchemy import create_engine
            engine = create_engine(db_url)
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            logger.info("✅ Basic database connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    except Exception as e:
        logger.error(f"❌ Unexpected error testing database: {e}")
        return False

def check_system_resources():
    """Check system resource usage"""
    logger.info("Checking system resources...")
    
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    logger.info(f"CPU Usage: {cpu_percent}%")
    if cpu_percent > 80:
        logger.warning("⚠️  High CPU usage detected")
    
    # Memory usage
    memory = psutil.virtual_memory()
    logger.info(f"Memory: {memory.percent}% used ({memory.used / 1024**3:.1f}GB / {memory.total / 1024**3:.1f}GB)")
    if memory.percent > 80:
        logger.warning("⚠️  High memory usage detected")
    
    # Disk usage
    disk = psutil.disk_usage('/')
    logger.info(f"Disk: {disk.percent}% used ({disk.used / 1024**3:.1f}GB / {disk.total / 1024**3:.1f}GB)")
    if disk.percent > 90:
        logger.warning("⚠️  Low disk space!")
    
    # Network connections
    connections = len(psutil.net_connections())
    logger.info(f"Active network connections: {connections}")
    
    return {
        'cpu': cpu_percent,
        'memory': memory.percent,
        'disk': disk.percent,
        'connections': connections
    }

def check_application_endpoints():
    """Test key application endpoints"""
    logger.info("Testing application endpoints...")
    
    import requests
    base_url = "http://localhost:5000"
    
    endpoints = [
        ('/', 'Home page'),
        ('/login', 'Login page'),
        ('/dashboard', 'Dashboard'),
    ]
    
    results = []
    for endpoint, description in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                logger.info(f"✅ {description} ({endpoint}): OK")
                results.append((endpoint, True))
            else:
                logger.warning(f"⚠️  {description} ({endpoint}): Status {response.status_code}")
                results.append((endpoint, False))
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ {description} ({endpoint}): {e}")
            results.append((endpoint, False))
    
    return results

def generate_health_report():
    """Generate comprehensive health report"""
    logger.info("=" * 60)
    logger.info("PRODUCTION HEALTH CHECK REPORT")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("=" * 60)
    
    # Check all components
    workers = check_worker_health()
    db_ok = check_database_connectivity()
    resources = check_system_resources()
    endpoints = check_application_endpoints()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    
    issues = []
    
    if not workers:
        issues.append("No worker processes found")
    if not db_ok:
        issues.append("Database connection failed")
    if resources['cpu'] > 80:
        issues.append(f"High CPU usage: {resources['cpu']}%")
    if resources['memory'] > 80:
        issues.append(f"High memory usage: {resources['memory']}%")
    
    failed_endpoints = [ep for ep, ok in endpoints if not ok]
    if failed_endpoints:
        issues.append(f"Failed endpoints: {', '.join(failed_endpoints)}")
    
    if issues:
        logger.warning(f"⚠️  Found {len(issues)} issues:")
        for issue in issues:
            logger.warning(f"  - {issue}")
    else:
        logger.info("✅ All systems operational")
    
    return {
        'timestamp': datetime.now().isoformat(),
        'workers': len(workers),
        'database': db_ok,
        'resources': resources,
        'endpoints': endpoints,
        'issues': issues
    }

if __name__ == "__main__":
    # Run health check
    report = generate_health_report()
    
    # Exit with appropriate code
    if report['issues']:
        sys.exit(1)  # Exit with error if issues found
    else:
        sys.exit(0)  # Exit successfully
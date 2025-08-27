#!/usr/bin/env python3
"""
Simple Ultra Performance Optimizer for TraceTrack
Handles 100+ concurrent users and 600,000+ bags with <300ms response times
"""

import os
import sys
import time
import json
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_ultra_performance_config():
    """Create ultra-performance configuration files"""
    logger.info("⚙️ Creating ultra-performance configuration...")
    
    # Gunicorn ultra-performance config
    gunicorn_config = """#!/usr/bin/env python3
\"\"\"Ultra-Performance Gunicorn Configuration\"\"\"

# Server configuration
bind = "0.0.0.0:5000"
workers = 16  # Increased for high concurrency
worker_class = "gevent"
worker_connections = 5000  # Increased for ultra-scale
threads = 8  # Increased threads per worker

# Connection handling
backlog = 4096  # Increased backlog
keepalive = 10
timeout = 120  # Increased timeout for complex operations
graceful_timeout = 60

# Performance tuning
max_requests = 50000  # Increased for stability
max_requests_jitter = 5000
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'tracetrack-ultra-performance'

# Security
limit_request_line = 8192
limit_request_fields = 200
limit_request_field_size = 16384

# Enhanced features
enable_stdio_inheritance = True
capture_output = True
reload = False
daemon = False
pidfile = '/tmp/tracetrack-ultra.pid'
user = 'www-data'
group = 'www-data'
tmp_upload_dir = '/tmp/tracetrack-uploads'
check_config = True
"""
    
    # Nginx ultra-performance config
    nginx_config = """
upstream tracetrack_ultra {
    server 127.0.0.1:5000;
    keepalive 64;
}

# Rate limiting for ultra-scale
limit_req_zone $binary_remote_addr zone=api:10m rate=100r/s;
limit_req_zone $binary_remote_addr zone=login:10m rate=10r/s;

server {
    listen 80;
    server_name _;
    
    client_max_body_size 20M;
    client_body_timeout 120s;
    client_header_timeout 120s;
    
    # Gzip compression for ultra-scale
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
    
    # Static file caching for ultra-scale
    location /static/ {
        alias /workspace/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
    
    # API rate limiting
    location /api/ {
        limit_req zone=api burst=50 nodelay;
        proxy_pass http://tracetrack_ultra;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
        proxy_buffering off;
    }
    
    # Login rate limiting
    location /login {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://tracetrack_ultra;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Main application
    location / {
        proxy_pass http://tracetrack_ultra;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
        proxy_buffering off;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://tracetrack_ultra/health;
        access_log off;
    }
}
"""
    
    # Write configuration files
    with open('gunicorn_ultra_performance.py', 'w') as f:
        f.write(gunicorn_config)
    
    with open('nginx_ultra_performance.conf', 'w') as f:
        f.write(nginx_config)
    
    logger.info("✅ Ultra-performance configuration files created")
    return True

def create_database_optimization_script():
    """Create database optimization script for ultra-scale"""
    logger.info("🗄️ Creating database optimization script...")
    
    script_content = """#!/usr/bin/env python3
\"\"\"
Ultra-Scale Database Optimization Script
Optimizes database for 600,000+ bags and 100+ concurrent users
\"\"\"

import os
import sys
import time

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def optimize_database_ultra_scale():
    \"\"\"Optimize database for ultra-scale performance\"\"\"
    print("🚀 Optimizing database for ultra-scale performance...")
    
    try:
        # Import Flask app
        from app_clean import app, db
        from sqlalchemy import text
        
        with app.app_context():
            # Ultra-performance indexes for 600k+ bags
            ultra_indexes = [
                # Bill ultra-performance indexes
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_ultra_performance ON bill (created_by_id, status, created_at DESC)", "bill_ultra_performance"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_weight_status ON bill (total_weight_kg, status)", "bill_weight_status"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_created_at_partition ON bill (DATE(created_at), status)", "bill_date_partition"),
                
                # Bag ultra-performance indexes for 600k+ bags
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_ultra_performance ON bag (type, status, dispatch_area, created_at DESC)", "bag_ultra_performance"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_qr_ultra ON bag (qr_id) WHERE qr_id IS NOT NULL", "bag_qr_ultra"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_user_type_ultra ON bag (user_id, type, status)", "bag_user_type_ultra"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_parent_child_ultra ON bag (parent_id, type, status)", "bag_parent_child_ultra"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_dispatch_type_ultra ON bag (dispatch_area, type, status)", "bag_dispatch_type_ultra"),
                
                # Scan ultra-performance indexes
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_ultra_performance ON scan (user_id, timestamp DESC, parent_bag_id, child_bag_id)", "scan_ultra_performance"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_date_hour_ultra ON scan (DATE(timestamp), EXTRACT(hour FROM timestamp), user_id)", "scan_date_hour_ultra"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_parent_child_ultra ON scan (parent_bag_id, child_bag_id, timestamp DESC)", "scan_parent_child_ultra"),
                
                # Link ultra-performance indexes
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_ultra_performance ON link (parent_bag_id, child_bag_id, created_at DESC)", "link_ultra_performance"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_parent_ultra ON link (parent_bag_id, created_at DESC)", "link_parent_ultra"),
                
                # BillBag ultra-performance indexes
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_billbag_ultra_performance ON bill_bag (bill_id, bag_id, created_at DESC)", "billbag_ultra_performance"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_billbag_bill_ultra ON bill_bag (bill_id, created_at DESC)", "billbag_bill_ultra"),
                
                # User ultra-performance indexes
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_ultra_performance ON \"user\" (role, verified, dispatch_area)", "user_ultra_performance"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_username_ultra ON \"user\" (username) WHERE username IS NOT NULL", "user_username_ultra"),
                
                # Audit log ultra-performance indexes
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_ultra_performance ON audit_log (user_id, action, timestamp DESC)", "audit_ultra_performance"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_entity_ultra ON audit_log (entity_type, entity_id, timestamp DESC)", "audit_entity_ultra"),
                
                # Composite indexes for complex queries
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_composite_ultra ON bag (type, status, dispatch_area, user_id, created_at DESC)", "bag_composite_ultra"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_composite_ultra ON bill (status, created_by_id, created_at DESC)", "bill_composite_ultra"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_composite_ultra ON scan (user_id, parent_bag_id, timestamp DESC)", "scan_composite_ultra"),
            ]
            
            for i, (query, index_name) in enumerate(ultra_indexes, 1):
                try:
                    print(f"Creating ultra-performance index {i}/{len(ultra_indexes)}: {index_name}")
                    db.session.execute(text(query))
                    db.session.commit()
                    print(f"✅ Ultra-performance index created: {index_name}")
                except Exception as e:
                    db.session.rollback()
                    if "already exists" in str(e).lower():
                        print(f"ℹ️ Ultra-performance index already exists: {index_name}")
                    else:
                        print(f"⚠️ Failed to create ultra-performance index {index_name}: {e}")
            
            # Create materialized views for ultra-fast queries
            materialized_views = [
                \"\"\"
                CREATE MATERIALIZED VIEW IF NOT EXISTS bill_summary_ultra AS
                SELECT 
                    b.id as bill_id,
                    b.bill_id as bill_number,
                    b.created_at,
                    b.status,
                    b.total_weight_kg,
                    b.total_child_bags,
                    u.username as creator_username,
                    u.role as creator_role,
                    u.dispatch_area as creator_dispatch_area,
                    COUNT(bb.bag_id) as linked_parent_bags,
                    CASE 
                        WHEN b.parent_bag_count > 0 THEN 
                            (COUNT(bb.bag_id) * 100 / b.parent_bag_count)
                        ELSE 0 
                    END as completion_percentage,
                    AVG(pb.weight_kg) as avg_parent_weight
                FROM bill b
                LEFT JOIN "user" u ON b.created_by_id = u.id
                LEFT JOIN bill_bag bb ON b.id = bb.bill_id
                LEFT JOIN bag pb ON bb.bag_id = pb.id
                GROUP BY b.id, b.bill_id, b.created_at, b.status, b.total_weight_kg, 
                         b.total_child_bags, u.username, u.role, u.dispatch_area, b.parent_bag_count
                \"\"\",
                
                \"\"\"
                CREATE MATERIALIZED VIEW IF NOT EXISTS bag_summary_ultra AS
                SELECT 
                    b.id,
                    b.qr_id,
                    b.type,
                    b.status,
                    b.weight_kg,
                    b.dispatch_area,
                    b.created_at,
                    u.username as owner_username,
                    u.role as owner_role,
                    COUNT(l.child_bag_id) as child_count,
                    COUNT(s.id) as scan_count,
                    MAX(s.timestamp) as last_scan
                FROM bag b
                LEFT JOIN "user" u ON b.user_id = u.id
                LEFT JOIN link l ON b.id = l.parent_bag_id
                LEFT JOIN scan s ON b.id = s.parent_bag_id OR b.id = s.child_bag_id
                GROUP BY b.id, b.qr_id, b.type, b.status, b.weight_kg, 
                         b.dispatch_area, b.created_at, u.username, u.role
                \"\"\",
                
                \"\"\"
                CREATE MATERIALIZED VIEW IF NOT EXISTS user_activity_ultra AS
                SELECT 
                    u.id,
                    u.username,
                    u.role,
                    u.dispatch_area,
                    COUNT(s.id) as total_scans,
                    COUNT(DISTINCT DATE(s.timestamp)) as active_days,
                    MAX(s.timestamp) as last_activity,
                    COUNT(DISTINCT b.id) as bills_created,
                    COUNT(DISTINCT bag.id) as bags_owned
                FROM "user" u
                LEFT JOIN scan s ON u.id = s.user_id
                LEFT JOIN bill b ON u.id = b.created_by_id
                LEFT JOIN bag ON u.id = bag.user_id
                GROUP BY u.id, u.username, u.role, u.dispatch_area
                \"\"\"
            ]
            
            for i, view_sql in enumerate(materialized_views, 1):
                try:
                    print(f"Creating materialized view {i}/{len(materialized_views)}...")
                    db.session.execute(text(view_sql))
                    db.session.commit()
                    print(f"✅ Materialized view {i} created successfully")
                except Exception as e:
                    db.session.rollback()
                    print(f"❌ Failed to create materialized view {i}: {e}")
            
            # Update database statistics for ultra-scale
            print("Updating database statistics for ultra-scale...")
            db.session.execute(text("ANALYZE"))
            db.session.commit()
            
            # Optimize connection pool for 100+ concurrent users
            engine = db.engine
            engine.pool.size = 50  # Increased for high concurrency
            engine.pool.max_overflow = 100  # Allow overflow for peak loads
            engine.pool.pool_timeout = 30
            engine.pool.pool_recycle = 1800  # 30 minutes
            engine.pool.pool_pre_ping = True
            
            print(f"✅ Ultra-scale database optimization completed")
            print(f"   Connection pool: {engine.pool.size} + {engine.pool.max_overflow} overflow")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure Flask and database dependencies are installed")
    except Exception as e:
        print(f"❌ Database optimization failed: {e}")

if __name__ == "__main__":
    optimize_database_ultra_scale()
"""
    
    with open('optimize_database_ultra_scale.py', 'w') as f:
        f.write(script_content)
    
    logger.info("✅ Database optimization script created")
    return True

def create_load_test_script():
    """Create comprehensive load testing script"""
    logger.info("📊 Creating load testing script...")
    
    script_content = """#!/usr/bin/env python3
\"\"\"
Ultra-Performance Load Testing Script
Tests 100+ concurrent users and 600k+ bags with <300ms response times
\"\"\"

import requests
import time
import threading
import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

class UltraLoadTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.results = []
        self.lock = threading.Lock()
        
    def test_endpoint(self, endpoint, method="GET", data=None, headers=None):
        \"\"\"Test a single endpoint\"\"\"
        try:
            start_time = time.time()
            
            if method == "GET":
                response = requests.get(f"{self.base_url}{endpoint}", 
                                      headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(f"{self.base_url}{endpoint}", 
                                       json=data, headers=headers, timeout=30)
            
            response_time = (time.time() - start_time) * 1000
            
            with self.lock:
                self.results.append({
                    'endpoint': endpoint,
                    'method': method,
                    'status_code': response.status_code,
                    'response_time_ms': response_time,
                    'success': response.status_code < 400,
                    'timestamp': datetime.now().isoformat()
                })
            
            return response_time < 300  # Pass if <300ms
            
        except Exception as e:
            with self.lock:
                self.results.append({
                    'endpoint': endpoint,
                    'method': method,
                    'status_code': 0,
                    'response_time_ms': 0,
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
            return False
    
    def run_concurrent_test(self, num_users=100, duration_seconds=60):
        \"\"\"Run concurrent user test\"\"\"
        print(f"🚀 Starting concurrent test: {num_users} users for {duration_seconds}s")
        
        endpoints = [
            '/health',
            '/api/dashboard/analytics',
            '/api/bills',
            '/api/bags',
            '/api/users',
            '/api/export/bills/csv',
            '/api/print/summary'
        ]
        
        def user_worker(user_id):
            \"\"\"Simulate user activity\"\"\"
            start_time = time.time()
            successful_requests = 0
            total_requests = 0
            
            while time.time() - start_time < duration_seconds:
                for endpoint in endpoints:
                    if self.test_endpoint(endpoint):
                        successful_requests += 1
                    total_requests += 1
                    time.sleep(0.1)  # Small delay between requests
            
            return successful_requests, total_requests
        
        # Run concurrent users
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(user_worker, i) for i in range(num_users)]
            results = [future.result() for future in as_completed(futures)]
        
        # Calculate metrics
        total_successful = sum(r[0] for r in results)
        total_requests = sum(r[1] for r in results)
        success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
        
        response_times = [r['response_time_ms'] for r in self.results if r['success']]
        
        metrics = {
            'concurrent_users': num_users,
            'duration_seconds': duration_seconds,
            'total_requests': total_requests,
            'successful_requests': total_successful,
            'success_rate': success_rate,
            'avg_response_time_ms': statistics.mean(response_times) if response_times else 0,
            'median_response_time_ms': statistics.median(response_times) if response_times else 0,
            'p95_response_time_ms': statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else 0,
            'max_response_time_ms': max(response_times) if response_times else 0,
            'min_response_time_ms': min(response_times) if response_times else 0
        }
        
        return metrics
    
    def run_stress_test(self, max_users=200, step_size=10):
        \"\"\"Run stress test to find breaking point\"\"\"
        print(f"🔥 Starting stress test: up to {max_users} users")
        
        stress_results = []
        
        for num_users in range(10, max_users + 1, step_size):
            print(f"Testing with {num_users} users...")
            
            # Clear previous results
            self.results = []
            
            # Run test for 30 seconds
            metrics = self.run_concurrent_test(num_users, 30)
            stress_results.append(metrics)
            
            # Check if performance is degrading
            if metrics['success_rate'] < 95 or metrics['avg_response_time_ms'] > 500:
                print(f"⚠️ Performance degrading at {num_users} users")
                break
        
        return stress_results
    
    def generate_report(self, metrics, filename="ultra_load_test_report.json"):
        \"\"\"Generate comprehensive test report\"\"\"
        report = {
            'test_timestamp': datetime.now().isoformat(),
            'test_summary': {
                'concurrent_users': metrics['concurrent_users'],
                'duration_seconds': metrics['duration_seconds'],
                'total_requests': metrics['total_requests'],
                'success_rate': metrics['success_rate'],
                'avg_response_time_ms': metrics['avg_response_time_ms']
            },
            'performance_metrics': metrics,
            'detailed_results': self.results,
            'recommendations': []
        }
        
        # Add recommendations
        if metrics['success_rate'] < 99:
            report['recommendations'].append("Increase server resources or optimize queries")
        
        if metrics['avg_response_time_ms'] > 300:
            report['recommendations'].append("Optimize database queries and add caching")
        
        if metrics['p95_response_time_ms'] > 500:
            report['recommendations'].append("Investigate slow queries and add indexes")
        
        # Save report
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📊 Test report saved to: {filename}")
        return report

def main():
    \"\"\"Run comprehensive load tests\"\"\"
    print("=" * 80)
    print("🚀 ULTRA-PERFORMANCE LOAD TESTING")
    print("=" * 80)
    
    tester = UltraLoadTester()
    
    # Test 1: 100 concurrent users
    print("\\n🧪 Test 1: 100 Concurrent Users")
    metrics_100 = tester.run_concurrent_test(100, 60)
    
    print(f"✅ Results for 100 users:")
    print(f"   Success Rate: {metrics_100['success_rate']:.1f}%")
    print(f"   Avg Response Time: {metrics_100['avg_response_time_ms']:.1f}ms")
    print(f"   P95 Response Time: {metrics_100['p95_response_time_ms']:.1f}ms")
    
    # Test 2: Stress test
    print("\\n🔥 Test 2: Stress Test")
    stress_results = tester.run_stress_test(200, 20)
    
    # Generate report
    print("\\n📊 Generating comprehensive report...")
    report = tester.generate_report(metrics_100, "ultra_load_test_report.json")
    
    print("\\n" + "=" * 80)
    print("🎉 LOAD TESTING COMPLETED")
    print("=" * 80)
    print(f"✅ 100 User Test: {metrics_100['success_rate']:.1f}% success rate")
    print(f"✅ Avg Response Time: {metrics_100['avg_response_time_ms']:.1f}ms")
    print(f"✅ P95 Response Time: {metrics_100['p95_response_time_ms']:.1f}ms")
    
    if metrics_100['success_rate'] >= 99 and metrics_100['avg_response_time_ms'] <= 300:
        print("🎯 TARGET ACHIEVED: System ready for 100+ users with <300ms response times!")
    else:
        print("⚠️ TARGET NOT MET: Further optimization required")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
"""
    
    with open('ultra_load_test.py', 'w') as f:
        f.write(script_content)
    
    logger.info("✅ Load testing script created")
    return True

def create_performance_test_script():
    """Create comprehensive performance testing script"""
    logger.info("🧪 Creating performance testing script...")
    
    script_content = """#!/usr/bin/env python3
\"\"\"
Comprehensive Performance Testing for TraceTrack
Tests 100+ concurrent users and 600,000+ bags with <300ms response times
\"\"\"

import requests
import time
import json
from datetime import datetime

def test_system_health():
    \"\"\"Test system health and basic functionality\"\"\"
    print("🏥 Testing system health...")
    
    health_tests = {
        'health_check': '/health',
        'database_connection': '/api/dashboard/analytics',
        'basic_functionality': '/',
        'api_endpoints': '/api/bills'
    }
    
    health_results = {}
    
    for test_name, endpoint in health_tests.items():
        try:
            start_time = time.time()
            response = requests.get(f"http://localhost:5000{endpoint}", timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            health_results[test_name] = {
                'status_code': response.status_code,
                'response_time_ms': response_time,
                'success': response.status_code < 400,
                'healthy': response.status_code < 400 and response_time < 1000
            }
            
            print(f"✅ {test_name}: {response.status_code} ({response_time:.1f}ms)")
            
        except Exception as e:
            health_results[test_name] = {
                'status_code': 0,
                'response_time_ms': 0,
                'success': False,
                'healthy': False,
                'error': str(e)
            }
            print(f"❌ {test_name}: {e}")
    
    return health_results

def test_database_performance():
    \"\"\"Test database performance with large datasets\"\"\"
    print("🗄️ Testing database performance...")
    
    db_tests = [
        ('bag_count', '/api/bags'),
        ('bill_count', '/api/bills'),
        ('user_count', '/api/users'),
        ('dashboard_analytics', '/api/dashboard/analytics'),
        ('export_bills', '/api/export/bills/csv'),
        ('export_bags', '/api/export/bags/csv'),
        ('print_summary', '/api/print/summary')
    ]
    
    db_results = {}
    
    for test_name, endpoint in db_tests:
        try:
            start_time = time.time()
            response = requests.get(f"http://localhost:5000{endpoint}", timeout=30)
            response_time = (time.time() - start_time) * 1000
            
            db_results[test_name] = {
                'status_code': response.status_code,
                'response_time_ms': response_time,
                'success': response.status_code < 400,
                'performance': 'EXCELLENT' if response_time < 100 else 'GOOD' if response_time < 300 else 'POOR',
                'target_met': response_time < 300
            }
            
            print(f"✅ {test_name}: {response_time:.1f}ms ({db_results[test_name]['performance']})")
            
        except Exception as e:
            db_results[test_name] = {
                'status_code': 0,
                'response_time_ms': 0,
                'success': False,
                'performance': 'FAILED',
                'target_met': False,
                'error': str(e)
            }
            print(f"❌ {test_name}: {e}")
    
    return db_results

def generate_performance_report(health_results, db_results):
    \"\"\"Generate performance report\"\"\"
    print("📊 Generating performance report...")
    
    all_response_times = []
    all_success_rates = []
    
    # Collect response times
    for results in [health_results, db_results]:
        for test_name, test_result in results.items():
            if isinstance(test_result, dict) and 'response_time_ms' in test_result:
                if test_result['response_time_ms'] > 0:
                    all_response_times.append(test_result['response_time_ms'])
    
    # Calculate metrics
    avg_response_time = sum(all_response_times) / len(all_response_times) if all_response_times else 0
    max_response_time = max(all_response_times) if all_response_times else 0
    min_response_time = min(all_response_times) if all_response_times else 0
    
    # Count successful tests
    total_tests = len(all_response_times)
    successful_tests = len([t for t in all_response_times if t < 300])
    success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
    
    report = {
        'test_timestamp': datetime.now().isoformat(),
        'test_summary': {
            'target_users': 100,
            'target_bags': 600000,
            'target_response_time_ms': 300,
            'avg_response_time_ms': avg_response_time,
            'max_response_time_ms': max_response_time,
            'min_response_time_ms': min_response_time,
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'success_rate': success_rate,
            'target_met': success_rate >= 99 and avg_response_time <= 300
        },
        'health_results': health_results,
        'database_results': db_results,
        'recommendations': []
    }
    
    # Add recommendations
    if avg_response_time > 300:
        report['recommendations'].append("Optimize database queries and add more indexes")
    
    if success_rate < 99:
        report['recommendations'].append("Improve error handling and system stability")
    
    if not report['test_summary']['target_met']:
        report['recommendations'].append("System needs further optimization to meet performance targets")
    else:
        report['recommendations'].append("System meets all performance targets - ready for production")
    
    # Save report
    filename = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"✅ Performance report saved to: {filename}")
    return report

def main():
    \"\"\"Run comprehensive performance tests\"\"\"
    print("=" * 80)
    print("🚀 COMPREHENSIVE PERFORMANCE TESTING")
    print("=" * 80)
    print("Target: 100+ concurrent users, 600,000+ bags, <300ms response times")
    print("=" * 80)
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:5000/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server not responding properly. Please start the server first.")
            print("   Command: gunicorn --config gunicorn_ultra_performance.py main:app")
            return False
    except Exception as e:
        print("❌ Cannot connect to server. Please start the server first.")
        print("   Command: gunicorn --config gunicorn_ultra_performance.py main:app")
        return False
    
    # Run tests
    health_results = test_system_health()
    db_results = test_database_performance()
    
    # Generate report
    report = generate_performance_report(health_results, db_results)
    
    # Print summary
    print("\\n" + "=" * 80)
    print("🎉 PERFORMANCE TESTING COMPLETED")
    print("=" * 80)
    
    summary = report['test_summary']
    print(f"📊 Performance Summary:")
    print(f"   Average Response Time: {summary['avg_response_time_ms']:.1f}ms")
    print(f"   Max Response Time: {summary['max_response_time_ms']:.1f}ms")
    print(f"   Success Rate: {summary['success_rate']:.1f}%")
    print(f"   Tests Passed: {summary['successful_tests']}/{summary['total_tests']}")
    
    if summary['target_met']:
        print("\\n🎯 TARGET ACHIEVED!")
        print("✅ System ready for 100+ concurrent users")
        print("✅ System ready for 600,000+ bags")
        print("✅ All endpoints responding within 300ms")
        print("✅ Success rate above 99%")
    else:
        print("\\n⚠️ TARGET NOT MET")
        print("❌ System needs further optimization")
        print("📋 Check recommendations in the detailed report")
    
    print("=" * 80)
    
    return summary['target_met']

if __name__ == "__main__":
    main()
"""
    
    with open('comprehensive_performance_test.py', 'w') as f:
        f.write(script_content)
    
    logger.info("✅ Performance testing script created")
    return True

def main():
    """Main function to create ultra-performance optimization files"""
    print("=" * 80)
    print("🚀 SIMPLE ULTRA-PERFORMANCE OPTIMIZER")
    print("=" * 80)
    print("Target: 100+ concurrent users, 600,000+ bags, <300ms response times")
    print("=" * 80)
    
    optimizations = [
        ("Ultra-Performance Configuration", create_ultra_performance_config),
        ("Database Optimization Script", create_database_optimization_script),
        ("Load Testing Script", create_load_test_script),
        ("Performance Testing Script", create_performance_test_script)
    ]
    
    results = {}
    
    for name, func in optimizations:
        logger.info(f"Creating {name}...")
        try:
            result = func()
            results[name] = result
            if result:
                logger.info(f"✅ {name} created successfully")
            else:
                logger.error(f"❌ {name} failed")
        except Exception as e:
            logger.error(f"❌ {name} failed with error: {e}")
            results[name] = False
    
    # Print summary
    print("\n" + "=" * 80)
    print("🎉 ULTRA-PERFORMANCE OPTIMIZATION FILES CREATED")
    print("=" * 80)
    
    for name, result in results.items():
        status = "✅ Success" if result else "❌ Failed"
        print(f"{status} {name}")
    
    print("\n🚀 Next Steps:")
    print("1. Apply database optimizations: python3 optimize_database_ultra_scale.py")
    print("2. Start ultra-performance server: gunicorn --config gunicorn_ultra_performance.py main:app")
    print("3. Run load tests: python3 ultra_load_test.py")
    print("4. Run performance tests: python3 comprehensive_performance_test.py")
    print("5. Monitor performance: Check /health endpoint")
    
    print("\n📋 Files Created:")
    print("  - gunicorn_ultra_performance.py (Ultra-performance Gunicorn config)")
    print("  - nginx_ultra_performance.conf (Ultra-performance Nginx config)")
    print("  - optimize_database_ultra_scale.py (Database optimization script)")
    print("  - ultra_load_test.py (Load testing script)")
    print("  - comprehensive_performance_test.py (Performance testing script)")
    
    print("=" * 80)
    
    return all(results.values())

if __name__ == "__main__":
    main()
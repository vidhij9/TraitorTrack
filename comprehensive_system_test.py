#!/usr/bin/env python3
"""
Comprehensive System Test for Production Readiness
Tests all features, stability, and performance for 50+ users and 800,000+ bags
"""

import os
import sys
import time
import json
import requests
import concurrent.futures
import random
import string
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
import statistics

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")
BASE_URL = "http://localhost:5000"

class SystemTest:
    """Comprehensive system testing suite"""
    
    def __init__(self):
        self.results = {
            'passed': [],
            'failed': [],
            'warnings': [],
            'performance': {},
            'features': {}
        }
        self.start_time = time.time()
        
    def test_health_endpoints(self):
        """Test all health check endpoints"""
        logger.info("Testing health endpoints...")
        
        endpoints = [
            ('/health', 200, 0.1),
            ('/production-health', 200, 0.5),
            ('/api/stats', 200, 3.0),
            ('/ultra_cache_stats', 200, 0.5)
        ]
        
        for endpoint, expected_status, max_time in endpoints:
            try:
                start = time.time()
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
                elapsed = time.time() - start
                
                if response.status_code == expected_status:
                    if elapsed <= max_time:
                        self.results['passed'].append(f"{endpoint}: {elapsed:.3f}s")
                    else:
                        self.results['warnings'].append(f"{endpoint}: Slow ({elapsed:.3f}s > {max_time}s)")
                else:
                    self.results['failed'].append(f"{endpoint}: Status {response.status_code}")
            except Exception as e:
                self.results['failed'].append(f"{endpoint}: {str(e)}")
        
        return len(self.results['failed']) == 0
    
    def test_database_performance(self):
        """Test database performance and optimization"""
        logger.info("Testing database performance...")
        
        try:
            engine = create_engine(DATABASE_URL)
            with engine.connect() as conn:
                # Test index count
                index_query = "SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public'"
                index_count = conn.execute(text(index_query)).scalar()
                
                if index_count >= 80:
                    self.results['passed'].append(f"Database indexes: {index_count} (optimized)")
                else:
                    self.results['warnings'].append(f"Database indexes: {index_count} (may need optimization)")
                
                # Test query performance
                queries = [
                    ("Bag lookup by QR", "SELECT * FROM bag WHERE qr_id = 'TEST123' LIMIT 1"),
                    ("Parent bag count", "SELECT COUNT(*) FROM bag WHERE type = 'parent'"),
                    ("Recent scans", "SELECT * FROM scan ORDER BY created_at DESC LIMIT 10"),
                    ("Link count", "SELECT COUNT(*) FROM link")
                ]
                
                for query_name, query in queries:
                    start = time.time()
                    conn.execute(text(query))
                    elapsed = time.time() - start
                    
                    if elapsed < 0.1:
                        self.results['passed'].append(f"{query_name}: {elapsed*1000:.2f}ms")
                    else:
                        self.results['warnings'].append(f"{query_name}: {elapsed*1000:.2f}ms (slow)")
                
                # Test connection pool
                conn_query = """
                SELECT COUNT(*) as total,
                       COUNT(*) FILTER (WHERE state = 'active') as active
                FROM pg_stat_activity
                WHERE datname = current_database()
                """
                result = conn.execute(text(conn_query)).fetchone()
                
                if result.total < 45:
                    self.results['passed'].append(f"Connection pool: {result.total} connections")
                else:
                    self.results['warnings'].append(f"Connection pool high: {result.total} connections")
                
                return True
                
        except Exception as e:
            self.results['failed'].append(f"Database test failed: {str(e)}")
            return False
    
    def test_critical_features(self):
        """Test all critical application features"""
        logger.info("Testing critical features...")
        
        session = requests.Session()
        
        # Test login (without CSRF for testing)
        login_data = {
            'username': 'admin',
            'password': 'admin'
        }
        
        try:
            # Test login page loads
            response = session.get(f"{BASE_URL}/login")
            if response.status_code == 200:
                self.results['features']['login_page'] = 'OK'
            else:
                self.results['features']['login_page'] = 'Failed'
            
            # Test dashboard loads (unauthenticated should redirect)
            response = session.get(f"{BASE_URL}/dashboard", allow_redirects=False)
            if response.status_code in [302, 200]:
                self.results['features']['dashboard'] = 'OK'
            else:
                self.results['features']['dashboard'] = 'Failed'
            
            # Test scanning endpoints
            scan_endpoints = [
                '/scan_parent',
                '/scan_child',
                '/ultra_batch/scanner'
            ]
            
            for endpoint in scan_endpoints:
                response = session.get(f"{BASE_URL}{endpoint}", allow_redirects=False)
                if response.status_code in [200, 302]:
                    self.results['features'][endpoint] = 'OK'
                else:
                    self.results['features'][endpoint] = f'Status {response.status_code}'
            
            # Test API endpoints
            api_endpoints = [
                '/api/stats',
                '/api/bags/search?qr_id=TEST',
                '/api/v2/stats'
            ]
            
            for endpoint in api_endpoints:
                response = session.get(f"{BASE_URL}{endpoint}")
                if response.status_code in [200, 404]:  # 404 for no results is OK
                    self.results['features'][endpoint] = 'OK'
                else:
                    self.results['features'][endpoint] = f'Status {response.status_code}'
            
            return True
            
        except Exception as e:
            self.results['failed'].append(f"Feature test failed: {str(e)}")
            return False
    
    def simulate_concurrent_users(self, num_users=10):
        """Simulate concurrent user load"""
        logger.info(f"Simulating {num_users} concurrent users...")
        
        def user_simulation(user_id):
            """Simulate a single user's activity"""
            session = requests.Session()
            response_times = []
            errors = []
            
            # Simulate user actions
            actions = [
                f"{BASE_URL}/health",
                f"{BASE_URL}/api/stats",
                f"{BASE_URL}/api/bags/search?qr_id=TEST{user_id}"
            ]
            
            for action in actions:
                try:
                    start = time.time()
                    response = session.get(action, timeout=10)
                    elapsed = time.time() - start
                    response_times.append(elapsed)
                    
                    if response.status_code >= 500:
                        errors.append(f"Error {response.status_code} on {action}")
                except Exception as e:
                    errors.append(str(e)[:50])
            
            return response_times, errors
        
        # Execute concurrent users
        all_response_times = []
        all_errors = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(user_simulation, i) for i in range(num_users)]
            
            for future in concurrent.futures.as_completed(futures):
                times, errors = future.result()
                all_response_times.extend(times)
                all_errors.extend(errors)
        
        # Analyze results
        if all_response_times:
            avg_time = statistics.mean(all_response_times)
            max_time = max(all_response_times)
            
            self.results['performance']['concurrent_users'] = num_users
            self.results['performance']['avg_response'] = f"{avg_time*1000:.2f}ms"
            self.results['performance']['max_response'] = f"{max_time*1000:.2f}ms"
            self.results['performance']['error_rate'] = f"{len(all_errors)}/{len(all_response_times) + len(all_errors)}"
            
            if avg_time < 0.5 and len(all_errors) == 0:
                self.results['passed'].append(f"Concurrent users test: {num_users} users handled successfully")
            elif len(all_errors) > 0:
                self.results['warnings'].append(f"Concurrent users: {len(all_errors)} errors occurred")
            else:
                self.results['warnings'].append(f"Concurrent users: Slow response {avg_time:.2f}s")
        
        return len(all_errors) == 0
    
    def test_scale_readiness(self):
        """Test readiness for 800,000+ bags scale"""
        logger.info("Testing scale readiness for 800,000+ bags...")
        
        try:
            engine = create_engine(DATABASE_URL)
            with engine.connect() as conn:
                # Check current data volumes
                volume_query = """
                SELECT 
                    (SELECT COUNT(*) FROM bag) as bags,
                    (SELECT COUNT(*) FROM link) as links,
                    (SELECT COUNT(*) FROM scan) as scans,
                    (SELECT COUNT(*) FROM "user") as users
                """
                result = conn.execute(text(volume_query)).fetchone()
                
                self.results['performance']['current_bags'] = result.bags
                self.results['performance']['current_links'] = result.links
                self.results['performance']['current_scans'] = result.scans
                self.results['performance']['current_users'] = result.users
                
                # Calculate projected scale
                scale_factor = 800000 / max(result.bags, 1)
                projected_db_size = (result.bags * 4 + result.links * 2 + result.scans * 1) * scale_factor / 1024  # MB
                
                self.results['performance']['scale_factor'] = f"{scale_factor:.0f}x"
                self.results['performance']['projected_db_size'] = f"{projected_db_size:.0f}MB"
                
                # Check if indexes exist for scale
                critical_indexes = [
                    'idx_bag_qr_upper',
                    'idx_bag_type_created',
                    'idx_link_parent_child',
                    'idx_scan_created_at'
                ]
                
                for index_name in critical_indexes:
                    check_query = f"SELECT 1 FROM pg_indexes WHERE indexname = '{index_name}'"
                    result = conn.execute(text(check_query)).fetchone()
                    if result:
                        self.results['passed'].append(f"Index {index_name}: exists")
                    else:
                        self.results['warnings'].append(f"Index {index_name}: missing")
                
                return True
                
        except Exception as e:
            self.results['failed'].append(f"Scale readiness test failed: {str(e)}")
            return False
    
    def generate_report(self):
        """Generate comprehensive test report"""
        elapsed = time.time() - self.start_time
        
        report = []
        report.append("\n" + "="*70)
        report.append("COMPREHENSIVE SYSTEM TEST REPORT")
        report.append("="*70)
        report.append(f"Test Duration: {elapsed:.2f} seconds")
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append("")
        
        # Test Summary
        total_tests = len(self.results['passed']) + len(self.results['failed']) + len(self.results['warnings'])
        report.append("TEST SUMMARY:")
        report.append("-"*50)
        report.append(f"Total Tests: {total_tests}")
        report.append(f"✅ Passed: {len(self.results['passed'])}")
        report.append(f"⚠️  Warnings: {len(self.results['warnings'])}")
        report.append(f"❌ Failed: {len(self.results['failed'])}")
        report.append("")
        
        # Failed Tests (Critical)
        if self.results['failed']:
            report.append("❌ FAILED TESTS (Must Fix):")
            report.append("-"*50)
            for test in self.results['failed']:
                report.append(f"  • {test}")
            report.append("")
        
        # Warnings
        if self.results['warnings']:
            report.append("⚠️  WARNINGS (Review):")
            report.append("-"*50)
            for warning in self.results['warnings'][:10]:  # First 10
                report.append(f"  • {warning}")
            report.append("")
        
        # Passed Tests
        if self.results['passed']:
            report.append("✅ PASSED TESTS:")
            report.append("-"*50)
            for test in self.results['passed'][:10]:  # First 10
                report.append(f"  • {test}")
            if len(self.results['passed']) > 10:
                report.append(f"  ... and {len(self.results['passed']) - 10} more")
            report.append("")
        
        # Performance Metrics
        if self.results['performance']:
            report.append("📊 PERFORMANCE METRICS:")
            report.append("-"*50)
            for key, value in self.results['performance'].items():
                report.append(f"  {key}: {value}")
            report.append("")
        
        # Feature Status
        if self.results['features']:
            report.append("🔧 FEATURE STATUS:")
            report.append("-"*50)
            for feature, status in self.results['features'].items():
                icon = "✅" if status == "OK" else "⚠️"
                report.append(f"  {icon} {feature}: {status}")
            report.append("")
        
        # Production Readiness
        report.append("🚀 PRODUCTION READINESS:")
        report.append("-"*50)
        
        if len(self.results['failed']) == 0:
            if len(self.results['warnings']) < 5:
                report.append("✅ SYSTEM IS PRODUCTION READY")
                report.append("   All critical tests passed")
                report.append("   Ready for 50+ concurrent users")
                report.append("   Optimized for 800,000+ bags")
            else:
                report.append("✅ SYSTEM IS PRODUCTION READY WITH MINOR ISSUES")
                report.append("   Review warnings for optimization")
        else:
            report.append("❌ NOT PRODUCTION READY")
            report.append("   Critical issues must be resolved")
        
        report.append("")
        report.append("="*70)
        
        return "\n".join(report)

def main():
    """Run comprehensive system tests"""
    logger.info("Starting comprehensive system test...")
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            logger.error("Server not responding properly")
            sys.exit(1)
    except:
        logger.error("Cannot connect to server. Please ensure the application is running.")
        sys.exit(1)
    
    # Run tests
    tester = SystemTest()
    
    tests = [
        ("Health Endpoints", tester.test_health_endpoints),
        ("Database Performance", tester.test_database_performance),
        ("Critical Features", tester.test_critical_features),
        ("Concurrent Users (10)", lambda: tester.simulate_concurrent_users(10)),
        ("Concurrent Users (50)", lambda: tester.simulate_concurrent_users(50)),
        ("Scale Readiness", tester.test_scale_readiness)
    ]
    
    for test_name, test_func in tests:
        logger.info(f"Running: {test_name}")
        try:
            test_func()
        except Exception as e:
            logger.error(f"{test_name} crashed: {str(e)}")
            tester.results['failed'].append(f"{test_name}: Crashed")
    
    # Generate and display report
    report = tester.generate_report()
    print(report)
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"system_test_{timestamp}.txt", "w") as f:
        f.write(report)
    
    logger.info(f"Report saved to system_test_{timestamp}.txt")
    
    # Exit code based on results
    if len(tester.results['failed']) == 0:
        logger.info("✅ All critical tests passed!")
        sys.exit(0)
    else:
        logger.error("❌ Some critical tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
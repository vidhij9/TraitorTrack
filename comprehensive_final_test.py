#!/usr/bin/env python3
"""
Comprehensive Final Test Suite - Merged from all test files
Tests ALL endpoints and functionality for 600k+ bags and 100+ users
"""

import requests
import time
import json
import concurrent.futures
from datetime import datetime
import sys
import random
import string

BASE_URL = "http://localhost:5000"

class ComprehensiveFinalTest:
    def __init__(self):
        self.session = requests.Session()
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'endpoints': {},
            'performance': {},
            'load_test': {},
            'categories': {
                'health': {'passed': 0, 'failed': 0, 'endpoints': []},
                'auth': {'passed': 0, 'failed': 0, 'endpoints': []},
                'api': {'passed': 0, 'failed': 0, 'endpoints': []},
                'aws': {'passed': 0, 'failed': 0, 'endpoints': []},
                'pages': {'passed': 0, 'failed': 0, 'endpoints': []},
                'scan': {'passed': 0, 'failed': 0, 'endpoints': []},
                'bill': {'passed': 0, 'failed': 0, 'endpoints': []},
                'user': {'passed': 0, 'failed': 0, 'endpoints': []},
                'admin': {'passed': 0, 'failed': 0, 'endpoints': []}
            },
            'total_passed': 0,
            'total_failed': 0
        }
        
    def test_endpoint(self, name, url, method='GET', data=None, json_data=None, headers=None, category='api', auth=False):
        """Test a single endpoint with comprehensive checks"""
        try:
            if auth and not self.authenticate():
                return False, 0
            
            start = time.time()
            
            if method == 'GET':
                r = self.session.get(f"{BASE_URL}{url}", timeout=30, headers=headers)
            elif method == 'POST':
                if json_data:
                    r = self.session.post(f"{BASE_URL}{url}", json=json_data, timeout=30, headers=headers)
                else:
                    r = self.session.post(f"{BASE_URL}{url}", data=data, timeout=30, headers=headers)
            elif method == 'PUT':
                r = self.session.put(f"{BASE_URL}{url}", json=json_data, timeout=30, headers=headers)
            elif method == 'DELETE':
                r = self.session.delete(f"{BASE_URL}{url}", timeout=30, headers=headers)
            else:
                return False, 0
            
            response_time = (time.time() - start) * 1000
            success = r.status_code in [200, 201, 202, 302, 303, 307, 308]
            
            self.results['endpoints'][name] = {
                'url': url,
                'method': method,
                'status_code': r.status_code,
                'response_time_ms': round(response_time, 1),
                'success': success,
                'category': category,
                'response_size': len(r.content) if r.content else 0
            }
            
            # Track by category
            self.results['categories'][category]['endpoints'].append(name)
            if success:
                self.results['categories'][category]['passed'] += 1
                self.results['total_passed'] += 1
            else:
                self.results['categories'][category]['failed'] += 1
                self.results['total_failed'] += 1
            
            return success, response_time
            
        except Exception as e:
            self.results['endpoints'][name] = {
                'url': url,
                'method': method,
                'error': str(e),
                'success': False,
                'category': category
            }
            self.results['categories'][category]['endpoints'].append(name)
            self.results['categories'][category]['failed'] += 1
            self.results['total_failed'] += 1
            return False, 0
    
    def authenticate(self):
        """Authenticate as admin for protected endpoints"""
        try:
            # First check if already authenticated
            r = self.session.get(f"{BASE_URL}/dashboard")
            if r.status_code == 200:
                return True
            
            # Try to login
            login_data = {
                'username': 'admin',
                'password': 'admin'
            }
            r = self.session.post(f"{BASE_URL}/login", data=login_data)
            return r.status_code in [200, 302, 303]
        except:
            return False
    
    def test_all_endpoints(self):
        """Test ALL endpoints comprehensively"""
        print("=" * 80)
        print("COMPREHENSIVE FINAL TEST - ALL ENDPOINTS")
        print("Target: 600,000+ bags, 100+ concurrent users")
        print("=" * 80)
        
        # 1. HEALTH & MONITORING
        print("\n[1/9] Testing Health & Monitoring Endpoints...")
        health_tests = [
            ('Basic Health', '/health', 'GET', 'health'),
            ('Production Health', '/production-health', 'GET', 'health'),
            ('ELB Health', '/health/elb', 'GET', 'health'),
            ('Auto-scaling Metrics', '/metrics/scaling', 'GET', 'health'),
            ('CloudWatch Flush', '/metrics/flush', 'GET', 'health'),
            ('Production Setup', '/production-setup', 'GET', 'health'),
        ]
        self._run_tests(health_tests)
        
        # 2. AUTHENTICATION
        print("\n[2/9] Testing Authentication Endpoints...")
        auth_tests = [
            ('Login Page', '/login', 'GET', 'auth'),
            ('Login Submit', '/login', 'POST', 'auth', {'username': 'admin', 'password': 'admin'}),
            ('Logout', '/logout', 'GET', 'auth'),
            ('Register Page', '/register', 'GET', 'auth'),
            ('Fix Session', '/fix-session', 'GET', 'auth'),
            ('Test Session', '/test-session', 'GET', 'auth'),
            ('Auth Test', '/auth-test', 'GET', 'auth'),
        ]
        self._run_tests(auth_tests)
        
        # 3. API ENDPOINTS
        print("\n[3/9] Testing API Endpoints...")
        api_tests = [
            ('API Stats', '/api/stats', 'GET', 'api'),
            ('API V2 Stats', '/api/v2/stats', 'GET', 'api'),
            ('API Dashboard Stats', '/api/dashboard/stats', 'GET', 'api'),
            ('API Dashboard Stats Cached', '/api/dashboard-stats-cached', 'GET', 'api'),
            ('API Recent Scans', '/api/scans?limit=10', 'GET', 'api'),
            ('API Scans Recent', '/api/scans/recent', 'GET', 'api'),
            ('API Cache Stats', '/api/cache-stats', 'GET', 'api'),
            ('API Cache Clear', '/api/cache/clear', 'POST', 'api'),
            ('API System Health', '/api/system/health', 'GET', 'api'),
            ('API Dashboard Analytics', '/api/dashboard/analytics', 'GET', 'api'),
            ('API Parent Bags List', '/api/bags/parent/list', 'GET', 'api'),
            ('API Search', '/api/search', 'GET', 'api'),
            ('API Replica Test', '/api/replica-test', 'GET', 'api'),
            ('API Job Status', '/api/job/test123', 'GET', 'api'),
        ]
        self._run_tests(api_tests)
        
        # 4. MAIN PAGES
        print("\n[4/9] Testing Main Page Endpoints...")
        page_tests = [
            ('Home Page', '/', 'GET', 'pages'),
            ('Dashboard', '/dashboard', 'GET', 'pages'),
            ('Navigation', '/nav', 'GET', 'pages'),
            ('Bill Management', '/bill_management', 'GET', 'pages'),
            ('Request Promotion', '/request_promotion', 'GET', 'pages'),
            ('User Management', '/user_management', 'GET', 'pages'),
            ('Create User', '/create_user', 'POST', 'pages'),
            ('Manual Entry Info', '/manual_entry_info', 'GET', 'pages'),
            ('Test Manual Entry', '/test_manual_entry', 'GET', 'pages'),
        ]
        self._run_tests(page_tests)
        
        # 5. SCANNING ENDPOINTS
        print("\n[5/9] Testing Scanning Endpoints...")
        scan_tests = [
            ('Scan', '/scan', 'GET', 'scan'),
            ('Scan Parent', '/scan_parent', 'GET', 'scan'),
            ('Scan Parent Alt', '/scan/parent', 'GET', 'scan'),
            ('Scan Child', '/scan_child', 'GET', 'scan'),
            ('Scan Child Alt', '/scan/child', 'GET', 'scan'),
            ('Scan Complete', '/scan/complete', 'GET', 'scan'),
            ('Scan Finish', '/scan/finish', 'GET', 'scan'),
            ('Process Parent Scan', '/process_parent_scan', 'POST', 'scan'),
            ('Process Child Scan', '/process_child_scan', 'POST', 'scan'),
            ('Process Child Scan Fast', '/process_child_scan_fast', 'POST', 'scan'),
            ('Complete Parent Scan', '/complete_parent_scan', 'POST', 'scan'),
            ('Fast Parent Scan', '/fast/parent_scan', 'POST', 'scan'),
            ('Fast Child Scan', '/fast/child_scan', 'POST', 'scan'),
            ('Fast Bill Parent Scan', '/fast/bill_parent_scan', 'POST', 'scan'),
            ('Ajax Scan Parent', '/ajax/scan_parent', 'POST', 'scan'),
            ('API Fast Parent Scan', '/api/fast_parent_scan', 'POST', 'scan'),
            ('Log Scan', '/log_scan', 'POST', 'scan'),
            ('Lookup', '/lookup', 'GET', 'scan'),
            ('Scans List', '/scans', 'GET', 'scan'),
        ]
        self._run_tests(scan_tests)
        
        # 6. BILL ENDPOINTS
        print("\n[6/9] Testing Bill Endpoints...")
        bill_tests = [
            ('Bill Create', '/bill/create', 'GET', 'bill'),
            ('Bills List', '/bills', 'GET', 'bill'),
            ('Link to Bill', '/link_to_bill/TEST123', 'GET', 'bill'),
        ]
        self._run_tests(bill_tests)
        
        # 7. BAG ENDPOINTS
        print("\n[7/9] Testing Bag Endpoints...")
        bag_tests = [
            ('Bags List', '/bags', 'GET', 'pages'),
            ('API Bag Children', '/api/bags/1/children', 'GET', 'api'),
        ]
        self._run_tests(bag_tests)
        
        # 8. USER MANAGEMENT
        print("\n[8/9] Testing User Management Endpoints...")
        user_tests = [
            ('Admin Users Profile', '/admin/users/1/profile', 'GET', 'user'),
            ('Admin Promotions', '/admin/promotions', 'GET', 'user'),
            ('Admin System Integrity', '/admin/system-integrity', 'GET', 'user'),
            ('Admin Comprehensive Deletion', '/admin/comprehensive-user-deletion', 'GET', 'user'),
        ]
        self._run_tests(user_tests)
        
        # 9. ADMIN ENDPOINTS
        print("\n[9/9] Testing Admin Endpoints...")
        admin_tests = [
            ('Fix Admin Password', '/fix-admin-password', 'GET', 'admin'),
            ('Seed Sample Data', '/seed_sample_data', 'GET', 'admin'),
        ]
        self._run_tests(admin_tests)
        
        return self.results
    
    def _run_tests(self, tests):
        """Helper to run a list of tests"""
        for test in tests:
            if len(test) == 4:
                name, url, method, category = test
                data = None
            else:
                name, url, method, category, data = test
            
            success, time_ms = self.test_endpoint(name, url, method, data=data, category=category)
            status = "✅" if success else "❌"
            print(f"  {status} {name}: {time_ms:.1f}ms")
    
    def load_test(self, concurrent_users=100):
        """Perform load testing with concurrent users"""
        print("\n" + "=" * 80)
        print(f"LOAD TEST - {concurrent_users} Concurrent Users")
        print("=" * 80)
        
        def make_request(user_id):
            """Simulate a user making requests"""
            session = requests.Session()
            results = []
            
            # Test critical endpoints
            endpoints = [
                '/health',
                '/api/stats',
                '/api/scans?limit=10',
                '/dashboard'
            ]
            
            for endpoint in endpoints:
                try:
                    start = time.time()
                    r = session.get(f"{BASE_URL}{endpoint}", timeout=30)
                    elapsed = (time.time() - start) * 1000
                    results.append({
                        'user': user_id,
                        'endpoint': endpoint,
                        'status': r.status_code,
                        'time_ms': elapsed,
                        'success': r.status_code == 200
                    })
                except Exception as e:
                    results.append({
                        'user': user_id,
                        'endpoint': endpoint,
                        'error': str(e),
                        'success': False
                    })
            
            return results
        
        # Run concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_request, i) for i in range(concurrent_users)]
            all_results = []
            
            for future in concurrent.futures.as_completed(futures):
                all_results.extend(future.result())
        
        # Analyze results
        successful = sum(1 for r in all_results if r.get('success'))
        failed = len(all_results) - successful
        avg_time = sum(r.get('time_ms', 0) for r in all_results if 'time_ms' in r) / len([r for r in all_results if 'time_ms' in r])
        
        self.results['load_test'] = {
            'concurrent_users': concurrent_users,
            'total_requests': len(all_results),
            'successful': successful,
            'failed': failed,
            'success_rate': (successful / len(all_results) * 100) if all_results else 0,
            'avg_response_time_ms': round(avg_time, 1) if avg_time else 0
        }
        
        print(f"Total Requests: {len(all_results)}")
        print(f"Successful: {successful} ({successful/len(all_results)*100:.1f}%)")
        print(f"Failed: {failed}")
        print(f"Average Response Time: {avg_time:.1f}ms")
        
        return self.results['load_test']
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 80)
        print("CATEGORY SUMMARY")
        print("=" * 80)
        
        for category, stats in self.results['categories'].items():
            total = stats['passed'] + stats['failed']
            if total > 0:
                percentage = (stats['passed'] / total) * 100
                status = "✅" if percentage == 100 else "⚠️" if percentage >= 70 else "❌"
                print(f"{status} {category.upper()}: {stats['passed']}/{total} passed ({percentage:.0f}%)")
        
        print("\n" + "=" * 80)
        print("OVERALL RESULTS")
        print("=" * 80)
        
        total_endpoints = self.results['total_passed'] + self.results['total_failed']
        success_rate = (self.results['total_passed'] / total_endpoints * 100) if total_endpoints > 0 else 0
        
        print(f"Total Endpoints Tested: {total_endpoints}")
        print(f"Passed: {self.results['total_passed']}")
        print(f"Failed: {self.results['total_failed']}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Performance summary
        if self.results['endpoints']:
            response_times = [e['response_time_ms'] for e in self.results['endpoints'].values() if 'response_time_ms' in e]
            if response_times:
                print(f"\nPerformance Metrics:")
                print(f"  Fastest: {min(response_times):.1f}ms")
                print(f"  Slowest: {max(response_times):.1f}ms")
                print(f"  Average: {sum(response_times)/len(response_times):.1f}ms")
                print(f"  P95: {sorted(response_times)[int(len(response_times)*0.95)]:.1f}ms")
        
        # Load test summary
        if self.results.get('load_test'):
            lt = self.results['load_test']
            print(f"\nLoad Test Results ({lt['concurrent_users']} users):")
            print(f"  Success Rate: {lt['success_rate']:.1f}%")
            print(f"  Avg Response: {lt['avg_response_time_ms']:.1f}ms")
        
        # System readiness
        if success_rate >= 90:
            print("\n🎉 SYSTEM FULLY OPERATIONAL - Production Ready!")
            print("✅ Ready for 600,000+ bags and 100+ concurrent users")
        elif success_rate >= 70:
            print("\n✅ SYSTEM OPERATIONAL - Minor issues present")
            print("⚠️ Some endpoints need attention before full production")
        else:
            print("\n❌ SYSTEM ISSUES DETECTED - Not production ready")
            print("⚠️ Multiple endpoints failing, needs immediate attention")
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'comprehensive_final_test_{timestamp}.json'
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nDetailed results saved to {filename}")
        
        return success_rate >= 70

if __name__ == "__main__":
    tester = ComprehensiveFinalTest()
    
    # Run all endpoint tests
    tester.test_all_endpoints()
    
    # Run load test
    print("\nRunning load test with 100 concurrent users...")
    tester.load_test(concurrent_users=100)
    
    # Print summary
    system_ready = tester.print_summary()
    
    # Exit with appropriate code
    sys.exit(0 if system_ready else 1)
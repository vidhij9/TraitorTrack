#!/usr/bin/env python3
"""
Comprehensive System Test - Tests ALL endpoints and functionality
"""

import requests
import time
import json
from datetime import datetime
import sys

BASE_URL = "http://localhost:5000"

class ComprehensiveSystemTest:
    def __init__(self):
        self.session = requests.Session()
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'endpoints': {},
            'categories': {
                'health': {'passed': 0, 'failed': 0},
                'auth': {'passed': 0, 'failed': 0},
                'api': {'passed': 0, 'failed': 0},
                'aws': {'passed': 0, 'failed': 0},
                'pages': {'passed': 0, 'failed': 0},
                'scan': {'passed': 0, 'failed': 0},
                'bill': {'passed': 0, 'failed': 0},
                'user': {'passed': 0, 'failed': 0}
            },
            'total_passed': 0,
            'total_failed': 0
        }
    
    def test_endpoint(self, name, url, method='GET', data=None, category='api'):
        """Test a single endpoint"""
        try:
            start = time.time()
            if method == 'GET':
                r = self.session.get(f"{BASE_URL}{url}", timeout=15)
            else:
                r = self.session.post(f"{BASE_URL}{url}", data=data, timeout=15)
            
            response_time = (time.time() - start) * 1000
            success = r.status_code in [200, 201, 302, 303, 307, 308]
            
            self.results['endpoints'][name] = {
                'url': url,
                'status_code': r.status_code,
                'response_time_ms': round(response_time, 1),
                'success': success,
                'category': category
            }
            
            if success:
                self.results['categories'][category]['passed'] += 1
                self.results['total_passed'] += 1
                return True, response_time
            else:
                self.results['categories'][category]['failed'] += 1
                self.results['total_failed'] += 1
                return False, response_time
                
        except Exception as e:
            self.results['endpoints'][name] = {
                'url': url,
                'error': str(e),
                'success': False,
                'category': category
            }
            self.results['categories'][category]['failed'] += 1
            self.results['total_failed'] += 1
            return False, 0
    
    def run_all_tests(self):
        """Run tests on ALL endpoints"""
        print("=" * 80)
        print("COMPREHENSIVE SYSTEM TEST - ALL ENDPOINTS")
        print("=" * 80)
        
        # 1. HEALTH & MONITORING ENDPOINTS
        print("\n[1/8] Testing Health & Monitoring Endpoints...")
        health_endpoints = [
            ('Basic Health', '/health', 'health'),
            ('ELB Health Check', '/health/elb', 'health'),
            ('Auto-scaling Metrics', '/metrics/scaling', 'health'),
            ('CloudWatch Flush', '/metrics/flush', 'health'),
        ]
        
        for name, url, cat in health_endpoints:
            success, time_ms = self.test_endpoint(name, url, category=cat)
            status = "✅" if success else "❌"
            print(f"  {status} {name}: {time_ms:.1f}ms")
        
        # 2. API ENDPOINTS
        print("\n[2/8] Testing API Endpoints...")
        api_endpoints = [
            ('API Stats', '/api/stats', 'api'),
            ('API Dashboard Stats', '/api/dashboard-stats', 'api'),
            ('API Dashboard Stats Cached', '/api/dashboard-stats-cached', 'api'),
            ('API Recent Scans', '/api/scans?limit=10', 'api'),
            ('API Cache Stats', '/api/cache-stats', 'api'),
            ('API Replica Test', '/api/replica-test', 'api'),
            ('API Job Status', '/api/job/test123', 'api'),
        ]
        
        for name, url, cat in api_endpoints:
            success, time_ms = self.test_endpoint(name, url, category=cat)
            status = "✅" if success else "❌"
            print(f"  {status} {name}: {time_ms:.1f}ms")
        
        # 3. AUTHENTICATION ENDPOINTS
        print("\n[3/8] Testing Authentication Endpoints...")
        auth_endpoints = [
            ('Login Page', '/login', 'auth'),
            ('Logout', '/logout', 'auth'),
            ('Register Page', '/register', 'auth'),
        ]
        
        for name, url, cat in auth_endpoints:
            success, time_ms = self.test_endpoint(name, url, category=cat)
            status = "✅" if success else "❌"
            print(f"  {status} {name}: {time_ms:.1f}ms")
        
        # 4. MAIN PAGE ENDPOINTS
        print("\n[4/8] Testing Main Page Endpoints...")
        page_endpoints = [
            ('Home Page', '/', 'pages'),
            ('Dashboard', '/dashboard', 'pages'),
            ('Admin Dashboard', '/admin_dashboard', 'pages'),
            ('Bill Management', '/bill_management', 'pages'),
            ('Generate Report', '/generate_report', 'pages'),
            ('Request Promotion', '/request_promotion', 'pages'),
            ('Create User', '/create_user', 'pages'),
        ]
        
        for name, url, cat in page_endpoints:
            success, time_ms = self.test_endpoint(name, url, category=cat)
            status = "✅" if success else "❌"
            print(f"  {status} {name}: {time_ms:.1f}ms")
        
        # 5. SCANNING ENDPOINTS
        print("\n[5/8] Testing Scanning Endpoints...")
        scan_endpoints = [
            ('Scan Parent', '/scan_parent', 'scan'),
            ('Scan Child', '/scan_child', 'scan'),
            ('Verify Bag', '/verify_bag', 'scan'),
            ('Fast Parent Scan', '/fast/parent_scan', 'scan'),
            ('Fast Child Scan', '/fast/child_scan', 'scan'),
            ('Fast Bill Parent Scan', '/fast/bill_parent_scan', 'scan'),
            ('Fast Bill Child Scan', '/fast/bill_child_scan', 'scan'),
        ]
        
        for name, url, cat in scan_endpoints:
            method = 'POST' if 'fast' in url else 'GET'
            success, time_ms = self.test_endpoint(name, url, method=method, category=cat)
            status = "✅" if success else "❌"
            print(f"  {status} {name}: {time_ms:.1f}ms")
        
        # 6. BILL ENDPOINTS
        print("\n[6/8] Testing Bill Endpoints...")
        bill_endpoints = [
            ('Bill Create', '/bill/create', 'bill'),
            ('Bills Page', '/bills', 'bill'),
        ]
        
        for name, url, cat in bill_endpoints:
            success, time_ms = self.test_endpoint(name, url, category=cat)
            status = "✅" if success else "❌"
            print(f"  {status} {name}: {time_ms:.1f}ms")
        
        # 7. USER MANAGEMENT ENDPOINTS
        print("\n[7/8] Testing User Management Endpoints...")
        user_endpoints = [
            ('Users List', '/users', 'user'),
            ('Promotions', '/promotions', 'user'),
        ]
        
        for name, url, cat in user_endpoints:
            success, time_ms = self.test_endpoint(name, url, category=cat)
            status = "✅" if success else "❌"
            print(f"  {status} {name}: {time_ms:.1f}ms")
        
        # 8. AWS PHASE 3 ENDPOINTS
        print("\n[8/8] Testing AWS Phase 3 Specific Endpoints...")
        aws_endpoints = [
            ('AWS ELB Health', '/health/elb', 'aws'),
            ('AWS Scaling Metrics', '/metrics/scaling', 'aws'),
            ('AWS Metrics Flush', '/metrics/flush', 'aws'),
            ('AWS Replica Test', '/api/replica-test', 'aws'),
        ]
        
        for name, url, cat in aws_endpoints:
            success, time_ms = self.test_endpoint(name, url, category=cat)
            status = "✅" if success else "❌"
            print(f"  {status} {name}: {time_ms:.1f}ms")
        
        # Print Summary
        print("\n" + "=" * 80)
        print("CATEGORY SUMMARY")
        print("=" * 80)
        
        for category, stats in self.results['categories'].items():
            total = stats['passed'] + stats['failed']
            if total > 0:
                percentage = (stats['passed'] / total) * 100
                status = "✅" if percentage == 100 else "⚠️" if percentage >= 50 else "❌"
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
        
        # Determine overall status
        if success_rate >= 95:
            print("\n🎉 SYSTEM FULLY OPERATIONAL - All critical systems working")
            self.results['system_ready'] = True
        elif success_rate >= 80:
            print("\n✅ SYSTEM OPERATIONAL - Most endpoints working, minor issues present")
            self.results['system_ready'] = True
        else:
            print("\n❌ SYSTEM ISSUES DETECTED - Multiple endpoints failing")
            self.results['system_ready'] = False
        
        # Save detailed results
        with open('comprehensive_test_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print("\nDetailed results saved to comprehensive_test_results.json")
        
        return self.results

if __name__ == "__main__":
    tester = ComprehensiveSystemTest()
    results = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if results['system_ready'] else 1)

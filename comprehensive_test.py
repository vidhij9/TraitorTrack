#!/usr/bin/env python3
"""
Comprehensive Website Testing Suite
Tests all functionality and endpoints under load
"""

import requests
import time
import json
import concurrent.futures
import statistics
from datetime import datetime
import random
import string

# Configuration
BASE_URL = "http://0.0.0.0:5000"
TEST_USERNAME = "admin"
TEST_PASSWORD = "admin"

class ComprehensiveTester:
    def __init__(self):
        self.session = requests.Session()
        self.results = {}
        self.errors = []
        
    def login(self):
        """Login to the system"""
        try:
            # Get CSRF token
            response = self.session.get(f"{BASE_URL}/login")
            
            # Login
            login_data = {
                'username': TEST_USERNAME,
                'password': TEST_PASSWORD
            }
            response = self.session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
            
            if response.status_code in [302, 200]:
                print(f"✅ Login successful as {TEST_USERNAME}")
                return True
            else:
                print(f"❌ Login failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def test_endpoint(self, method, path, data=None, name=None):
        """Test a single endpoint"""
        url = f"{BASE_URL}{path}"
        name = name or path
        
        try:
            start = time.time()
            
            if method == "GET":
                response = self.session.get(url, timeout=10)
            elif method == "POST":
                response = self.session.post(url, data=data or {}, timeout=10)
            else:
                response = self.session.request(method, url, data=data, timeout=10)
            
            elapsed = (time.time() - start) * 1000
            
            self.results[name] = {
                'status': response.status_code,
                'time_ms': elapsed,
                'success': response.status_code < 400
            }
            
            status_icon = "✅" if response.status_code < 400 else "❌"
            print(f"  {status_icon} {name:40} Status: {response.status_code:3} Time: {elapsed:7.1f}ms")
            
            return response.status_code < 400
            
        except Exception as e:
            self.errors.append(f"{name}: {str(e)}")
            print(f"  ❌ {name:40} Error: {str(e)[:50]}")
            return False
    
    def test_all_pages(self):
        """Test all main pages"""
        print("\n📄 Testing Main Pages:")
        print("-" * 60)
        
        pages = [
            ("GET", "/", "Homepage"),
            ("GET", "/dashboard", "Dashboard"),
            ("GET", "/scan_parent", "Scan Parent"),
            ("GET", "/scan_child", "Scan Child"),
            ("GET", "/lookup", "Lookup"),
            ("GET", "/bill_management", "Bill Management"),
            ("GET", "/user_management", "User Management"),
            ("GET", "/admin/promotions", "Admin Promotions"),
            ("GET", "/user_profile", "User Profile"),
            ("GET", "/parent_bags", "Parent Bags"),
            ("GET", "/child_bags", "Child Bags"),
            ("GET", "/scan_history", "Scan History"),
            ("GET", "/analytics", "Analytics"),
            ("GET", "/bill_summary", "Bill Summary"),
        ]
        
        for method, path, name in pages:
            self.test_endpoint(method, path, name=name)
    
    def test_api_endpoints(self):
        """Test all API endpoints"""
        print("\n🔌 Testing API Endpoints:")
        print("-" * 60)
        
        apis = [
            ("GET", "/api/stats", "Dashboard Stats"),
            ("GET", "/api/scans?limit=10", "Recent Scans"),
            ("GET", "/api/bags?limit=10", "Recent Bags"),
            ("GET", "/api/bills?limit=10", "Recent Bills"),
            ("GET", "/api/cached/stats", "Cached Stats"),
            ("GET", "/api/cached/recent_scans?limit=10", "Cached Scans"),
            ("GET", "/api/cache/stats", "Cache Statistics"),
            ("GET", "/health", "Health Check"),
            ("GET", "/api/health/redis", "Redis Health"),
            ("GET", "/api/v2/stats", "V2 Stats"),
            ("GET", "/api/batch_scan/status", "Batch Scan Status"),
        ]
        
        for method, path, name in apis:
            self.test_endpoint(method, path, name=name)
    
    def test_scanning_workflow(self):
        """Test the complete scanning workflow"""
        print("\n📱 Testing Scanning Workflow:")
        print("-" * 60)
        
        # Generate test QR codes
        parent_qr = f"SB{random.randint(10000, 99999)}"
        child_qr = f"C{random.randint(100000, 999999)}"
        
        print(f"  Testing with Parent: {parent_qr}, Child: {child_qr}")
        
        # Test parent scan
        parent_data = {
            'qr_code': parent_qr
        }
        self.test_endpoint("POST", "/fast/parent_scan", parent_data, "Fast Parent Scan")
        
        # Test child scan
        child_data = {
            'parent_qr': parent_qr,
            'child_qr': child_qr
        }
        self.test_endpoint("POST", "/process_child_scan", child_data, "Process Child Scan")
        
        # Test lookup
        lookup_data = {
            'qr_code': parent_qr
        }
        self.test_endpoint("POST", "/lookup", lookup_data, "Lookup QR")
    
    def test_user_management(self):
        """Test user management functions"""
        print("\n👥 Testing User Management:")
        print("-" * 60)
        
        # Test user creation
        test_user = f"test_{random.randint(1000, 9999)}"
        user_data = {
            'username': test_user,
            'email': f"{test_user}@test.com",
            'password': 'test123',
            'role': 'dispatcher',
            'dispatch_area': 'Test Area'
        }
        
        if self.test_endpoint("POST", "/create_user", user_data, "Create User"):
            # Test user deletion preview
            delete_data = {
                'username': test_user,
                'role': 'dispatcher'
            }
            self.test_endpoint("POST", "/admin/preview-user-deletion", delete_data, "Preview Deletion")
    
    def load_test_endpoint(self, path, concurrent_users=50):
        """Load test a specific endpoint"""
        def make_request():
            try:
                start = time.time()
                response = requests.get(f"{BASE_URL}{path}", timeout=5)
                elapsed = (time.time() - start) * 1000
                return elapsed if response.status_code == 200 else None
            except:
                return None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_request) for _ in range(concurrent_users)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        successful = [r for r in results if r is not None]
        
        if successful:
            return {
                'success_rate': len(successful) / len(results) * 100,
                'avg_time': statistics.mean(successful),
                'min_time': min(successful),
                'max_time': max(successful),
                'median_time': statistics.median(successful)
            }
        return None
    
    def test_load_performance(self):
        """Test system under load"""
        print("\n⚡ Load Testing (50 concurrent users):")
        print("-" * 60)
        
        endpoints = [
            ("/health", "Health Check"),
            ("/api/stats", "Dashboard Stats"),
            ("/api/scans?limit=10", "Recent Scans"),
            ("/", "Homepage"),
        ]
        
        for path, name in endpoints:
            result = self.load_test_endpoint(path, 50)
            if result:
                status = "✅" if result['success_rate'] >= 95 else ("⚠️" if result['success_rate'] >= 80 else "❌")
                print(f"  {status} {name:20} Success: {result['success_rate']:.1f}% Avg: {result['avg_time']:.1f}ms")
            else:
                print(f"  ❌ {name:20} Failed completely")
    
    def test_database_operations(self):
        """Test database-heavy operations"""
        print("\n💾 Testing Database Operations:")
        print("-" * 60)
        
        # Test bill creation
        bill_data = {
            'bill_number': f"BILL-{random.randint(10000, 99999)}"
        }
        self.test_endpoint("POST", "/create_bill", bill_data, "Create Bill")
        
        # Test analytics
        self.test_endpoint("GET", "/api/analytics/summary", None, "Analytics Summary")
        
        # Test export
        self.test_endpoint("GET", "/api/export/scans?format=json", None, "Export Scans")
    
    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("=" * 80)
        print("COMPREHENSIVE WEBSITE TESTING")
        print("=" * 80)
        print(f"Time: {datetime.now()}")
        print(f"Target: {BASE_URL}")
        print("-" * 80)
        
        # Login first
        if not self.login():
            print("❌ Cannot proceed without login")
            return
        
        # Run all test categories
        self.test_all_pages()
        self.test_api_endpoints()
        self.test_scanning_workflow()
        self.test_user_management()
        self.test_database_operations()
        self.test_load_performance()
        
        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.results)
        successful = sum(1 for r in self.results.values() if r['success'])
        failed = total_tests - successful
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {successful/total_tests*100:.1f}%")
        
        # Performance stats
        response_times = [r['time_ms'] for r in self.results.values() if 'time_ms' in r]
        if response_times:
            print(f"\nPerformance Statistics:")
            print(f"  Average Response: {statistics.mean(response_times):.1f}ms")
            print(f"  Median Response: {statistics.median(response_times):.1f}ms")
            print(f"  Fastest: {min(response_times):.1f}ms")
            print(f"  Slowest: {max(response_times):.1f}ms")
        
        # Errors
        if self.errors:
            print(f"\n⚠️ Errors Encountered:")
            for error in self.errors[:5]:
                print(f"  - {error}")
        
        # Recommendations
        print("\n📊 Recommendations:")
        if failed > 0:
            print(f"  ⚠️ Fix {failed} failing endpoints")
        
        avg_time = statistics.mean(response_times) if response_times else 0
        if avg_time > 500:
            print(f"  ⚠️ Average response time ({avg_time:.0f}ms) needs optimization")
        elif avg_time > 200:
            print(f"  ⚠️ Consider optimizing response times (currently {avg_time:.0f}ms)")
        else:
            print(f"  ✅ Good response times ({avg_time:.0f}ms average)")
        
        print("=" * 80)

if __name__ == "__main__":
    tester = ComprehensiveTester()
    tester.run_all_tests()
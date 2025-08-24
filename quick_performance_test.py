#!/usr/bin/env python3
"""
Quick Performance Test - Check current state of the application
"""

import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

class QuickPerformanceTest:
    def __init__(self, base_url="http://0.0.0.0:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def test_basic_endpoints(self):
        """Test basic endpoint response times"""
        print("\n=== BASIC ENDPOINT TESTS ===")
        endpoints = [
            ('GET', '/health', None),
            ('GET', '/login', None),
            ('GET', '/', None)
        ]
        
        for method, path, data in endpoints:
            try:
                start = time.perf_counter()
                if method == 'GET':
                    response = self.session.get(f"{self.base_url}{path}", timeout=10)
                else:
                    response = self.session.post(f"{self.base_url}{path}", json=data, timeout=10)
                elapsed = (time.perf_counter() - start) * 1000
                
                print(f"{method:4} {path:20} - Status: {response.status_code:3} - Time: {elapsed:6.1f}ms")
            except Exception as e:
                print(f"{method:4} {path:20} - Error: {str(e)[:50]}")
    
    def test_concurrent_load(self, num_users=10):
        """Test with concurrent users"""
        print(f"\n=== CONCURRENT LOAD TEST ({num_users} users) ===")
        
        def make_request(user_id):
            times = []
            errors = 0
            
            for i in range(5):  # Each user makes 5 requests
                try:
                    start = time.perf_counter()
                    response = self.session.get(f"{self.base_url}/health", timeout=5)
                    elapsed = (time.perf_counter() - start) * 1000
                    times.append(elapsed)
                except:
                    errors += 1
            
            return {'user_id': user_id, 'times': times, 'errors': errors}
        
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_users)]
            all_times = []
            total_errors = 0
            
            for future in as_completed(futures):
                result = future.result()
                all_times.extend(result['times'])
                total_errors += result['errors']
        
        if all_times:
            print(f"Total Requests: {len(all_times) + total_errors}")
            print(f"Successful: {len(all_times)}")
            print(f"Failed: {total_errors}")
            print(f"Mean Response Time: {statistics.mean(all_times):.1f}ms")
            print(f"Median Response Time: {statistics.median(all_times):.1f}ms")
            print(f"Min Response Time: {min(all_times):.1f}ms")
            print(f"Max Response Time: {max(all_times):.1f}ms")
            
            # Check if meets targets
            meets_target = statistics.mean(all_times) < 100
            print(f"\nMeets <100ms target: {'✅ YES' if meets_target else '❌ NO'}")
        else:
            print("All requests failed!")
    
    def test_database_queries(self):
        """Test database-heavy endpoints"""
        print("\n=== DATABASE QUERY TESTS ===")
        
        # First login as a test user
        try:
            login_resp = self.session.post(f"{self.base_url}/login", data={
                'username': 'admin',
                'password': 'admin123'
            }, timeout=10)
            
            if login_resp.status_code >= 400:
                print("Login failed, trying API endpoints without auth...")
        except:
            print("Login failed, continuing without auth...")
        
        db_endpoints = [
            ('GET', '/api/stats', None),
            ('GET', '/api/scans?limit=10', None),
            ('POST', '/api/fast_parent_scan', {'qr_code': 'TEST12345'})
        ]
        
        for method, path, data in db_endpoints:
            try:
                start = time.perf_counter()
                if method == 'GET':
                    response = self.session.get(f"{self.base_url}{path}", timeout=10)
                else:
                    response = self.session.post(f"{self.base_url}{path}", json=data, timeout=10)
                elapsed = (time.perf_counter() - start) * 1000
                
                status_icon = '✅' if response.status_code < 400 else '❌'
                time_icon = '✅' if elapsed < 100 else '⚠️' if elapsed < 500 else '❌'
                
                print(f"{method:4} {path:30} - Status: {status_icon} {response.status_code:3} - Time: {time_icon} {elapsed:6.1f}ms")
            except Exception as e:
                print(f"{method:4} {path:30} - Error: {str(e)[:50]}")
    
    def run_all_tests(self):
        """Run all performance tests"""
        print("\n" + "="*60)
        print("QUICK PERFORMANCE TEST")
        print("="*60)
        
        # Check if server is running
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            print(f"✅ Server is running at {self.base_url}")
        except:
            print(f"❌ Cannot connect to server at {self.base_url}")
            return
        
        # Run tests
        self.test_basic_endpoints()
        self.test_database_queries()
        self.test_concurrent_load(10)
        self.test_concurrent_load(25)
        self.test_concurrent_load(50)
        
        print("\n" + "="*60)
        print("TEST COMPLETE")
        print("="*60)


if __name__ == "__main__":
    tester = QuickPerformanceTest()
    tester.run_all_tests()
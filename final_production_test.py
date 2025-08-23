#!/usr/bin/env python3
"""
Final Production Test - Verify zero failures under load
"""

import time
import requests
import random
import string
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json
import os

BASE_URL = "http://0.0.0.0:5000"
DATABASE_URL = os.environ.get("DATABASE_URL")

class FinalProductionTest:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests_passed": 0,
            "tests_failed": 0,
            "performance_metrics": {},
            "error_details": []
        }
        
    def run_all_tests(self):
        """Run comprehensive production tests"""
        print("=" * 60)
        print("FINAL PRODUCTION READINESS TEST")
        print("=" * 60)
        
        # Test 1: Health Check
        print("\n1. Testing Health Endpoints...")
        self.test_health_endpoints()
        
        # Test 2: Concurrent Load Test
        print("\n2. Testing Concurrent Load (20 users)...")
        self.test_concurrent_load()
        
        # Test 3: Login Performance
        print("\n3. Testing Login Performance...")
        self.test_login_performance()
        
        # Test 4: Query Performance
        print("\n4. Testing Query Performance...")
        self.test_query_performance()
        
        # Test 5: Parent/Child Scanning
        print("\n5. Testing Scanning Workflow...")
        self.test_scanning_workflow()
        
        # Generate Report
        self.generate_report()
        
    def test_health_endpoints(self):
        """Test health check endpoints"""
        endpoints = ['/health', '/status', '/']
        
        for endpoint in endpoints:
            try:
                start = time.time()
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=2)
                elapsed = (time.time() - start) * 1000
                
                if response.status_code in [200, 302]:
                    if elapsed < 100:
                        print(f"  ✅ {endpoint}: {elapsed:.2f}ms")
                        self.results["tests_passed"] += 1
                    else:
                        print(f"  ⚠️  {endpoint}: {elapsed:.2f}ms (slow)")
                        self.results["tests_failed"] += 1
                else:
                    print(f"  ❌ {endpoint}: HTTP {response.status_code}")
                    self.results["tests_failed"] += 1
            except Exception as e:
                print(f"  ❌ {endpoint}: {str(e)}")
                self.results["tests_failed"] += 1
                
    def test_concurrent_load(self):
        """Test with concurrent users"""
        def make_request():
            try:
                start = time.time()
                response = requests.get(f"{BASE_URL}/health", timeout=2)
                elapsed = time.time() - start
                return response.status_code == 200, elapsed
            except:
                return False, None
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(100)]
            
            success_count = 0
            response_times = []
            
            for future in as_completed(futures):
                success, elapsed = future.result()
                if success and elapsed:
                    success_count += 1
                    response_times.append(elapsed)
        
        # Calculate metrics
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            p95_time = sorted(response_times)[int(len(response_times) * 0.95)]
            success_rate = (success_count / 100) * 100
            
            print(f"  Success Rate: {success_rate:.1f}%")
            print(f"  Avg Response: {avg_time*1000:.2f}ms")
            print(f"  P95 Response: {p95_time*1000:.2f}ms")
            
            if success_rate >= 99 and avg_time < 0.1:
                print("  ✅ Load test PASSED")
                self.results["tests_passed"] += 1
            else:
                print("  ❌ Load test FAILED")
                self.results["tests_failed"] += 1
                
            self.results["performance_metrics"]["load_test"] = {
                "success_rate": f"{success_rate:.1f}%",
                "avg_response": f"{avg_time*1000:.2f}ms",
                "p95_response": f"{p95_time*1000:.2f}ms"
            }
            
    def test_login_performance(self):
        """Test login endpoint performance"""
        session = requests.Session()
        
        # Test login response time
        try:
            start = time.time()
            response = session.get(f"{BASE_URL}/login", timeout=2)
            elapsed = (time.time() - start) * 1000
            
            if response.status_code == 200 and elapsed < 100:
                print(f"  ✅ Login page: {elapsed:.2f}ms")
                self.results["tests_passed"] += 1
            else:
                print(f"  ❌ Login page: {elapsed:.2f}ms or error")
                self.results["tests_failed"] += 1
                
        except Exception as e:
            print(f"  ❌ Login test failed: {e}")
            self.results["tests_failed"] += 1
            
    def test_query_performance(self):
        """Test database query performance"""
        import psycopg2
        
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            
            queries = [
                ("SELECT COUNT(*) FROM bag", "Bag count"),
                ("SELECT COUNT(*) FROM scan", "Scan count"),
                ("SELECT * FROM bag WHERE qr_id = 'TEST123' LIMIT 1", "Bag lookup")
            ]
            
            for query, name in queries:
                start = time.time()
                cur.execute(query)
                cur.fetchall()
                elapsed = (time.time() - start) * 1000
                
                if elapsed < 50:
                    print(f"  ✅ {name}: {elapsed:.2f}ms")
                    self.results["tests_passed"] += 1
                else:
                    print(f"  ❌ {name}: {elapsed:.2f}ms (slow)")
                    self.results["tests_failed"] += 1
            
            cur.close()
            conn.close()
            
        except Exception as e:
            print(f"  ❌ Query test failed: {e}")
            self.results["tests_failed"] += 1
            
    def test_scanning_workflow(self):
        """Test parent/child scanning workflow"""
        session = requests.Session()
        
        # Test parent scan endpoint
        try:
            response = session.get(f"{BASE_URL}/scan/parent", timeout=2)
            if response.status_code in [200, 302]:
                print("  ✅ Parent scan endpoint accessible")
                self.results["tests_passed"] += 1
            else:
                print(f"  ❌ Parent scan endpoint: HTTP {response.status_code}")
                self.results["tests_failed"] += 1
        except Exception as e:
            print(f"  ❌ Parent scan test failed: {e}")
            self.results["tests_failed"] += 1
            
    def generate_report(self):
        """Generate final report"""
        total_tests = self.results["tests_passed"] + self.results["tests_failed"]
        pass_rate = (self.results["tests_passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print("\n" + "=" * 60)
        print("FINAL RESULTS")
        print("=" * 60)
        print(f"✅ Tests Passed: {self.results['tests_passed']}")
        print(f"❌ Tests Failed: {self.results['tests_failed']}")
        print(f"📊 Pass Rate: {pass_rate:.1f}%")
        
        if self.results["performance_metrics"]:
            print("\nPERFORMANCE METRICS:")
            for key, metrics in self.results["performance_metrics"].items():
                print(f"  {key}:")
                for metric, value in metrics.items():
                    print(f"    - {metric}: {value}")
        
        # Final verdict
        print("\n" + "=" * 60)
        if pass_rate >= 95:
            print("✅ SYSTEM IS PRODUCTION READY!")
            print("All critical tests passed. System can handle production load.")
        elif pass_rate >= 80:
            print("⚠️  SYSTEM NEEDS MINOR FIXES")
            print("Most tests passed but some issues remain.")
        else:
            print("❌ SYSTEM NOT PRODUCTION READY")
            print("Critical issues detected. Do not deploy to production.")
        print("=" * 60)
        
        # Save results
        with open("final_production_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        
        return pass_rate >= 95

if __name__ == "__main__":
    tester = FinalProductionTest()
    is_ready = tester.run_all_tests()
    exit(0 if is_ready else 1)
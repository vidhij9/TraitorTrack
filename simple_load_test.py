#!/usr/bin/env python3
"""
Simple Load Testing Script for TraceTrack
Tests system performance with concurrent users
"""

import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import statistics
import json
from datetime import datetime

class SimpleLoadTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.results = []
        self.errors = []
        self.lock = threading.Lock()
        
    def test_request(self, endpoint, method="GET"):
        """Make a single test request"""
        try:
            start = time.time()
            
            if method == "GET":
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
            else:
                response = requests.post(f"{self.base_url}{endpoint}", timeout=10)
            
            duration = (time.time() - start) * 1000  # Convert to ms
            
            with self.lock:
                self.results.append({
                    "endpoint": endpoint,
                    "duration": duration,
                    "status": response.status_code,
                    "success": response.status_code in [200, 302]
                })
            
            return True
            
        except Exception as e:
            with self.lock:
                self.errors.append(f"{endpoint}: {str(e)}")
            return False
    
    def user_simulation(self, user_id):
        """Simulate a single user session"""
        # Test various endpoints
        endpoints = [
            "/health",
            "/",
            "/login",
            "/dashboard",
            "/bags",
            "/bills",
            "/api/dashboard/analytics",
            "/api/bags",
            "/api/bills",
            "/lookup"
        ]
        
        for endpoint in endpoints:
            self.test_request(endpoint)
            time.sleep(0.1)  # Small delay between requests
        
        print(f"User {user_id} completed")
    
    def run_load_test(self, num_users=10):
        """Run load test with concurrent users"""
        print(f"\n{'='*60}")
        print(f"STARTING LOAD TEST WITH {num_users} CONCURRENT USERS")
        print(f"{'='*60}\n")
        
        start_time = time.time()
        
        # Run concurrent users
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(self.user_simulation, i) for i in range(num_users)]
            
            # Wait for completion
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f"User simulation error: {e}")
        
        duration = time.time() - start_time
        
        # Analyze results
        self.print_results(duration, num_users)
    
    def print_results(self, duration, num_users):
        """Print test results"""
        print(f"\n{'='*60}")
        print("LOAD TEST RESULTS")
        print(f"{'='*60}\n")
        
        successful = [r for r in self.results if r["success"]]
        failed = [r for r in self.results if not r["success"]]
        
        print(f"📊 OVERALL STATISTICS:")
        print(f"  Total Requests: {len(self.results)}")
        print(f"  Successful: {len(successful)} ({len(successful)/len(self.results)*100:.1f}%)")
        print(f"  Failed: {len(failed)} ({len(failed)/len(self.results)*100:.1f}%)")
        print(f"  Errors: {len(self.errors)}")
        print(f"  Test Duration: {duration:.2f} seconds")
        print(f"  Requests/Second: {len(self.results)/duration:.2f}")
        
        if self.results:
            response_times = [r["duration"] for r in self.results]
            
            print(f"\n⏱️  RESPONSE TIME STATISTICS (ms):")
            print(f"  Min: {min(response_times):.2f}")
            print(f"  Max: {max(response_times):.2f}")
            print(f"  Mean: {statistics.mean(response_times):.2f}")
            print(f"  Median: {statistics.median(response_times):.2f}")
            
            # Calculate percentiles
            sorted_times = sorted(response_times)
            p50 = sorted_times[int(len(sorted_times) * 0.50)]
            p90 = sorted_times[int(len(sorted_times) * 0.90)]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            
            print(f"  P50: {p50:.2f}")
            print(f"  P90: {p90:.2f}") 
            print(f"  P95: {p95:.2f}")
            
            # Endpoint breakdown
            endpoint_stats = {}
            for result in self.results:
                endpoint = result["endpoint"]
                if endpoint not in endpoint_stats:
                    endpoint_stats[endpoint] = {
                        "count": 0,
                        "total_time": 0,
                        "errors": 0
                    }
                endpoint_stats[endpoint]["count"] += 1
                endpoint_stats[endpoint]["total_time"] += result["duration"]
                if not result["success"]:
                    endpoint_stats[endpoint]["errors"] += 1
            
            print(f"\n📍 ENDPOINT STATISTICS:")
            for endpoint, stats in endpoint_stats.items():
                avg_time = stats["total_time"] / stats["count"]
                error_rate = (stats["errors"] / stats["count"]) * 100
                print(f"  {endpoint}:")
                print(f"    Requests: {stats['count']}")
                print(f"    Avg Time: {avg_time:.2f}ms")
                print(f"    Error Rate: {error_rate:.1f}%")
            
            # Performance assessment
            print(f"\n🎯 PERFORMANCE ASSESSMENT:")
            
            success_rate = (len(successful) / len(self.results)) * 100
            
            if p95 < 300:
                print("  ✅ EXCELLENT: P95 < 300ms")
            elif p95 < 500:
                print("  ⚠️  GOOD: P95 < 500ms")
            elif p95 < 1000:
                print("  ⚠️  MODERATE: P95 < 1000ms")
            else:
                print("  ❌ NEEDS IMPROVEMENT: P95 > 1000ms")
            
            if success_rate > 99:
                print("  ✅ EXCELLENT: Success rate > 99%")
            elif success_rate > 95:
                print("  ⚠️  GOOD: Success rate > 95%")
            else:
                print("  ❌ NEEDS IMPROVEMENT: Success rate < 95%")
            
            # Save results
            with open("simple_load_test_results.json", "w") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "num_users": num_users,
                    "duration": duration,
                    "total_requests": len(self.results),
                    "success_rate": success_rate,
                    "p50": p50,
                    "p90": p90,
                    "p95": p95,
                    "endpoint_stats": endpoint_stats
                }, f, indent=2)
            
            print("\nResults saved to simple_load_test_results.json")
        
        if self.errors:
            print(f"\n❌ ERRORS (showing first 5):")
            for error in self.errors[:5]:
                print(f"  - {error}")
        
        print(f"\n{'='*60}\n")

if __name__ == "__main__":
    import sys
    
    num_users = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    
    tester = SimpleLoadTester()
    tester.run_load_test(num_users)
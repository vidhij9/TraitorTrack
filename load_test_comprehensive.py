#!/usr/bin/env python3
"""
Comprehensive Load Testing Script for TraceTrack Application
Tests all endpoints systematically with performance targets
"""

import asyncio
import aiohttp
import time
import json
import random
import string
from datetime import datetime
from typing import Dict, List, Tuple
import statistics
from concurrent.futures import ThreadPoolExecutor
import os

# Configuration
BASE_URL = "http://0.0.0.0:5000"
CONCURRENT_USERS = 50
REQUESTS_PER_USER = 10
TARGET_RESPONSE_TIME_MS = 100  # Target: <100ms for all endpoints

# Test user credentials
TEST_USERS = [
    {"username": "admin", "password": "admin123"},
    {"username": "biller1", "password": "password123"},
    {"username": "dispatcher1", "password": "password123"}
]

class LoadTestResult:
    def __init__(self, endpoint: str, method: str):
        self.endpoint = endpoint
        self.method = method
        self.response_times: List[float] = []
        self.status_codes: Dict[int, int] = {}
        self.errors: List[str] = []
        self.start_time = None
        self.end_time = None
    
    def add_result(self, response_time: float, status_code: int, error: str = None):
        self.response_times.append(response_time)
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
        if error:
            self.errors.append(error)
    
    def get_stats(self) -> Dict:
        if not self.response_times:
            return {
                "endpoint": self.endpoint,
                "method": self.method,
                "error": "No successful requests"
            }
        
        sorted_times = sorted(self.response_times)
        return {
            "endpoint": self.endpoint,
            "method": self.method,
            "total_requests": len(self.response_times),
            "avg_response_time_ms": statistics.mean(self.response_times),
            "median_response_time_ms": statistics.median(self.response_times),
            "min_response_time_ms": min(self.response_times),
            "max_response_time_ms": max(self.response_times),
            "p95_response_time_ms": sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0,
            "p99_response_time_ms": sorted_times[int(len(sorted_times) * 0.99)] if sorted_times else 0,
            "status_codes": self.status_codes,
            "error_count": len(self.errors),
            "error_rate": len(self.errors) / max(len(self.response_times), 1),
            "meets_target": statistics.mean(self.response_times) < TARGET_RESPONSE_TIME_MS
        }

class LoadTester:
    def __init__(self):
        self.results: Dict[str, LoadTestResult] = {}
        self.session_cookies = {}
    
    async def login(self, session: aiohttp.ClientSession, username: str, password: str) -> bool:
        """Login and store session cookie"""
        try:
            data = {
                "username": username,
                "password": password,
                "csrf_token": "test_token"  # Simplified for testing
            }
            async with session.post(f"{BASE_URL}/login", data=data, allow_redirects=False) as resp:
                if resp.status in [200, 302, 303]:
                    # Store cookies for this session
                    return True
                return False
        except Exception as e:
            print(f"Login failed for {username}: {e}")
            return False
    
    async def test_endpoint(self, session: aiohttp.ClientSession, method: str, endpoint: str, 
                           data: Dict = None, json_data: Dict = None) -> Tuple[float, int, str]:
        """Test a single endpoint and return response time, status code, and error if any"""
        start_time = time.time()
        error = None
        status_code = 0
        
        try:
            kwargs = {
                "timeout": aiohttp.ClientTimeout(total=30),
                "allow_redirects": False
            }
            
            if data:
                kwargs["data"] = data
            if json_data:
                kwargs["json"] = json_data
                kwargs["headers"] = {"Content-Type": "application/json"}
            
            url = f"{BASE_URL}{endpoint}"
            
            if method == "GET":
                async with session.get(url, **kwargs) as resp:
                    status_code = resp.status
                    await resp.text()  # Consume response body
            elif method == "POST":
                async with session.post(url, **kwargs) as resp:
                    status_code = resp.status
                    await resp.text()
            elif method == "DELETE":
                async with session.delete(url, **kwargs) as resp:
                    status_code = resp.status
                    await resp.text()
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
        except asyncio.TimeoutError:
            error = "Timeout"
            response_time = 30000  # 30 second timeout
            status_code = 0
        except Exception as e:
            error = str(e)
            response_time = (time.time() - start_time) * 1000
            status_code = 0
        
        return response_time, status_code, error
    
    async def run_endpoint_test(self, endpoint: str, method: str = "GET", 
                               data: Dict = None, json_data: Dict = None,
                               auth_required: bool = True):
        """Run load test for a specific endpoint"""
        result_key = f"{method} {endpoint}"
        self.results[result_key] = LoadTestResult(endpoint, method)
        
        print(f"\n🔧 Testing {method} {endpoint}...")
        
        async def test_user_requests(user_idx: int):
            """Run requests for a single user"""
            async with aiohttp.ClientSession() as session:
                # Login if auth required
                if auth_required and user_idx < len(TEST_USERS):
                    user = TEST_USERS[user_idx % len(TEST_USERS)]
                    await self.login(session, user["username"], user["password"])
                
                # Run multiple requests
                for _ in range(REQUESTS_PER_USER):
                    response_time, status_code, error = await self.test_endpoint(
                        session, method, endpoint, data, json_data
                    )
                    self.results[result_key].add_result(response_time, status_code, error)
        
        # Run tests concurrently for all users
        tasks = [test_user_requests(i) for i in range(CONCURRENT_USERS)]
        await asyncio.gather(*tasks)
        
        # Print immediate results
        stats = self.results[result_key].get_stats()
        status = "✅" if stats.get("meets_target", False) else "⚠️"
        print(f"{status} {endpoint}: Avg={stats.get('avg_response_time_ms', 0):.1f}ms, "
              f"P95={stats.get('p95_response_time_ms', 0):.1f}ms, "
              f"Errors={stats.get('error_count', 0)}")
    
    def generate_random_data(self) -> Dict:
        """Generate random test data"""
        return {
            "parent_qr": f"PB{random.randint(10000, 99999)}",
            "child_qr": f"CB{random.randint(10000, 99999)}",
            "bill_number": f"BILL{random.randint(1000000, 9999999)}",
            "customer_name": f"Customer {random.randint(1, 1000)}",
            "destination": random.choice(["New York", "Los Angeles", "Chicago", "Houston"]),
            "expected_parent_bags": random.randint(1, 10),
            "weight_per_parent": 30,
            "csrf_token": "test_token"
        }

async def main():
    """Main load testing function"""
    print("=" * 80)
    print("🚀 COMPREHENSIVE LOAD TESTING FOR TRACETRACK")
    print(f"Configuration: {CONCURRENT_USERS} concurrent users, {REQUESTS_PER_USER} requests each")
    print(f"Target Response Time: <{TARGET_RESPONSE_TIME_MS}ms")
    print("=" * 80)
    
    tester = LoadTester()
    test_data = tester.generate_random_data()
    
    # Test categories with endpoints
    test_plan = {
        "🔐 Authentication Endpoints": [
            ("/login", "GET", None, None, False),
            ("/login", "POST", {"username": "admin", "password": "admin123", "csrf_token": "test"}, None, False),
            ("/logout", "GET", None, None, True),
            ("/register", "GET", None, None, False),
            ("/auth-test", "GET", None, None, False),
        ],
        "📊 Dashboard & Core Pages": [
            ("/", "GET", None, None, False),
            ("/dashboard", "GET", None, None, True),
            ("/profile", "GET", None, None, True),
        ],
        "📦 Scanning Endpoints": [
            ("/scan", "GET", None, None, True),
            ("/scan_parent", "GET", None, None, True),
            ("/scan_child", "GET", None, None, True),
            ("/ajax/scan_parent", "POST", test_data, None, True),
            ("/process_child_scan_fast", "POST", test_data, None, True),
            ("/api/fast_parent_scan", "POST", None, {"parent_qr": test_data["parent_qr"], "child_qr": test_data["child_qr"]}, True),
        ],
        "📋 Bill Management": [
            ("/bills", "GET", None, None, True),
            ("/bill_management", "GET", None, None, True),
            ("/bill/create", "GET", None, None, True),
            ("/bill/1", "GET", None, None, True),
            ("/bill/1/scan_parent", "GET", None, None, True),
            ("/fast/bill_parent_scan", "POST", None, {"bill_id": 1, "parent_qr": test_data["parent_qr"]}, True),
            ("/bill/manual_parent_entry", "POST", {"bill_id": 1, "parent_qr": test_data["parent_qr"], "csrf_token": "test"}, None, True),
        ],
        "👜 Bag Management": [
            ("/bags", "GET", None, None, True),
            ("/bag_management", "GET", None, None, True),
            ("/lookup", "GET", None, None, True),
            ("/bag/PB12345", "GET", None, None, True),
            ("/child_lookup", "GET", None, None, True),
        ],
        "🔌 API Endpoints": [
            ("/api/v2/stats", "GET", None, None, True),
            ("/api/scans", "GET", None, None, True),
            ("/api/bags", "GET", None, None, True),
            ("/api/bills", "GET", None, None, True),
            ("/api/users", "GET", None, None, True),
            ("/api/health", "GET", None, None, False),
            ("/health", "GET", None, None, False),
            ("/api/activity/7", "GET", None, None, True),
            ("/api/scanned-children", "GET", None, None, True),
            ("/api/bill/1/weights", "GET", None, None, True),
        ],
        "👤 User & Admin Management": [
            ("/user_management", "GET", None, None, True),
            ("/admin/users/1", "GET", None, None, True),
            ("/admin/users/1/profile", "GET", None, None, True),
            ("/admin/promotions", "GET", None, None, True),
            ("/admin/system-integrity", "GET", None, None, True),
        ],
        "📈 Reports & Summaries": [
            ("/scans", "GET", None, None, True),
            ("/api/bill_summary/eod", "GET", None, None, True),
            ("/eod_summary_preview", "GET", None, None, True),
        ]
    }
    
    # Run tests for each category
    for category, endpoints in test_plan.items():
        print(f"\n{category}")
        print("-" * 60)
        
        for endpoint_config in endpoints:
            endpoint, method, data, json_data, auth_required = endpoint_config
            await tester.run_endpoint_test(endpoint, method, data, json_data, auth_required)
            await asyncio.sleep(0.5)  # Small delay between endpoint tests
    
    # Print summary report
    print("\n" + "=" * 80)
    print("📊 LOAD TEST SUMMARY REPORT")
    print("=" * 80)
    
    # Categorize results
    passing_endpoints = []
    slow_endpoints = []
    failing_endpoints = []
    
    for key, result in tester.results.items():
        stats = result.get_stats()
        if "error" in stats or stats.get("error_rate", 0) > 0.1:
            failing_endpoints.append(stats)
        elif not stats.get("meets_target", False):
            slow_endpoints.append(stats)
        else:
            passing_endpoints.append(stats)
    
    # Print passing endpoints
    if passing_endpoints:
        print(f"\n✅ PASSING ENDPOINTS ({len(passing_endpoints)}):")
        for stats in sorted(passing_endpoints, key=lambda x: x.get("avg_response_time_ms", 0)):
            print(f"  • {stats['method']} {stats['endpoint']}: "
                  f"Avg={stats.get('avg_response_time_ms', 0):.1f}ms, "
                  f"P95={stats.get('p95_response_time_ms', 0):.1f}ms")
    
    # Print slow endpoints
    if slow_endpoints:
        print(f"\n⚠️ SLOW ENDPOINTS ({len(slow_endpoints)}) - Need Optimization:")
        for stats in sorted(slow_endpoints, key=lambda x: x.get("avg_response_time_ms', 0), reverse=True):
            print(f"  • {stats['method']} {stats['endpoint']}: "
                  f"Avg={stats.get('avg_response_time_ms', 0):.1f}ms "
                  f"(Target: <{TARGET_RESPONSE_TIME_MS}ms), "
                  f"P95={stats.get('p95_response_time_ms', 0):.1f}ms")
    
    # Print failing endpoints
    if failing_endpoints:
        print(f"\n❌ FAILING ENDPOINTS ({len(failing_endpoints)}):")
        for stats in failing_endpoints:
            print(f"  • {stats['method']} {stats['endpoint']}: "
                  f"Errors={stats.get('error_count', 0)}, "
                  f"Error Rate={stats.get('error_rate', 0):.1%}")
    
    # Overall statistics
    all_response_times = []
    total_errors = 0
    total_requests = 0
    
    for result in tester.results.values():
        all_response_times.extend(result.response_times)
        total_errors += len(result.errors)
        total_requests += len(result.response_times) + len(result.errors)
    
    if all_response_times:
        sorted_all_times = sorted(all_response_times)
        print("\n" + "=" * 80)
        print("📈 OVERALL PERFORMANCE METRICS:")
        print(f"  Total Requests: {total_requests}")
        print(f"  Total Errors: {total_errors} ({total_errors/max(total_requests, 1)*100:.1f}%)")
        print(f"  Average Response Time: {statistics.mean(all_response_times):.1f}ms")
        print(f"  Median Response Time: {statistics.median(all_response_times):.1f}ms")
        print(f"  P95 Response Time: {sorted_all_times[int(len(sorted_all_times) * 0.95)]:.1f}ms")
        print(f"  P99 Response Time: {sorted_all_times[int(len(sorted_all_times) * 0.99)]:.1f}ms")
        print(f"  Min Response Time: {min(all_response_times):.1f}ms")
        print(f"  Max Response Time: {max(all_response_times):.1f}ms")
    
    # Final verdict
    print("\n" + "=" * 80)
    if not slow_endpoints and not failing_endpoints:
        print("🎉 ALL ENDPOINTS MEET PERFORMANCE TARGETS!")
    else:
        print(f"⚠️ {len(slow_endpoints)} slow endpoints and {len(failing_endpoints)} failing endpoints need attention.")
    print("=" * 80)
    
    # Save detailed results to file
    with open("load_test_results.json", "w") as f:
        results_data = {
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "concurrent_users": CONCURRENT_USERS,
                "requests_per_user": REQUESTS_PER_USER,
                "target_response_time_ms": TARGET_RESPONSE_TIME_MS
            },
            "results": {
                key: result.get_stats() for key, result in tester.results.items()
            }
        }
        json.dump(results_data, f, indent=2)
    
    print("\n📁 Detailed results saved to load_test_results.json")

if __name__ == "__main__":
    asyncio.run(main())
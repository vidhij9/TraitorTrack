#!/usr/bin/env python3
"""
Focused Load Testing Script for Critical Endpoints
Tests performance of key endpoints that have shown issues
"""

import asyncio
import aiohttp
import time
import json
import random
import statistics
from datetime import datetime
from typing import Dict, List, Tuple

# Configuration
BASE_URL = "http://0.0.0.0:5000"
CONCURRENT_USERS = 20
REQUESTS_PER_USER = 5
TARGET_RESPONSE_TIME_MS = 100

class LoadTestResult:
    def __init__(self, endpoint: str, method: str):
        self.endpoint = endpoint
        self.method = method
        self.response_times: List[float] = []
        self.status_codes: Dict[int, int] = {}
        self.errors: List[str] = []
    
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
            "error_rate": len(self.errors) / max(len(self.response_times) + len(self.errors), 1),
            "meets_target": statistics.mean(self.response_times) < TARGET_RESPONSE_TIME_MS
        }

async def test_endpoint(session: aiohttp.ClientSession, method: str, endpoint: str, 
                       data: Dict = None, json_data: Dict = None) -> Tuple[float, int, str]:
    """Test a single endpoint and return response time, status code, and error if any"""
    start_time = time.time()
    error = None
    status_code = 0
    
    try:
        kwargs = {
            "timeout": aiohttp.ClientTimeout(total=10),
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
                await resp.text()
        elif method == "POST":
            async with session.post(url, **kwargs) as resp:
                status_code = resp.status
                await resp.text()
        
        response_time = (time.time() - start_time) * 1000
        
    except asyncio.TimeoutError:
        error = "Timeout"
        response_time = 10000
        status_code = 0
    except Exception as e:
        error = str(e)
        response_time = (time.time() - start_time) * 1000
        status_code = 0
    
    return response_time, status_code, error

async def run_endpoint_test(endpoint: str, method: str = "GET", 
                           data: Dict = None, json_data: Dict = None):
    """Run load test for a specific endpoint"""
    result = LoadTestResult(endpoint, method)
    
    print(f"Testing {method} {endpoint}...")
    
    async def test_user_requests():
        """Run requests for a single user"""
        async with aiohttp.ClientSession() as session:
            for _ in range(REQUESTS_PER_USER):
                response_time, status_code, error = await test_endpoint(
                    session, method, endpoint, data, json_data
                )
                result.add_result(response_time, status_code, error)
    
    # Run tests concurrently for all users
    tasks = [test_user_requests() for _ in range(CONCURRENT_USERS)]
    await asyncio.gather(*tasks)
    
    # Return statistics
    return result.get_stats()

async def main():
    """Main load testing function for critical endpoints"""
    print("=" * 80)
    print("🚀 FOCUSED LOAD TESTING FOR CRITICAL ENDPOINTS")
    print(f"Configuration: {CONCURRENT_USERS} concurrent users, {REQUESTS_PER_USER} requests each")
    print(f"Target Response Time: <{TARGET_RESPONSE_TIME_MS}ms")
    print("=" * 80)
    
    # Test data
    test_data = {
        "parent_qr": f"PB{random.randint(10000, 99999)}",
        "child_qr": f"CB{random.randint(10000, 99999)}",
        "bill_id": 1,
        "csrf_token": "test_token"
    }
    
    # Critical endpoints to test
    critical_endpoints = [
        # Health checks - should be fast
        ("/health", "GET", None, None),
        ("/api/health", "GET", None, None),
        
        # Main pages - checking for slow queries
        ("/", "GET", None, None),
        ("/login", "GET", None, None),
        
        # API endpoints that showed slow performance
        ("/api/v2/stats", "GET", None, None),
        
        # Scanning endpoints - critical for operations
        ("/api/fast_parent_scan", "POST", None, {
            "parent_qr": test_data["parent_qr"],
            "child_qr": test_data["child_qr"]
        }),
        
        # Bill operations
        ("/fast/bill_parent_scan", "POST", None, {
            "bill_id": test_data["bill_id"],
            "parent_qr": test_data["parent_qr"]
        }),
    ]
    
    results = []
    for endpoint_config in critical_endpoints:
        endpoint, method, data, json_data = endpoint_config
        stats = await run_endpoint_test(endpoint, method, data, json_data)
        results.append(stats)
        
        # Print immediate result
        status = "✅" if stats.get("meets_target", False) else "⚠️"
        print(f"{status} {endpoint}: Avg={stats.get('avg_response_time_ms', 0):.1f}ms, "
              f"P95={stats.get('p95_response_time_ms', 0):.1f}ms, "
              f"Errors={stats.get('error_count', 0)}")
        print("-" * 60)
        await asyncio.sleep(0.5)
    
    # Print summary
    print("\n" + "=" * 80)
    print("📊 LOAD TEST SUMMARY")
    print("=" * 80)
    
    passing = [r for r in results if r.get("meets_target", False) and r.get("error_rate", 0) < 0.1]
    slow = [r for r in results if not r.get("meets_target", False) and r.get("error_rate", 0) < 0.1]
    failing = [r for r in results if r.get("error_rate", 0) >= 0.1]
    
    if passing:
        print(f"\n✅ PASSING ({len(passing)} endpoints):")
        for r in passing:
            print(f"  • {r['method']} {r['endpoint']}: {r['avg_response_time_ms']:.1f}ms")
    
    if slow:
        print(f"\n⚠️ SLOW ({len(slow)} endpoints) - Need Optimization:")
        for r in sorted(slow, key=lambda x: x['avg_response_time_ms'], reverse=True):
            print(f"  • {r['method']} {r['endpoint']}: {r['avg_response_time_ms']:.1f}ms (Target: <{TARGET_RESPONSE_TIME_MS}ms)")
    
    if failing:
        print(f"\n❌ FAILING ({len(failing)} endpoints):")
        for r in failing:
            print(f"  • {r['method']} {r['endpoint']}: Error rate {r['error_rate']:.1%}")
    
    # Overall assessment
    total_endpoints = len(results)
    print(f"\n📈 OVERALL: {len(passing)}/{total_endpoints} endpoints meet performance targets")
    
    if len(passing) == total_endpoints:
        print("🎉 ALL ENDPOINTS MEET PERFORMANCE TARGETS!")
    else:
        print(f"⚠️ {len(slow) + len(failing)} endpoints need attention")
    
    # Save results
    with open("load_test_focused_results.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "concurrent_users": CONCURRENT_USERS,
                "requests_per_user": REQUESTS_PER_USER,
                "target_response_time_ms": TARGET_RESPONSE_TIME_MS
            },
            "results": results
        }, f, indent=2)
    
    print("\n📁 Results saved to load_test_focused_results.json")

if __name__ == "__main__":
    asyncio.run(main())
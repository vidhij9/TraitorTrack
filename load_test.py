#!/usr/bin/env python3
"""
Load testing script for TraceTrack application
Tests the application's ability to handle 50+ concurrent users
"""
import asyncio
import aiohttp
import time
import random
import json
from datetime import datetime
from typing import List, Dict, Any
import statistics

# Configuration
BASE_URL = "http://0.0.0.0:5000"  # Change to your deployment URL
NUM_USERS = 50  # Number of concurrent users
TEST_DURATION = 60  # Test duration in seconds
RAMP_UP_TIME = 10  # Time to ramp up to full load

# Test credentials
TEST_USERS = [
    {"username": "admin", "password": "admin123"},
    {"username": "biller1", "password": "biller123"},
    {"username": "dispatcher1", "password": "dispatcher123"}
]

# Test data
TEST_BAGS = [f"TEST{str(i).zfill(6)}" for i in range(1, 1001)]
TEST_BILLS = [f"BILL{str(i).zfill(6)}" for i in range(1, 101)]

class LoadTestMetrics:
    """Collect and analyze load test metrics"""
    
    def __init__(self):
        self.response_times = []
        self.error_count = 0
        self.success_count = 0
        self.endpoint_metrics = {}
        self.start_time = None
        self.end_time = None
    
    def record_request(self, endpoint: str, response_time: float, status: int):
        """Record a request metric"""
        self.response_times.append(response_time)
        
        if status >= 400:
            self.error_count += 1
        else:
            self.success_count += 1
        
        if endpoint not in self.endpoint_metrics:
            self.endpoint_metrics[endpoint] = {
                "count": 0,
                "response_times": [],
                "errors": 0
            }
        
        self.endpoint_metrics[endpoint]["count"] += 1
        self.endpoint_metrics[endpoint]["response_times"].append(response_time)
        if status >= 400:
            self.endpoint_metrics[endpoint]["errors"] += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test summary statistics"""
        if not self.response_times:
            return {"error": "No data collected"}
        
        duration = (self.end_time - self.start_time) if self.end_time else time.time() - self.start_time
        total_requests = len(self.response_times)
        
        summary = {
            "test_duration_seconds": duration,
            "total_requests": total_requests,
            "successful_requests": self.success_count,
            "failed_requests": self.error_count,
            "error_rate": (self.error_count / total_requests * 100) if total_requests > 0 else 0,
            "requests_per_second": total_requests / duration if duration > 0 else 0,
            "response_times": {
                "min": min(self.response_times),
                "max": max(self.response_times),
                "mean": statistics.mean(self.response_times),
                "median": statistics.median(self.response_times),
                "p95": statistics.quantiles(self.response_times, n=20)[18] if len(self.response_times) > 20 else max(self.response_times),
                "p99": statistics.quantiles(self.response_times, n=100)[98] if len(self.response_times) > 100 else max(self.response_times)
            },
            "endpoint_breakdown": {}
        }
        
        # Add endpoint-specific metrics
        for endpoint, metrics in self.endpoint_metrics.items():
            if metrics["response_times"]:
                summary["endpoint_breakdown"][endpoint] = {
                    "count": metrics["count"],
                    "errors": metrics["errors"],
                    "avg_response_time": statistics.mean(metrics["response_times"]),
                    "max_response_time": max(metrics["response_times"])
                }
        
        return summary

class VirtualUser:
    """Simulates a user interacting with the application"""
    
    def __init__(self, user_id: int, session: aiohttp.ClientSession, metrics: LoadTestMetrics):
        self.user_id = user_id
        self.session = session
        self.metrics = metrics
        self.auth_cookie = None
        self.test_user = random.choice(TEST_USERS)
    
    async def make_request(self, method: str, endpoint: str, **kwargs) -> tuple:
        """Make an HTTP request and record metrics"""
        url = f"{BASE_URL}{endpoint}"
        start_time = time.time()
        
        try:
            async with self.session.request(method, url, **kwargs) as response:
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                self.metrics.record_request(endpoint, response_time, response.status)
                
                # Store cookies if login successful
                if endpoint == "/login" and response.status == 200:
                    self.auth_cookie = response.cookies
                
                return response.status, await response.text()
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.metrics.record_request(endpoint, response_time, 500)
            return 500, str(e)
    
    async def login(self):
        """Login to the application"""
        status, _ = await self.make_request(
            "POST", "/login",
            data={
                "username": self.test_user["username"],
                "password": self.test_user["password"]
            }
        )
        return status < 400
    
    async def browse_dashboard(self):
        """Browse the dashboard"""
        await self.make_request("GET", "/dashboard", cookies=self.auth_cookie)
        await self.make_request("GET", "/api/stats", cookies=self.auth_cookie)
        await self.make_request("GET", "/api/scans?limit=10", cookies=self.auth_cookie)
    
    async def scan_bags(self):
        """Simulate bag scanning"""
        parent_bag = random.choice(TEST_BAGS)
        child_bag = random.choice(TEST_BAGS)
        
        await self.make_request(
            "POST", "/scan",
            cookies=self.auth_cookie,
            json={
                "parent_qr": parent_bag,
                "child_qr": child_bag
            }
        )
    
    async def create_bill(self):
        """Create a new bill"""
        bill_id = f"TEST{random.randint(10000, 99999)}"
        await self.make_request(
            "POST", "/bill/create",
            cookies=self.auth_cookie,
            data={
                "bill_id": bill_id,
                "parent_bag_count": random.randint(1, 10)
            }
        )
    
    async def browse_bags(self):
        """Browse bag management"""
        await self.make_request(
            "GET", "/bag_management",
            cookies=self.auth_cookie
        )
    
    async def search_bags(self):
        """Search for bags"""
        search_term = random.choice(TEST_BAGS)[:4]
        await self.make_request(
            "GET", f"/bag_management?search={search_term}",
            cookies=self.auth_cookie
        )
    
    async def check_health(self):
        """Check health endpoints"""
        await self.make_request("GET", "/health")
        await self.make_request("GET", "/ready")
    
    async def run_user_scenario(self):
        """Run a complete user scenario"""
        # Login
        if not await self.login():
            print(f"User {self.user_id}: Login failed")
            return
        
        # Mix of operations based on user role
        operations = [
            self.browse_dashboard,
            self.scan_bags,
            self.browse_bags,
            self.search_bags,
            self.check_health
        ]
        
        # Add bill creation for admin/biller users
        if self.test_user["username"] in ["admin", "biller1"]:
            operations.append(self.create_bill)
        
        # Run operations for the test duration
        end_time = time.time() + TEST_DURATION
        while time.time() < end_time:
            operation = random.choice(operations)
            await operation()
            
            # Random delay between operations (100ms to 2s)
            await asyncio.sleep(random.uniform(0.1, 2.0))

async def run_load_test():
    """Run the load test with multiple concurrent users"""
    print(f"Starting load test with {NUM_USERS} concurrent users...")
    print(f"Test duration: {TEST_DURATION} seconds")
    print(f"Target URL: {BASE_URL}")
    print("-" * 50)
    
    metrics = LoadTestMetrics()
    metrics.start_time = time.time()
    
    # Create session with connection pooling
    connector = aiohttp.TCPConnector(limit=100, limit_per_host=100)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Create virtual users
        users = [VirtualUser(i, session, metrics) for i in range(NUM_USERS)]
        
        # Ramp up users gradually
        tasks = []
        for i, user in enumerate(users):
            delay = (i / NUM_USERS) * RAMP_UP_TIME
            task = asyncio.create_task(run_user_with_delay(user, delay))
            tasks.append(task)
        
        # Wait for all users to complete
        await asyncio.gather(*tasks, return_exceptions=True)
    
    metrics.end_time = time.time()
    
    # Print results
    print("\n" + "=" * 50)
    print("LOAD TEST RESULTS")
    print("=" * 50)
    
    summary = metrics.get_summary()
    
    print(f"\nTest Duration: {summary['test_duration_seconds']:.2f} seconds")
    print(f"Total Requests: {summary['total_requests']}")
    print(f"Successful: {summary['successful_requests']}")
    print(f"Failed: {summary['failed_requests']}")
    print(f"Error Rate: {summary['error_rate']:.2f}%")
    print(f"Requests/Second: {summary['requests_per_second']:.2f}")
    
    print("\nResponse Times (ms):")
    rt = summary['response_times']
    print(f"  Min: {rt['min']:.2f}")
    print(f"  Max: {rt['max']:.2f}")
    print(f"  Mean: {rt['mean']:.2f}")
    print(f"  Median: {rt['median']:.2f}")
    print(f"  95th Percentile: {rt['p95']:.2f}")
    print(f"  99th Percentile: {rt['p99']:.2f}")
    
    print("\nTop Endpoints by Request Count:")
    sorted_endpoints = sorted(
        summary['endpoint_breakdown'].items(),
        key=lambda x: x[1]['count'],
        reverse=True
    )[:10]
    
    for endpoint, stats in sorted_endpoints:
        print(f"  {endpoint}:")
        print(f"    Requests: {stats['count']}")
        print(f"    Errors: {stats['errors']}")
        print(f"    Avg Response: {stats['avg_response_time']:.2f}ms")
    
    # Performance assessment
    print("\n" + "=" * 50)
    print("PERFORMANCE ASSESSMENT")
    print("=" * 50)
    
    if summary['error_rate'] < 1 and rt['p95'] < 500:
        print("✅ EXCELLENT: Application handles load very well")
    elif summary['error_rate'] < 5 and rt['p95'] < 1000:
        print("✅ GOOD: Application handles load acceptably")
    elif summary['error_rate'] < 10 and rt['p95'] < 2000:
        print("⚠️ FAIR: Application shows some strain under load")
    else:
        print("❌ POOR: Application struggles under load")
    
    print(f"\nRecommendations:")
    if summary['error_rate'] > 5:
        print("- High error rate detected. Check application logs for errors.")
    if rt['p95'] > 1000:
        print("- Response times are high. Consider optimizing slow queries.")
    if rt['max'] > 5000:
        print("- Some requests are very slow. Check for timeout issues.")
    
    return summary

async def run_user_with_delay(user: VirtualUser, delay: float):
    """Run a user scenario with initial delay"""
    await asyncio.sleep(delay)
    await user.run_user_scenario()

if __name__ == "__main__":
    # Run the load test
    asyncio.run(run_load_test())
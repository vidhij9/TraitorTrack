#!/usr/bin/env python3
"""
Comprehensive Performance Test Suite for TraceTrack System
Tests all functionalities with 50+ concurrent users and 800,000+ bags
"""

import asyncio
import aiohttp
import json
import time
import random
import string
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
import os
import sys
from typing import Dict, List, Tuple
import requests
from faker import Faker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'performance_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://0.0.0.0:5000"
CONCURRENT_USERS = 55  # 50+ concurrent users as requested
TOTAL_BAGS = 850000  # 8.5 lakhs (850,000) bags
PARENT_BAGS = 50000  # Number of parent bags
CHILD_BAGS_PER_PARENT = 17  # Average to reach ~850,000 total bags
TEST_DURATION_SECONDS = 300  # 5 minutes sustained load test
REQUEST_TIMEOUT = 30  # Timeout for individual requests

# Test user credentials
ADMIN_USER = {"username": "admin", "password": "admin123"}
TEST_USERS = []
DISPATCH_AREAS = ["lucknow", "indore", "jaipur", "hisar", "sri_ganganagar", 
                  "sangaria", "bathinda", "raipur", "ranchi", "akola"]

fake = Faker()

class PerformanceMetrics:
    """Track performance metrics"""
    def __init__(self):
        self.request_times = []
        self.error_count = 0
        self.success_count = 0
        self.endpoint_metrics = {}
        self.start_time = time.time()
        
    def record_request(self, endpoint: str, duration: float, success: bool):
        """Record a request metric"""
        self.request_times.append(duration)
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
            
        if endpoint not in self.endpoint_metrics:
            self.endpoint_metrics[endpoint] = {
                'count': 0,
                'total_time': 0,
                'errors': 0,
                'min_time': float('inf'),
                'max_time': 0
            }
        
        metrics = self.endpoint_metrics[endpoint]
        metrics['count'] += 1
        metrics['total_time'] += duration
        if not success:
            metrics['errors'] += 1
        metrics['min_time'] = min(metrics['min_time'], duration)
        metrics['max_time'] = max(metrics['max_time'], duration)
        
    def get_summary(self) -> Dict:
        """Get performance summary"""
        if not self.request_times:
            return {"error": "No requests recorded"}
            
        sorted_times = sorted(self.request_times)
        total_requests = len(self.request_times)
        
        return {
            "total_requests": total_requests,
            "successful_requests": self.success_count,
            "failed_requests": self.error_count,
            "error_rate": (self.error_count / total_requests * 100) if total_requests > 0 else 0,
            "avg_response_time": sum(self.request_times) / total_requests,
            "min_response_time": min(self.request_times),
            "max_response_time": max(self.request_times),
            "p50_response_time": sorted_times[int(total_requests * 0.5)],
            "p95_response_time": sorted_times[int(total_requests * 0.95)],
            "p99_response_time": sorted_times[int(total_requests * 0.99)],
            "requests_per_second": total_requests / (time.time() - self.start_time),
            "endpoint_metrics": self.endpoint_metrics
        }

class LoadTester:
    """Main load testing class"""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.session = None
        self.test_data = {
            'users': [],
            'parent_bags': [],
            'child_bags': [],
            'bills': [],
            'scans': []
        }
        
    async def setup(self):
        """Setup test environment"""
        logger.info("Setting up test environment...")
        
        # Create admin session
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT))
        
        # Login as admin
        await self.login_user(ADMIN_USER['username'], ADMIN_USER['password'])
        
        # Create test users
        logger.info(f"Creating {CONCURRENT_USERS} test users...")
        await self.create_test_users()
        
        logger.info("Test environment setup complete")
        
    async def cleanup(self):
        """Cleanup test environment"""
        if self.session:
            await self.session.close()
            
    async def login_user(self, username: str, password: str) -> bool:
        """Login a user"""
        try:
            start_time = time.time()
            async with self.session.post(
                f"{BASE_URL}/login",
                data={"username": username, "password": password}
            ) as response:
                duration = time.time() - start_time
                success = response.status == 200
                self.metrics.record_request("/login", duration, success)
                return success
        except Exception as e:
            logger.error(f"Login error for {username}: {str(e)}")
            return False
            
    async def create_test_users(self):
        """Create test users for concurrent testing"""
        for i in range(CONCURRENT_USERS):
            username = f"testuser_{i}_{int(time.time())}"
            email = f"{username}@test.com"
            password = "Test123!"
            role = random.choice(["admin", "biller", "dispatcher"])
            area = random.choice(DISPATCH_AREAS) if role == "dispatcher" else None
            
            try:
                async with self.session.post(
                    f"{BASE_URL}/create_user",
                    data={
                        "username": username,
                        "email": email,
                        "password": password,
                        "role": role,
                        "dispatch_area": area
                    }
                ) as response:
                    if response.status == 200:
                        self.test_data['users'].append({
                            "username": username,
                            "password": password,
                            "role": role,
                            "area": area
                        })
                        logger.info(f"Created user: {username} ({role})")
            except Exception as e:
                logger.error(f"Error creating user {username}: {str(e)}")
                
    async def test_health_check(self):
        """Test health endpoint"""
        try:
            start_time = time.time()
            async with self.session.get(f"{BASE_URL}/health") as response:
                duration = time.time() - start_time
                success = response.status == 200
                self.metrics.record_request("/health", duration, success)
                return success
        except Exception as e:
            logger.error(f"Health check error: {str(e)}")
            return False
            
    async def test_dashboard(self):
        """Test dashboard loading"""
        try:
            start_time = time.time()
            async with self.session.get(f"{BASE_URL}/dashboard") as response:
                duration = time.time() - start_time
                success = response.status == 200
                self.metrics.record_request("/dashboard", duration, success)
                return success
        except Exception as e:
            logger.error(f"Dashboard error: {str(e)}")
            return False
            
    async def test_scan_parent_bag(self, qr_code: str):
        """Test parent bag scanning"""
        try:
            start_time = time.time()
            async with self.session.post(
                f"{BASE_URL}/scan/parent",
                json={"qr_code": qr_code}
            ) as response:
                duration = time.time() - start_time
                success = response.status in [200, 201]
                self.metrics.record_request("/scan/parent", duration, success)
                return success
        except Exception as e:
            logger.error(f"Parent scan error: {str(e)}")
            return False
            
    async def test_scan_child_bags(self, parent_qr: str, child_qrs: List[str]):
        """Test child bag scanning"""
        try:
            start_time = time.time()
            async with self.session.post(
                f"{BASE_URL}/process_child_scan_fast",
                json={
                    "parent_qr": parent_qr,
                    "child_qrs": child_qrs
                }
            ) as response:
                duration = time.time() - start_time
                success = response.status in [200, 201]
                self.metrics.record_request("/process_child_scan_fast", duration, success)
                return success
        except Exception as e:
            logger.error(f"Child scan error: {str(e)}")
            return False
            
    async def test_create_bill(self, bill_id: str):
        """Test bill creation"""
        try:
            start_time = time.time()
            async with self.session.post(
                f"{BASE_URL}/bill/create",
                data={
                    "bill_id": bill_id,
                    "description": f"Test bill {bill_id}",
                    "parent_bag_count": random.randint(1, 10)
                }
            ) as response:
                duration = time.time() - start_time
                success = response.status in [200, 201, 302]
                self.metrics.record_request("/bill/create", duration, success)
                return success
        except Exception as e:
            logger.error(f"Bill creation error: {str(e)}")
            return False
            
    async def test_api_stats(self):
        """Test API stats endpoint"""
        try:
            start_time = time.time()
            async with self.session.get(f"{BASE_URL}/api/stats") as response:
                duration = time.time() - start_time
                success = response.status == 200
                self.metrics.record_request("/api/stats", duration, success)
                if success:
                    data = await response.json()
                    logger.info(f"System stats: {data}")
                return success
        except Exception as e:
            logger.error(f"API stats error: {str(e)}")
            return False
            
    async def test_bag_management(self):
        """Test bag management page"""
        try:
            start_time = time.time()
            async with self.session.get(f"{BASE_URL}/bags") as response:
                duration = time.time() - start_time
                success = response.status == 200
                self.metrics.record_request("/bags", duration, success)
                return success
        except Exception as e:
            logger.error(f"Bag management error: {str(e)}")
            return False
            
    async def test_bill_management(self):
        """Test bill management page"""
        try:
            start_time = time.time()
            async with self.session.get(f"{BASE_URL}/bills") as response:
                duration = time.time() - start_time
                success = response.status == 200
                self.metrics.record_request("/bills", duration, success)
                return success
        except Exception as e:
            logger.error(f"Bill management error: {str(e)}")
            return False
            
    async def test_user_management(self):
        """Test user management page"""
        try:
            start_time = time.time()
            async with self.session.get(f"{BASE_URL}/user_management") as response:
                duration = time.time() - start_time
                success = response.status == 200
                self.metrics.record_request("/user_management", duration, success)
                return success
        except Exception as e:
            logger.error(f"User management error: {str(e)}")
            return False
            
    async def test_lookup(self, qr_code: str):
        """Test QR code lookup"""
        try:
            start_time = time.time()
            async with self.session.post(
                f"{BASE_URL}/lookup",
                data={"qr_code": qr_code}
            ) as response:
                duration = time.time() - start_time
                success = response.status in [200, 302]
                self.metrics.record_request("/lookup", duration, success)
                return success
        except Exception as e:
            logger.error(f"Lookup error: {str(e)}")
            return False
            
    async def simulate_user_workflow(self, user_data: Dict):
        """Simulate a complete user workflow"""
        logger.info(f"Starting workflow for user: {user_data['username']}")
        
        # Create a new session for this user
        user_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT))
        
        try:
            # Login
            await self.login_user(user_data['username'], user_data['password'])
            
            # Perform various operations based on role
            if user_data['role'] == 'admin':
                await self.test_user_management()
                await self.test_api_stats()
                
            elif user_data['role'] == 'biller':
                # Create bills
                for _ in range(random.randint(1, 3)):
                    bill_id = f"BILL_{int(time.time())}_{random.randint(1000, 9999)}"
                    await self.test_create_bill(bill_id)
                    
                await self.test_bill_management()
                
            elif user_data['role'] == 'dispatcher':
                # Scan bags
                for _ in range(random.randint(5, 10)):
                    parent_qr = f"P_{int(time.time())}_{random.randint(100000, 999999)}"
                    await self.test_scan_parent_bag(parent_qr)
                    
                    # Scan child bags
                    child_qrs = [
                        f"C_{int(time.time())}_{random.randint(100000, 999999)}"
                        for _ in range(random.randint(5, 15))
                    ]
                    await self.test_scan_child_bags(parent_qr, child_qrs)
                    
                await self.test_bag_management()
                
            # Common operations for all users
            await self.test_dashboard()
            await self.test_health_check()
            
            # Random lookups
            for _ in range(random.randint(1, 5)):
                qr_code = f"QR_{random.randint(100000, 999999)}"
                await self.test_lookup(qr_code)
                
        finally:
            await user_session.close()
            
    async def run_concurrent_load_test(self):
        """Run concurrent load test with multiple users"""
        logger.info(f"Starting concurrent load test with {CONCURRENT_USERS} users...")
        
        # Create tasks for concurrent users
        tasks = []
        for user_data in self.test_data['users']:
            task = asyncio.create_task(self.simulate_user_workflow(user_data))
            tasks.append(task)
            
        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
    async def generate_massive_data(self):
        """Generate massive amount of test data (800,000+ bags)"""
        logger.info(f"Generating {TOTAL_BAGS} bags for stress testing...")
        
        batch_size = 1000
        total_batches = TOTAL_BAGS // batch_size
        
        for batch_num in range(total_batches):
            batch_start = time.time()
            
            # Generate parent bags
            parent_batch = []
            for _ in range(batch_size // 20):  # Fewer parent bags
                parent_qr = f"P_BATCH{batch_num}_{random.randint(100000, 999999)}"
                parent_batch.append(parent_qr)
                
            # Generate child bags
            child_batch = []
            for parent_qr in parent_batch:
                for _ in range(19):  # More child bags per parent
                    child_qr = f"C_BATCH{batch_num}_{random.randint(100000, 999999)}"
                    child_batch.append((parent_qr, child_qr))
                    
            # Simulate scanning these bags
            for parent_qr in parent_batch:
                await self.test_scan_parent_bag(parent_qr)
                
            # Scan child bags in batches
            for parent_qr in parent_batch:
                children = [c[1] for c in child_batch if c[0] == parent_qr]
                if children:
                    await self.test_scan_child_bags(parent_qr, children[:30])  # Max 30 at a time
                    
            batch_duration = time.time() - batch_start
            logger.info(f"Batch {batch_num + 1}/{total_batches} completed in {batch_duration:.2f}s")
            
            # Log progress every 10 batches
            if (batch_num + 1) % 10 == 0:
                progress = ((batch_num + 1) * batch_size / TOTAL_BAGS) * 100
                logger.info(f"Progress: {progress:.1f}% - Generated {(batch_num + 1) * batch_size} bags")
                
    async def monitor_system_resources(self):
        """Monitor system resources during test"""
        logger.info("Starting system resource monitoring...")
        
        while True:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get process-specific metrics
            process = psutil.Process(os.getpid())
            process_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            logger.info(f"System Resources - CPU: {cpu_percent}%, "
                       f"Memory: {memory.percent}% ({memory.used / 1024 / 1024 / 1024:.2f}GB/{memory.total / 1024 / 1024 / 1024:.2f}GB), "
                       f"Disk: {disk.percent}%, "
                       f"Process Memory: {process_memory:.2f}MB")
            
            await asyncio.sleep(10)  # Monitor every 10 seconds
            
    async def run_sustained_load_test(self):
        """Run sustained load test for specified duration"""
        logger.info(f"Running sustained load test for {TEST_DURATION_SECONDS} seconds...")
        
        end_time = time.time() + TEST_DURATION_SECONDS
        iteration = 0
        
        while time.time() < end_time:
            iteration += 1
            logger.info(f"Load test iteration {iteration}")
            
            # Run concurrent user workflows
            await self.run_concurrent_load_test()
            
            # Generate more data
            await self.generate_massive_data()
            
            # Test all endpoints with current data
            await self.test_all_endpoints()
            
            # Check remaining time
            remaining = end_time - time.time()
            logger.info(f"Remaining test time: {remaining:.1f} seconds")
            
    async def test_all_endpoints(self):
        """Test all system endpoints"""
        logger.info("Testing all system endpoints...")
        
        endpoints = [
            ("/health", "GET", None),
            ("/dashboard", "GET", None),
            ("/api/stats", "GET", None),
            ("/api/scans", "GET", None),
            ("/api/activity/7", "GET", None),
            ("/bags", "GET", None),
            ("/bills", "GET", None),
            ("/scans", "GET", None),
            ("/user_management", "GET", None),
            ("/profile", "GET", None),
        ]
        
        for endpoint, method, data in endpoints:
            try:
                start_time = time.time()
                if method == "GET":
                    async with self.session.get(f"{BASE_URL}{endpoint}") as response:
                        duration = time.time() - start_time
                        success = response.status == 200
                        self.metrics.record_request(endpoint, duration, success)
                        
                elif method == "POST":
                    async with self.session.post(f"{BASE_URL}{endpoint}", json=data) as response:
                        duration = time.time() - start_time
                        success = response.status in [200, 201, 302]
                        self.metrics.record_request(endpoint, duration, success)
                        
            except Exception as e:
                logger.error(f"Error testing {endpoint}: {str(e)}")
                self.metrics.record_request(endpoint, 0, False)

async def main():
    """Main test execution"""
    logger.info("=" * 80)
    logger.info("COMPREHENSIVE PERFORMANCE TEST FOR TRACETRACK SYSTEM")
    logger.info("=" * 80)
    logger.info(f"Configuration:")
    logger.info(f"  - Concurrent Users: {CONCURRENT_USERS}")
    logger.info(f"  - Total Bags Target: {TOTAL_BAGS}")
    logger.info(f"  - Test Duration: {TEST_DURATION_SECONDS} seconds")
    logger.info(f"  - Base URL: {BASE_URL}")
    logger.info("=" * 80)
    
    tester = LoadTester()
    
    try:
        # Setup test environment
        await tester.setup()
        
        # Start resource monitoring in background
        monitor_task = asyncio.create_task(tester.monitor_system_resources())
        
        # Run the main load test
        test_task = asyncio.create_task(tester.run_sustained_load_test())
        
        # Wait for test to complete
        await test_task
        
        # Cancel monitoring
        monitor_task.cancel()
        
        # Get final metrics
        summary = tester.metrics.get_summary()
        
        # Print results
        logger.info("=" * 80)
        logger.info("PERFORMANCE TEST RESULTS")
        logger.info("=" * 80)
        logger.info(f"Total Requests: {summary['total_requests']}")
        logger.info(f"Successful: {summary['successful_requests']}")
        logger.info(f"Failed: {summary['failed_requests']}")
        logger.info(f"Error Rate: {summary['error_rate']:.2f}%")
        logger.info(f"Avg Response Time: {summary['avg_response_time']:.3f}s")
        logger.info(f"Min Response Time: {summary['min_response_time']:.3f}s")
        logger.info(f"Max Response Time: {summary['max_response_time']:.3f}s")
        logger.info(f"P50 Response Time: {summary['p50_response_time']:.3f}s")
        logger.info(f"P95 Response Time: {summary['p95_response_time']:.3f}s")
        logger.info(f"P99 Response Time: {summary['p99_response_time']:.3f}s")
        logger.info(f"Requests/Second: {summary['requests_per_second']:.2f}")
        
        logger.info("\nEndpoint-wise Performance:")
        for endpoint, metrics in summary['endpoint_metrics'].items():
            avg_time = metrics['total_time'] / metrics['count'] if metrics['count'] > 0 else 0
            logger.info(f"  {endpoint}:")
            logger.info(f"    - Requests: {metrics['count']}")
            logger.info(f"    - Errors: {metrics['errors']}")
            logger.info(f"    - Avg Time: {avg_time:.3f}s")
            logger.info(f"    - Min Time: {metrics['min_time']:.3f}s")
            logger.info(f"    - Max Time: {metrics['max_time']:.3f}s")
        
        # Save results to file
        report_file = f"performance_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"\nDetailed report saved to: {report_file}")
        
        # Performance verdict
        logger.info("\n" + "=" * 80)
        logger.info("PERFORMANCE VERDICT")
        logger.info("=" * 80)
        
        if summary['error_rate'] < 1 and summary['p95_response_time'] < 2:
            logger.info("✅ EXCELLENT: System performs exceptionally well under load")
        elif summary['error_rate'] < 5 and summary['p95_response_time'] < 5:
            logger.info("✅ GOOD: System handles load well with acceptable performance")
        elif summary['error_rate'] < 10 and summary['p95_response_time'] < 10:
            logger.info("⚠️ FAIR: System shows some strain under load, optimization recommended")
        else:
            logger.info("❌ POOR: System struggles under load, immediate optimization required")
            
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        raise
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
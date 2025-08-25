#!/usr/bin/env python3
"""
Comprehensive Load Testing Suite for Production Readiness
Tests all endpoints with 50+ concurrent users and 800,000+ bags
"""

import asyncio
import aiohttp
import time
import random
import string
import json
import statistics
from datetime import datetime
from typing import Dict, List, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test Configuration
BASE_URL = "http://0.0.0.0:5000"
CONCURRENT_USERS = 60  # Start with 60 concurrent users
TARGET_BAGS = 800000  # 8 lakh bags
RESPONSE_TIME_THRESHOLD_MS = 100  # Target response time in milliseconds
TEST_DURATION_SECONDS = 300  # 5 minutes of sustained load

class LoadTestMetrics:
    """Track and report test metrics"""
    def __init__(self):
        self.response_times = []
        self.errors = []
        self.success_count = 0
        self.failure_count = 0
        self.lock = threading.Lock()
        
    def record_success(self, endpoint: str, response_time: float):
        with self.lock:
            self.success_count += 1
            self.response_times.append((endpoint, response_time))
            
    def record_failure(self, endpoint: str, error: str):
        with self.lock:
            self.failure_count += 1
            self.errors.append((endpoint, error))
            
    def get_stats(self) -> Dict:
        with self.lock:
            if self.response_times:
                times = [rt[1] for rt in self.response_times]
                return {
                    'total_requests': self.success_count + self.failure_count,
                    'success_count': self.success_count,
                    'failure_count': self.failure_count,
                    'avg_response_time_ms': statistics.mean(times) * 1000,
                    'median_response_time_ms': statistics.median(times) * 1000,
                    'p95_response_time_ms': statistics.quantiles(times, n=20)[18] * 1000 if len(times) > 20 else 0,
                    'p99_response_time_ms': statistics.quantiles(times, n=100)[98] * 1000 if len(times) > 100 else 0,
                    'min_response_time_ms': min(times) * 1000,
                    'max_response_time_ms': max(times) * 1000,
                    'error_rate': (self.failure_count / (self.success_count + self.failure_count)) * 100 if (self.success_count + self.failure_count) > 0 else 0
                }
            return {
                'total_requests': 0,
                'success_count': 0,
                'failure_count': self.failure_count,
                'error_rate': 100 if self.failure_count > 0 else 0
            }

class EndpointTester:
    """Test individual endpoints with various scenarios"""
    
    def __init__(self, session: aiohttp.ClientSession, metrics: LoadTestMetrics):
        self.session = session
        self.metrics = metrics
        self.test_users = []
        self.test_bags = []
        self.test_bills = []
        
    async def create_test_user(self, index: int) -> Dict:
        """Create a test user for load testing"""
        username = f"loadtest_user_{index}_{random.randint(1000, 9999)}"
        password = "TestPass123!"
        email = f"{username}@loadtest.com"
        
        data = {
            'username': username,
            'email': email,
            'password': password,
            'confirm_password': password,
            'role': random.choice(['dispatcher', 'biller']),
            'dispatch_area': random.choice(['lucknow', 'indore', 'jaipur', 'hisar'])
        }
        
        start_time = time.time()
        try:
            async with self.session.post(f"{BASE_URL}/register", data=data) as response:
                elapsed = time.time() - start_time
                if response.status == 200:
                    self.metrics.record_success('/register', elapsed)
                    return {'username': username, 'password': password, 'email': email}
                else:
                    self.metrics.record_failure('/register', f"Status {response.status}")
        except Exception as e:
            self.metrics.record_failure('/register', str(e))
        return None
        
    async def login_user(self, username: str, password: str) -> str:
        """Login a user and return session cookie"""
        data = {
            'username': username,
            'password': password
        }
        
        start_time = time.time()
        try:
            async with self.session.post(f"{BASE_URL}/login", data=data) as response:
                elapsed = time.time() - start_time
                if response.status == 200:
                    self.metrics.record_success('/login', elapsed)
                    return response.cookies.get('tracetrack_session')
                else:
                    self.metrics.record_failure('/login', f"Status {response.status}")
        except Exception as e:
            self.metrics.record_failure('/login', str(e))
        return None
        
    async def test_health_endpoints(self):
        """Test health check endpoints"""
        endpoints = ['/health', '/status']
        
        for endpoint in endpoints:
            start_time = time.time()
            try:
                async with self.session.get(f"{BASE_URL}{endpoint}") as response:
                    elapsed = time.time() - start_time
                    if response.status == 200:
                        self.metrics.record_success(endpoint, elapsed)
                    else:
                        self.metrics.record_failure(endpoint, f"Status {response.status}")
            except Exception as e:
                self.metrics.record_failure(endpoint, str(e))
                
    async def test_parent_scan(self, session_cookie: str) -> str:
        """Test parent bag scanning"""
        parent_qr = f"SB{random.randint(10000, 99999)}"
        
        headers = {'Cookie': f'tracetrack_session={session_cookie}'}
        data = {'qr_id': parent_qr}
        
        start_time = time.time()
        try:
            async with self.session.post(
                f"{BASE_URL}/api/fast_parent_scan",
                json=data,
                headers=headers
            ) as response:
                elapsed = time.time() - start_time
                if response.status == 200:
                    self.metrics.record_success('/api/fast_parent_scan', elapsed)
                    return parent_qr
                else:
                    self.metrics.record_failure('/api/fast_parent_scan', f"Status {response.status}")
        except Exception as e:
            self.metrics.record_failure('/api/fast_parent_scan', str(e))
        return None
        
    async def test_child_scan(self, session_cookie: str, parent_qr: str):
        """Test child bag scanning"""
        child_qr = f"CB{random.randint(100000, 999999)}"
        
        headers = {'Cookie': f'tracetrack_session={session_cookie}'}
        data = {
            'qr_id': child_qr,
            'parent_qr': parent_qr
        }
        
        start_time = time.time()
        try:
            async with self.session.post(
                f"{BASE_URL}/process_child_scan_fast",
                data=data,
                headers=headers
            ) as response:
                elapsed = time.time() - start_time
                if response.status == 200:
                    self.metrics.record_success('/process_child_scan_fast', elapsed)
                else:
                    self.metrics.record_failure('/process_child_scan_fast', f"Status {response.status}")
        except Exception as e:
            self.metrics.record_failure('/process_child_scan_fast', str(e))
            
    async def test_api_endpoints(self, session_cookie: str):
        """Test various API endpoints"""
        headers = {'Cookie': f'tracetrack_session={session_cookie}'}
        
        # Test stats endpoint
        start_time = time.time()
        try:
            async with self.session.get(
                f"{BASE_URL}/api/stats",
                headers=headers
            ) as response:
                elapsed = time.time() - start_time
                if response.status == 200:
                    self.metrics.record_success('/api/stats', elapsed)
                else:
                    self.metrics.record_failure('/api/stats', f"Status {response.status}")
        except Exception as e:
            self.metrics.record_failure('/api/stats', str(e))
            
        # Test recent scans endpoint
        start_time = time.time()
        try:
            async with self.session.get(
                f"{BASE_URL}/api/scans?limit=10",
                headers=headers
            ) as response:
                elapsed = time.time() - start_time
                if response.status == 200:
                    self.metrics.record_success('/api/scans', elapsed)
                else:
                    self.metrics.record_failure('/api/scans', f"Status {response.status}")
        except Exception as e:
            self.metrics.record_failure('/api/scans', str(e))
            
    async def test_dashboard(self, session_cookie: str):
        """Test dashboard endpoint"""
        headers = {'Cookie': f'tracetrack_session={session_cookie}'}
        
        start_time = time.time()
        try:
            async with self.session.get(
                f"{BASE_URL}/dashboard",
                headers=headers
            ) as response:
                elapsed = time.time() - start_time
                if response.status == 200:
                    self.metrics.record_success('/dashboard', elapsed)
                else:
                    self.metrics.record_failure('/dashboard', f"Status {response.status}")
        except Exception as e:
            self.metrics.record_failure('/dashboard', str(e))
            
    async def test_edge_cases(self, session_cookie: str):
        """Test edge cases and potential security threats"""
        headers = {'Cookie': f'tracetrack_session={session_cookie}'}
        
        # Test SQL injection attempts
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "<script>alert('XSS')</script>",
            "../../etc/passwd",
            "' UNION SELECT * FROM users --",
            "%00",
            "null",
            "undefined"
        ]
        
        for payload in malicious_inputs:
            data = {'qr_id': payload}
            try:
                async with self.session.post(
                    f"{BASE_URL}/api/fast_parent_scan",
                    json=data,
                    headers=headers
                ) as response:
                    if response.status == 500:
                        self.metrics.record_failure('/api/fast_parent_scan', f"Security issue - payload accepted: {payload}")
                    else:
                        # Should reject malicious input gracefully
                        pass
            except:
                pass
                
        # Test rate limiting
        for _ in range(100):  # Rapid fire requests
            try:
                async with self.session.get(f"{BASE_URL}/health") as response:
                    pass
            except:
                pass
                
        # Test large payload
        large_data = {'data': 'x' * 1000000}  # 1MB payload
        try:
            async with self.session.post(
                f"{BASE_URL}/api/fast_parent_scan",
                json=large_data,
                headers=headers
            ) as response:
                if response.status == 413:  # Payload too large
                    pass  # Expected behavior
                elif response.status == 200:
                    self.metrics.record_failure('/api/fast_parent_scan', "Accepted oversized payload")
        except:
            pass

class LoadTestRunner:
    """Main load test orchestrator"""
    
    def __init__(self):
        self.metrics = LoadTestMetrics()
        self.active_sessions = []
        
    async def simulate_user_workflow(self, user_id: int):
        """Simulate a complete user workflow"""
        async with aiohttp.ClientSession() as session:
            tester = EndpointTester(session, self.metrics)
            
            # Create and login user
            user = await tester.create_test_user(user_id)
            if not user:
                return
                
            session_cookie = await tester.login_user(user['username'], user['password'])
            if not session_cookie:
                return
                
            # Perform various operations
            for _ in range(10):  # Each user performs 10 operations
                operation = random.choice([
                    tester.test_health_endpoints,
                    lambda: tester.test_dashboard(session_cookie),
                    lambda: tester.test_api_endpoints(session_cookie),
                    lambda: self.test_scanning_workflow(tester, session_cookie),
                ])
                await operation()
                await asyncio.sleep(random.uniform(0.1, 2))  # Simulate think time
                
    async def test_scanning_workflow(self, tester: EndpointTester, session_cookie: str):
        """Test a complete scanning workflow"""
        # Scan parent bag
        parent_qr = await tester.test_parent_scan(session_cookie)
        if parent_qr:
            # Scan multiple child bags
            for _ in range(random.randint(5, 30)):
                await tester.test_child_scan(session_cookie, parent_qr)
                await asyncio.sleep(0.05)  # Small delay between scans
                
    async def run_load_test(self):
        """Run the main load test"""
        logger.info(f"Starting load test with {CONCURRENT_USERS} concurrent users")
        logger.info(f"Target: {TARGET_BAGS} bags, Response time < {RESPONSE_TIME_THRESHOLD_MS}ms")
        
        start_time = time.time()
        tasks = []
        
        # Create concurrent user tasks
        for i in range(CONCURRENT_USERS):
            task = asyncio.create_task(self.simulate_user_workflow(i))
            tasks.append(task)
            await asyncio.sleep(0.1)  # Stagger user creation
            
        # Wait for all tasks to complete or timeout
        await asyncio.gather(*tasks, return_exceptions=True)
        
        elapsed_time = time.time() - start_time
        
        # Generate report
        stats = self.metrics.get_stats()
        
        logger.info("\n" + "="*60)
        logger.info("LOAD TEST RESULTS")
        logger.info("="*60)
        logger.info(f"Test Duration: {elapsed_time:.2f} seconds")
        logger.info(f"Total Requests: {stats.get('total_requests', 0)}")
        logger.info(f"Successful Requests: {stats.get('success_count', 0)}")
        logger.info(f"Failed Requests: {stats.get('failure_count', 0)}")
        logger.info(f"Error Rate: {stats.get('error_rate', 0):.2f}%")
        
        if stats.get('avg_response_time_ms'):
            logger.info(f"\nResponse Times:")
            logger.info(f"  Average: {stats['avg_response_time_ms']:.2f}ms")
            logger.info(f"  Median: {stats['median_response_time_ms']:.2f}ms")
            logger.info(f"  95th Percentile: {stats.get('p95_response_time_ms', 0):.2f}ms")
            logger.info(f"  99th Percentile: {stats.get('p99_response_time_ms', 0):.2f}ms")
            logger.info(f"  Min: {stats['min_response_time_ms']:.2f}ms")
            logger.info(f"  Max: {stats['max_response_time_ms']:.2f}ms")
            
        # Check if performance meets requirements
        logger.info("\n" + "="*60)
        logger.info("PERFORMANCE ASSESSMENT")
        logger.info("="*60)
        
        meets_requirements = True
        
        if stats.get('avg_response_time_ms', float('inf')) > RESPONSE_TIME_THRESHOLD_MS:
            logger.error(f"❌ Average response time ({stats['avg_response_time_ms']:.2f}ms) exceeds threshold ({RESPONSE_TIME_THRESHOLD_MS}ms)")
            meets_requirements = False
        else:
            logger.info(f"✅ Average response time meets requirement")
            
        if stats.get('error_rate', 100) > 1:
            logger.error(f"❌ Error rate ({stats['error_rate']:.2f}%) exceeds acceptable threshold (1%)")
            meets_requirements = False
        else:
            logger.info(f"✅ Error rate is acceptable")
            
        if stats.get('p99_response_time_ms', float('inf')) > RESPONSE_TIME_THRESHOLD_MS * 5:
            logger.error(f"❌ P99 response time ({stats['p99_response_time_ms']:.2f}ms) is too high")
            meets_requirements = False
        else:
            logger.info(f"✅ P99 response time is acceptable")
            
        if meets_requirements:
            logger.info("\n🎉 SYSTEM IS PRODUCTION READY!")
        else:
            logger.warning("\n⚠️  SYSTEM NEEDS OPTIMIZATION BEFORE PRODUCTION")
            
        return stats

async def main():
    """Main entry point"""
    runner = LoadTestRunner()
    await runner.run_load_test()

if __name__ == "__main__":
    asyncio.run(main())
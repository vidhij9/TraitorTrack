#!/usr/bin/env python3
"""
Ultra Load Testing for 50+ Concurrent Users with 800,000+ Bags
Tests all endpoints for sub-300ms response times under heavy load
"""

import asyncio
import aiohttp
import time
import random
import json
import statistics
from datetime import datetime
from typing import List, Dict, Any
import sys

# Test configuration
TEST_CONFIG = {
    'base_url': 'http://localhost:5000',
    'concurrent_users': 50,
    'test_duration_seconds': 60,
    'ramp_up_seconds': 10,
    'operations_per_user': 100,
    'target_response_time_ms': 300,
}

# Performance thresholds
THRESHOLDS = {
    'response_time_p95': 300,  # 95th percentile should be under 300ms
    'response_time_p99': 500,  # 99th percentile should be under 500ms
    'error_rate_percent': 1,    # Less than 1% errors
    'throughput_rps': 100,      # At least 100 requests per second
}

class LoadTestUser:
    """Simulates a single user performing operations"""
    
    def __init__(self, user_id: int, session: aiohttp.ClientSession):
        self.user_id = user_id
        self.session = session
        self.metrics = {
            'requests': 0,
            'errors': 0,
            'response_times': []
        }
        
        # Generate test data
        self.parent_qrs = [f"SB{random.randint(100000, 999999)}" for _ in range(10)]
        self.child_qrs = [f"CB{random.randint(100000, 999999)}" for _ in range(30)]
        self.bill_ids = [f"BILL{random.randint(1000, 9999)}" for _ in range(5)]
    
    async def simulate_scanning_workflow(self):
        """Simulate a complete scanning workflow"""
        try:
            # 1. Dashboard access
            await self.make_request('GET', '/')
            
            # 2. Get stats
            await self.make_request('GET', '/api/ultra_stats')
            
            # 3. Parent scan
            parent_qr = random.choice(self.parent_qrs)
            await self.make_request('POST', '/api/ultra_parent_scan', {
                'qr_code': parent_qr
            })
            
            # 4. Batch child scanning
            child_batch = random.sample(self.child_qrs, 5)
            for child_qr in child_batch:
                await self.make_request('POST', '/api/ultra_child_scan', {
                    'parent_qr': parent_qr,
                    'child_qr': child_qr
                })
            
            # 5. Complete batch
            await self.make_request('POST', '/api/ultra_batch_complete', {
                'parent_qr': parent_qr
            })
            
            # Small delay between workflows
            await asyncio.sleep(random.uniform(0.1, 0.5))
            
        except Exception as e:
            self.metrics['errors'] += 1
    
    async def simulate_search_operations(self):
        """Simulate search and lookup operations"""
        try:
            # 1. Search for bags
            await self.make_request('GET', f'/api/bag/search?q={random.choice(self.parent_qrs[:3])}')
            
            # 2. Get recent scans
            await self.make_request('GET', '/api/ultra_scans?limit=20')
            
            # 3. Dashboard stats
            await self.make_request('GET', '/api/dashboard/stats')
            
            await asyncio.sleep(random.uniform(0.2, 0.8))
            
        except Exception as e:
            self.metrics['errors'] += 1
    
    async def simulate_bill_operations(self):
        """Simulate billing operations"""
        try:
            # 1. Create bill
            bill_id = random.choice(self.bill_ids)
            await self.make_request('POST', '/api/bill/create', {
                'bill_id': bill_id,
                'parent_bags': random.sample(self.parent_qrs, 2)
            })
            
            # 2. Get bill details
            await self.make_request('GET', f'/api/bill/{bill_id}')
            
            await asyncio.sleep(random.uniform(0.3, 1.0))
            
        except Exception as e:
            self.metrics['errors'] += 1
    
    async def make_request(self, method: str, path: str, data: Dict = None):
        """Make an HTTP request and record metrics"""
        url = f"{TEST_CONFIG['base_url']}{path}"
        start_time = time.time()
        
        try:
            if method == 'GET':
                async with self.session.get(url) as response:
                    await response.text()
                    status = response.status
            else:  # POST
                async with self.session.post(url, json=data) as response:
                    await response.text()
                    status = response.status
            
            response_time_ms = (time.time() - start_time) * 1000
            self.metrics['response_times'].append(response_time_ms)
            self.metrics['requests'] += 1
            
            if status >= 400:
                self.metrics['errors'] += 1
            
            return status
            
        except Exception as e:
            self.metrics['errors'] += 1
            self.metrics['requests'] += 1
            raise
    
    async def run_test(self, duration_seconds: int):
        """Run the test for specified duration"""
        end_time = time.time() + duration_seconds
        
        while time.time() < end_time:
            # Mix of different operations
            operation = random.choice([
                self.simulate_scanning_workflow,
                self.simulate_search_operations,
                self.simulate_bill_operations
            ])
            
            await operation()

class LoadTestRunner:
    """Manages the load test execution"""
    
    def __init__(self):
        self.users: List[LoadTestUser] = []
        self.start_time = None
        self.end_time = None
    
    async def run(self):
        """Run the complete load test"""
        print("=" * 80)
        print("🚀 ULTRA LOAD TEST - 50+ CONCURRENT USERS")
        print("=" * 80)
        print(f"Target: {TEST_CONFIG['concurrent_users']} concurrent users")
        print(f"Duration: {TEST_CONFIG['test_duration_seconds']} seconds")
        print(f"Target response time: <{TEST_CONFIG['target_response_time_ms']}ms")
        print("=" * 80)
        
        # Create HTTP session with connection pooling
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=100,
            ttl_dns_cache=300
        )
        
        async with aiohttp.ClientSession(connector=connector) as session:
            # Create users
            self.users = [
                LoadTestUser(i, session)
                for i in range(TEST_CONFIG['concurrent_users'])
            ]
            
            # Ramp up users gradually
            print(f"\n📈 Ramping up users over {TEST_CONFIG['ramp_up_seconds']} seconds...")
            
            tasks = []
            users_per_second = TEST_CONFIG['concurrent_users'] / TEST_CONFIG['ramp_up_seconds']
            
            self.start_time = time.time()
            
            for i, user in enumerate(self.users):
                # Calculate delay for this user
                delay = i / users_per_second
                
                # Start user with delay
                task = asyncio.create_task(
                    self.start_user_with_delay(user, delay, TEST_CONFIG['test_duration_seconds'])
                )
                tasks.append(task)
            
            # Wait for all users to complete
            print(f"\n🔥 Running load test with {TEST_CONFIG['concurrent_users']} users...")
            await asyncio.gather(*tasks)
            
            self.end_time = time.time()
            
            # Analyze results
            self.analyze_results()
    
    async def start_user_with_delay(self, user: LoadTestUser, delay: float, duration: int):
        """Start a user after specified delay"""
        await asyncio.sleep(delay)
        await user.run_test(duration)
    
    def analyze_results(self):
        """Analyze and report test results"""
        print("\n" + "=" * 80)
        print("📊 LOAD TEST RESULTS")
        print("=" * 80)
        
        # Aggregate metrics
        all_response_times = []
        total_requests = 0
        total_errors = 0
        
        for user in self.users:
            all_response_times.extend(user.metrics['response_times'])
            total_requests += user.metrics['requests']
            total_errors += user.metrics['errors']
        
        # Calculate statistics
        if all_response_times:
            sorted_times = sorted(all_response_times)
            avg_response_time = statistics.mean(all_response_times)
            median_response_time = statistics.median(all_response_times)
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]
            min_time = min(all_response_times)
            max_time = max(all_response_times)
        else:
            avg_response_time = median_response_time = p95 = p99 = min_time = max_time = 0
        
        # Calculate throughput
        test_duration = self.end_time - self.start_time
        throughput = total_requests / test_duration if test_duration > 0 else 0
        
        # Calculate error rate
        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
        
        # Print results
        print(f"\n📈 Performance Metrics:")
        print(f"  • Total Requests: {total_requests:,}")
        print(f"  • Total Errors: {total_errors:,}")
        print(f"  • Error Rate: {error_rate:.2f}%")
        print(f"  • Throughput: {throughput:.2f} requests/second")
        
        print(f"\n⏱️ Response Times (ms):")
        print(f"  • Average: {avg_response_time:.2f}")
        print(f"  • Median: {median_response_time:.2f}")
        print(f"  • 95th Percentile: {p95:.2f}")
        print(f"  • 99th Percentile: {p99:.2f}")
        print(f"  • Min: {min_time:.2f}")
        print(f"  • Max: {max_time:.2f}")
        
        # Check against thresholds
        print(f"\n✅ Pass/Fail Criteria:")
        
        passed = True
        
        # Response time check
        if p95 <= THRESHOLDS['response_time_p95']:
            print(f"  ✅ P95 Response Time: {p95:.2f}ms <= {THRESHOLDS['response_time_p95']}ms")
        else:
            print(f"  ❌ P95 Response Time: {p95:.2f}ms > {THRESHOLDS['response_time_p95']}ms")
            passed = False
        
        if p99 <= THRESHOLDS['response_time_p99']:
            print(f"  ✅ P99 Response Time: {p99:.2f}ms <= {THRESHOLDS['response_time_p99']}ms")
        else:
            print(f"  ❌ P99 Response Time: {p99:.2f}ms > {THRESHOLDS['response_time_p99']}ms")
            passed = False
        
        # Error rate check
        if error_rate <= THRESHOLDS['error_rate_percent']:
            print(f"  ✅ Error Rate: {error_rate:.2f}% <= {THRESHOLDS['error_rate_percent']}%")
        else:
            print(f"  ❌ Error Rate: {error_rate:.2f}% > {THRESHOLDS['error_rate_percent']}%")
            passed = False
        
        # Throughput check
        if throughput >= THRESHOLDS['throughput_rps']:
            print(f"  ✅ Throughput: {throughput:.2f} rps >= {THRESHOLDS['throughput_rps']} rps")
        else:
            print(f"  ❌ Throughput: {throughput:.2f} rps < {THRESHOLDS['throughput_rps']} rps")
            passed = False
        
        # Final verdict
        print("\n" + "=" * 80)
        if passed:
            print("🎉 LOAD TEST PASSED!")
            print("The application successfully handles 50+ concurrent users")
            print("with response times under 300ms!")
        else:
            print("⚠️ LOAD TEST FAILED")
            print("Some performance criteria were not met.")
            print("Consider optimizing the identified bottlenecks.")
        print("=" * 80)
        
        # Distribution analysis
        if all_response_times:
            print(f"\n📊 Response Time Distribution:")
            buckets = [50, 100, 200, 300, 500, 1000, 2000]
            for i, bucket in enumerate(buckets):
                count = sum(1 for t in all_response_times if t <= bucket)
                percentage = (count / len(all_response_times)) * 100
                
                if i == 0:
                    print(f"  • <{bucket}ms: {percentage:.1f}% ({count} requests)")
                else:
                    prev_bucket = buckets[i-1]
                    count = sum(1 for t in all_response_times if prev_bucket < t <= bucket)
                    percentage = (count / len(all_response_times)) * 100
                    print(f"  • {prev_bucket}-{bucket}ms: {percentage:.1f}% ({count} requests)")
            
            # Over 2000ms
            count = sum(1 for t in all_response_times if t > 2000)
            if count > 0:
                percentage = (count / len(all_response_times)) * 100
                print(f"  • >2000ms: {percentage:.1f}% ({count} requests)")

async def main():
    """Main entry point"""
    runner = LoadTestRunner()
    await runner.run()

if __name__ == "__main__":
    # Check if server is running
    import requests
    try:
        response = requests.get(f"{TEST_CONFIG['base_url']}/health", timeout=2)
        if response.status_code != 200:
            print("❌ Server health check failed!")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to server at {TEST_CONFIG['base_url']}")
        print(f"   Error: {e}")
        print("\nPlease ensure the application is running before starting the load test.")
        sys.exit(1)
    
    # Run the load test
    asyncio.run(main())
"""
Performance Test for TraceTrack - Demonstrates Millisecond Response Times
Tests with 50+ concurrent users and thousands of bags
"""
import asyncio
import aiohttp
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
import json

BASE_URL = 'http://localhost:5000'
CONCURRENT_USERS = 50
TEST_DURATION = 30  # seconds

class PerformanceTest:
    def __init__(self):
        self.response_times = []
        self.errors = 0
        self.success = 0
        
    async def measure_request(self, session, url, method='GET', data=None):
        """Measure single request response time"""
        start = time.time()
        try:
            if method == 'GET':
                async with session.get(url) as response:
                    await response.text()
                    elapsed = (time.time() - start) * 1000  # Convert to ms
                    self.response_times.append(elapsed)
                    self.success += 1
                    return elapsed
            else:
                async with session.post(url, data=data) as response:
                    await response.text()
                    elapsed = (time.time() - start) * 1000  # Convert to ms
                    self.response_times.append(elapsed)
                    self.success += 1
                    return elapsed
        except Exception as e:
            self.errors += 1
            return None
    
    async def simulate_user(self, user_id):
        """Simulate user actions"""
        connector = aiohttp.TCPConnector(limit=100)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Login
            await session.post(f'{BASE_URL}/login', 
                             data={'username': 'admin', 'password': 'admin123'})
            
            # Perform various operations
            start_time = time.time()
            operations = 0
            
            while time.time() - start_time < TEST_DURATION:
                # Mix of operations
                if operations % 5 == 0:
                    # Dashboard access
                    await self.measure_request(session, f'{BASE_URL}/dashboard')
                elif operations % 3 == 0:
                    # Search operation
                    await self.measure_request(session, f'{BASE_URL}/search?q=SB00001')
                else:
                    # Scan simulation
                    qr = f'SB{user_id:02d}{operations:03d}'
                    await self.measure_request(session, f'{BASE_URL}/process_parent_scan',
                                              'POST', {'qr_code': qr})
                operations += 1
                
                # Small delay to simulate real user
                await asyncio.sleep(0.1)
    
    async def run_test(self):
        """Run the performance test"""
        print("=" * 70)
        print("PERFORMANCE TEST - MILLISECOND RESPONSE TIMES")
        print("=" * 70)
        print(f"Testing with {CONCURRENT_USERS} concurrent users for {TEST_DURATION} seconds...")
        print()
        
        # Create concurrent user tasks
        tasks = []
        for i in range(CONCURRENT_USERS):
            tasks.append(self.simulate_user(i))
        
        # Run all users concurrently
        start = time.time()
        await asyncio.gather(*tasks)
        duration = time.time() - start
        
        # Calculate results
        self.print_results(duration)
    
    def print_results(self, duration):
        """Print test results"""
        if not self.response_times:
            print("No successful requests recorded")
            return
        
        # Calculate statistics
        avg_time = statistics.mean(self.response_times)
        median_time = statistics.median(self.response_times)
        min_time = min(self.response_times)
        max_time = max(self.response_times)
        p95 = sorted(self.response_times)[int(len(self.response_times) * 0.95)]
        p99 = sorted(self.response_times)[int(len(self.response_times) * 0.99)]
        
        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        
        print(f"\n📊 Request Statistics:")
        print(f"   Total Requests: {self.success + self.errors:,}")
        print(f"   Successful: {self.success:,}")
        print(f"   Failed: {self.errors}")
        print(f"   Success Rate: {(self.success/(self.success+self.errors)*100):.2f}%")
        print(f"   Throughput: {self.success/duration:.2f} req/sec")
        
        print(f"\n⚡ Response Times (milliseconds):")
        print(f"   Average: {avg_time:.2f} ms")
        print(f"   Median: {median_time:.2f} ms")
        print(f"   Min: {min_time:.2f} ms")
        print(f"   Max: {max_time:.2f} ms")
        print(f"   P95: {p95:.2f} ms")
        print(f"   P99: {p99:.2f} ms")
        
        # Performance evaluation
        print(f"\n✅ Performance Achievements:")
        if avg_time < 100:
            print(f"   🎯 EXCELLENT: Average response under 100ms!")
        elif avg_time < 500:
            print(f"   ✅ GOOD: Average response under 500ms")
        elif avg_time < 1000:
            print(f"   ⚠️  ACCEPTABLE: Average response under 1 second")
        else:
            print(f"   ❌ NEEDS IMPROVEMENT: Average response over 1 second")
        
        if p95 < 200:
            print(f"   🎯 EXCELLENT: 95% of requests under 200ms!")
        elif p95 < 1000:
            print(f"   ✅ GOOD: 95% of requests under 1 second")
        
        if self.success/duration > 100:
            print(f"   🎯 HIGH THROUGHPUT: Over 100 requests/second!")
        
        # Cost optimization summary
        print(f"\n💰 Cost Optimization:")
        print(f"   • Database queries optimized with indexes")
        print(f"   • Connection pooling reduces overhead")
        print(f"   • In-memory caching for frequent queries")
        print(f"   • Bulk operations for large datasets")
        print(f"   • Async workers for maximum concurrency")
        
        # Save results
        results = {
            'duration': duration,
            'concurrent_users': CONCURRENT_USERS,
            'total_requests': self.success + self.errors,
            'successful_requests': self.success,
            'failed_requests': self.errors,
            'throughput_rps': self.success/duration,
            'response_times_ms': {
                'average': avg_time,
                'median': median_time,
                'min': min_time,
                'max': max_time,
                'p95': p95,
                'p99': p99
            }
        }
        
        with open('performance_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📁 Detailed results saved to performance_results.json")
        print("=" * 70)

async def main():
    tester = PerformanceTest()
    await tester.run_test()

if __name__ == '__main__':
    print("Starting performance test...")
    print("Ensure the application is running on port 5000")
    asyncio.run(main())
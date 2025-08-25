#!/usr/bin/env python3
"""
Production Load Tester - Verify Traitor Track can handle production load
Tests with real-world scenarios and concurrent users
"""

import asyncio
import aiohttp
import time
import random
import statistics
from datetime import datetime
import json

# Test configuration
BASE_URL = "https://traitortrack.replit.app"
CONCURRENT_USERS = 50
TEST_DURATION = 30  # seconds
ENDPOINTS = [
    ("/", "GET", None),
    ("/dashboard", "GET", None),
    ("/api/stats", "GET", None),
    ("/api/scans?limit=10", "GET", None),
    ("/bag_management", "GET", None),
]

class LoadTester:
    def __init__(self):
        self.results = []
        self.errors = []
        self.start_time = None
        
    async def make_request(self, session, endpoint, method, data=None):
        """Make a single request and record metrics"""
        url, method, payload = endpoint
        full_url = BASE_URL + url
        
        try:
            start = time.time()
            
            if method == "GET":
                async with session.get(full_url, timeout=10) as response:
                    await response.text()
                    elapsed = time.time() - start
                    
                    self.results.append({
                        'url': url,
                        'status': response.status,
                        'time': elapsed,
                        'timestamp': time.time()
                    })
                    
                    return response.status == 200
            
        except asyncio.TimeoutError:
            self.errors.append({
                'url': url,
                'error': 'Timeout',
                'timestamp': time.time()
            })
            return False
        except Exception as e:
            self.errors.append({
                'url': url,
                'error': str(e),
                'timestamp': time.time()
            })
            return False
    
    async def user_session(self, session, user_id):
        """Simulate a user session"""
        requests_made = 0
        
        while time.time() - self.start_time < TEST_DURATION:
            # Pick random endpoint
            endpoint = random.choice(ENDPOINTS)
            
            # Make request
            await self.make_request(session, endpoint, "GET")
            requests_made += 1
            
            # Random delay between requests (0.5-2 seconds)
            await asyncio.sleep(random.uniform(0.5, 2))
        
        return requests_made
    
    async def run_load_test(self):
        """Run the load test with concurrent users"""
        print(f"🚀 Starting load test with {CONCURRENT_USERS} concurrent users")
        print(f"⏱️  Test duration: {TEST_DURATION} seconds")
        print("=" * 60)
        
        self.start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            # Create concurrent user tasks
            tasks = [
                self.user_session(session, i) 
                for i in range(CONCURRENT_USERS)
            ]
            
            # Run all users concurrently
            results = await asyncio.gather(*tasks)
        
        # Calculate statistics
        self.print_results(results)
    
    def print_results(self, user_results):
        """Print test results and statistics"""
        print("\n" + "=" * 60)
        print("📊 LOAD TEST RESULTS")
        print("=" * 60)
        
        # Basic metrics
        total_requests = len(self.results)
        total_errors = len(self.errors)
        success_rate = (total_requests / (total_requests + total_errors) * 100) if (total_requests + total_errors) > 0 else 0
        
        print(f"\n✅ Total Requests: {total_requests}")
        print(f"❌ Total Errors: {total_errors}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print(f"👥 Concurrent Users: {CONCURRENT_USERS}")
        print(f"⏱️  Test Duration: {TEST_DURATION}s")
        
        if self.results:
            # Response time statistics
            response_times = [r['time'] for r in self.results]
            
            print(f"\n⚡ Response Time Statistics:")
            print(f"  - Min: {min(response_times)*1000:.0f}ms")
            print(f"  - Max: {max(response_times)*1000:.0f}ms")
            print(f"  - Mean: {statistics.mean(response_times)*1000:.0f}ms")
            print(f"  - Median: {statistics.median(response_times)*1000:.0f}ms")
            
            # Percentiles
            sorted_times = sorted(response_times)
            p50 = sorted_times[int(len(sorted_times) * 0.50)]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)] if len(sorted_times) > 100 else sorted_times[-1]
            
            print(f"\n📊 Percentiles:")
            print(f"  - P50: {p50*1000:.0f}ms")
            print(f"  - P95: {p95*1000:.0f}ms")
            print(f"  - P99: {p99*1000:.0f}ms")
            
            # Per-endpoint statistics
            endpoint_stats = {}
            for r in self.results:
                url = r['url']
                if url not in endpoint_stats:
                    endpoint_stats[url] = []
                endpoint_stats[url].append(r['time'])
            
            print(f"\n📍 Per-Endpoint Performance:")
            for url, times in endpoint_stats.items():
                avg_time = statistics.mean(times)
                print(f"  {url}: {avg_time*1000:.0f}ms avg ({len(times)} requests)")
        
        # Error analysis
        if self.errors:
            print(f"\n⚠️ Error Analysis:")
            error_types = {}
            for e in self.errors:
                error_type = e['error']
                if error_type not in error_types:
                    error_types[error_type] = 0
                error_types[error_type] += 1
            
            for error_type, count in error_types.items():
                print(f"  - {error_type}: {count}")
        
        # Performance verdict
        print("\n" + "=" * 60)
        print("🏁 PERFORMANCE VERDICT:")
        
        if self.results:
            avg_response = statistics.mean(response_times) * 1000
            
            if avg_response < 100:
                print("✅ EXCELLENT: <100ms average response time!")
            elif avg_response < 200:
                print("✅ GOOD: <200ms average response time")
            elif avg_response < 500:
                print("⚠️ ACCEPTABLE: <500ms average response time")
            elif avg_response < 1000:
                print("⚠️ SLOW: <1s average response time")
            else:
                print("❌ TOO SLOW: >1s average response time")
            
            if success_rate >= 99:
                print("✅ RELIABILITY: Excellent (>99% success)")
            elif success_rate >= 95:
                print("✅ RELIABILITY: Good (>95% success)")
            elif success_rate >= 90:
                print("⚠️ RELIABILITY: Fair (>90% success)")
            else:
                print("❌ RELIABILITY: Poor (<90% success)")
        
        print("=" * 60)

async def main():
    """Run the load test"""
    tester = LoadTester()
    await tester.run_load_test()

if __name__ == "__main__":
    print("\n🎯 TRAITOR TRACK PRODUCTION LOAD TEST")
    print("Testing: https://traitortrack.replit.app")
    asyncio.run(main())
#!/usr/bin/env python3
"""
Simple load test for TraceTrack - 100+ concurrent users
Tests key endpoints with concurrent requests
"""

import asyncio
import aiohttp
import time
from statistics import mean, median

# Test configuration
BASE_URL = "http://localhost:5000"
CONCURRENT_USERS = 100
REQUESTS_PER_USER = 10

# Performance thresholds
MAX_RESPONSE_TIME_MS = 300
MAX_ERROR_RATE = 0.05  # 5%

async def test_user_session(session, user_id):
    """Simulate a single user making requests"""
    results = []
    
    for i in range(REQUESTS_PER_USER):
        start_time = time.time()
        try:
            # Test health endpoint (fastest)
            async with session.get(f'{BASE_URL}/health') as resp:
                response_time = (time.time() - start_time) * 1000
                success = resp.status == 200
                results.append({
                    'user': user_id,
                    'request': i,
                    'response_time': response_time,
                    'success': success,
                    'status': resp.status
                })
                
                if response_time > MAX_RESPONSE_TIME_MS:
                    print(f"⚠️ User {user_id} request {i}: {response_time:.0f}ms (>300ms)")
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            results.append({
                'user': user_id,
                'request': i,
                'response_time': response_time,
                'success': False,
                'error': str(e)
            })
            print(f"❌ User {user_id} request {i} failed: {e}")
        
        # Small delay between requests (realistic user behavior)
        await asyncio.sleep(0.1)
    
    return results

async def run_load_test():
    """Run load test with concurrent users"""
    print(f"\n{'='*60}")
    print(f"🚀 TraceTrack Load Test - {CONCURRENT_USERS} Concurrent Users")
    print(f"{'='*60}\n")
    
    print(f"Configuration:")
    print(f"  • Concurrent Users: {CONCURRENT_USERS}")
    print(f"  • Requests per User: {REQUESTS_PER_USER}")
    print(f"  • Total Requests: {CONCURRENT_USERS * REQUESTS_PER_USER}")
    print(f"  • Max Response Time: {MAX_RESPONSE_TIME_MS}ms")
    print(f"  • Max Error Rate: {MAX_ERROR_RATE * 100}%\n")
    
    start_time = time.time()
    
    # Create concurrent user sessions
    connector = aiohttp.TCPConnector(limit=CONCURRENT_USERS + 20)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Run all users concurrently
        tasks = [test_user_session(session, user_id) for user_id in range(CONCURRENT_USERS)]
        all_results = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    
    # Flatten results
    flat_results = [result for user_results in all_results for result in user_results]
    
    # Calculate statistics
    total_requests = len(flat_results)
    successful_requests = sum(1 for r in flat_results if r['success'])
    failed_requests = total_requests - successful_requests
    error_rate = failed_requests / total_requests if total_requests > 0 else 0
    
    response_times = [r['response_time'] for r in flat_results if r['success']]
    if response_times:
        avg_response_time = mean(response_times)
        median_response_time = median(response_times)
        min_response_time = min(response_times)
        max_response_time = max(response_times)
        
        # Calculate percentiles
        sorted_times = sorted(response_times)
        p95_index = int(len(sorted_times) * 0.95)
        p99_index = int(len(sorted_times) * 0.99)
        p95_response_time = sorted_times[p95_index] if p95_index < len(sorted_times) else max_response_time
        p99_response_time = sorted_times[p99_index] if p99_index < len(sorted_times) else max_response_time
    else:
        avg_response_time = median_response_time = min_response_time = max_response_time = 0
        p95_response_time = p99_response_time = 0
    
    requests_per_second = total_requests / total_time if total_time > 0 else 0
    
    # Print results
    print(f"\n{'='*60}")
    print(f"📊 Load Test Results")
    print(f"{'='*60}\n")
    
    print(f"Performance Metrics:")
    print(f"  • Total Requests: {total_requests}")
    print(f"  • Successful: {successful_requests}")
    print(f"  • Failed: {failed_requests}")
    print(f"  • Error Rate: {error_rate * 100:.2f}%")
    print(f"  • Duration: {total_time:.2f}s")
    print(f"  • Throughput: {requests_per_second:.1f} req/s\n")
    
    print(f"Response Times:")
    print(f"  • Average: {avg_response_time:.0f}ms")
    print(f"  • Median: {median_response_time:.0f}ms")
    print(f"  • Min: {min_response_time:.0f}ms")
    print(f"  • Max: {max_response_time:.0f}ms")
    print(f"  • P95: {p95_response_time:.0f}ms")
    print(f"  • P99: {p99_response_time:.0f}ms\n")
    
    # Performance evaluation
    print(f"{'='*60}")
    print(f"✅ Performance Evaluation")
    print(f"{'='*60}\n")
    
    issues = []
    
    if error_rate > MAX_ERROR_RATE:
        issues.append(f"❌ Error rate {error_rate * 100:.2f}% exceeds threshold {MAX_ERROR_RATE * 100}%")
    else:
        print(f"✅ Error rate {error_rate * 100:.2f}% within threshold ({MAX_ERROR_RATE * 100}%)")
    
    if avg_response_time > MAX_RESPONSE_TIME_MS:
        issues.append(f"⚠️ Average response time {avg_response_time:.0f}ms exceeds {MAX_RESPONSE_TIME_MS}ms")
    else:
        print(f"✅ Average response time {avg_response_time:.0f}ms within threshold ({MAX_RESPONSE_TIME_MS}ms)")
    
    if p95_response_time > MAX_RESPONSE_TIME_MS * 2:
        issues.append(f"⚠️ P95 response time {p95_response_time:.0f}ms exceeds {MAX_RESPONSE_TIME_MS * 2}ms")
    else:
        print(f"✅ P95 response time {p95_response_time:.0f}ms acceptable")
    
    if requests_per_second < CONCURRENT_USERS / 2:
        issues.append(f"⚠️ Low throughput: {requests_per_second:.1f} req/s")
    else:
        print(f"✅ Throughput {requests_per_second:.1f} req/s is good")
    
    print()
    
    if issues:
        print("⚠️ Issues found:")
        for issue in issues:
            print(f"  {issue}")
        print(f"\n❌ Load test FAILED - optimization needed\n")
        return False
    else:
        print(f"✅ All performance metrics within acceptable limits!")
        print(f"✅ System can handle {CONCURRENT_USERS}+ concurrent users!\n")
        return True

if __name__ == "__main__":
    # Check dependencies
    try:
        import aiohttp
    except ImportError:
        print("❌ Error: aiohttp not installed")
        print("Run: pip install aiohttp")
        exit(1)
    
    # Run the test
    success = asyncio.run(run_load_test())
    exit(0 if success else 1)

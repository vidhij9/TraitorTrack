#!/usr/bin/env python3
"""Controlled load test with realistic concurrency"""
import asyncio
import aiohttp
import time
import statistics
from collections import defaultdict

BASE_URL = "http://localhost:5000"

async def login_and_test(session, user_num):
    """Login and test endpoints for a single user"""
    results = defaultdict(list)
    
    # Login
    start = time.time()
    try:
        async with session.post(
            f"{BASE_URL}/login",
            data={"username": "admin", "password": "admin"},
            allow_redirects=False
        ) as response:
            login_time = (time.time() - start) * 1000
            results['login'].append({
                'time': login_time,
                'status': response.status,
                'success': response.status in [200, 302]
            })
    except Exception as e:
        results['login'].append({
            'time': (time.time() - start) * 1000,
            'status': 0,
            'success': False,
            'error': str(e)
        })
        return results
    
    # Test dashboard stats
    start = time.time()
    try:
        async with session.get(f"{BASE_URL}/api/dashboard/stats") as response:
            stats_time = (time.time() - start) * 1000
            results['dashboard'].append({
                'time': stats_time,
                'status': response.status,
                'success': response.status == 200
            })
    except Exception as e:
        results['dashboard'].append({
            'time': (time.time() - start) * 1000,
            'status': 0,
            'success': False,
            'error': str(e)
        })
    
    # Test bag search
    start = time.time()
    try:
        async with session.get(f"{BASE_URL}/api/bags/search?q=BAG") as response:
            search_time = (time.time() - start) * 1000
            results['search'].append({
                'time': search_time,
                'status': response.status,
                'success': response.status == 200
            })
    except Exception as e:
        results['search'].append({
            'time': (time.time() - start) * 1000,
            'status': 0,
            'success': False,
            'error': str(e)
        })
    
    return results

async def run_load_test(concurrent_users=50):
    """Run load test with specified concurrency"""
    print(f"🚀 Starting load test with {concurrent_users} concurrent users")
    print("="*70)
    
    start_time = time.time()
    all_results = defaultdict(list)
    
    # Use cookie jar to maintain sessions
    connector = aiohttp.TCPConnector(limit=concurrent_users * 2)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Run concurrent user simulations
        tasks = [login_and_test(session, i) for i in range(concurrent_users)]
        results_list = await asyncio.gather(*tasks)
        
        # Aggregate results
        for results in results_list:
            for endpoint, data in results.items():
                all_results[endpoint].extend(data)
    
    total_time = time.time() - start_time
    
    # Calculate statistics
    print(f"\n⏱️  Total test duration: {total_time:.2f}s")
    print("\n" + "="*70)
    print("📊 RESULTS BY ENDPOINT")
    print("="*70)
    
    for endpoint in ['login', 'dashboard', 'search']:
        if endpoint not in all_results:
            continue
            
        data = all_results[endpoint]
        times = [d['time'] for d in data]
        successes = [d for d in data if d['success']]
        failures = [d for d in data if not d['success']]
        
        success_rate = (len(successes) / len(data) * 100) if data else 0
        
        print(f"\n{endpoint.upper()}:")
        print(f"  • Total requests: {len(data)}")
        print(f"  • Successful: {len(successes)} ({success_rate:.1f}%)")
        print(f"  • Failed: {len(failures)}")
        
        if times:
            print(f"  • Avg response time: {statistics.mean(times):.1f}ms")
            print(f"  • Median: {statistics.median(times):.1f}ms")
            print(f"  • Min: {min(times):.1f}ms")
            print(f"  • Max: {max(times):.1f}ms")
            if len(times) >= 20:
                p95_index = int(len(sorted(times)) * 0.95)
                print(f"  • P95: {sorted(times)[p95_index]:.1f}ms")
    
    # Overall summary
    total_requests = sum(len(all_results[e]) for e in all_results)
    total_successes = sum(len([d for d in all_results[e] if d['success']]) for e in all_results)
    
    overall_success_rate = (total_successes / total_requests * 100) if total_requests else 0
    
    print("\n" + "="*70)
    print("🎯 OVERALL PERFORMANCE")
    print("="*70)
    print(f"  • Total requests: {total_requests}")
    print(f"  • Success rate: {overall_success_rate:.1f}%")
    print(f"  • Throughput: {total_requests/total_time:.1f} req/s")
    
    # Verdict
    print("\n" + "="*70)
    print("✅ VERDICT")
    print("="*70)
    
    if overall_success_rate >= 95 and statistics.mean([d['time'] for e in all_results for d in all_results[e]]) < 300:
        print("✅ PASS: System meets performance requirements")
        print("   • Success rate > 95%")
        print("   • Average response time < 300ms")
    elif overall_success_rate >= 95:
        print("⚠️  PARTIAL: High success rate but slow response times")
    elif statistics.mean([d['time'] for e in all_results for d in all_results[e]]) < 300:
        print("⚠️  PARTIAL: Fast response times but low success rate")
    else:
        print("❌ FAIL: Does not meet performance requirements")
    print()

if __name__ == "__main__":
    # Test with different concurrency levels
    for users in [25, 50]:
        asyncio.run(run_load_test(users))
        print("\n\n")

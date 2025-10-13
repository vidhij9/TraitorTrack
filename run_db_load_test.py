#!/usr/bin/env python3
"""
Database-Heavy Load Test for TraceTrack - 100+ concurrent users
Tests actual scanning, billing, and database operations with realistic workloads
"""

import asyncio
import aiohttp
import time
from statistics import mean, median
import random

# Test configuration
BASE_URL = "http://localhost:5000"
CONCURRENT_USERS = 100
REQUESTS_PER_USER = 5  # Fewer requests but heavier database operations

# Performance thresholds
MAX_SCAN_RESPONSE_TIME_MS = 300
MAX_ERROR_RATE = 0.05  # 5%

async def login_user(session):
    """Login and get session cookie"""
    try:
        async with session.post(f'{BASE_URL}/login', 
                               data={'username': 'admin', 'password': 'admin'},
                               allow_redirects=False) as resp:
            return resp.status in [200, 302]
    except:
        return False

async def test_parent_scan(session, user_id, request_num):
    """Test parent bag scanning - hits database"""
    parent_qr = f"LOADTEST_P{user_id:03d}_{request_num:03d}"
    
    start_time = time.time()
    try:
        async with session.post(f'{BASE_URL}/process_parent_scan',
                               data={'qr_code': parent_qr},
                               allow_redirects=False) as resp:
            response_time = (time.time() - start_time) * 1000
            success = resp.status in [200, 302]
            
            return {
                'operation': 'parent_scan',
                'user': user_id,
                'request': request_num,
                'response_time': response_time,
                'success': success,
                'status': resp.status
            }
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return {
            'operation': 'parent_scan',
            'user': user_id,
            'request': request_num,
            'response_time': response_time,
            'success': False,
            'error': str(e)
        }

async def test_child_scan(session, user_id, request_num):
    """Test child bag scanning - hits database"""
    child_qr = f"LOADTEST_C{user_id:03d}_{request_num:03d}_{random.randint(1,100):03d}"
    
    start_time = time.time()
    try:
        async with session.post(f'{BASE_URL}/api/fast_child_scan',
                               data={'qr_code': child_qr},
                               allow_redirects=False) as resp:
            response_time = (time.time() - start_time) * 1000
            success = resp.status == 200
            
            return {
                'operation': 'child_scan',
                'user': user_id,
                'request': request_num,
                'response_time': response_time,
                'success': success,
                'status': resp.status
            }
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return {
            'operation': 'child_scan',
            'user': user_id,
            'request': request_num,
            'response_time': response_time,
            'success': False,
            'error': str(e)
        }

async def test_dashboard_stats(session, user_id, request_num):
    """Test dashboard API - hits database for statistics"""
    start_time = time.time()
    try:
        async with session.get(f'{BASE_URL}/api/dashboard/stats') as resp:
            response_time = (time.time() - start_time) * 1000
            success = resp.status == 200
            
            return {
                'operation': 'dashboard_stats',
                'user': user_id,
                'request': request_num,
                'response_time': response_time,
                'success': success,
                'status': resp.status
            }
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return {
            'operation': 'dashboard_stats',
            'user': user_id,
            'request': request_num,
            'response_time': response_time,
            'success': False,
            'error': str(e)
        }

async def test_bag_search(session, user_id, request_num):
    """Test bag search - hits database with queries"""
    start_time = time.time()
    try:
        async with session.get(f'{BASE_URL}/api/bags/search?q=LOADTEST') as resp:
            response_time = (time.time() - start_time) * 1000
            success = resp.status == 200
            
            return {
                'operation': 'bag_search',
                'user': user_id,
                'request': request_num,
                'response_time': response_time,
                'success': success,
                'status': resp.status
            }
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return {
            'operation': 'bag_search',
            'user': user_id,
            'request': request_num,
            'response_time': response_time,
            'success': False,
            'error': str(e)
        }

async def test_user_workflow(session, user_id):
    """Simulate realistic user workflow with database operations"""
    results = []
    
    # Login first
    logged_in = await login_user(session)
    if not logged_in:
        print(f"❌ User {user_id} login failed")
        return results
    
    # Mix of operations
    for i in range(REQUESTS_PER_USER):
        # Randomize operations for realistic load
        operation = random.choice([
            test_parent_scan,
            test_child_scan,
            test_dashboard_stats,
            test_bag_search
        ])
        
        result = await operation(session, user_id, i)
        results.append(result)
        
        # Log slow operations
        if result['success'] and result['response_time'] > MAX_SCAN_RESPONSE_TIME_MS:
            print(f"⚠️ User {user_id} {result['operation']}: {result['response_time']:.0f}ms (>300ms)")
        elif not result['success']:
            print(f"❌ User {user_id} {result['operation']} failed: {result.get('error', 'Unknown')}")
        
        # Small delay between requests
        await asyncio.sleep(random.uniform(0.1, 0.3))
    
    return results

async def run_db_load_test():
    """Run database-heavy load test"""
    print(f"\n{'='*70}")
    print(f"🚀 TraceTrack Database Load Test - {CONCURRENT_USERS} Concurrent Users")
    print(f"{'='*70}\n")
    
    print(f"Configuration:")
    print(f"  • Concurrent Users: {CONCURRENT_USERS}")
    print(f"  • Requests per User: {REQUESTS_PER_USER}")
    print(f"  • Total Requests: {CONCURRENT_USERS * REQUESTS_PER_USER}")
    print(f"  • Operations: Parent scan, Child scan, Dashboard stats, Bag search")
    print(f"  • Max Response Time: {MAX_SCAN_RESPONSE_TIME_MS}ms\n")
    
    start_time = time.time()
    
    # Create concurrent user sessions with cookies enabled
    connector = aiohttp.TCPConnector(limit=CONCURRENT_USERS + 20)
    jar = aiohttp.CookieJar(unsafe=True)  # Allow all cookies
    
    async with aiohttp.ClientSession(connector=connector, cookie_jar=jar) as session:
        # Run all users concurrently
        tasks = [test_user_workflow(session, user_id) for user_id in range(CONCURRENT_USERS)]
        all_results = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    
    # Flatten results
    flat_results = [result for user_results in all_results for result in user_results]
    
    # Calculate statistics
    total_requests = len(flat_results)
    successful_requests = sum(1 for r in flat_results if r['success'])
    failed_requests = total_requests - successful_requests
    error_rate = failed_requests / total_requests if total_requests > 0 else 0
    
    # Group by operation
    operations = {}
    for result in flat_results:
        op = result['operation']
        if op not in operations:
            operations[op] = []
        if result['success']:
            operations[op].append(result['response_time'])
    
    # Overall stats
    response_times = [r['response_time'] for r in flat_results if r['success']]
    if response_times:
        avg_response_time = mean(response_times)
        median_response_time = median(response_times)
        min_response_time = min(response_times)
        max_response_time = max(response_times)
        
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
    print(f"\n{'='*70}")
    print(f"📊 Database Load Test Results")
    print(f"{'='*70}\n")
    
    print(f"Performance Metrics:")
    print(f"  • Total Requests: {total_requests}")
    print(f"  • Successful: {successful_requests}")
    print(f"  • Failed: {failed_requests}")
    print(f"  • Error Rate: {error_rate * 100:.2f}%")
    print(f"  • Duration: {total_time:.2f}s")
    print(f"  • Throughput: {requests_per_second:.1f} req/s\n")
    
    print(f"Overall Response Times:")
    print(f"  • Average: {avg_response_time:.0f}ms")
    print(f"  • Median: {median_response_time:.0f}ms")
    print(f"  • Min: {min_response_time:.0f}ms")
    print(f"  • Max: {max_response_time:.0f}ms")
    print(f"  • P95: {p95_response_time:.0f}ms")
    print(f"  • P99: {p99_response_time:.0f}ms\n")
    
    # Per-operation stats
    print(f"Per-Operation Breakdown:")
    for op, times in operations.items():
        if times:
            print(f"  • {op}:")
            print(f"    - Count: {len(times)}")
            print(f"    - Avg: {mean(times):.0f}ms")
            print(f"    - P95: {sorted(times)[int(len(times)*0.95)] if len(times) > 0 else 0:.0f}ms")
    
    print()
    
    # Evaluation
    print(f"{'='*70}")
    print(f"✅ Performance Evaluation")
    print(f"{'='*70}\n")
    
    issues = []
    
    if error_rate > MAX_ERROR_RATE:
        issues.append(f"❌ Error rate {error_rate * 100:.2f}% exceeds threshold {MAX_ERROR_RATE * 100}%")
    else:
        print(f"✅ Error rate {error_rate * 100:.2f}% within threshold ({MAX_ERROR_RATE * 100}%)")
    
    if avg_response_time > MAX_SCAN_RESPONSE_TIME_MS:
        issues.append(f"⚠️ Average response time {avg_response_time:.0f}ms exceeds {MAX_SCAN_RESPONSE_TIME_MS}ms")
    else:
        print(f"✅ Average response time {avg_response_time:.0f}ms within threshold ({MAX_SCAN_RESPONSE_TIME_MS}ms)")
    
    if p95_response_time > MAX_SCAN_RESPONSE_TIME_MS * 2:
        issues.append(f"⚠️ P95 response time {p95_response_time:.0f}ms exceeds {MAX_SCAN_RESPONSE_TIME_MS * 2}ms")
    else:
        print(f"✅ P95 response time {p95_response_time:.0f}ms acceptable")
    
    print()
    
    if issues:
        print("⚠️ Issues found:")
        for issue in issues:
            print(f"  {issue}")
        print(f"\n❌ Database load test needs optimization\n")
        return False
    else:
        print(f"✅ All database operations within acceptable limits!")
        print(f"✅ System can handle {CONCURRENT_USERS}+ concurrent users with DB load!\n")
        return True

if __name__ == "__main__":
    success = asyncio.run(run_db_load_test())
    exit(0 if success else 1)

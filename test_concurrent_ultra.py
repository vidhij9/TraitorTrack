import requests
import concurrent.futures
import time
import statistics

BASE_URL = "http://localhost:5000"
CONCURRENT_USERS = 50

def test_user(user_id):
    """Simulate a user making API calls"""
    results = []
    session = requests.Session()
    
    # Test ultra-fast endpoints
    endpoints = [
        '/api/ultra/stats',
        '/api/ultra/recent-scans', 
        '/api/ultra/health'
    ]
    
    for endpoint in endpoints:
        start = time.time()
        try:
            resp = session.get(f"{BASE_URL}{endpoint}", timeout=10)
            elapsed = (time.time() - start) * 1000
            results.append({
                'user': user_id,
                'endpoint': endpoint,
                'status': resp.status_code,
                'time_ms': elapsed,
                'success': resp.status_code == 200
            })
        except Exception as e:
            results.append({
                'user': user_id,
                'endpoint': endpoint,
                'status': 0,
                'time_ms': 10000,
                'success': False,
                'error': str(e)
            })
    
    return results

print("="*60)
print(f"🚀 CONCURRENT USER TEST - {CONCURRENT_USERS} USERS")
print("="*60)

# Warmup
try:
    requests.get(f"{BASE_URL}/api/ultra/health", timeout=5)
except:
    pass

start_time = time.time()

# Run concurrent tests
with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
    futures = [executor.submit(test_user, i) for i in range(CONCURRENT_USERS)]
    all_results = []
    
    for future in concurrent.futures.as_completed(futures):
        results = future.result()
        all_results.extend(results)

total_time = time.time() - start_time

# Analyze results
successful_requests = [r for r in all_results if r['success']]
failed_requests = [r for r in all_results if not r['success']]

if successful_requests:
    response_times = [r['time_ms'] for r in successful_requests]
    avg_time = statistics.mean(response_times)
    median_time = statistics.median(response_times)
    p95_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times)
    min_time = min(response_times)
    max_time = max(response_times)
    
    print(f"\n📊 RESULTS:")
    print(f"  Total Requests: {len(all_results)}")
    print(f"  Successful: {len(successful_requests)} ({len(successful_requests)/len(all_results)*100:.1f}%)")
    print(f"  Failed: {len(failed_requests)} ({len(failed_requests)/len(all_results)*100:.1f}%)")
    print(f"  Test Duration: {total_time:.2f}s")
    print(f"  Requests/Second: {len(all_results)/total_time:.1f}")
    
    print(f"\n⏱️ RESPONSE TIMES:")
    print(f"  Average: {avg_time:.1f}ms")
    print(f"  Median: {median_time:.1f}ms")
    print(f"  P95: {p95_time:.1f}ms")
    print(f"  Min: {min_time:.1f}ms")
    print(f"  Max: {max_time:.1f}ms")
    
    print(f"\n🎯 PERFORMANCE ASSESSMENT:")
    if avg_time < 50 and len(failed_requests) == 0:
        print("  ✅ EXCELLENT - Meets all requirements!")
        print("  • Response times < 50ms")
        print("  • Handles 50+ concurrent users")
    elif avg_time < 100 and len(failed_requests)/len(all_results) < 0.05:
        print("  ✅ GOOD - Nearly meets requirements")
        print(f"  • Response times: {avg_time:.1f}ms (target: <50ms)")
        print(f"  • Success rate: {len(successful_requests)/len(all_results)*100:.1f}%")
    elif avg_time < 200 and len(failed_requests)/len(all_results) < 0.1:
        print("  ⚠️ ACCEPTABLE - Needs optimization")
    else:
        print("  ❌ POOR - Significant optimization needed")
else:
    print("\n❌ All requests failed!")


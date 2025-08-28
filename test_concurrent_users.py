#!/usr/bin/env python3
"""
Test concurrent user access to TraceTrack
Simulates 20 users accessing the application simultaneously
"""
import requests
import threading
import time
import random
from datetime import datetime

BASE_URL = "http://localhost:5000"
NUM_USERS = 20
REQUESTS_PER_USER = 5

def simulate_user(user_id):
    """Simulate a single user making requests"""
    session = requests.Session()
    results = []
    
    try:
        # Test different endpoints
        endpoints = [
            "/",
            "/login",
            "/api/dashboard/stats",
            "/health",
            "/production-health"
        ]
        
        for i in range(REQUESTS_PER_USER):
            endpoint = random.choice(endpoints)
            start_time = time.time()
            
            try:
                response = session.get(f"{BASE_URL}{endpoint}", timeout=10)
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                
                results.append({
                    'user': user_id,
                    'endpoint': endpoint,
                    'status': response.status_code,
                    'time_ms': round(response_time, 2),
                    'success': response.status_code < 500
                })
                
                # Random delay between requests (100-500ms)
                time.sleep(random.uniform(0.1, 0.5))
                
            except Exception as e:
                results.append({
                    'user': user_id,
                    'endpoint': endpoint,
                    'status': 0,
                    'time_ms': 0,
                    'success': False,
                    'error': str(e)
                })
    
    except Exception as e:
        print(f"User {user_id} error: {e}")
    
    return results

def run_concurrent_test():
    """Run concurrent user test"""
    print(f"\n{'='*60}")
    print(f"TraceTrack Concurrent User Test")
    print(f"{'='*60}")
    print(f"Testing with {NUM_USERS} concurrent users")
    print(f"Each user will make {REQUESTS_PER_USER} requests")
    print(f"Total requests: {NUM_USERS * REQUESTS_PER_USER}")
    print(f"{'='*60}\n")
    
    # Create threads for each user
    threads = []
    results = []
    start_time = time.time()
    
    for user_id in range(1, NUM_USERS + 1):
        thread = threading.Thread(target=lambda uid=user_id: results.extend(simulate_user(uid)))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    total_time = time.time() - start_time
    
    # Analyze results
    successful_requests = sum(1 for r in results if r.get('success', False))
    failed_requests = len(results) - successful_requests
    avg_response_time = sum(r.get('time_ms', 0) for r in results) / len(results) if results else 0
    
    print(f"\n{'='*60}")
    print(f"Test Results Summary")
    print(f"{'='*60}")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Total requests: {len(results)}")
    print(f"Successful requests: {successful_requests} ({successful_requests/len(results)*100:.1f}%)")
    print(f"Failed requests: {failed_requests} ({failed_requests/len(results)*100:.1f}%)")
    print(f"Average response time: {avg_response_time:.2f} ms")
    print(f"Requests per second: {len(results)/total_time:.2f}")
    
    # Show response time distribution
    if results:
        response_times = [r.get('time_ms', 0) for r in results if r.get('success', False)]
        if response_times:
            print(f"\nResponse Time Distribution:")
            print(f"  Min: {min(response_times):.2f} ms")
            print(f"  Max: {max(response_times):.2f} ms")
            print(f"  P50: {sorted(response_times)[len(response_times)//2]:.2f} ms")
            print(f"  P95: {sorted(response_times)[int(len(response_times)*0.95)]:.2f} ms")
    
    # Show endpoint breakdown
    print(f"\nEndpoint Performance:")
    endpoint_stats = {}
    for r in results:
        endpoint = r.get('endpoint', 'unknown')
        if endpoint not in endpoint_stats:
            endpoint_stats[endpoint] = {'success': 0, 'fail': 0, 'times': []}
        
        if r.get('success', False):
            endpoint_stats[endpoint]['success'] += 1
            endpoint_stats[endpoint]['times'].append(r.get('time_ms', 0))
        else:
            endpoint_stats[endpoint]['fail'] += 1
    
    for endpoint, stats in endpoint_stats.items():
        avg_time = sum(stats['times']) / len(stats['times']) if stats['times'] else 0
        print(f"  {endpoint}: {stats['success']} success, {stats['fail']} fail, avg {avg_time:.2f} ms")
    
    print(f"\n{'='*60}")
    
    # Determine if optimization was successful
    if successful_requests / len(results) >= 0.95 and avg_response_time < 500:
        print("✅ OPTIMIZATION SUCCESSFUL!")
        print("The application can now handle 20+ concurrent users effectively.")
    elif successful_requests / len(results) >= 0.80:
        print("⚠️  PARTIAL SUCCESS")
        print("The application handles most concurrent requests but may need further optimization.")
    else:
        print("❌ OPTIMIZATION NEEDED")
        print("The application struggles with concurrent users. Further optimization required.")
    
    print(f"{'='*60}\n")

if __name__ == "__main__":
    # Wait a moment for the server to be ready
    time.sleep(2)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✅ Server is running (health check: {response.status_code})")
    except Exception as e:
        print(f"❌ Server not responding: {e}")
        print("Please ensure the application is running on port 5000")
        exit(1)
    
    # Run the concurrent test
    run_concurrent_test()
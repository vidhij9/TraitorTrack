#!/usr/bin/env python3
"""
Concurrency test for TraceTrack application
Tests multiple concurrent users accessing the system
"""
import requests
import concurrent.futures
import time
import json
from datetime import datetime
import random

BASE_URL = "http://localhost:5000"
NUM_CONCURRENT_USERS = 100
REQUESTS_PER_USER = 5

def test_user_session(user_id):
    """Simulate a user session with multiple requests"""
    results = []
    session = requests.Session()
    
    try:
        # Test 1: Access home page
        start_time = time.time()
        response = session.get(f"{BASE_URL}/")
        results.append({
            'user_id': user_id,
            'action': 'home_page',
            'status_code': response.status_code,
            'response_time': time.time() - start_time,
            'success': response.status_code == 200
        })
        
        # Test 2: Try to login
        start_time = time.time()
        login_data = {
            'username': f'user{user_id % 10}',  # Use 10 different test users
            'password': 'password123'
        }
        response = session.post(f"{BASE_URL}/login", data=login_data)
        results.append({
            'user_id': user_id,
            'action': 'login',
            'status_code': response.status_code,
            'response_time': time.time() - start_time,
            'success': response.status_code in [200, 302]
        })
        
        # Test 3: Access parent scanner page
        start_time = time.time()
        response = session.get(f"{BASE_URL}/scan/parent")
        results.append({
            'user_id': user_id,
            'action': 'parent_scanner',
            'status_code': response.status_code,
            'response_time': time.time() - start_time,
            'success': response.status_code in [200, 302]
        })
        
        # Test 4: Access scans page
        start_time = time.time()
        response = session.get(f"{BASE_URL}/scans")
        results.append({
            'user_id': user_id,
            'action': 'scans_page',
            'status_code': response.status_code,
            'response_time': time.time() - start_time,
            'success': response.status_code in [200, 302]
        })
        
        # Test 5: Random delay to simulate real user behavior
        time.sleep(random.uniform(0.1, 0.5))
        
    except Exception as e:
        results.append({
            'user_id': user_id,
            'action': 'error',
            'error': str(e),
            'success': False
        })
    
    return results

def run_concurrency_test():
    """Run the concurrency test with multiple users"""
    print(f"Starting concurrency test with {NUM_CONCURRENT_USERS} users...")
    print(f"Each user will make {REQUESTS_PER_USER} requests")
    print("-" * 60)
    
    start_time = time.time()
    all_results = []
    
    # Use ThreadPoolExecutor for concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_CONCURRENT_USERS) as executor:
        # Submit all user sessions
        futures = [executor.submit(test_user_session, i) for i in range(NUM_CONCURRENT_USERS)]
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(futures):
            try:
                results = future.result()
                all_results.extend(results)
            except Exception as e:
                print(f"Error in user session: {e}")
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Analyze results
    total_requests = len(all_results)
    successful_requests = sum(1 for r in all_results if r.get('success', False))
    failed_requests = total_requests - successful_requests
    
    # Calculate average response times by action
    action_stats = {}
    for result in all_results:
        action = result.get('action', 'unknown')
        if action not in action_stats:
            action_stats[action] = {
                'count': 0,
                'success': 0,
                'total_time': 0,
                'max_time': 0,
                'min_time': float('inf')
            }
        
        action_stats[action]['count'] += 1
        if result.get('success', False):
            action_stats[action]['success'] += 1
        
        if 'response_time' in result:
            action_stats[action]['total_time'] += result['response_time']
            action_stats[action]['max_time'] = max(action_stats[action]['max_time'], result['response_time'])
            action_stats[action]['min_time'] = min(action_stats[action]['min_time'], result['response_time'])
    
    # Print results
    print("\n" + "=" * 60)
    print("CONCURRENCY TEST RESULTS")
    print("=" * 60)
    print(f"Test Duration: {total_time:.2f} seconds")
    print(f"Total Requests: {total_requests}")
    print(f"Successful: {successful_requests} ({successful_requests/total_requests*100:.1f}%)")
    print(f"Failed: {failed_requests} ({failed_requests/total_requests*100:.1f}%)")
    print(f"Requests per second: {total_requests/total_time:.2f}")
    
    print("\n" + "-" * 60)
    print("PERFORMANCE BY ACTION:")
    print("-" * 60)
    
    for action, stats in action_stats.items():
        if stats['count'] > 0:
            avg_time = stats['total_time'] / stats['count'] if stats['count'] > 0 else 0
            success_rate = stats['success'] / stats['count'] * 100 if stats['count'] > 0 else 0
            
            print(f"\n{action.upper()}:")
            print(f"  Total: {stats['count']} requests")
            print(f"  Success Rate: {success_rate:.1f}%")
            if stats['min_time'] != float('inf'):
                print(f"  Avg Response Time: {avg_time:.3f}s")
                print(f"  Min Response Time: {stats['min_time']:.3f}s")
                print(f"  Max Response Time: {stats['max_time']:.3f}s")
    
    # Check for 500 errors
    error_500_count = sum(1 for r in all_results if r.get('status_code') == 500)
    if error_500_count > 0:
        print(f"\n⚠️  WARNING: {error_500_count} requests returned 500 errors!")
    
    # Save detailed results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"concurrency_test_results_{timestamp}.json"
    with open(filename, 'w') as f:
        json.dump({
            'summary': {
                'duration': total_time,
                'total_requests': total_requests,
                'successful': successful_requests,
                'failed': failed_requests,
                'requests_per_second': total_requests/total_time,
                'error_500_count': error_500_count
            },
            'action_stats': action_stats,
            'detailed_results': all_results
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {filename}")
    
    # Return success status
    return error_500_count == 0 and success_rate > 95

if __name__ == "__main__":
    success = run_concurrency_test()
    if success:
        print("\n✅ Concurrency test PASSED!")
    else:
        print("\n❌ Concurrency test FAILED - Issues detected")
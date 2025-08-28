#!/usr/bin/env python3
"""
Staged concurrent test - gradually increases load to test limits
"""
import requests
import threading
import time
import statistics
from collections import defaultdict

BASE_URL = "http://localhost:5000"

class TestUser:
    def __init__(self, user_id):
        self.user_id = user_id
        self.session = requests.Session()
        self.results = []
        
    def make_requests(self, num_requests=5):
        """Make multiple requests and track performance"""
        endpoints = [
            '/health',
            '/',
            '/login',
            '/production-health',
            '/api/dashboard/stats'
        ]
        
        for i in range(num_requests):
            endpoint = endpoints[i % len(endpoints)]
            start_time = time.time()
            
            try:
                if endpoint == '/login':
                    response = self.session.get(f"{BASE_URL}{endpoint}", timeout=10)
                else:
                    response = self.session.get(f"{BASE_URL}{endpoint}", timeout=10)
                
                elapsed = (time.time() - start_time) * 1000
                self.results.append({
                    'endpoint': endpoint,
                    'status': response.status_code,
                    'time': elapsed,
                    'success': response.status_code < 400
                })
            except Exception as e:
                elapsed = (time.time() - start_time) * 1000
                self.results.append({
                    'endpoint': endpoint,
                    'status': 0,
                    'time': elapsed,
                    'success': False,
                    'error': str(e)
                })
            
            # Small delay between requests
            time.sleep(0.1)

def run_staged_test():
    """Run test with gradually increasing concurrent users"""
    print("\n" + "="*70)
    print("TraceTrack Staged Concurrent Load Test")
    print("="*70)
    
    test_stages = [
        (5, "Light Load"),
        (10, "Moderate Load"),
        (15, "Normal Load"),
        (20, "Target Load"),
        (25, "Peak Load")
    ]
    
    all_results = {}
    
    for num_users, stage_name in test_stages:
        print(f"\n▶ Stage: {stage_name} ({num_users} users)")
        print("-" * 40)
        
        users = []
        threads = []
        
        # Create and start user threads
        for i in range(num_users):
            user = TestUser(i + 1)
            users.append(user)
            thread = threading.Thread(target=user.make_requests, args=(3,))
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
            time.sleep(0.05)  # Stagger starts slightly
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=15)
        
        elapsed = time.time() - start_time
        
        # Analyze results
        all_times = []
        success_count = 0
        total_count = 0
        endpoint_stats = defaultdict(list)
        
        for user in users:
            for result in user.results:
                total_count += 1
                if result['success']:
                    success_count += 1
                    all_times.append(result['time'])
                    endpoint_stats[result['endpoint']].append(result['time'])
        
        # Calculate statistics
        if all_times:
            success_rate = (success_count / total_count * 100) if total_count > 0 else 0
            avg_time = statistics.mean(all_times)
            median_time = statistics.median(all_times)
            max_time = max(all_times)
            
            print(f"  Success Rate: {success_rate:.1f}%")
            print(f"  Total Requests: {total_count}")
            print(f"  Avg Response: {avg_time:.0f} ms")
            print(f"  Median Response: {median_time:.0f} ms")
            print(f"  Max Response: {max_time:.0f} ms")
            print(f"  Requests/Second: {total_count/elapsed:.1f}")
            
            # Store results
            all_results[num_users] = {
                'stage': stage_name,
                'success_rate': success_rate,
                'avg_response': avg_time,
                'median_response': median_time,
                'max_response': max_time,
                'rps': total_count/elapsed
            }
            
            # Performance indicator
            if success_rate >= 95 and avg_time < 1000:
                print(f"  Status: ✅ EXCELLENT")
            elif success_rate >= 90 and avg_time < 2000:
                print(f"  Status: ⚠️  ACCEPTABLE")
            else:
                print(f"  Status: ❌ NEEDS OPTIMIZATION")
        else:
            print(f"  Status: ❌ ALL REQUESTS FAILED")
        
        # Cool down between stages
        time.sleep(2)
    
    # Final summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    
    # Find optimal concurrent users
    optimal_users = 0
    for users, results in all_results.items():
        if results['success_rate'] >= 95 and results['avg_response'] < 1000:
            optimal_users = users
    
    if optimal_users >= 20:
        print(f"\n✅ SUCCESS: Application can handle {optimal_users} concurrent users!")
        print(f"   The target of 20+ concurrent users has been achieved.")
    elif optimal_users >= 15:
        print(f"\n⚠️  PARTIAL SUCCESS: Application handles {optimal_users} concurrent users well.")
        print(f"   Some optimization may be needed for 20+ users.")
    else:
        print(f"\n❌ NEEDS OPTIMIZATION: Application struggles beyond {optimal_users} users.")
        print(f"   Multi-worker configuration is required for production.")
    
    # Deployment recommendation
    print("\n" + "="*70)
    print("Deployment Recommendation")
    print("="*70)
    
    if optimal_users >= 20:
        print("Current configuration is sufficient for production with 20+ users.")
    else:
        print("For production deployment with 20+ concurrent users:")
        print("Use the multi-worker configuration:")
        print("  gunicorn --workers 4 --threads 2 --worker-class gthread ...")
        print("\nThis provides 8 concurrent request handlers for better performance.")
    
    return optimal_users >= 20

if __name__ == "__main__":
    # Check server health first
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✅ Server is running (health check: {response.status_code})")
    except Exception as e:
        print(f"❌ Server not responding: {e}")
        exit(1)
    
    # Run staged test
    success = run_staged_test()
    exit(0 if success else 1)
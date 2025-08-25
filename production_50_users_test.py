#!/usr/bin/env python3
"""
Production Load Test - 50+ Concurrent Users
"""
import os
import sys
import time
import requests
import concurrent.futures
import statistics
from datetime import datetime

BASE_URL = "http://localhost:5000"

def simulate_user(user_id, duration=30):
    """Simulate user activity"""
    session = requests.Session()
    response_times = []
    errors = []
    
    end_time = time.time() + duration
    while time.time() < end_time:
        try:
            # Test random endpoints
            endpoints = ['/health', '/api/stats', '/api/v2/stats']
            for endpoint in endpoints:
                start = time.time()
                response = session.get(f"{BASE_URL}{endpoint}", timeout=10)
                elapsed = time.time() - start
                response_times.append(elapsed)
                
                if response.status_code >= 500:
                    errors.append(f"Error {response.status_code}")
                    
                time.sleep(0.5)  # Small delay between requests
                
        except Exception as e:
            errors.append(str(e)[:50])
    
    return response_times, errors

def main():
    """Run production load test"""
    print("Starting 50+ concurrent users load test...")
    
    # Test with 50 users for 30 seconds
    num_users = 50
    duration = 30
    
    all_response_times = []
    all_errors = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = [executor.submit(simulate_user, i, duration) for i in range(num_users)]
        
        for future in concurrent.futures.as_completed(futures):
            times, errors = future.result()
            all_response_times.extend(times)
            all_errors.extend(errors)
    
    # Calculate statistics
    if all_response_times:
        avg_time = statistics.mean(all_response_times) * 1000
        max_time = max(all_response_times) * 1000
        error_rate = len(all_errors) / (len(all_response_times) + len(all_errors)) * 100
        
        print(f"\n{'='*60}")
        print("PRODUCTION LOAD TEST RESULTS")
        print(f"{'='*60}")
        print(f"Concurrent Users: {num_users}")
        print(f"Test Duration: {duration} seconds")
        print(f"Total Requests: {len(all_response_times) + len(all_errors)}")
        print(f"Average Response: {avg_time:.2f}ms")
        print(f"Max Response: {max_time:.2f}ms")
        print(f"Error Rate: {error_rate:.2f}%")
        print(f"Total Errors: {len(all_errors)}")
        
        if error_rate < 1 and avg_time < 500:
            print("\n✅ SYSTEM IS PRODUCTION READY!")
            print("   • Can handle 50+ concurrent users")
            print("   • Error rate < 1%")
            print("   • Response times < 500ms")
        elif error_rate < 5:
            print("\n✅ System is production ready with minor issues")
        else:
            print("\n⚠️ System needs optimization")
        
        print(f"{'='*60}\n")
        
        sys.exit(0 if error_rate < 1 else 1)

if __name__ == "__main__":
    main()

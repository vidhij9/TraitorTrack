#!/usr/bin/env python3
"""
Cache Performance Test - Verify query optimizations
"""

import time
import requests
import statistics

BASE_URL = "http://0.0.0.0:5000"

def test_endpoint(endpoint, name, iterations=5):
    """Test an endpoint multiple times and measure performance"""
    times = []
    
    print(f"\nTesting {name} ({endpoint})...")
    print("-" * 50)
    
    for i in range(iterations):
        start = time.time()
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
        elapsed = (time.time() - start) * 1000  # Convert to ms
        times.append(elapsed)
        
        status = "✅" if response.status_code == 200 else "❌"
        cache_hit = "CACHED" if elapsed < 100 else "UNCACHED"
        print(f"  Request {i+1}: {elapsed:.2f}ms {status} [{cache_hit}]")
        
        # Small delay between requests
        time.sleep(0.1)
    
    # Calculate statistics
    avg_time = statistics.mean(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f"\n  Average: {avg_time:.2f}ms")
    print(f"  Min: {min_time:.2f}ms")
    print(f"  Max: {max_time:.2f}ms")
    
    # Performance assessment
    if avg_time < 50:
        print("  🚀 EXCELLENT - Under 50ms target!")
    elif avg_time < 100:
        print("  ✅ GOOD - Under 100ms")
    elif avg_time < 200:
        print("  ⚠️  FAIR - Needs optimization")
    else:
        print("  ❌ POOR - Requires immediate attention")
    
    return times

def main():
    print("=" * 60)
    print("CACHE PERFORMANCE TEST")
    print("=" * 60)
    
    endpoints = [
        ("/health", "Health Check"),
        ("/status", "Status Check"),
        ("/api/stats", "Dashboard Stats API"),
    ]
    
    all_times = {}
    
    for endpoint, name in endpoints:
        times = test_endpoint(endpoint, name)
        all_times[name] = times
    
    # Overall summary
    print("\n" + "=" * 60)
    print("PERFORMANCE SUMMARY")
    print("=" * 60)
    
    total_avg = 0
    for name, times in all_times.items():
        avg = statistics.mean(times)
        total_avg += avg
        status = "🚀" if avg < 50 else "✅" if avg < 100 else "⚠️" if avg < 200 else "❌"
        print(f"{status} {name}: {avg:.2f}ms average")
    
    overall_avg = total_avg / len(all_times)
    print(f"\nOverall Average: {overall_avg:.2f}ms")
    
    if overall_avg < 100:
        print("✅ SYSTEM PERFORMANCE: PRODUCTION READY")
    else:
        print("❌ SYSTEM PERFORMANCE: NEEDS OPTIMIZATION")

if __name__ == "__main__":
    main()
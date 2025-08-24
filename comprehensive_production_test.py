#!/usr/bin/env python3
"""
Comprehensive Production Test
Tests all critical functionality and performance metrics
"""

import requests
import json
import time
import concurrent.futures
from datetime import datetime
import statistics
import sys

BASE_URL = 'http://localhost:5000'

def test_endpoint(url, method='GET', data=None):
    """Test a single endpoint and return response time"""
    start = time.time()
    try:
        if method == 'GET':
            response = requests.get(url, timeout=5)
        else:
            response = requests.post(url, data=data, timeout=5)
        elapsed = (time.time() - start) * 1000  # Convert to ms
        return {
            'success': response.status_code == 200,
            'status_code': response.status_code,
            'time_ms': round(elapsed, 2)
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'time_ms': round((time.time() - start) * 1000, 2)
        }

def run_concurrent_test(endpoint, count=50):
    """Run concurrent requests to an endpoint"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n📊 Testing {endpoint} with {count} concurrent requests...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
        futures = [executor.submit(test_endpoint, url) for _ in range(count)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    # Calculate statistics
    times = [r['time_ms'] for r in results if r['success']]
    failures = [r for r in results if not r['success']]
    
    if times:
        stats = {
            'endpoint': endpoint,
            'total_requests': count,
            'successful': len(times),
            'failed': len(failures),
            'avg_time_ms': round(statistics.mean(times), 2),
            'median_time_ms': round(statistics.median(times), 2),
            'min_time_ms': round(min(times), 2),
            'max_time_ms': round(max(times), 2),
            'p95_time_ms': round(statistics.quantiles(times, n=20)[18], 2) if len(times) > 1 else times[0],
            'p99_time_ms': round(statistics.quantiles(times, n=100)[98], 2) if len(times) > 1 else times[0]
        }
    else:
        stats = {
            'endpoint': endpoint,
            'total_requests': count,
            'successful': 0,
            'failed': len(failures),
            'error': 'All requests failed'
        }
    
    return stats

def check_system_health():
    """Check if the system is running and healthy"""
    print("🔍 Checking system health...")
    
    health_checks = [
        ('/', 'Homepage'),
        ('/login', 'Login page'),
        ('/production-health', 'Health endpoint'),
        ('/api/stats', 'Stats API'),
        ('/api/fast_stats', 'Fast stats API')
    ]
    
    all_healthy = True
    for endpoint, name in health_checks:
        result = test_endpoint(f"{BASE_URL}{endpoint}")
        status = "✅" if result['success'] else "❌"
        print(f"  {status} {name}: {result['time_ms']}ms")
        if not result['success']:
            all_healthy = False
            if 'error' in result:
                print(f"     Error: {result['error']}")
    
    return all_healthy

def run_comprehensive_test():
    """Run comprehensive production tests"""
    print("=" * 70)
    print("🚀 COMPREHENSIVE PRODUCTION TEST")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Check system health first
    if not check_system_health():
        print("\n❌ System health check failed. Please ensure the application is running.")
        return False
    
    # Test critical endpoints under load
    endpoints = [
        '/api/fast_stats',
        '/api/stats',
        '/api/fast_scans',
        '/api/search?query=SB',
        '/'
    ]
    
    all_results = []
    for endpoint in endpoints:
        result = run_concurrent_test(endpoint, count=50)
        all_results.append(result)
        
        # Print results
        if 'error' not in result:
            print(f"  ✅ Success rate: {result['successful']}/{result['total_requests']}")
            print(f"  ⏱️  Average: {result['avg_time_ms']}ms | Median: {result['median_time_ms']}ms")
            print(f"  📈 P95: {result['p95_time_ms']}ms | P99: {result['p99_time_ms']}ms")
            print(f"  🔄 Range: {result['min_time_ms']}ms - {result['max_time_ms']}ms")
        else:
            print(f"  ❌ {result['error']}")
    
    # Calculate overall statistics
    print("\n" + "=" * 70)
    print("📊 OVERALL RESULTS")
    print("=" * 70)
    
    total_requests = sum(r['total_requests'] for r in all_results)
    total_successful = sum(r.get('successful', 0) for r in all_results)
    total_failed = sum(r.get('failed', 0) for r in all_results)
    
    print(f"Total requests: {total_requests}")
    print(f"Successful: {total_successful} ({total_successful/total_requests*100:.1f}%)")
    print(f"Failed: {total_failed} ({total_failed/total_requests*100:.1f}%)")
    
    # Check if system meets production criteria
    avg_times = [r.get('avg_time_ms', 0) for r in all_results if 'avg_time_ms' in r]
    if avg_times:
        overall_avg = statistics.mean(avg_times)
        print(f"\nOverall average response time: {overall_avg:.2f}ms")
        
        if overall_avg < 100:
            print("✅ EXCELLENT: System achieves <100ms average response time!")
        elif overall_avg < 200:
            print("✅ GOOD: System achieves <200ms average response time")
        elif overall_avg < 500:
            print("⚠️  ACCEPTABLE: System achieves <500ms average response time")
        else:
            print("❌ NEEDS OPTIMIZATION: System exceeds 500ms average response time")
    
    # Production readiness score
    score = 0
    if total_successful / total_requests > 0.99:
        score += 30
        print("\n✅ Reliability: 99%+ success rate")
    elif total_successful / total_requests > 0.95:
        score += 20
        print("\n⚠️  Reliability: 95%+ success rate")
    else:
        print("\n❌ Reliability: <95% success rate")
    
    if avg_times and overall_avg < 100:
        score += 40
        print("✅ Performance: <100ms average")
    elif avg_times and overall_avg < 200:
        score += 30
        print("✅ Performance: <200ms average")
    elif avg_times and overall_avg < 500:
        score += 20
        print("⚠️  Performance: <500ms average")
    else:
        print("❌ Performance: >500ms average")
    
    # Check P99 performance
    p99_times = [r.get('p99_time_ms', 0) for r in all_results if 'p99_time_ms' in r]
    if p99_times:
        p99_avg = statistics.mean(p99_times)
        if p99_avg < 500:
            score += 30
            print(f"✅ P99 Latency: {p99_avg:.0f}ms (<500ms)")
        elif p99_avg < 1000:
            score += 20
            print(f"⚠️  P99 Latency: {p99_avg:.0f}ms (<1000ms)")
        else:
            print(f"❌ P99 Latency: {p99_avg:.0f}ms (>1000ms)")
    
    print("\n" + "=" * 70)
    print(f"🏆 PRODUCTION READINESS SCORE: {score}/100")
    
    if score >= 90:
        print("✅ SYSTEM IS PRODUCTION READY!")
    elif score >= 70:
        print("⚠️  SYSTEM IS MOSTLY READY (minor optimizations needed)")
    else:
        print("❌ SYSTEM NEEDS OPTIMIZATION")
    
    print("=" * 70)
    print(f"🏁 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    return score >= 70

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)
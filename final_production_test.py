#!/usr/bin/env python3
"""
Final Production Test - Verify optimizations work
"""

import requests
import time
import statistics

print("🎯 FINAL PRODUCTION TEST")
print("=" * 60)

# Test endpoints
endpoints = [
    "/health",
    "/api/stats",
    "/dashboard",
    "/",
]

base_url = "https://traitortrack.replit.app"
response_times = []

print("\n📊 Testing individual endpoints:")
print("-" * 40)

for endpoint in endpoints:
    times = []
    for i in range(3):
        start = time.time()
        try:
            r = requests.get(base_url + endpoint, timeout=10)
            elapsed = time.time() - start
            times.append(elapsed)
            status = "✅" if r.status_code == 200 else f"❌ {r.status_code}"
            print(f"{endpoint}: {elapsed*1000:.0f}ms {status}")
        except Exception as e:
            print(f"{endpoint}: ❌ Failed - {e}")
        time.sleep(0.5)
    
    if times:
        avg = statistics.mean(times)
        response_times.append(avg)
        print(f"  Average: {avg*1000:.0f}ms")
    print()

print("=" * 60)
print("📈 OVERALL RESULTS:")

if response_times:
    overall_avg = statistics.mean(response_times) * 1000
    
    print(f"Average response time: {overall_avg:.0f}ms")
    
    if overall_avg < 100:
        print("✅ EXCELLENT: <100ms target achieved!")
    elif overall_avg < 200:
        print("✅ VERY GOOD: <200ms response times")
    elif overall_avg < 500:
        print("⚠️ GOOD: <500ms response times")
    elif overall_avg < 1000:
        print("⚠️ ACCEPTABLE: <1s response times")
    else:
        print("❌ NEEDS IMPROVEMENT: >1s response times")
else:
    print("❌ No successful responses")

print("=" * 60)

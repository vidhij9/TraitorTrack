#!/usr/bin/env python3
"""Test script for optimized endpoints"""
import requests
import time
import statistics

BASE_URL = "http://localhost:5000"

def test_endpoints():
    """Test optimized endpoints with authentication"""
    session = requests.Session()
    
    # Login
    print("🔐 Logging in as admin...")
    login_response = session.post(
        f"{BASE_URL}/login",
        data={"username": "admin", "password": "admin"},
        allow_redirects=False
    )
    
    if login_response.status_code not in [200, 302]:
        print(f"❌ Login failed: {login_response.status_code}")
        return
    
    print("✅ Login successful\n")
    
    # Test dashboard stats endpoint
    print("📊 Testing /api/dashboard/stats endpoint...")
    stats_times = []
    
    for i in range(10):
        start = time.time()
        response = session.get(f"{BASE_URL}/api/dashboard/stats")
        elapsed = (time.time() - start) * 1000
        stats_times.append(elapsed)
        
        if response.status_code == 200:
            data = response.json()
            if i == 0:
                print(f"   Response: {data}")
    
    print(f"\n   Stats endpoint performance (10 requests):")
    print(f"   Average: {statistics.mean(stats_times):.2f}ms")
    print(f"   Median: {statistics.median(stats_times):.2f}ms")
    print(f"   Min: {min(stats_times):.2f}ms")
    print(f"   Max: {max(stats_times):.2f}ms")
    
    # Test bag search endpoint
    print("\n🔍 Testing /api/bags/search endpoint...")
    search_times = []
    
    for i in range(10):
        start = time.time()
        response = session.get(f"{BASE_URL}/api/bags/search?q=BAG")
        elapsed = (time.time() - start) * 1000
        search_times.append(elapsed)
        
        if response.status_code == 200:
            data = response.json()
            if i == 0:
                print(f"   Response: {len(data.get('bags', []))} bags found")
    
    print(f"\n   Search endpoint performance (10 requests):")
    print(f"   Average: {statistics.mean(search_times):.2f}ms")
    print(f"   Median: {statistics.median(search_times):.2f}ms")
    print(f"   Min: {min(search_times):.2f}ms")
    print(f"   Max: {max(search_times):.2f}ms")
    
    # Performance summary
    print("\n" + "="*70)
    print("📈 PERFORMANCE SUMMARY")
    print("="*70)
    
    stats_status = "✅" if statistics.mean(stats_times) < 300 else "⚠️"
    search_status = "✅" if statistics.mean(search_times) < 300 else "⚠️"
    
    print(f"\nDashboard Stats: {stats_status}")
    print(f"  • Average: {statistics.mean(stats_times):.1f}ms")
    print(f"  • Median: {statistics.median(stats_times):.1f}ms")
    print(f"\nBag Search: {search_status}")
    print(f"  • Average: {statistics.mean(search_times):.1f}ms")
    print(f"  • Median: {statistics.median(search_times):.1f}ms")
    print()

if __name__ == "__main__":
    test_endpoints()

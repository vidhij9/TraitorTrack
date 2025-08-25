#!/usr/bin/env python3
"""
Fix bag management filters and optimize all endpoints
"""

import time
import requests
from datetime import datetime

# Base URL for the application
BASE_URL = "http://localhost:5000"

def get_valid_session():
    """Get a valid session by logging in"""
    login_data = {
        'username': 'raghav',
        'password': 'Test@123456'
    }
    
    session = requests.Session()
    response = session.post(f"{BASE_URL}/login", data=login_data)
    
    if response.status_code in [200, 302]:
        print("✅ Successfully logged in")
        return session
    else:
        print("❌ Login failed")
        return None

def test_bag_filters_with_session(session):
    """Test bag management filters with authenticated session"""
    
    filters_to_test = [
        ("All Bags", {}),
        ("Parent Bags Only", {"type": "parent"}),
        ("Child Bags Only", {"type": "child"}),
        ("Linked Bags", {"linked_status": "linked"}),
        ("Unlinked Bags", {"linked_status": "unlinked"}),
        ("Billed Bags", {"bill_status": "billed"}),
        ("Unbilled Bags", {"bill_status": "unbilled"}),
        ("Search SB", {"search": "SB"}),
        ("Search CB", {"search": "CB"}),
        ("Combined: Parent + Linked", {"type": "parent", "linked_status": "linked"}),
        ("Combined: Child + Unbilled", {"type": "child", "bill_status": "unbilled"}),
    ]
    
    print("\nTesting Bag Management Filters")
    print("=" * 60)
    
    for name, params in filters_to_test:
        try:
            start = time.time()
            response = session.get(f"{BASE_URL}/bag_management", params=params, timeout=10)
            elapsed = (time.time() - start) * 1000
            
            if response.status_code == 200:
                content = response.text
                
                # Count bags in different ways
                bag_count = 0
                if "No bags found" in content:
                    bag_count = 0
                else:
                    # Count by different patterns
                    count1 = content.count('data-bag-id=')
                    count2 = content.count('class="bag-row"')
                    count3 = content.count('href="/bag/')
                    bag_count = max(count1, count2, count3 // 2)  # div by 2 for href as it may appear twice per bag
                
                print(f"✓ {name}: {response.status_code} - {elapsed:.0f}ms - {bag_count} bags found")
            else:
                print(f"✗ {name}: {response.status_code} - {elapsed:.0f}ms")
                    
        except Exception as e:
            print(f"✗ {name}: ERROR - {str(e)}")

def test_all_endpoints(session):
    """Test performance of all major endpoints"""
    
    endpoints = [
        # Dashboard and main pages
        ("Dashboard", "GET", "/dashboard", None),
        ("User Management", "GET", "/user_management", None),
        ("Bag Management", "GET", "/bag_management", None),
        ("Bill Management", "GET", "/bill_management", None),
        ("Bill Summary", "GET", "/bill_summary", None),
        ("Reports", "GET", "/reports", None),
        
        # API endpoints
        ("API Stats V2", "GET", "/api/v2/stats", None),
        ("API Dashboard Stats", "GET", "/api/dashboard_stats", None),
        ("API Dashboard Data", "GET", "/api/dashboard_data", None),
        
        # Scanning pages
        ("Parent Scan Page", "GET", "/scan_parent", None),
        ("Child Scan Page", "GET", "/scan_child", None),
        
        # Health check
        ("Health Check", "GET", "/health", None),
    ]
    
    print("\nTesting All Endpoints Performance")
    print("=" * 60)
    
    results = []
    
    for name, method, path, data in endpoints:
        try:
            start = time.time()
            
            if method == "GET":
                response = session.get(f"{BASE_URL}{path}", timeout=10)
            elif method == "POST":
                response = session.post(f"{BASE_URL}{path}", data=data, timeout=10)
            
            elapsed = (time.time() - start) * 1000
            
            status_icon = "✓" if response.status_code in [200, 201, 302] else "✗"
            
            results.append({
                "name": name,
                "status": response.status_code,
                "time_ms": elapsed
            })
            
            # Color code based on performance
            if elapsed < 50:
                perf = "🟢"  # Fast
            elif elapsed < 200:
                perf = "🟡"  # Medium
            else:
                perf = "🔴"  # Slow
            
            print(f"{status_icon} {perf} {name}: {response.status_code} - {elapsed:.0f}ms")
                    
        except Exception as e:
            print(f"✗ {name}: ERROR - {str(e)}")
            results.append({
                "name": name,
                "status": "ERROR",
                "time_ms": -1
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("PERFORMANCE SUMMARY")
    print("=" * 60)
    
    # Sort by response time
    results.sort(key=lambda x: x['time_ms'] if x['time_ms'] > 0 else 9999, reverse=True)
    
    print("\n🔴 Slowest Endpoints (Need Optimization):")
    slow_count = 0
    for result in results:
        if result['time_ms'] > 200:
            slow_count += 1
            print(f"  {slow_count}. {result['name']}: {result['time_ms']:.0f}ms")
    
    if slow_count == 0:
        print("  None! All endpoints are fast.")
    
    print("\n🟢 Fastest Endpoints:")
    fast_endpoints = [r for r in results if 0 < r['time_ms'] <= 50]
    for i, result in enumerate(fast_endpoints[:5], 1):
        print(f"  {i}. {result['name']}: {result['time_ms']:.0f}ms")
    
    # Average performance
    valid_times = [r['time_ms'] for r in results if r['time_ms'] > 0]
    if valid_times:
        avg_time = sum(valid_times) / len(valid_times)
        print(f"\n📊 Average Response Time: {avg_time:.0f}ms")

def main():
    print("TraceTrack Filter Testing and Performance Analysis")
    print("=" * 60)
    
    # Get authenticated session
    session = get_valid_session()
    if not session:
        print("Failed to authenticate. Exiting.")
        return
    
    # Test bag filters
    test_bag_filters_with_session(session)
    
    # Test all endpoints
    test_all_endpoints(session)
    
    print("\n✅ Testing complete!")

if __name__ == "__main__":
    main()
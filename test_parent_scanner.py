#!/usr/bin/env python3
"""Test parent scanner performance"""

import requests
import time
import json

def test_parent_scan(qr_code="SB00123"):
    """Test parent scan endpoint performance"""
    
    # Get CSRF token from session
    session = requests.Session()
    
    # Login first (assuming test credentials)
    login_data = {
        'username': 'dispatcher1',
        'password': 'password123'
    }
    
    print("Logging in...")
    login_resp = session.post('http://localhost:5000/login', data=login_data, allow_redirects=False)
    
    if login_resp.status_code not in [200, 302]:
        print(f"Login failed: {login_resp.status_code}")
        return
    
    print(f"Testing parent scan for: {qr_code}")
    
    # Test parent scan
    start = time.time()
    
    scan_data = {
        'qr_code': qr_code,
        'csrf_token': ''  # Will use session
    }
    
    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    response = session.post(
        'http://localhost:5000/fast/parent_scan',
        data=scan_data,
        headers=headers
    )
    
    end = time.time()
    elapsed_ms = (end - start) * 1000
    
    print(f"Response time: {elapsed_ms:.2f}ms")
    print(f"Status code: {response.status_code}")
    
    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
    except:
        print(f"Response text: {response.text[:500]}")
    
    # Test multiple scans to get average
    print("\nRunning 10 scans for average...")
    times = []
    
    for i in range(10):
        qr = f"SB{str(i+50000).zfill(5)}"
        start = time.time()
        response = session.post(
            'http://localhost:5000/fast/parent_scan',
            data={'qr_code': qr, 'csrf_token': ''},
            headers=headers
        )
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)
        print(f"  Scan {i+1}: {qr} - {elapsed:.2f}ms")
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f"\nPerformance Summary:")
    print(f"  Average: {avg_time:.2f}ms")
    print(f"  Min: {min_time:.2f}ms")
    print(f"  Max: {max_time:.2f}ms")
    
    if avg_time > 100:
        print(f"  ⚠️  WARNING: Average time {avg_time:.2f}ms exceeds 100ms target!")
    else:
        print(f"  ✅ Performance within target (<100ms)")

if __name__ == "__main__":
    test_parent_scan()
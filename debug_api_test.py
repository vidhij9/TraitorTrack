#!/usr/bin/env python3
"""
Debug API Test - Find out why we're getting 400 errors
"""

import requests

def test_parent_scan():
    """Test parent scan with different approaches"""
    base_url = "http://localhost:5000"
    session = requests.Session()
    
    # Login first
    print("Logging in...")
    resp = session.post(f"{base_url}/login", data={
        'username': 'admin',
        'password': 'admin123'
    })
    print(f"Login status: {resp.status_code}\n")
    
    # Test 1: Form data without headers
    print("Test 1: Form data without headers")
    resp = session.post(f"{base_url}/process_parent_scan", data={
        'qr_code': 'SB12345',
        'location': 'Test Area'
    })
    print(f"Status: {resp.status_code}")
    if resp.status_code == 400:
        print(f"Response: {resp.text[:500]}")
    print()
    
    # Test 2: Form data with X-Requested-With header
    print("Test 2: Form data with X-Requested-With header")
    resp = session.post(f"{base_url}/process_parent_scan", 
        data={
            'qr_code': 'SB12345',
            'location': 'Test Area'
        },
        headers={'X-Requested-With': 'XMLHttpRequest'}
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        try:
            print(f"JSON Response: {resp.json()}")
        except:
            print(f"HTML Response: {resp.text[:200]}")
    print()
    
    # Test 3: JSON data
    print("Test 3: JSON data")
    resp = session.post(f"{base_url}/process_parent_scan", 
        json={
            'qr_code': 'SB12345',
            'location': 'Test Area'
        },
        headers={'Content-Type': 'application/json'}
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"Response: {resp.text[:500]}")
    print()

if __name__ == "__main__":
    test_parent_scan()
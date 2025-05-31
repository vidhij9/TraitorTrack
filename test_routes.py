#!/usr/bin/env python3
"""
Simple route testing script for TraceTrack application.
Tests key routes to ensure they respond correctly.
"""

import requests
import sys

def test_routes():
    """Test key application routes"""
    base_url = "http://localhost:5000"
    
    print("Testing TraceTrack Application Routes...")
    print("=" * 50)
    
    # Test cases: (route, expected_status, description)
    test_cases = [
        ("/", 302, "Home page (should redirect to login)"),
        ("/login", 200, "Login page"),
        ("/register", 200, "Registration page"),
        ("/api/stats", 302, "Stats API (requires login)"),
        ("/api/scans", 302, "Scans API (requires login)"),
        ("/api/activity/7", 302, "Activity API (requires login)"),
        ("/bags", 302, "Bag management (requires login)"),
        ("/bills", 302, "Bill management (requires login)"),
        ("/scan/parent", 302, "Parent scan (requires login)"),
        ("/scan/child", 302, "Child scan (requires login)"),
        ("/user_management", 302, "User management (requires login)"),
    ]
    
    passed = 0
    failed = 0
    
    for route, expected_status, description in test_cases:
        try:
            response = requests.get(f"{base_url}{route}", timeout=5, allow_redirects=False)
            if response.status_code == expected_status:
                print(f"✓ {description}")
                passed += 1
            else:
                print(f"✗ {description} - Expected {expected_status}, got {response.status_code}")
                failed += 1
        except requests.exceptions.RequestException as e:
            print(f"✗ {description} - Connection error: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")
    
    if failed == 0:
        print("All route tests passed!")
        return True
    else:
        print(f"{failed} tests failed.")
        return False

if __name__ == "__main__":
    success = test_routes()
    sys.exit(0 if success else 1)
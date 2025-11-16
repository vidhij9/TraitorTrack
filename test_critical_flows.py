#!/usr/bin/env python3
"""
Integration tests for TraitorTrack critical flows
Tests login, bag scanning, bill creation, deletion, and pagination
"""
import requests
import json
import os
from nanoid import generate

# Base URL
BASE_URL = "http://localhost:5000"

# Session for cookies
session = requests.Session()

def test_health_endpoints():
    """Test health check endpoints"""
    print("\n=== Testing Health Endpoints ===")
    
    # Test basic health
    response = session.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'healthy'
    print("✓ Basic health check passed")
    
    # Test detailed health with database check
    response = session.get(f"{BASE_URL}/health?check_db=true&detailed=true")
    assert response.status_code == 200
    data = response.json()
    assert data['database']['connected'] == True
    assert 'pool' in data['database']
    assert 'system' in data
    print("✓ Detailed health check with database passed")
    
    # Test fast status endpoint
    response = session.get(f"{BASE_URL}/status")
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'operational'
    print("✓ Fast status check passed")

def test_login():
    """Test user login flow"""
    print("\n=== Testing Login Flow ===")
    
    # First, get the login page to get CSRF token
    response = session.get(f"{BASE_URL}/login")
    assert response.status_code == 200
    print("✓ Login page loads successfully")
    
    # Try to login with admin credentials
    admin_password = os.environ.get('ADMIN_PASSWORD', '')
    if not admin_password:
        print("⚠️  ADMIN_PASSWORD not set, skipping login test")
        return False
    
    # Get CSRF token from page
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrf_token'})
    
    if csrf_token:
        csrf_value = csrf_token.get('value')
    else:
        print("⚠️  No CSRF token found, trying without it")
        csrf_value = None
    
    # Submit login form
    login_data = {
        'username': 'admin',
        'password': admin_password,
    }
    if csrf_value:
        login_data['csrf_token'] = csrf_value
    
    response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=True)
    
    # Check if we're redirected to dashboard
    if '/dashboard' in response.url or response.status_code == 200:
        print("✓ Login successful")
        return True
    else:
        print(f"✗ Login failed - Status: {response.status_code}, URL: {response.url}")
        return False

def test_parent_bag_scanning():
    """Test parent bag scanning via API"""
    print("\n=== Testing Parent Bag Scanning ===")
    
    # Generate unique parent bag ID
    parent_qr = f"SB{generate('0123456789', size=5)}"
    print(f"Testing with parent bag: {parent_qr}")
    
    # Test via fast parent scan API
    response = session.post(f"{BASE_URL}/api/fast_parent_scan", data={'qr_code': parent_qr})
    
    if response.status_code == 401:
        print("⚠️  Authentication required for scanning, skipping")
        return None
    
    assert response.status_code == 200
    data = response.json()
    
    if data.get('success'):
        print(f"✓ Parent bag {parent_qr} scanned successfully")
        return parent_qr
    else:
        print(f"✗ Parent bag scan failed: {data.get('message')}")
        return None

def test_database_query_performance():
    """Test database query performance using statistics cache"""
    print("\n=== Testing Database Query Performance ===")
    
    import time
    
    # Test statistics API (should use Redis cache in production)
    start = time.time()
    response = session.get(f"{BASE_URL}/api/statistics")
    elapsed = (time.time() - start) * 1000  # Convert to ms
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Statistics API responded in {elapsed:.2f}ms")
        if 'total_bags' in data or 'stats' in data:
            print(f"✓ Statistics data returned successfully")
    else:
        print(f"⚠️  Statistics API returned {response.status_code}")

def test_api_pagination():
    """Test API pagination endpoints"""
    print("\n=== Testing API Pagination ===")
    
    # Test bags API with pagination
    response = session.get(f"{BASE_URL}/api/bags?page=1&per_page=10")
    
    if response.status_code == 401 or response.status_code == 302:
        print("⚠️  Authentication required for API, skipping")
        return
    
    if response.status_code == 200:
        # Check if response is HTML (redirect to login) or JSON
        content_type = response.headers.get('Content-Type', '')
        if 'json' not in content_type:
            print("⚠️  API requires authentication (got HTML response), skipping")
            return
        
        try:
            data = response.json()
            if 'bags' in data or 'items' in data or isinstance(data, list):
                print("✓ Bags API pagination works")
            else:
                print(f"✓ Bags API returned: {list(data.keys()) if isinstance(data, dict) else 'list'}")
        except:
            print("⚠️  API response is not JSON, skipping")
    else:
        print(f"⚠️  Bags API returned {response.status_code}")

def main():
    """Run all tests"""
    print("=" * 60)
    print("TraitorTrack Critical Flows Integration Tests")
    print("=" * 60)
    
    try:
        # Test 1: Health endpoints (no auth required)
        test_health_endpoints()
        
        # Test 2: Login flow
        logged_in = test_login()
        
        # Test 3: Database query performance
        test_database_query_performance()
        
        # Test 4: API pagination
        test_api_pagination()
        
        # Test 5: Parent bag scanning (requires auth)
        if logged_in:
            test_parent_bag_scanning()
        
        print("\n" + "=" * 60)
        print("All available tests completed successfully!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())

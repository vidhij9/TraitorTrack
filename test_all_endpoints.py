#!/usr/bin/env python3
"""
Comprehensive endpoint testing for TraceTrack application
Tests all critical endpoints to ensure seamless operation
"""

import requests
import json
import time
import sys
from datetime import datetime

# Base URL for testing
BASE_URL = "http://localhost:5000"

# Test results storage
test_results = {
    "passed": 0,
    "failed": 0,
    "errors": []
}

def print_test_header(test_name):
    """Print formatted test header"""
    print(f"\n{'='*60}")
    print(f"Testing: {test_name}")
    print(f"{'='*60}")

def test_endpoint(method, path, description, data=None, headers=None, session=None, expected_status=200):
    """Test a single endpoint"""
    url = f"{BASE_URL}{path}"
    print(f"\n✓ Testing {method} {path}: {description}")
    
    try:
        if session:
            req_session = session
        else:
            req_session = requests.Session()
            
        if method == "GET":
            response = req_session.get(url, headers=headers)
        elif method == "POST":
            response = req_session.post(url, data=data, headers=headers)
        else:
            response = req_session.request(method, url, data=data, headers=headers)
            
        status_ok = response.status_code == expected_status
        
        if status_ok:
            print(f"  ✅ Status: {response.status_code} - PASS")
            test_results["passed"] += 1
        else:
            print(f"  ❌ Status: {response.status_code} (expected {expected_status}) - FAIL")
            test_results["failed"] += 1
            test_results["errors"].append(f"{method} {path}: Got {response.status_code}, expected {expected_status}")
            
        # Check response time
        if hasattr(response, 'elapsed'):
            ms = response.elapsed.total_seconds() * 1000
            if ms < 300:
                print(f"  ⚡ Response time: {ms:.2f}ms - Good")
            elif ms < 1000:
                print(f"  ⏱  Response time: {ms:.2f}ms - Acceptable")
            else:
                print(f"  🐌 Response time: {ms:.2f}ms - Slow")
                
        return response
        
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        test_results["failed"] += 1
        test_results["errors"].append(f"{method} {path}: {str(e)}")
        return None

def test_public_endpoints():
    """Test all public endpoints"""
    print_test_header("PUBLIC ENDPOINTS")
    
    # Basic pages
    test_endpoint("GET", "/", "Home page")
    test_endpoint("GET", "/health", "Health check")
    test_endpoint("GET", "/login", "Login page")
    test_endpoint("GET", "/register", "Register page")
    test_endpoint("GET", "/api/health", "API health check")

def test_authentication():
    """Test authentication flow"""
    print_test_header("AUTHENTICATION FLOW")
    
    session = requests.Session()
    
    # Test registration (might fail if user exists)
    reg_data = {
        "username": "testuser_" + str(int(time.time())),
        "email": f"test_{int(time.time())}@example.com",
        "password": "TestPass123!",
        "role": "dispatcher",
        "dispatch_area": "Area1"
    }
    
    response = test_endpoint("POST", "/register", "User registration", 
                            data=reg_data, session=session, expected_status=302)
    
    # Test login with admin
    login_data = {
        "username": "admin",
        "password": "admin"
    }
    
    response = test_endpoint("POST", "/login", "Admin login", 
                            data=login_data, session=session, expected_status=302)
    
    if response and response.status_code == 302:
        print("  ✅ Login successful, session created")
        
        # Test authenticated endpoints
        test_endpoint("GET", "/dashboard", "Dashboard access", session=session)
        test_endpoint("GET", "/profile", "Profile access", session=session)
        test_endpoint("GET", "/api/v2/stats", "API stats", session=session)
        test_endpoint("GET", "/api/stats", "API stats alternate", session=session)
        test_endpoint("GET", "/api/scans", "Recent scans API", session=session)
        
        # Test logout
        test_endpoint("GET", "/logout", "Logout", session=session, expected_status=302)
    
    return session

def test_scanning_endpoints():
    """Test scanning related endpoints"""
    print_test_header("SCANNING ENDPOINTS")
    
    # Login first
    session = requests.Session()
    login_data = {"username": "admin", "password": "admin"}
    session.post(f"{BASE_URL}/login", data=login_data)
    
    # Test scanning pages
    test_endpoint("GET", "/scan_parent", "Parent scan page", session=session)
    test_endpoint("GET", "/scan_child", "Child scan page", session=session)
    test_endpoint("GET", "/batch_scanning", "Batch scan page", session=session)
    
    # Test scanning APIs
    parent_data = {"qr_code": f"SB{int(time.time()) % 100000:05d}"}
    test_endpoint("POST", "/fast/parent_scan", "Fast parent scan API", 
                 data=parent_data, session=session)
    
    child_data = {"qr_code": f"CB{int(time.time()) % 100000:05d}"}
    test_endpoint("POST", "/fast/child_scan", "Fast child scan API", 
                 data=child_data, session=session)

def test_management_pages():
    """Test all management pages"""
    print_test_header("MANAGEMENT PAGES")
    
    # Login as admin
    session = requests.Session()
    login_data = {"username": "admin", "password": "admin"}
    session.post(f"{BASE_URL}/login", data=login_data)
    
    # Test all management pages
    test_endpoint("GET", "/bag_management", "Bag management", session=session)
    test_endpoint("GET", "/bill_management", "Bill management", session=session)
    test_endpoint("GET", "/user_management", "User management", session=session)
    test_endpoint("GET", "/lookup", "Lookup page", session=session)
    test_endpoint("GET", "/analytics", "Analytics page", session=session)
    test_endpoint("GET", "/admin/promotions", "Admin promotions", session=session)

def test_api_endpoints():
    """Test all API endpoints"""
    print_test_header("API ENDPOINTS")
    
    # Login as admin
    session = requests.Session()
    login_data = {"username": "admin", "password": "admin"}
    session.post(f"{BASE_URL}/login", data=login_data)
    
    # Dashboard and stats APIs
    test_endpoint("GET", "/api/dashboard/analytics", "Dashboard analytics", session=session)
    test_endpoint("GET", "/api/dashboard-stats", "Dashboard stats", session=session)
    test_endpoint("GET", "/api/bag-count", "Bag count API", session=session)
    test_endpoint("GET", "/api/recent-scans", "Recent scans API", session=session)
    
    # Search and lookup APIs
    lookup_data = {"query": "SB", "query_type": "qr"}
    test_endpoint("POST", "/api/lookup", "Lookup API", data=lookup_data, session=session)
    
    # Bill APIs
    test_endpoint("GET", "/api/bills", "Bills list API", session=session)
    test_endpoint("GET", "/api/bills/active", "Active bills API", session=session)

def test_database_operations():
    """Test database operations and connection pooling"""
    print_test_header("DATABASE OPERATIONS")
    
    session = requests.Session()
    login_data = {"username": "admin", "password": "admin"}
    session.post(f"{BASE_URL}/login", data=login_data)
    
    # Create test data
    print("\n📊 Testing database operations:")
    
    # Test bag creation
    for i in range(5):
        qr_code = f"TEST{int(time.time())}{i:03d}"
        response = session.post(f"{BASE_URL}/fast/parent_scan", 
                               data={"qr_code": qr_code})
        if response and response.status_code == 200:
            print(f"  ✅ Created test bag {qr_code}")
            
    # Test concurrent reads
    import concurrent.futures
    
    def fetch_stats(session_num):
        s = requests.Session()
        s.post(f"{BASE_URL}/login", data={"username": "admin", "password": "admin"})
        return s.get(f"{BASE_URL}/api/v2/stats")
    
    print("\n🔄 Testing concurrent access (10 simultaneous requests):")
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_stats, i) for i in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
        successful = sum(1 for r in results if r.status_code == 200)
        print(f"  ✅ Successful concurrent requests: {successful}/10")

def test_performance():
    """Test performance metrics"""
    print_test_header("PERFORMANCE METRICS")
    
    session = requests.Session()
    login_data = {"username": "admin", "password": "admin"}
    session.post(f"{BASE_URL}/login", data=login_data)
    
    endpoints = [
        "/dashboard",
        "/api/v2/stats", 
        "/bag_management",
        "/api/dashboard-stats"
    ]
    
    print("\n⚡ Response time benchmarks:")
    for endpoint in endpoints:
        times = []
        for _ in range(3):
            start = time.time()
            response = session.get(f"{BASE_URL}{endpoint}")
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
            
        avg_time = sum(times) / len(times)
        if avg_time < 300:
            status = "✅ EXCELLENT"
        elif avg_time < 1000:
            status = "⚠️  ACCEPTABLE"
        else:
            status = "❌ SLOW"
            
        print(f"  {endpoint}: {avg_time:.2f}ms avg - {status}")

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("TRACETRACK COMPREHENSIVE ENDPOINT TESTING")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing URL: {BASE_URL}")
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("\n❌ Server not responding properly!")
            return False
    except:
        print("\n❌ Cannot connect to server! Is it running?")
        return False
    
    # Run all test suites
    test_public_endpoints()
    test_authentication()
    test_scanning_endpoints()
    test_management_pages()
    test_api_endpoints()
    test_database_operations()
    test_performance()
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"✅ Passed: {test_results['passed']}")
    print(f"❌ Failed: {test_results['failed']}")
    print(f"Success Rate: {(test_results['passed']/(test_results['passed']+test_results['failed'])*100):.1f}%")
    
    if test_results["errors"]:
        print("\n⚠️  Failed Tests:")
        for error in test_results["errors"][:10]:  # Show first 10 errors
            print(f"  - {error}")
    
    if test_results["failed"] == 0:
        print("\n🎉 ALL TESTS PASSED! System is working seamlessly!")
        return True
    else:
        print(f"\n⚠️  {test_results['failed']} tests failed. Review errors above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
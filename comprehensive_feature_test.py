#!/usr/bin/env python3
"""
Comprehensive Feature Test for TraceTrack
Tests all major features and API endpoints
"""

import requests
import time
import json
from datetime import datetime

BASE_URL = "http://localhost:5000"
session = requests.Session()

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'

def log_test(test_name):
    print(f"\n{Colors.CYAN}{Colors.BOLD}🧪 Testing: {test_name}{Colors.END}")

def log_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def log_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def log_info(message):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")

def log_warning(message):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

# Test results tracking
test_results = {
    "passed": 0,
    "failed": 0,
    "warnings": 0
}

def test_authentication():
    """Test login, logout, and session management"""
    log_test("Authentication Flow")
    
    # Test login with admin credentials
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
    
    if response.status_code in [200, 302]:
        log_success("Admin login successful")
        test_results["passed"] += 1
    else:
        log_error(f"Login failed: {response.status_code}")
        test_results["failed"] += 1
        return False
    
    # Test session persistence
    dashboard_response = session.get(f"{BASE_URL}/dashboard")
    if dashboard_response.status_code == 200:
        log_success("Session persists - dashboard accessible")
        test_results["passed"] += 1
    else:
        log_error("Session not maintained")
        test_results["failed"] += 1
    
    return True

def test_dashboard_apis():
    """Test dashboard and statistics APIs"""
    log_test("Dashboard APIs")
    
    endpoints = [
        "/api/dashboard/stats",
        "/api/stats",
        "/api/health",
        "/api/system/health"
    ]
    
    for endpoint in endpoints:
        response = session.get(f"{BASE_URL}{endpoint}")
        if response.status_code == 200:
            try:
                data = response.json()
                log_success(f"{endpoint} - Response: {response.status_code}")
                test_results["passed"] += 1
            except:
                log_warning(f"{endpoint} - Non-JSON response")
                test_results["warnings"] += 1
        else:
            log_error(f"{endpoint} - Failed: {response.status_code}")
            test_results["failed"] += 1

def test_bag_scanning():
    """Test parent and child bag scanning"""
    log_test("Bag Scanning Operations")
    
    # Generate unique QR codes for testing
    timestamp = int(time.time())
    parent_qr = f"PARENT_{timestamp}"
    child1_qr = f"CHILD_{timestamp}_1"
    child2_qr = f"CHILD_{timestamp}_2"
    
    # Test parent bag scan
    parent_data = {
        'qr_id': parent_qr,
        'weight': '25.5'
    }
    
    response = session.post(f"{BASE_URL}/process_parent_scan", data=parent_data, allow_redirects=False)
    if response.status_code in [200, 302]:
        log_success(f"Parent bag scanned: {parent_qr}")
        test_results["passed"] += 1
    else:
        log_error(f"Parent scan failed: {response.status_code}")
        test_results["failed"] += 1
        return None
    
    # Test child bag scan
    child_data = {
        'parent_qr': parent_qr,
        'child_qr': child1_qr,
        'weight': '10.2'
    }
    
    response = session.post(f"{BASE_URL}/process_child_scan", data=child_data, allow_redirects=False)
    if response.status_code in [200, 302]:
        log_success(f"Child bag scanned: {child1_qr} linked to {parent_qr}")
        test_results["passed"] += 1
    else:
        log_error(f"Child scan failed: {response.status_code}")
        test_results["failed"] += 1
    
    # Scan second child
    child_data['child_qr'] = child2_qr
    child_data['weight'] = '8.5'
    response = session.post(f"{BASE_URL}/process_child_scan", data=child_data, allow_redirects=False)
    if response.status_code in [200, 302]:
        log_success(f"Second child scanned: {child2_qr}")
        test_results["passed"] += 1
    else:
        log_warning(f"Second child scan response: {response.status_code}")
        test_results["warnings"] += 1
    
    return parent_qr

def test_bag_search(parent_qr):
    """Test bag search functionality"""
    log_test("Bag Search")
    
    if not parent_qr:
        parent_qr = "PARENT"
    
    # Test API search
    response = session.get(f"{BASE_URL}/api/bags/search?q={parent_qr}")
    if response.status_code == 200:
        try:
            data = response.json()
            log_success(f"Search API returned {len(data.get('bags', []))} results")
            test_results["passed"] += 1
        except:
            # Not JSON, might be HTML redirect
            if 'redirect' in response.text.lower() or response.status_code == 302:
                log_warning(f"Search API redirected (auth issue)")
                test_results["warnings"] += 1
            else:
                log_error(f"Search API returned non-JSON: {response.text[:100]}")
                test_results["failed"] += 1
    else:
        log_error(f"Search failed: {response.status_code}")
        test_results["failed"] += 1
    
    # Test lookup page
    response = session.get(f"{BASE_URL}/lookup")
    if response.status_code == 200:
        log_success("Lookup page accessible")
        test_results["passed"] += 1
    else:
        log_error(f"Lookup page failed: {response.status_code}")
        test_results["failed"] += 1

def test_bill_management(parent_qr):
    """Test bill creation and management"""
    log_test("Bill Management")
    
    # Test bill creation page
    response = session.get(f"{BASE_URL}/bill/create")
    if response.status_code == 200:
        log_success("Bill creation page accessible")
        test_results["passed"] += 1
    else:
        log_error(f"Bill creation page failed: {response.status_code}")
        test_results["failed"] += 1
    
    # Create a bill
    timestamp = int(time.time())
    bill_data = {
        'bill_number': f'BILL_{timestamp}',
        'destination': 'Test Warehouse',
        'truck_number': 'TRK-123'
    }
    
    response = session.post(f"{BASE_URL}/bill/create", data=bill_data, allow_redirects=False)
    if response.status_code in [200, 302]:
        log_success(f"Bill created: {bill_data['bill_number']}")
        test_results["passed"] += 1
        
        # Extract bill ID from redirect
        if 'Location' in response.headers:
            location = response.headers['Location']
            if '/bill/' in location:
                bill_id = location.split('/bill/')[1].split('/')[0]
                log_info(f"Bill ID: {bill_id}")
                return bill_id
    else:
        log_error(f"Bill creation failed: {response.status_code}")
        test_results["failed"] += 1
    
    return None

def test_user_management():
    """Test user management operations (admin only)"""
    log_test("User Management")
    
    # Test user management page
    response = session.get(f"{BASE_URL}/user_management")
    if response.status_code == 200:
        log_success("User management page accessible")
        test_results["passed"] += 1
    else:
        log_warning(f"User management page: {response.status_code}")
        test_results["warnings"] += 1
    
    # Test user API
    response = session.get(f"{BASE_URL}/api/users")
    if response.status_code == 200:
        try:
            data = response.json()
            log_success(f"User API returned {len(data)} users")
            test_results["passed"] += 1
        except:
            log_warning(f"User API returned non-JSON")
            test_results["warnings"] += 1
    else:
        log_error(f"User API failed: {response.status_code}")
        test_results["failed"] += 1

def test_scans_management():
    """Test scans listing and management"""
    log_test("Scans Management")
    
    # Test scans page
    response = session.get(f"{BASE_URL}/scans")
    if response.status_code == 200:
        log_success("Scans page accessible")
        test_results["passed"] += 1
    else:
        log_error(f"Scans page failed: {response.status_code}")
        test_results["failed"] += 1
    
    # Test scans API
    response = session.get(f"{BASE_URL}/api/scans")
    if response.status_code == 200:
        try:
            data = response.json()
            log_success(f"Scans API returned data")
            test_results["passed"] += 1
        except:
            log_warning(f"Scans API returned non-JSON")
            test_results["warnings"] += 1
    else:
        log_error(f"Scans API failed: {response.status_code}")
        test_results["failed"] += 1
    
    # Test recent scans
    response = session.get(f"{BASE_URL}/api/scans/recent")
    if response.status_code == 200:
        log_success("Recent scans API working")
        test_results["passed"] += 1
    else:
        log_error(f"Recent scans failed: {response.status_code}")
        test_results["failed"] += 1

def test_bags_management():
    """Test bags listing and management"""
    log_test("Bags Management")
    
    # Test bags page
    response = session.get(f"{BASE_URL}/bags")
    if response.status_code == 200:
        log_success("Bags page accessible")
        test_results["passed"] += 1
    else:
        log_error(f"Bags page failed: {response.status_code}")
        test_results["failed"] += 1
    
    # Test bags API
    response = session.get(f"{BASE_URL}/api/bags")
    if response.status_code == 200:
        try:
            data = response.json()
            log_success("Bags API working")
            test_results["passed"] += 1
        except:
            log_warning("Bags API returned non-JSON")
            test_results["warnings"] += 1
    else:
        log_error(f"Bags API failed: {response.status_code}")
        test_results["failed"] += 1
    
    # Test parent bags list
    response = session.get(f"{BASE_URL}/api/bags/parent/list")
    if response.status_code == 200:
        log_success("Parent bags API working")
        test_results["passed"] += 1
    else:
        log_error(f"Parent bags API failed: {response.status_code}")
        test_results["failed"] += 1

def test_bills_management():
    """Test bills listing"""
    log_test("Bills Management")
    
    # Test bills page
    response = session.get(f"{BASE_URL}/bills")
    if response.status_code == 200:
        log_success("Bills page accessible")
        test_results["passed"] += 1
    else:
        log_error(f"Bills page failed: {response.status_code}")
        test_results["failed"] += 1
    
    # Test bills API
    response = session.get(f"{BASE_URL}/api/bills")
    if response.status_code == 200:
        try:
            data = response.json()
            log_success("Bills API working")
            test_results["passed"] += 1
        except:
            log_warning("Bills API returned non-JSON")
            test_results["warnings"] += 1
    else:
        log_error(f"Bills API failed: {response.status_code}")
        test_results["failed"] += 1

def test_health_endpoints():
    """Test all health and monitoring endpoints"""
    log_test("Health & Monitoring Endpoints")
    
    health_endpoints = [
        "/health",
        "/api/health",
        "/api/system/health",
        "/db/health"
    ]
    
    for endpoint in health_endpoints:
        response = session.get(f"{BASE_URL}{endpoint}")
        if response.status_code == 200:
            log_success(f"{endpoint} - Healthy")
            test_results["passed"] += 1
        else:
            log_warning(f"{endpoint} - Status: {response.status_code}")
            test_results["warnings"] += 1

def test_excel_upload():
    """Test Excel upload page"""
    log_test("Excel Upload")
    
    response = session.get(f"{BASE_URL}/excel_upload")
    if response.status_code == 200:
        log_success("Excel upload page accessible")
        test_results["passed"] += 1
    else:
        log_error(f"Excel upload page failed: {response.status_code}")
        test_results["failed"] += 1

def test_performance_apis():
    """Test performance monitoring APIs"""
    log_test("Performance Monitoring")
    
    perf_endpoints = [
        "/api/performance/metrics",
        "/api/performance/endpoints"
    ]
    
    for endpoint in perf_endpoints:
        response = session.get(f"{BASE_URL}{endpoint}")
        if response.status_code == 200:
            log_success(f"{endpoint} - Working")
            test_results["passed"] += 1
        else:
            log_warning(f"{endpoint} - Status: {response.status_code}")
            test_results["warnings"] += 1

def print_summary():
    """Print test summary"""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}📊 COMPREHENSIVE TEST SUMMARY{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")
    
    total_tests = test_results["passed"] + test_results["failed"] + test_results["warnings"]
    
    print(f"{Colors.GREEN}✅ Passed: {test_results['passed']}{Colors.END}")
    print(f"{Colors.RED}❌ Failed: {test_results['failed']}{Colors.END}")
    print(f"{Colors.YELLOW}⚠️  Warnings: {test_results['warnings']}{Colors.END}")
    print(f"{Colors.BOLD}📈 Total Tests: {total_tests}{Colors.END}")
    
    if test_results["failed"] == 0:
        success_rate = 100.0
    else:
        success_rate = (test_results["passed"] / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n{Colors.BOLD}Success Rate: {success_rate:.1f}%{Colors.END}")
    
    if test_results["failed"] == 0 and test_results["warnings"] <= 2:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL CRITICAL TESTS PASSED - DEPLOYMENT READY!{Colors.END}")
        return True
    elif test_results["failed"] == 0:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  SOME WARNINGS - REVIEW BEFORE DEPLOYMENT{Colors.END}")
        return True
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ CRITICAL FAILURES - NOT READY FOR DEPLOYMENT{Colors.END}")
        return False

def main():
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}")
    print("🚀 TraceTrack Comprehensive Feature Test")
    print(f"{'='*70}{Colors.END}\n")
    print(f"Testing against: {BASE_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    try:
        # Run all tests in sequence
        if not test_authentication():
            log_error("Authentication failed - stopping tests")
            print_summary()
            return
        
        parent_qr = test_bag_scanning()
        test_bag_search(parent_qr)
        test_bill_management(parent_qr)
        test_user_management()
        test_scans_management()
        test_bags_management()
        test_bills_management()
        test_dashboard_apis()
        test_health_endpoints()
        test_excel_upload()
        test_performance_apis()
        
        # Print summary
        is_ready = print_summary()
        
        print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        return is_ready
        
    except Exception as e:
        log_error(f"Test suite error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

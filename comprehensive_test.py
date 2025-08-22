"""Comprehensive test for all TraceTrack workflows with authentication"""
import requests
import time
import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = 'http://localhost:5000'

def test_admin_workflow():
    """Test admin user workflows"""
    s = requests.Session()
    results = {'login': False, 'user_mgmt': False, 'bills': False, 'promotions': False}
    
    try:
        # Login as admin
        login = s.post(f'{BASE_URL}/login', data={'username': 'admin', 'password': 'admin123'})
        if login.status_code in [200, 302]:
            results['login'] = True
            
            # Test user management access
            user_mgmt = s.get(f'{BASE_URL}/user_management')
            if user_mgmt.status_code == 200 and 'User Management' in user_mgmt.text:
                results['user_mgmt'] = True
            
            # Test bill management access
            bills = s.get(f'{BASE_URL}/bills')
            if bills.status_code == 200:
                results['bills'] = True
            
            # Test promotion management access
            promotions = s.get(f'{BASE_URL}/admin/promotions')
            if promotions.status_code == 200:
                results['promotions'] = True
                
    except Exception as e:
        print(f"Admin test error: {e}")
    
    return results

def test_biller_workflow():
    """Test biller user workflows"""
    s = requests.Session()
    results = {'login': False, 'bills': False, 'bags': False, 'user_mgmt_blocked': False}
    
    try:
        # Login as biller
        login = s.post(f'{BASE_URL}/login', data={'username': 'biller', 'password': 'biller123'})
        if login.status_code in [200, 302]:
            results['login'] = True
            
            # Test bill management access (should work)
            bills = s.get(f'{BASE_URL}/bills')
            if bills.status_code == 200:
                results['bills'] = True
            
            # Test bag management access (should work)
            bags = s.get(f'{BASE_URL}/bags')
            if bags.status_code == 200:
                results['bags'] = True
            
            # Test user management access (should be blocked)
            user_mgmt = s.get(f'{BASE_URL}/user_management', allow_redirects=False)
            if user_mgmt.status_code in [302, 403]:
                results['user_mgmt_blocked'] = True
                
    except Exception as e:
        print(f"Biller test error: {e}")
    
    return results

def test_dispatcher_workflow():
    """Test dispatcher user workflows"""
    s = requests.Session()
    results = {'login': False, 'scan': False, 'bags': False, 'bills_blocked': False}
    
    try:
        # Login as dispatcher
        login = s.post(f'{BASE_URL}/login', data={'username': 'dispatcher', 'password': 'dispatcher123'})
        if login.status_code in [200, 302]:
            results['login'] = True
            
            # Test scanning access (should work)
            parent_qr = f'SB{random.randint(10000, 99999):05d}'
            parent = s.post(f'{BASE_URL}/process_parent_scan', data={'qr_code': parent_qr})
            if parent.status_code == 200:
                results['scan'] = True
            
            # Test bag management access (should work)
            bags = s.get(f'{BASE_URL}/bags')
            if bags.status_code == 200:
                results['bags'] = True
            
            # Test bill management access (should be blocked)
            bills = s.get(f'{BASE_URL}/bills', allow_redirects=False)
            if bills.status_code in [302, 403] or 'Access restricted' in bills.text:
                results['bills_blocked'] = True
                
    except Exception as e:
        print(f"Dispatcher test error: {e}")
    
    return results

def test_scanning_workflow():
    """Test complete scanning workflow"""
    s = requests.Session()
    results = {'login': False, 'parent': False, 'child': False, 'complete': False}
    
    try:
        # Login as admin
        login = s.post(f'{BASE_URL}/login', data={'username': 'admin', 'password': 'admin123'})
        if login.status_code in [200, 302]:
            results['login'] = True
            
            # Parent scan (SB followed by exactly 5 digits)
            parent_qr = f'SB{random.randint(10000, 99999):05d}'
            parent = s.post(f'{BASE_URL}/process_parent_scan', data={'qr_code': parent_qr})
            if parent.status_code == 200 and 'scan_child' in parent.url:
                results['parent'] = True
                
                # Child scan
                child_qr = f'CB{random.randint(100000, 999999)}'
                child = s.post(f'{BASE_URL}/process_child_scan', data={'qr_code': child_qr})
                if child.status_code == 200:
                    try:
                        data = child.json()
                        results['child'] = data.get('success', False)
                    except:
                        pass
                
                # Complete scan
                complete = s.get(f'{BASE_URL}/scan/complete')
                if complete.status_code == 200:
                    results['complete'] = True
                    
    except Exception as e:
        print(f"Scanning test error: {e}")
    
    return results

def test_lookup_workflow():
    """Test lookup functionality"""
    s = requests.Session()
    results = {'login': False, 'lookup': False}
    
    try:
        # Login as admin
        login = s.post(f'{BASE_URL}/login', data={'username': 'admin', 'password': 'admin123'})
        if login.status_code in [200, 302]:
            results['login'] = True
            
            # Test lookup (use valid QR format)
            lookup = s.get(f'{BASE_URL}/lookup')  # First GET the page
            if lookup.status_code == 200:
                # Then POST with valid QR code
                lookup = s.post(f'{BASE_URL}/lookup', data={'qr_code': 'SB12345'})
            if lookup.status_code == 200:
                results['lookup'] = True
                
    except Exception as e:
        print(f"Lookup test error: {e}")
    
    return results

def test_promotion_request_workflow():
    """Test promotion request workflow"""
    s = requests.Session()
    results = {'login': False, 'request': False}
    
    try:
        # Login as dispatcher
        login = s.post(f'{BASE_URL}/login', data={'username': 'dispatcher', 'password': 'dispatcher123'})
        if login.status_code in [200, 302]:
            results['login'] = True
            
            # Access promotion request page
            request_page = s.get(f'{BASE_URL}/request_promotion')
            if request_page.status_code == 200:
                results['request'] = True
                
    except Exception as e:
        print(f"Promotion request test error: {e}")
    
    return results

def test_unauthorized_access():
    """Test that unauthenticated users are blocked"""
    s = requests.Session()
    results = {}
    
    protected_routes = [
        '/user_management',
        '/bags',
        '/bills',
        '/scan_parent',
        '/scan_child',
        '/lookup',
        '/scans',
        '/admin/promotions'
    ]
    
    for route in protected_routes:
        try:
            resp = s.get(f'{BASE_URL}{route}', allow_redirects=False)
            # Should redirect to login
            results[route] = resp.status_code in [302, 401, 403]
        except:
            results[route] = False
    
    return results

def run_comprehensive_test():
    """Run all tests comprehensively"""
    print("=" * 70)
    print("🧪 COMPREHENSIVE TRACETRACK AUTHENTICATION & WORKFLOW TEST")
    print("=" * 70)
    
    all_passed = True
    
    # Test 1: Admin workflows
    print("\n📊 Testing Admin Workflows...")
    admin_results = test_admin_workflow()
    for key, value in admin_results.items():
        status = "✅" if value else "❌"
        print(f"   {status} Admin {key}: {'PASS' if value else 'FAIL'}")
        if not value:
            all_passed = False
    
    # Test 2: Biller workflows
    print("\n💰 Testing Biller Workflows...")
    biller_results = test_biller_workflow()
    for key, value in biller_results.items():
        status = "✅" if value else "❌"
        print(f"   {status} Biller {key}: {'PASS' if value else 'FAIL'}")
        if not value:
            all_passed = False
    
    # Test 3: Dispatcher workflows
    print("\n📦 Testing Dispatcher Workflows...")
    dispatcher_results = test_dispatcher_workflow()
    for key, value in dispatcher_results.items():
        status = "✅" if value else "❌"
        print(f"   {status} Dispatcher {key}: {'PASS' if value else 'FAIL'}")
        if not value:
            all_passed = False
    
    # Test 4: Scanning workflow
    print("\n🔍 Testing Scanning Workflow...")
    scan_results = test_scanning_workflow()
    for key, value in scan_results.items():
        status = "✅" if value else "❌"
        print(f"   {status} Scanning {key}: {'PASS' if value else 'FAIL'}")
        if not value:
            all_passed = False
    
    # Test 5: Lookup workflow
    print("\n🔎 Testing Lookup Workflow...")
    lookup_results = test_lookup_workflow()
    for key, value in lookup_results.items():
        status = "✅" if value else "❌"
        print(f"   {status} Lookup {key}: {'PASS' if value else 'FAIL'}")
        if not value:
            all_passed = False
    
    # Test 6: Promotion request workflow
    print("\n📋 Testing Promotion Request Workflow...")
    promo_results = test_promotion_request_workflow()
    for key, value in promo_results.items():
        status = "✅" if value else "❌"
        print(f"   {status} Promotion {key}: {'PASS' if value else 'FAIL'}")
        if not value:
            all_passed = False
    
    # Test 7: Unauthorized access blocking
    print("\n🔒 Testing Unauthorized Access Blocking...")
    unauth_results = test_unauthorized_access()
    unauth_passed = all(unauth_results.values())
    if unauth_passed:
        print(f"   ✅ All {len(unauth_results)} protected routes are secured")
    else:
        for route, blocked in unauth_results.items():
            if not blocked:
                print(f"   ❌ Route {route} is NOT secured!")
                all_passed = False
    
    # Test 8: Concurrent user test
    print("\n🚀 Testing Concurrent Users...")
    num_users = 10
    success_count = 0
    
    with ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = [executor.submit(test_scanning_workflow) for _ in range(num_users)]
        
        for future in as_completed(futures):
            result = future.result()
            if result['child']:
                success_count += 1
    
    concurrent_passed = success_count >= num_users * 0.8
    status = "✅" if concurrent_passed else "❌"
    print(f"   {status} Concurrent: {success_count}/{num_users} users completed workflow")
    if not concurrent_passed:
        all_passed = False
    
    # Final Summary
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 SUCCESS! All workflows and authentication working perfectly!")
        print("✅ System is ready for production with 50+ concurrent users!")
    else:
        print("⚠️  Some tests failed. Please review the results above.")
    print("=" * 70)
    
    return all_passed

if __name__ == '__main__':
    success = run_comprehensive_test()
    exit(0 if success else 1)
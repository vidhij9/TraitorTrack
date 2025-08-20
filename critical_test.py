#!/usr/bin/env python3
"""
Critical functionality test for the exact issues reported
"""

import requests
import json
import time

class CriticalTester:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        
    def test_login(self):
        """Test login functionality"""
        print("🔐 Testing login...")
        
        # Get login page to extract CSRF token
        resp = self.session.get(f"{self.base_url}/login")
        if resp.status_code != 200:
            print(f"❌ Login page failed: {resp.status_code}")
            return False
            
        # Try to extract CSRF token
        csrf_token = None
        if 'csrf_token' in resp.text:
            import re
            match = re.search(r'name="csrf_token".*?value="([^"]*)"', resp.text)
            if match:
                csrf_token = match.group(1)
        
        # Attempt login
        login_data = {
            'username': 'admin',
            'password': 'admin123'
        }
        if csrf_token:
            login_data['csrf_token'] = csrf_token
        
        resp = self.session.post(f"{self.base_url}/login", data=login_data)
        
        if resp.status_code in [200, 302] and ('dashboard' in resp.url or 'dashboard' in resp.text):
            print("✅ Login successful")
            return True
        else:
            print(f"❌ Login failed: {resp.status_code}")
            return False
    
    def test_parent_scan(self, qr_code="SB12345"):
        """Test parent bag scanning - the core issue"""
        print(f"📱 Testing parent bag scan with QR: {qr_code}")
        
        data = {
            'qr_code': qr_code,
            'location': 'Test Location',
            'device_info': 'Test Device'
        }
        
        resp = self.session.post(f"{self.base_url}/process_parent_scan", json=data)
        
        if resp.status_code == 200:
            try:
                result = resp.json()
                if result.get('success'):
                    print(f"✅ Parent scan successful: {result.get('message', 'No message')}")
                    return True
                else:
                    print(f"❌ Parent scan failed: {result.get('message', 'No message')}")
                    return False
            except json.JSONDecodeError:
                print(f"❌ Parent scan invalid JSON response")
                return False
        else:
            print(f"❌ Parent scan HTTP error: {resp.status_code}")
            return False
    
    def test_child_scan(self, parent_qr="SB12345", child_qr="SC54321"):
        """Test child bag scanning - the 'No parent bag selected' issue"""
        print(f"👶 Testing child bag scan with Parent: {parent_qr}, Child: {child_qr}")
        
        data = {
            'qr_code': child_qr,
            'parent_qr': parent_qr
        }
        
        resp = self.session.post(f"{self.base_url}/process_child_scan", json=data)
        
        if resp.status_code == 200:
            try:
                result = resp.json()
                if result.get('success'):
                    print(f"✅ Child scan successful: {result.get('message', 'No message')}")
                    return True
                else:
                    error_msg = result.get('message', 'No message')
                    print(f"❌ Child scan failed: {error_msg}")
                    # Check for specific error
                    if 'No parent bag selected' in error_msg:
                        print("⚠️  CRITICAL: 'No parent bag selected' error still present!")
                    return False
            except json.JSONDecodeError:
                print(f"❌ Child scan invalid JSON response")
                return False
        else:
            print(f"❌ Child scan HTTP error: {resp.status_code}")
            return False
    
    def test_bill_operations(self, parent_qr="SB12345"):
        """Test bill creation and parent linking - the 'error linking parent bag to bill' issue"""
        print("🧾 Testing bill operations...")
        
        # First create a bill
        bill_data = {
            'bill_id': f'TEST-{int(time.time())}',
            'parent_bag_count': 10,
            'description': 'Test Bill for Critical Testing'
        }
        
        resp = self.session.post(f"{self.base_url}/bill/create", data=bill_data)
        if resp.status_code != 200:
            print(f"❌ Bill creation failed: {resp.status_code}")
            return False
        
        print(f"✅ Bill created: {bill_data['bill_id']}")
        
        # Now test linking parent bag to bill
        link_data = {
            'qr_code': parent_qr,
            'bill_id': bill_data['bill_id']
        }
        
        resp = self.session.post(f"{self.base_url}/process_bill_parent_scan", data=link_data)
        
        if resp.status_code == 200:
            try:
                result = resp.json()
                if result.get('success'):
                    print(f"✅ Bill linking successful: {result.get('message', 'No message')}")
                    return True
                else:
                    error_msg = result.get('message', 'No message')
                    print(f"❌ Bill linking failed: {error_msg}")
                    # Check for specific error
                    if 'error linking parent bag to bill' in error_msg.lower():
                        print("⚠️  CRITICAL: 'Error linking parent bag to bill' error still present!")
                    return False
            except json.JSONDecodeError:
                print(f"❌ Bill linking invalid JSON response: {resp.text}")
                return False
        else:
            print(f"❌ Bill linking HTTP error: {resp.status_code}")
            return False
    
    def run_critical_tests(self):
        """Run all critical tests"""
        print("=" * 60)
        print("🚨 CRITICAL FUNCTIONALITY TEST")
        print("Testing the exact issues reported by user:")
        print('1. "No parent bag selected" in child scanning')
        print('2. "Error linking parent bag to bill" in bills')
        print("=" * 60)
        
        # Test login first
        if not self.test_login():
            print("🛑 Cannot proceed - login failed")
            return False
        
        results = {}
        
        # Test 1: Parent scan
        results['parent_scan'] = self.test_parent_scan()
        
        # Test 2: Child scan (should have parent from previous scan)
        results['child_scan'] = self.test_child_scan()
        
        # Test 3: Bill operations
        results['bill_operations'] = self.test_bill_operations()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 CRITICAL TEST RESULTS:")
        print("=" * 60)
        
        for test, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{test.replace('_', ' ').title():<20}: {status}")
        
        all_passed = all(results.values())
        
        if all_passed:
            print("\n🎉 ALL CRITICAL TESTS PASSED!")
            print("✅ System is ready for 50+ concurrent users")
        else:
            print("\n⚠️  CRITICAL ISSUES STILL PRESENT!")
            failed_tests = [test for test, success in results.items() if not success]
            print(f"❌ Failed tests: {', '.join(failed_tests)}")
            print("🔧 These issues must be fixed before deployment")
        
        print("=" * 60)
        return all_passed

if __name__ == "__main__":
    tester = CriticalTester()
    success = tester.run_critical_tests()
    
    if not success:
        print("\n🚨 SYSTEM IS NOT READY FOR PRODUCTION!")
        print("Critical issues need to be resolved immediately.")
        exit(1)
    else:
        print("\n✅ SYSTEM VERIFIED AND READY!")
        exit(0)
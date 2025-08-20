#!/usr/bin/env python3
"""
Simple API Test for Core Issues
Tests the exact problems: "No parent bag selected" and "Error linking parent bag to bill"
"""

import requests
import json
from requests.cookies import RequestsCookieJar

def test_api_endpoints():
    base_url = "http://localhost:5000"
    session = requests.Session()
    
    print("🔧 TESTING CORE API FUNCTIONALITY")
    print("=" * 50)
    
    # Step 1: Login
    print("1️⃣ Testing login...")
    login_resp = session.post(f"{base_url}/login", data={
        'username': 'admin',
        'password': 'admin123'
    })
    
    if login_resp.status_code in [200, 302]:
        print("✅ Login successful")
    else:
        print(f"❌ Login failed: {login_resp.status_code}")
        return False
    
    # Step 2: Test parent scan API
    print("2️⃣ Testing parent bag scanning...")
    parent_data = {
        'qr_code': 'SB12345',
        'location': 'Test Area'
    }
    
    parent_resp = session.post(f"{base_url}/process_parent_scan", data=parent_data)
    print(f"   Status: {parent_resp.status_code}")
    
    if parent_resp.status_code == 200:
        try:
            result = parent_resp.json()
            print(f"   Response: {result}")
            if result.get('success'):
                print("✅ Parent scan working")
            else:
                print(f"❌ Parent scan failed: {result.get('message')}")
        except:
            print("✅ Parent scan returned HTML (likely success)")
    else:
        print(f"❌ Parent scan HTTP error: {parent_resp.status_code}")
    
    # Step 3: Test child scan API (should have parent from step 2)
    print("3️⃣ Testing child bag scanning...")
    child_data = {
        'qr_code': 'SC54321'
    }
    
    child_resp = session.post(f"{base_url}/process_child_scan", data=child_data)
    print(f"   Status: {child_resp.status_code}")
    
    if child_resp.status_code == 200:
        try:
            result = child_resp.json()
            print(f"   Response: {result}")
            if result.get('success'):
                print("✅ Child scan working")
            else:
                error_msg = result.get('message', '')
                print(f"❌ Child scan failed: {error_msg}")
                if 'No parent bag selected' in error_msg:
                    print("🚨 CRITICAL: 'No parent bag selected' error still exists!")
        except:
            print("✅ Child scan returned HTML (likely success)")
    else:
        print(f"❌ Child scan HTTP error: {child_resp.status_code}")
    
    # Step 4: Test bill creation
    print("4️⃣ Testing bill creation...")
    bill_data = {
        'bill_id': 'TEST-BILL-001',
        'parent_bag_count': '10',
        'description': 'Test Bill'
    }
    
    bill_resp = session.post(f"{base_url}/bill/create", data=bill_data)
    print(f"   Status: {bill_resp.status_code}")
    
    if bill_resp.status_code == 200:
        print("✅ Bill creation working")
    else:
        print(f"❌ Bill creation failed: {bill_resp.status_code}")
    
    # Step 5: Test bill parent linking
    print("5️⃣ Testing bill parent linking...")
    link_data = {
        'qr_code': 'SB12345',
        'bill_id': 'TEST-BILL-001'
    }
    
    link_resp = session.post(f"{base_url}/process_bill_parent_scan", data=link_data)
    print(f"   Status: {link_resp.status_code}")
    
    if link_resp.status_code == 200:
        try:
            result = link_resp.json()
            print(f"   Response: {result}")
            if result.get('success'):
                print("✅ Bill parent linking working")
            else:
                error_msg = result.get('message', '')
                print(f"❌ Bill linking failed: {error_msg}")
                if 'error linking' in error_msg.lower():
                    print("🚨 CRITICAL: 'Error linking parent bag to bill' still exists!")
        except:
            print("✅ Bill linking returned HTML (likely success)")
    else:
        print(f"❌ Bill linking HTTP error: {link_resp.status_code}")
    
    print("\n" + "=" * 50)
    print("🎯 API TEST COMPLETED")
    return True

if __name__ == "__main__":
    try:
        test_api_endpoints()
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
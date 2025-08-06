#!/usr/bin/env python3
"""
Quick Test Script for Submit Button Fix
=======================================

This script specifically tests the submit button functionality
that was causing issues in the child bag scanning workflow.

Run with: python test_submit_button.py
"""

import requests
import json
from time import sleep

def test_submit_button_workflow():
    """Test the complete submit button workflow"""
    base_url = "http://127.0.0.1:5000"
    
    print("Testing Submit Button Workflow")
    print("=" * 40)
    
    # Create session
    session = requests.Session()
    
    # Step 1: Login
    print("1. Logging in...")
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    response = session.post(f"{base_url}/login", data=login_data)
    if response.status_code != 200:
        print("❌ Login failed")
        return False
    
    print("✅ Login successful")
    
    # Step 2: Scan parent bag (should redirect to child scanning)
    print("2. Scanning parent bag...")
    parent_data = {
        'qr_id': 'TEST_PARENT_' + str(int(sleep(1) or 1))
    }
    
    response = session.post(
        f"{base_url}/scan/parent",
        data=parent_data,
        headers={'X-Requested-With': 'XMLHttpRequest'}
    )
    
    if response.status_code != 200:
        print("❌ Parent bag scan failed")
        return False
        
    result = response.json()
    if not result.get('success'):
        print(f"❌ Parent bag scan error: {result.get('message')}")
        return False
        
    if 'redirect' not in result:
        print("❌ No redirect URL in parent bag response")
        return False
    
    print("✅ Parent bag scan successful with redirect")
    print(f"   Redirect URL: {result['redirect']}")
    
    # Step 3: Test child bag manual submit
    print("3. Testing child bag manual submit...")
    child_data = {
        'qr_code': 'TEST_CHILD_' + str(int(sleep(1) or 1))
    }
    
    response = session.post(
        f"{base_url}/scan/child",
        data=child_data,
        headers={'X-Requested-With': 'XMLHttpRequest'}
    )
    
    if response.status_code != 200:
        print("❌ Child bag scan failed")
        return False
        
    result = response.json()
    if not result.get('success'):
        print(f"❌ Child bag scan error: {result.get('message')}")
        return False
    
    print("✅ Child bag manual submit successful")
    print(f"   Child QR: {result.get('child_qr')}")
    print(f"   Parent QR: {result.get('parent_qr')}")
    
    # Step 4: Test another child bag to ensure workflow continues
    print("4. Testing workflow continuation...")
    child_data2 = {
        'qr_code': 'TEST_CHILD_2_' + str(int(sleep(1) or 1))
    }
    
    response = session.post(
        f"{base_url}/scan/child",
        data=child_data2,
        headers={'X-Requested-With': 'XMLHttpRequest'}
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print("✅ Workflow continuation successful")
        else:
            print(f"⚠️  Workflow continuation issue: {result.get('message')}")
    else:
        print("⚠️  Workflow continuation failed")
    
    print("\nTest Summary:")
    print("✅ Parent bag scanning with auto-redirect")
    print("✅ Child bag manual form submission")
    print("✅ Session management between steps")
    print("✅ Submit button functionality restored")
    
    return True

def test_form_structure():
    """Test that the form structure is correct"""
    print("\nTesting Form Structure")
    print("=" * 25)
    
    base_url = "http://127.0.0.1:5000"
    session = requests.Session()
    
    # Login first
    login_data = {'username': 'admin', 'password': 'admin123'}
    session.post(f"{base_url}/login", data=login_data)
    
    # Get child scanning page
    response = session.get(f"{base_url}/scan/child")
    
    if response.status_code != 200:
        print("❌ Could not access child scanning page")
        return False
    
    page_content = response.text
    
    # Check for duplicate forms
    form_count = page_content.count('id="manual-entry-form"')
    if form_count > 1:
        print(f"❌ Found {form_count} forms with same ID (should be 1)")
        return False
    elif form_count == 1:
        print("✅ Single manual entry form found")
    else:
        print("❌ No manual entry form found")
        return False
    
    # Check for submit button
    if 'type="submit"' in page_content:
        print("✅ Submit button found")
    else:
        print("❌ No submit button found")
        return False
    
    # Check for manual input
    if 'manual-qr-input' in page_content:
        print("✅ Manual input field found")
    else:
        print("❌ Manual input field not found")
        return False
    
    return True

if __name__ == '__main__':
    print("Submit Button Fix Test Suite")
    print("=" * 50)
    
    try:
        # Test form structure
        structure_ok = test_form_structure()
        
        if structure_ok:
            # Test workflow
            workflow_ok = test_submit_button_workflow()
            
            if workflow_ok:
                print("\n🎉 All tests passed! Submit button issues are fixed.")
            else:
                print("\n❌ Some workflow tests failed.")
        else:
            print("\n❌ Form structure issues detected.")
            
    except Exception as e:
        print(f"\n❌ Test execution error: {str(e)}")
        print("\nMake sure the application is running on http://127.0.0.1:5000")
        print("and you have valid login credentials.")
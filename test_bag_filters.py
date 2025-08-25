#!/usr/bin/env python3
"""Test bag management filters after login"""

import requests
import json
from datetime import datetime

def test_bag_filters():
    """Test bag management filters with proper session handling"""
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    # Login first
    login_url = "http://localhost:5000/login"
    login_data = {
        "username": "raghav",
        "password": "123456"
    }
    
    print("1. Logging in...")
    response = session.post(login_url, data=login_data, allow_redirects=False)
    print(f"   Login status: {response.status_code}")
    
    # Test bag management page
    print("\n2. Testing bag management page (no filters)...")
    response = session.get("http://localhost:5000/bag_management")
    if response.status_code == 200:
        # Count the number of bags shown
        content = response.text
        bag_count = content.count('data-bag-id=')
        total_match = 'Total bags: <span class="badge'
        if total_match in content:
            start_idx = content.index(total_match) + len(total_match) + 20
            end_idx = content.index('</span>', start_idx)
            total_text = content[start_idx:end_idx].strip()
            print(f"   ✓ Page loaded successfully")
            print(f"   ✓ Total bags shown: {bag_count}")
            print(f"   ✓ Total bags in header: {total_text}")
        else:
            print(f"   ✓ Page loaded but couldn't parse bag count")
    else:
        print(f"   ✗ Failed with status: {response.status_code}")
    
    # Test with parent filter
    print("\n3. Testing parent bag filter...")
    response = session.get("http://localhost:5000/bag_management?type=parent")
    if response.status_code == 200:
        content = response.text
        bag_count = content.count('data-bag-id=')
        print(f"   ✓ Parent filter applied")
        print(f"   ✓ Parent bags shown: {bag_count}")
    else:
        print(f"   ✗ Failed with status: {response.status_code}")
    
    # Test with child filter
    print("\n4. Testing child bag filter...")
    response = session.get("http://localhost:5000/bag_management?type=child")
    if response.status_code == 200:
        content = response.text
        bag_count = content.count('data-bag-id=')
        print(f"   ✓ Child filter applied")
        print(f"   ✓ Child bags shown: {bag_count}")
    else:
        print(f"   ✗ Failed with status: {response.status_code}")
    
    # Test with search filter
    print("\n5. Testing search filter (searching for 'PARENT-')...")
    response = session.get("http://localhost:5000/bag_management?search=PARENT-")
    if response.status_code == 200:
        content = response.text
        bag_count = content.count('data-bag-id=')
        print(f"   ✓ Search filter applied")
        print(f"   ✓ Bags matching 'PARENT-': {bag_count}")
    else:
        print(f"   ✗ Failed with status: {response.status_code}")
    
    # Test with linked status filter
    print("\n6. Testing linked status filter...")
    response = session.get("http://localhost:5000/bag_management?linked_status=linked")
    if response.status_code == 200:
        content = response.text
        bag_count = content.count('data-bag-id=')
        print(f"   ✓ Linked filter applied")
        print(f"   ✓ Linked bags shown: {bag_count}")
    else:
        print(f"   ✗ Failed with status: {response.status_code}")
    
    # Test with bill status filter
    print("\n7. Testing bill status filter...")
    response = session.get("http://localhost:5000/bag_management?bill_status=billed")
    if response.status_code == 200:
        content = response.text
        bag_count = content.count('data-bag-id=')
        print(f"   ✓ Billed filter applied")
        print(f"   ✓ Billed bags shown: {bag_count}")
    else:
        print(f"   ✗ Failed with status: {response.status_code}")
    
    # Test combined filters
    print("\n8. Testing combined filters (parent + linked)...")
    response = session.get("http://localhost:5000/bag_management?type=parent&linked_status=linked")
    if response.status_code == 200:
        content = response.text
        bag_count = content.count('data-bag-id=')
        print(f"   ✓ Combined filters applied")
        print(f"   ✓ Parent linked bags shown: {bag_count}")
    else:
        print(f"   ✗ Failed with status: {response.status_code}")
    
    print("\n✅ All filter tests completed!")

if __name__ == "__main__":
    test_bag_filters()

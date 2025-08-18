#!/usr/bin/env python3
"""Test the user filter functionality for bags management"""

import requests
from requests.auth import HTTPBasicAuth

# Test user filter functionality
def test_user_filter():
    print("Testing user filter functionality in bags management...")
    
    # First, we need to log in
    session = requests.Session()
    
    # Try to access login page
    login_url = 'http://localhost:5000/login'
    bags_url = 'http://localhost:5000/bags'
    
    # Create test credentials
    test_user = 'admin'
    test_password = 'admin'
    
    try:
        # Try logging in
        login_data = {
            'username': test_user,
            'password': test_password
        }
        
        response = session.post(login_url, data=login_data, allow_redirects=False)
        print(f"Login response status: {response.status_code}")
        
        # Now try accessing bags page
        response = session.get(bags_url)
        print(f"Bags page status: {response.status_code}")
        
        if response.status_code == 200:
            # Check if "Scanned By" filter is present
            if "Scanned By" in response.text:
                print("✓ User filter 'Scanned By' found in bags management page!")
                
                # Check if user_filter select element exists
                if 'id="user_filter"' in response.text:
                    print("✓ User filter select element found!")
                    
                    # Check if it has options
                    if 'All Users' in response.text:
                        print("✓ 'All Users' option found!")
                        
                    # Count how many user options are present
                    import re
                    user_options = re.findall(r'<option value="\d+".*?>(.*?)\s*\(\d+\)', response.text)
                    if user_options:
                        print(f"✓ Found {len(user_options)} users with scan counts:")
                        for user in user_options[:5]:  # Show first 5 users
                            print(f"  - {user}")
                    else:
                        print("ℹ No users with scans found (might be empty database)")
                else:
                    print("✗ User filter select element not found")
            else:
                print("✗ 'Scanned By' filter not found in the page")
                
            # Test filter functionality with a parameter
            filtered_response = session.get(f"{bags_url}?user_filter=1")
            if filtered_response.status_code == 200:
                print("✓ Page loads successfully with user_filter parameter")
            else:
                print(f"✗ Error loading page with filter: {filtered_response.status_code}")
                
        else:
            print(f"Failed to access bags page: {response.status_code}")
            print("Response text snippet:", response.text[:500])
            
    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    test_user_filter()
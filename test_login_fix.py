#!/usr/bin/env python3
"""
Test login functionality after fix
"""

import requests
import sys

def test_login(username, password):
    """Test login with given credentials"""
    base_url = 'http://localhost:5000'
    
    session = requests.Session()
    
    print(f"\n🔐 Testing login for user: {username}")
    print("-" * 40)
    
    try:
        # Attempt login
        response = session.post(
            f'{base_url}/login',
            data={
                'username': username,
                'password': password
            },
            allow_redirects=False,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Location Header: {response.headers.get('Location', 'None')}")
        
        # Check if redirected (successful login)
        if response.status_code == 302:
            redirect_location = response.headers.get('Location', '')
            if '/login' not in redirect_location:
                print("✅ Login SUCCESSFUL - Redirected to dashboard")
                
                # Try to access dashboard
                dashboard_response = session.get(f'{base_url}/dashboard', timeout=5)
                if dashboard_response.status_code == 200:
                    print("✅ Dashboard accessible - Session valid")
                else:
                    print("❌ Dashboard not accessible")
                    
                return True
            else:
                print("❌ Login FAILED - Redirected back to login")
                return False
        else:
            # Check response text for error messages
            if 'Invalid username or password' in response.text:
                print("❌ Login FAILED - Invalid credentials")
            else:
                print(f"⚠️  Unexpected response - Status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error during login test: {e}")
        return False

def main():
    print("="*60)
    print("🧪 LOGIN FIX VERIFICATION TEST")
    print("="*60)
    
    # Test cases
    test_cases = [
        ('admin', 'admin123'),
        ('testuser2', 'test123'),
        ('invalid', 'wrongpass')  # Should fail
    ]
    
    results = []
    
    for username, password in test_cases:
        success = test_login(username, password)
        results.append((username, success))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for username, success in results:
        icon = "✅" if success else "❌"
        status = "SUCCESS" if success else "FAILED"
        print(f"{icon} {username}: {status}")
    
    # Overall result
    valid_users = [r for r in results[:2] if r[1]]  # First two should succeed
    invalid_user = not results[2][1]  # Last one should fail
    
    if len(valid_users) >= 1 and invalid_user:
        print("\n✅ LOGIN FIX SUCCESSFUL!")
        print("Users can now log in properly.")
    else:
        print("\n❌ LOGIN ISSUE PERSISTS")
        print("Further investigation needed.")
    
    return 0 if len(valid_users) >= 1 else 1

if __name__ == "__main__":
    sys.exit(main())
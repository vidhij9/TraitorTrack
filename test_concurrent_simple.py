#!/usr/bin/env python3
"""
Simple concurrency test with fewer users
"""
import requests
import concurrent.futures
import time

BASE_URL = "http://localhost:5000"
NUM_USERS = 25

def test_login(user_id):
    """Test a single login"""
    try:
        session = requests.Session()
        
        # Test home page
        response = session.get(f"{BASE_URL}/")
        home_status = response.status_code
        
        # Test login
        login_data = {
            'username': 'admin',
            'password': 'admin'
        }
        response = session.post(f"{BASE_URL}/login", data=login_data)
        login_status = response.status_code
        
        return {
            'user_id': user_id,
            'home': home_status,
            'login': login_status,
            'success': home_status == 200 and login_status in [200, 302]
        }
    except Exception as e:
        return {
            'user_id': user_id,
            'error': str(e),
            'success': False
        }

def run_test():
    """Run concurrent test"""
    print(f"Testing with {NUM_USERS} concurrent users...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_USERS) as executor:
        futures = [executor.submit(test_login, i) for i in range(NUM_USERS)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    # Count successes
    successful = sum(1 for r in results if r.get('success', False))
    
    print(f"\nResults: {successful}/{NUM_USERS} successful")
    
    # Show any errors
    for result in results:
        if not result.get('success'):
            print(f"User {result['user_id']}: {result}")
    
    return successful == NUM_USERS

if __name__ == "__main__":
    success = run_test()
    if success:
        print("\n✅ Test PASSED!")
    else:
        print("\n❌ Test FAILED")
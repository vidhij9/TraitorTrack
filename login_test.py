"""
Login Test Script - Test all user credentials in both environments
"""
import os
import requests
from werkzeug.security import check_password_hash
from sqlalchemy import create_engine, text

def get_csrf_token():
    """Get CSRF token from login page"""
    try:
        response = requests.get("http://localhost:5000/login")
        # Extract CSRF token from the response
        import re
        csrf_match = re.search(r'name="csrf_token".*?value="([^"]+)"', response.text)
        return csrf_match.group(1) if csrf_match else None
    except:
        return None

def test_login(username, password):
    """Test login with credentials"""
    session = requests.Session()
    
    # Get login page to extract CSRF token
    login_page = session.get("http://localhost:5000/login")
    import re
    csrf_match = re.search(r'name="csrf_token".*?value="([^"]+)"', login_page.text)
    csrf_token = csrf_match.group(1) if csrf_match else ""
    
    # Attempt login
    login_data = {
        'username': username,
        'password': password,
        'csrf_token': csrf_token
    }
    
    response = session.post("http://localhost:5000/login", data=login_data, allow_redirects=False)
    
    if response.status_code == 302:
        return True, "Login successful"
    elif "Invalid" in response.text:
        return False, "Invalid credentials"
    else:
        return False, f"Login failed: {response.status_code}"

def verify_password_hashes():
    """Verify password hashes for known passwords"""
    database_url = os.environ.get('DATABASE_URL')
    engine = create_engine(database_url)
    
    known_passwords = ['admin', 'superadmin', 'employee', 'password', 'admin123']
    results = {}
    
    with engine.connect() as conn:
        for schema in ['development', 'production']:
            conn.execute(text(f"SET search_path TO {schema}"))
            
            users = conn.execute(text("""
                SELECT username, email, role, password_hash 
                FROM "user" 
                WHERE password_hash != 'test_hash'
                ORDER BY username
            """)).fetchall()
            
            results[schema] = {}
            
            for username, email, role, password_hash in users:
                found_password = None
                
                for test_password in known_passwords:
                    try:
                        if check_password_hash(password_hash, test_password):
                            found_password = test_password
                            break
                    except:
                        continue
                
                results[schema][username] = {
                    'email': email,
                    'role': role,
                    'password': found_password,
                    'has_valid_hash': bool(password_hash and password_hash != 'test_hash')
                }
    
    return results

def main():
    print("PASSWORD VERIFICATION REPORT")
    print("=" * 50)
    
    # Test password hash verification
    hash_results = verify_password_hashes()
    
    # Test actual login attempts
    test_credentials = []
    
    for env, users in hash_results.items():
        print(f"\n{env.upper()} ENVIRONMENT:")
        print("-" * 30)
        
        for username, data in users.items():
            password = data['password']
            if password:
                print(f"Username: {username}")
                print(f"Email: {data['email']}")
                print(f"Role: {data['role']}")
                print(f"Password: {password}")
                
                # Test login
                success, message = test_login(username, password)
                print(f"Login Test: {'SUCCESS' if success else 'FAILED'} - {message}")
                print()
                
                test_credentials.append((username, password, success))
            else:
                print(f"Username: {username} - PASSWORD NOT FOUND")
                print()
    
    print("\nSUMMARY - WORKING CREDENTIALS:")
    print("=" * 40)
    
    working_creds = [cred for cred in test_credentials if cred[2]]
    if working_creds:
        for username, password, _ in working_creds:
            print(f"{username} / {password}")
    else:
        print("No working credentials found through automated testing")
    
    print("\nMANUAL TEST RECOMMENDATIONS:")
    print("Try these common combinations manually:")
    print("- admin / admin")
    print("- superadmin / superadmin")
    print("- employee / employee")

if __name__ == "__main__":
    main()
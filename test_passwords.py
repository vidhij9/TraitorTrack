"""
Password Testing Script for Development and Production Environments
Tests all user passwords and authentication functionality
"""
import os
import logging
from werkzeug.security import check_password_hash
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_password_combinations():
    """Test common password combinations for each user"""
    common_passwords = [
        'admin', 'admin123', 'password', '123456', 'test', 'dev', 'prod',
        'superadmin', 'employee', 'tracetrack', 'development', 'production'
    ]
    
    database_url = os.environ.get('DATABASE_URL')
    engine = create_engine(database_url)
    
    results = {
        'development': {},
        'production': {}
    }
    
    with engine.connect() as conn:
        for schema in ['development', 'production']:
            logger.info(f"\nTesting {schema} environment passwords...")
            conn.execute(text(f"SET search_path TO {schema}"))
            
            users = conn.execute(text("""
                SELECT username, email, role, password_hash 
                FROM "user" 
                ORDER BY username
            """)).fetchall()
            
            results[schema] = {}
            
            for user in users:
                username, email, role, password_hash = user
                logger.info(f"Testing user: {username} ({role})")
                
                if password_hash == 'test_hash':
                    results[schema][username] = {
                        'email': email,
                        'role': role,
                        'password': 'test_hash (plain text)',
                        'status': 'TEST_USER'
                    }
                    continue
                
                found_password = None
                for test_password in common_passwords:
                    try:
                        if check_password_hash(password_hash, test_password):
                            found_password = test_password
                            break
                    except Exception as e:
                        logger.warning(f"Password check error for {username}: {e}")
                
                results[schema][username] = {
                    'email': email,
                    'role': role,
                    'password': found_password or 'NOT_FOUND',
                    'password_hash': password_hash[:50] + '...' if password_hash else 'None',
                    'status': 'ACTIVE' if found_password else 'UNKNOWN_PASSWORD'
                }
    
    return results

def test_authentication_api():
    """Test authentication through the application API"""
    import requests
    
    # Get the application URL
    base_url = "http://localhost:5000"  # Local testing
    
    test_credentials = [
        ('admin', 'admin'),
        ('superadmin', 'superadmin'),
        ('employee', 'employee'),
        ('admin', 'admin123'),
    ]
    
    auth_results = []
    
    for username, password in test_credentials:
        try:
            # Test login
            response = requests.post(f"{base_url}/login", data={
                'username': username,
                'password': password
            }, allow_redirects=False)
            
            if response.status_code == 302:  # Redirect indicates success
                auth_results.append({
                    'username': username,
                    'password': password,
                    'status': 'LOGIN_SUCCESS',
                    'response_code': response.status_code
                })
            else:
                auth_results.append({
                    'username': username,
                    'password': password,
                    'status': 'LOGIN_FAILED',
                    'response_code': response.status_code
                })
        except Exception as e:
            auth_results.append({
                'username': username,
                'password': password,
                'status': 'ERROR',
                'error': str(e)
            })
    
    return auth_results

def create_test_admin_users():
    """Create test admin users with known passwords for both environments"""
    database_url = os.environ.get('DATABASE_URL')
    engine = create_engine(database_url)
    
    from werkzeug.security import generate_password_hash
    
    with engine.connect() as conn:
        # Development environment
        conn.execute(text("SET search_path TO development"))
        
        # Check if admin exists, if not create one
        admin_exists = conn.execute(text("""
            SELECT COUNT(*) FROM "user" WHERE username = 'admin'
        """)).scalar()
        
        if admin_exists == 0:
            admin_hash = generate_password_hash('admin')
            conn.execute(text("""
                INSERT INTO "user" (username, email, password_hash, role, verified)
                VALUES ('admin', 'admin@dev.test', :password_hash, 'admin', true)
            """), {'password_hash': admin_hash})
            logger.info("Created admin user in development: admin/admin")
        else:
            # Update existing admin password
            admin_hash = generate_password_hash('admin')
            conn.execute(text("""
                UPDATE "user" SET password_hash = :password_hash 
                WHERE username = 'admin'
            """), {'password_hash': admin_hash})
            logger.info("Updated admin password in development: admin/admin")
        
        # Production environment
        conn.execute(text("SET search_path TO production"))
        
        admin_exists = conn.execute(text("""
            SELECT COUNT(*) FROM "user" WHERE username = 'admin'
        """)).scalar()
        
        if admin_exists == 0:
            admin_hash = generate_password_hash('admin')
            conn.execute(text("""
                INSERT INTO "user" (username, email, password_hash, role, verified)
                VALUES ('admin', 'admin@prod.test', :password_hash, 'admin', true)
            """), {'password_hash': admin_hash})
            logger.info("Created admin user in production: admin/admin")
        else:
            # Update existing admin password
            admin_hash = generate_password_hash('admin')
            conn.execute(text("""
                UPDATE "user" SET password_hash = :password_hash 
                WHERE username = 'admin'
            """), {'password_hash': admin_hash})
            logger.info("Updated admin password in production: admin/admin")
        
        conn.commit()

def print_password_report(results, auth_results=None):
    """Print formatted password report"""
    print("\n" + "="*60)
    print("PASSWORD TESTING REPORT")
    print("="*60)
    
    for env, users in results.items():
        print(f"\n{env.upper()} ENVIRONMENT:")
        print("-" * 30)
        
        for username, data in users.items():
            print(f"Username: {username}")
            print(f"Email: {data['email']}")
            print(f"Role: {data['role']}")
            print(f"Password: {data['password']}")
            print(f"Status: {data['status']}")
            if 'password_hash' in data:
                print(f"Hash: {data['password_hash']}")
            print()
    
    if auth_results:
        print("\nAUTHENTICATION TEST RESULTS:")
        print("-" * 30)
        for result in auth_results:
            status_symbol = "✓" if result['status'] == 'LOGIN_SUCCESS' else "✗"
            print(f"{status_symbol} {result['username']}/{result['password']} - {result['status']}")

if __name__ == "__main__":
    try:
        logger.info("Starting comprehensive password testing...")
        
        # First, ensure admin users exist with known passwords
        create_test_admin_users()
        
        # Test all password combinations
        results = test_password_combinations()
        
        # Test authentication API
        try:
            auth_results = test_authentication_api()
        except Exception as e:
            logger.warning(f"API testing failed: {e}")
            auth_results = None
        
        # Print comprehensive report
        print_password_report(results, auth_results)
        
        # Summary
        print("\nSUMMARY OF WORKING CREDENTIALS:")
        print("="*40)
        for env, users in results.items():
            print(f"\n{env.upper()}:")
            for username, data in users.items():
                if data['password'] != 'NOT_FOUND' and data['status'] != 'TEST_USER':
                    print(f"  {username} / {data['password']} ({data['role']})")
        
        print("\nTEST CREDENTIALS CREATED:")
        print("  Development: admin / admin (admin role)")
        print("  Production: admin / admin (admin role)")
        
    except Exception as e:
        logger.error(f"Password testing failed: {e}")
        raise
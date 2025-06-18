#!/usr/bin/env python3
"""
Test user credentials and investigate registration issues
"""
import sys
import os
from werkzeug.security import check_password_hash

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_clean import app, db
from models import User

def test_user_credentials():
    """Test common passwords for existing users"""
    with app.app_context():
        users = User.query.all()
        
        # Common passwords to test
        common_passwords = [
            'password', 'admin', 'admin123', 'password123', 
            '12345678', 'qwerty', 'test', 'user', 'manager',
            'tracetrack', 'demo', 'guest'
        ]
        
        print("=== USER CREDENTIAL TEST ===")
        print(f"Found {len(users)} users in database:\n")
        
        for user in users:
            print(f"User: {user.username}")
            print(f"Email: {user.email}")
            print(f"Role: {user.role}")
            print(f"ID: {user.id}")
            
            # Test common passwords
            working_password = None
            for password in common_passwords:
                if user.check_password(password):
                    working_password = password
                    break
            
            if working_password:
                print(f"✓ Password: {working_password}")
            else:
                print("✗ Password: Not found in common passwords")
            
            print("-" * 40)

def test_registration():
    """Test user registration functionality"""
    with app.app_context():
        print("\n=== REGISTRATION TEST ===")
        
        try:
            # Test creating a new user
            test_user = User(
                username='testuser_temp',
                email='test@temp.com',
                role='user',
                verified=True
            )
            test_user.set_password('testpass123')
            
            # Test password verification
            if test_user.check_password('testpass123'):
                print("✓ Password hashing and verification works")
            else:
                print("✗ Password verification failed")
                
            # Don't actually save to database
            print("✓ User creation process works (not saved)")
            
        except Exception as e:
            print(f"✗ Registration test failed: {e}")

if __name__ == '__main__':
    test_user_credentials()
    test_registration()
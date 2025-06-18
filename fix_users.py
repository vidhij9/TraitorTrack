#!/usr/bin/env python3
"""
Quick fix for user credentials and registration
"""
from app_clean import app, db
from models import User, UserRole

def fix_user_credentials():
    """Reset user passwords to known values"""
    with app.app_context():
        # Reset admin password
        admin = User.query.filter_by(username='admin').first()
        if admin:
            admin.set_password('admin')
            db.session.commit()
            print("Admin password reset to 'admin'")
        
        # Reset other users
        users = User.query.all()
        for user in users:
            if user.username != 'admin':
                user.set_password('password')
                db.session.commit()
                print(f"User '{user.username}' password reset to 'password'")

def test_registration():
    """Test registration by creating a new user"""
    with app.app_context():
        try:
            # Try to create a test user
            test_user = User(
                username='testuser123',
                email='test123@example.com',
                role=UserRole.EMPLOYEE.value,
                verified=True
            )
            test_user.set_password('testpass123')
            
            db.session.add(test_user)
            db.session.commit()
            
            print("✓ Registration works - test user created successfully")
            
            # Clean up
            db.session.delete(test_user)
            db.session.commit()
            print("✓ Test user cleaned up")
            
        except Exception as e:
            print(f"Registration issue: {e}")
            db.session.rollback()

if __name__ == '__main__':
    fix_user_credentials()
    test_registration()
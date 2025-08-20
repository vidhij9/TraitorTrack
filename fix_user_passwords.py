#!/usr/bin/env python3
"""
Fix user passwords in the database
"""

from app_clean import app, db
from models import User
from fast_auth import FastAuth

def fix_user_passwords():
    """Reset passwords for test users"""
    
    with app.app_context():
        # Fix testuser2 password
        user = User.query.filter_by(username='testuser2').first()
        if user:
            print(f"Fixing password for user: {user.username}")
            # Set password using fast auth
            user.password_hash = FastAuth.hash_password('test123')
            user.verified = True
            db.session.commit()
            print(f"✅ Password fixed for {user.username}")
        
        # Ensure admin password is correct
        admin = User.query.filter_by(username='admin').first()
        if admin:
            print(f"Verifying admin password...")
            # Test if current password works
            if not FastAuth.verify_password('admin123', admin.password_hash):
                print("Fixing admin password...")
                admin.password_hash = FastAuth.hash_password('admin123')
                admin.verified = True
                db.session.commit()
                print("✅ Admin password fixed")
            else:
                print("✅ Admin password already correct")
        
        # Create a new test user if needed
        test_user = User.query.filter_by(username='testuser').first()
        if not test_user:
            print("Creating testuser...")
            test_user = User()
            test_user.username = 'testuser'
            test_user.email = 'test@example.com'
            test_user.password_hash = FastAuth.hash_password('test123')
            test_user.role = 'dispatcher'
            test_user.verified = True
            db.session.add(test_user)
            db.session.commit()
            print("✅ Created testuser")
        else:
            # Fix existing testuser password
            test_user.password_hash = FastAuth.hash_password('test123')
            test_user.verified = True
            db.session.commit()
            print("✅ Fixed testuser password")
        
        print("\n📊 User Status:")
        print("-" * 40)
        users = User.query.all()
        for user in users:
            verified_status = "✅" if user.verified else "❌"
            print(f"  {user.username}: Role={user.role}, Verified={verified_status}")

if __name__ == "__main__":
    fix_user_passwords()
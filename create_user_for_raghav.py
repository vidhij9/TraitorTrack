#!/usr/bin/env python3
"""
USER CREATION SCRIPT FOR RAGHAV
Run this script to create working users that can login immediately.
"""

from app_clean import app, db
from models import User, UserRole
from werkzeug.security import generate_password_hash

def create_user(username, email, password, role='dispatcher'):
    """Create a user that will definitely work with the login system"""
    
    with app.app_context():
        print(f"🔧 Creating user: {username}")
        
        # Check if user already exists
        existing = User.query.filter_by(username=username).first()
        if existing:
            print(f"   ⚠️ User {username} already exists - updating password")
            user = existing
        else:
            # Create new user
            user = User()
            user.username = username
            user.email = email
            user.role = role
            user.verified = True
            db.session.add(user)
        
        # Set password using werkzeug (guaranteed to work)
        password_hash = generate_password_hash(password)
        user.password_hash = password_hash
        
        try:
            db.session.commit()
            print(f"   ✅ User created successfully!")
            print(f"   Username: {username}")
            print(f"   Password: {password}")
            print(f"   Role: {role}")
            print(f"   Hash: {password_hash[:30]}...")
            
            # Test the password immediately
            from werkzeug.security import check_password_hash
            test_result = check_password_hash(password_hash, password)
            print(f"   Password test: {'✅ PASS' if test_result else '❌ FAIL'}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"   ❌ Error: {e}")
            return False

def main():
    """Create multiple users for testing"""
    print("🚀 CREATING WORKING USERS FOR PRODUCTION")
    print("="*60)
    
    # List of users to create
    users_to_create = [
        ("newuser1", "newuser1@company.com", "newuser123", "dispatcher"),
        ("newuser2", "newuser2@company.com", "newuser123", "dispatcher"), 
        ("testbiller", "testbiller@company.com", "testbiller123", "biller"),
        ("testadmin", "testadmin@company.com", "testadmin123", "admin"),
    ]
    
    success_count = 0
    
    for username, email, password, role in users_to_create:
        if create_user(username, email, password, role):
            success_count += 1
        print()
    
    print("="*60)
    print(f"✅ SUMMARY: {success_count}/{len(users_to_create)} users created successfully")
    print()
    print("📋 LOGIN CREDENTIALS:")
    print("-" * 40)
    for username, email, password, role in users_to_create:
        print(f"Username: {username}")
        print(f"Password: {password}")
        print(f"Role: {role}")
        print()
    
    print("🎯 TEST THESE USERS AT: https://traitortrack.replit.app/login")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Force development setup with clean user data
"""
import os
import sys

# Force development environment before importing app
os.environ['ENVIRONMENT'] = 'development'
os.environ['FLASK_ENV'] = 'development'

from app_clean import app, db
from models import User, UserRole

def setup_clean_dev_environment():
    """Setup clean development environment"""
    with app.app_context():
        print("Setting up clean development environment...")
        
        # Create development users with different usernames to avoid conflicts
        dev_users = [
            ('devadmin', 'devadmin@test.com', 'admin123', UserRole.ADMIN),
            ('devuser1', 'devuser1@test.com', 'password123', UserRole.EMPLOYEE),
            ('devuser2', 'devuser2@test.com', 'password123', UserRole.EMPLOYEE),
            ('testmanager', 'testmgr@test.com', 'manager123', UserRole.ADMIN),
        ]
        
        for username, email, password, role in dev_users:
            existing = User.query.filter_by(username=username).first()
            if not existing:
                user = User()
                user.username = username
                user.email = email
                user.role = role.value
                user.verified = True
                user.set_password(password)
                
                db.session.add(user)
                print(f"Created: {username} / {password} ({role.value})")
        
        try:
            db.session.commit()
            print("Development users created successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating users: {e}")
        
        # Show all users
        all_users = User.query.all()
        print(f"\nTotal users in database: {len(all_users)}")
        for user in all_users:
            print(f"- {user.username} ({user.email}) [{user.role}]")

if __name__ == '__main__':
    setup_clean_dev_environment()
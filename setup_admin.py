#!/usr/bin/env python3
"""
Admin setup script for TraceTrack production environment
Run this once to create the admin user in production
"""

import os
import sys
from werkzeug.security import generate_password_hash

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

def setup_admin():
    """Create admin user for production"""
    try:
        from app_clean import app, db
        from models import User, UserRole
        
        with app.app_context():
            # Check if admin already exists
            existing_admin = User.query.filter_by(username='admin').first()
            if existing_admin:
                print("Admin user already exists.")
                print(f"Username: admin")
                print("Password: admin")
                return
            
            # Create admin user
            admin_user = User()
            admin_user.username = 'admin'
            admin_user.email = 'admin@traitortrack.app'
            admin_user.role = UserRole.ADMIN.value
            admin_user.verified = True
            admin_user.set_password('admin')
            
            db.session.add(admin_user)
            db.session.commit()
            
            print("Admin user created successfully!")
            print("Username: admin")
            print("Password: admin")
            print("\nIMPORTANT: Change the admin password after first login!")
            
    except Exception as e:
        print(f"Error creating admin user: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    setup_admin()
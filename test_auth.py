#!/usr/bin/env python3
"""Test authentication directly"""

import os
import sys
sys.path.insert(0, os.path.abspath('.'))

from app_clean import app, db
from models import User, UserRole
from werkzeug.security import generate_password_hash, check_password_hash

with app.app_context():
    # Get admin user
    admin = User.query.filter_by(username='admin').first()
    if admin:
        print(f"Admin found: {admin.username}")
        print(f"Email: {admin.email}")
        print(f"Role: {admin.role}")
        print(f"Verified: {admin.verified}")
        print(f"Password hash length: {len(admin.password_hash) if admin.password_hash else 0}")
        
        # Test password check
        test_password = 'admin'
        password_check = check_password_hash(admin.password_hash, test_password)
        print(f"Password check for '{test_password}': {password_check}")
        
        # Update admin user if needed
        if not admin.verified or not password_check:
            print("Updating admin user...")
            admin.verified = True
            admin.password_hash = generate_password_hash('admin')
            db.session.commit()
            print("Admin user updated")
            
            # Test again
            new_check = check_password_hash(admin.password_hash, 'admin')
            print(f"New password check: {new_check}")
    else:
        print("Creating new admin user...")
        admin = User()
        admin.username = 'admin'
        admin.email = 'admin@traitortrack.app'
        admin.role = UserRole.ADMIN.value
        admin.verified = True
        admin.set_password('admin')
        
        db.session.add(admin)
        db.session.commit()
        print("New admin user created")
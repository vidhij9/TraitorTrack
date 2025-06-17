#!/usr/bin/env python3
"""Create a simple admin user for easy testing"""

import os
os.environ['ENVIRONMENT'] = 'development'

from app_clean import app, db
from models import User
from werkzeug.security import generate_password_hash

def create_simple_admin():
    with app.app_context():
        # Check if simple admin already exists
        existing = User.query.filter_by(username='testadmin').first()
        if existing:
            print("testadmin user already exists!")
            return
        
        # Create simple test admin
        admin = User(
            username='testadmin',
            email='testadmin@test.com',
            role='admin',
            password_hash=generate_password_hash('test123'),
            verified=True
        )
        db.session.add(admin)
        db.session.commit()
        
        print("Created simple admin user:")
        print("Username: testadmin")
        print("Password: test123")
        print("Role: admin")

if __name__ == "__main__":
    create_simple_admin()

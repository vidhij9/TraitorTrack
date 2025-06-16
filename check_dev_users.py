#!/usr/bin/env python3
"""Check available users in development database"""

import os
os.environ['ENVIRONMENT'] = 'development'

from app_clean import app, db
from models import User

def check_users():
    with app.app_context():
        users = User.query.all()
        print("Available users in development database:")
        print("=" * 40)
        for user in users:
            print(f"Username: {user.username}")
            print(f"Email: {user.email}")
            print(f"Role: {user.role}")
            print(f"Verified: {user.verified}")
            print("-" * 20)
        
        if not users:
            print("No users found in development database!")
        else:
            print(f"\nTotal users: {len(users)}")
            print("\nTry logging in with these credentials:")
            print("- Check if there's an 'admin' user")
            print("- Default password might be 'admin123' or similar")

if __name__ == "__main__":
    check_users()
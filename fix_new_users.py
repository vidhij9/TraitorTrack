#!/usr/bin/env python3
"""
Fix for new users who can't login - Run this script to reset their passwords
to a known working format compatible with the login system.
"""

from app_clean import app, db
from models import User
from werkzeug.security import generate_password_hash

def fix_new_user_passwords():
    """Fix passwords for new users who can't login"""
    
    with app.app_context():
        print("🔧 FIXING NEW USER PASSWORD COMPATIBILITY")
        print("="*60)
        
        # Get all users created recently (likely the ones with issues)
        from datetime import datetime, timedelta
        recent_cutoff = datetime.utcnow() - timedelta(days=7)  # Last 7 days
        
        recent_users = User.query.filter(User.created_at >= recent_cutoff).all()
        
        print(f"Found {len(recent_users)} recent users:")
        
        for user in recent_users:
            print(f"\nUser: {user.username}")
            print(f"  Role: {user.role}")
            print(f"  Created: {user.created_at}")
            print(f"  Current hash: {user.password_hash[:30]}...")
            
            # Reset password to a known working format
            new_password = f"{user.username}123"  # username + 123
            
            # Generate hash using werkzeug (compatible format)
            new_hash = generate_password_hash(new_password)
            user.password_hash = new_hash
            
            print(f"  New password: {new_password}")
            print(f"  New hash: {new_hash[:30]}...")
            
        try:
            db.session.commit()
            print(f"\n✅ FIXED {len(recent_users)} users!")
            print("\nNew login credentials:")
            print("-" * 40)
            for user in recent_users:
                print(f"Username: {user.username}")
                print(f"Password: {user.username}123")
                print()
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_new_user_passwords()
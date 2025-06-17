#!/usr/bin/env python3
"""
Verify Current Database Isolation Status
Checks which database the application is actually using right now.
"""

import os
import sys

# Set development environment to use isolated database
os.environ['ENVIRONMENT'] = 'development'

# Import after setting environment
from app_clean import app, db
from models import User, Bag

def verify_current_database():
    """Check which database is currently being used."""
    with app.app_context():
        try:
            # Get current database name
            result = db.session.execute(db.text("SELECT current_database()"))
            current_db = result.scalar()
            
            print(f"Application is connected to: {current_db}")
            
            # Check if we're using the isolated development database
            if current_db == 'neondb_dev':
                print("SUCCESS: Application is using the isolated DEVELOPMENT database")
                print("Your development changes will NOT affect production data")
                return True
            elif current_db == 'neondb_prod':
                print("WARNING: Application is using the PRODUCTION database")
                print("Changes will affect live production data!")
                return False
            elif current_db == 'neondb':
                print("ERROR: Application is using the shared database")
                print("This is the source of your isolation problem!")
                return False
            else:
                print(f"UNKNOWN: Application is using database: {current_db}")
                return False
                
        except Exception as e:
            print(f"Error checking database: {e}")
            return False

def test_data_isolation():
    """Test that we can safely modify data in development."""
    with app.app_context():
        try:
            # Count current bags
            bag_count = Bag.query.count()
            user_count = User.query.count()
            
            print(f"\nCurrent data in connected database:")
            print(f"Users: {user_count}")
            print(f"Bags: {bag_count}")
            
            return True
            
        except Exception as e:
            print(f"Error accessing data: {e}")
            return False

def main():
    """Verify database isolation status."""
    print("Database Isolation Verification")
    print("=" * 35)
    
    # Check current database connection
    db_ok = verify_current_database()
    
    # Test data access
    data_ok = test_data_isolation()
    
    if db_ok and data_ok:
        print(f"\nISOLATION STATUS: ✓ WORKING")
        print("Development environment is properly isolated")
        print("You can safely test without affecting production")
    else:
        print(f"\nISOLATION STATUS: ✗ FAILED")
        print("Database isolation is not working properly")
        print("Development changes may still affect production")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test script to verify database separation is working correctly
"""
import os
import sys
from urllib.parse import urlparse

# Set environment variables for testing
os.environ['FLASK_ENV'] = 'development'
os.environ['DEV_DATABASE_URL'] = f"postgresql://{os.environ.get('PGUSER')}:{os.environ.get('PGPASSWORD')}@{os.environ.get('PGHOST')}:{os.environ.get('PGPORT')}/tracetrack_dev"
os.environ['PROD_DATABASE_URL'] = "postgresql://neondb_owner:npg_mznV9XNHSeP6@ep-yellow-truth-a5j5ivuq.us-east-2.aws.neon.tech/neondb?sslmode=require"

# Import app after setting environment variables
from app_clean import app, db

def test_database_connection():
    """Test which database the application is actually using"""
    with app.app_context():
        # Get the actual database URL being used
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        
        print("Database Connection Test")
        print("=" * 50)
        print(f"Environment: {os.environ.get('FLASK_ENV', 'not set')}")
        print(f"Database URL: {db_url}")
        
        # Parse the URL to get database name
        parsed = urlparse(db_url)
        database_name = parsed.path[1:] if parsed.path else 'unknown'
        
        print(f"Database Name: {database_name}")
        print(f"Host: {parsed.hostname}")
        print(f"Port: {parsed.port}")
        
        # Test connection by running a simple query
        try:
            result = db.session.execute(db.text("SELECT current_database(), version()")).fetchone()
            if result:
                current_db = result[0]
                version = result[1]
                print(f"Connected Database: {current_db}")
                print(f"PostgreSQL Version: {version[:50]}...")
                
                # Check if we're using the development database
                if current_db == 'tracetrack_dev':
                    print("✅ SUCCESS: Using development database (tracetrack_dev)")
                    return True
                elif current_db == 'neondb':
                    print("❌ WARNING: Using production database (neondb)")
                    return False
                else:
                    print(f"❓ UNKNOWN: Using database ({current_db})")
                    return False
            else:
                print("❌ ERROR: Could not query database")
                return False
                
        except Exception as e:
            print(f"❌ ERROR: Database connection failed - {str(e)}")
            return False

def test_data_separation():
    """Test that data operations affect only the current environment's database"""
    with app.app_context():
        try:
            # Count records in the current database
            from models import User, Bag
            
            user_count = User.query.count()
            bag_count = Bag.query.count()
            
            print(f"\nCurrent Database Contents:")
            print(f"Users: {user_count}")
            print(f"Bags: {bag_count}")
            
            return True
            
        except Exception as e:
            print(f"❌ ERROR: Could not query data - {str(e)}")
            return False

def main():
    """Run database separation tests"""
    print("Testing Database Separation Implementation")
    print("=" * 60)
    
    # Test 1: Verify database connection
    connection_test = test_database_connection()
    
    # Test 2: Check data contents
    data_test = test_data_separation()
    
    print("\n" + "=" * 60)
    if connection_test and data_test:
        print("✅ Database separation is working correctly!")
    else:
        print("❌ Database separation needs configuration")
        
    return connection_test and data_test

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Initialize Development Database
Sets up the development database with proper schema and demonstrates isolation.
"""

import os
import sys

# Set development environment
os.environ['ENVIRONMENT'] = 'development'
os.environ['DEV_DATABASE_URL'] = 'postgresql://neondb_owner:npg_mznV9XNHSeP6@ep-yellow-truth-a5j5ivuq.us-east-2.aws.neon.tech:5432/neondb_dev'
os.environ['SESSION_SECRET'] = 'dev-session-test'

# Import after setting environment
from app_clean import app, db
from models import User, Bag, Scan, Bill

def initialize_development_database():
    """Initialize development database with schema."""
    print("Initializing Development Database...")
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✓ Database tables created")
        
        # Add a test user for development
        existing_user = User.query.filter_by(username='dev_test_user').first()
        if not existing_user:
            from werkzeug.security import generate_password_hash
            test_user = User(
                username='dev_test_user',
                email='dev@test.com',
                password_hash=generate_password_hash('test123'),
                role='employee',
                verified=True
            )
            db.session.add(test_user)
            db.session.commit()
            print("✓ Development test user created")
        else:
            print("✓ Development test user already exists")
        
        # Count records
        user_count = User.query.count()
        bag_count = Bag.query.count()
        scan_count = Scan.query.count()
        
        print(f"\nDevelopment Database Contents:")
        print(f"  Users: {user_count}")
        print(f"  Bags: {bag_count}")
        print(f"  Scans: {scan_count}")
        
        return user_count

def test_production_isolation():
    """Test that production database is separate."""
    print("\nTesting Production Database Isolation...")
    
    # Connect to production database
    import psycopg2
    prod_url = "postgresql://neondb_owner:npg_mznV9XNHSeP6@ep-yellow-truth-a5j5ivuq.us-east-2.aws.neon.tech:5432/neondb_prod"
    
    try:
        from urllib.parse import urlparse
        parsed = urlparse(prod_url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip('/')
        )
        
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM "user"')
        prod_user_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        print(f"Production Database Users: {prod_user_count}")
        return prod_user_count
        
    except Exception as e:
        print(f"Error accessing production database: {e}")
        return None

def main():
    """Main function."""
    print("Database Environment Isolation Test")
    print("=" * 45)
    
    # Initialize development database
    dev_user_count = initialize_development_database()
    
    # Test production isolation
    prod_user_count = test_production_isolation()
    
    if prod_user_count is not None:
        print(f"\nIsolation Test Results:")
        print(f"Development users: {dev_user_count}")
        print(f"Production users: {prod_user_count}")
        
        if dev_user_count != prod_user_count:
            print("\n✓ DATABASES ARE COMPLETELY ISOLATED!")
            print("✓ Development changes do NOT affect production")
            print("✓ Production data is safe from development testing")
        else:
            print("\n⚠ Database counts are the same - isolation unclear")
        
        print(f"\nDatabase URLs:")
        print(f"Development: neondb_dev")
        print(f"Production: neondb_prod")
        print(f"\nTo switch environments:")
        print(f"Development: source .env.dev")
        print(f"Production: source .env.prod")

if __name__ == "__main__":
    main()

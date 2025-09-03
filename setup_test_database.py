#!/usr/bin/env python
"""
Setup Test Database Schema
Creates all tables and indexes in the Replit Neon test database
WITHOUT copying any data from production
"""
import os
import sys
sys.path.insert(0, '/home/runner/workspace')

from app_clean import app, db
from models import User, Bag, Link, Bill, BillBag, Scan, PromotionRequest, AuditLog
from werkzeug.security import generate_password_hash
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_database_schema():
    """Create all tables in the test database"""
    
    with app.app_context():
        # Check which database we're using
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        
        if 'amazonaws.com' in db_uri:
            print("❌ ERROR: Connected to AWS RDS production database!")
            print("   Aborting to prevent production changes.")
            return False
        
        if 'neon.tech' not in db_uri:
            print("⚠️ WARNING: Not connected to Replit Neon test database")
            print(f"   Connected to: {db_uri[:50]}")
            response = input("Continue anyway? (yes/no): ")
            if response.lower() != 'yes':
                return False
        
        print("=" * 60)
        print("Setting up Test Database Schema")
        print("=" * 60)
        print(f"Database: Replit Neon (Testing)")
        
        try:
            # Create all tables
            print("\n1. Creating tables...")
            db.create_all()
            print("   ✓ All tables created successfully")
            
            # List created tables
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"\n2. Tables created: {len(tables)}")
            for table in sorted(tables):
                columns = inspector.get_columns(table)
                print(f"   - {table} ({len(columns)} columns)")
            
            # Create indexes (they should be created automatically with tables)
            print("\n3. Indexes created automatically with tables")
            
            # Create a test admin user for login
            print("\n4. Creating test admin user...")
            
            # Check if admin already exists
            existing_admin = User.query.filter_by(username='admin').first()
            if existing_admin:
                print("   - Admin user already exists")
            else:
                admin = User()
                admin.username = 'admin'
                admin.email = 'admin@test.com'
                admin.set_password('admin123')  # Test password
                admin.role = 'admin'
                admin.verified = True
                db.session.add(admin)
                db.session.commit()
                print("   ✓ Created test admin user")
                print("     Username: admin")
                print("     Password: admin123")
            
            # Create a test dispatcher user
            existing_dispatcher = User.query.filter_by(username='dispatcher').first()
            if existing_dispatcher:
                print("   - Dispatcher user already exists")
            else:
                dispatcher = User()
                dispatcher.username = 'dispatcher'
                dispatcher.email = 'dispatcher@test.com'
                dispatcher.set_password('dispatcher123')
                dispatcher.role = 'dispatcher'
                dispatcher.dispatch_area = 'lucknow'
                dispatcher.verified = True
                db.session.add(dispatcher)
                db.session.commit()
                print("   ✓ Created test dispatcher user")
                print("     Username: dispatcher")
                print("     Password: dispatcher123")
            
            # Create a test biller user
            existing_biller = User.query.filter_by(username='biller').first()
            if existing_biller:
                print("   - Biller user already exists")
            else:
                biller = User()
                biller.username = 'biller'
                biller.email = 'biller@test.com'
                biller.set_password('biller123')
                biller.role = 'biller'
                biller.verified = True
                db.session.add(biller)
                db.session.commit()
                print("   ✓ Created test biller user")
                print("     Username: biller")
                print("     Password: biller123")
            
            print("\n" + "=" * 60)
            print("✅ Test Database Setup Complete!")
            print("=" * 60)
            print("\nYou can now login with these test accounts:")
            print("  1. Admin:      admin / admin123")
            print("  2. Dispatcher: dispatcher / dispatcher123")
            print("  3. Biller:     biller / biller123")
            print("\nThe database is ready for testing with:")
            print("  - All tables and indexes created")
            print("  - No production data copied")
            print("  - Test users for each role")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error setting up database: {e}")
            import traceback
            traceback.print_exc()
            return False

def verify_test_setup():
    """Verify the test database setup"""
    
    with app.app_context():
        print("\n" + "=" * 60)
        print("Verifying Test Database Setup")
        print("=" * 60)
        
        try:
            # Count records in each table
            from models import User, Bag, Link, Bill, Scan
            
            user_count = User.query.count()
            bag_count = Bag.query.count()
            link_count = Link.query.count()
            bill_count = Bill.query.count()
            scan_count = Scan.query.count()
            
            print(f"\nRecord counts:")
            print(f"  Users: {user_count}")
            print(f"  Bags:  {bag_count}")
            print(f"  Links: {link_count}")
            print(f"  Bills: {bill_count}")
            print(f"  Scans: {scan_count}")
            
            # List users
            users = User.query.all()
            if users:
                print(f"\nUsers in database:")
                for user in users:
                    print(f"  - {user.username} ({user.role})")
            
            print("\n✓ Test database is properly configured")
            
        except Exception as e:
            print(f"❌ Verification failed: {e}")

if __name__ == "__main__":
    # Ensure we're in testing mode
    os.environ['ENVIRONMENT'] = 'development'
    
    print("🔧 TEST DATABASE SETUP TOOL")
    print("=" * 60)
    print("This will create all tables in the Replit Neon test database")
    print("WITHOUT copying any data from production.")
    print("=" * 60)
    
    # Setup the database
    if create_test_database_schema():
        verify_test_setup()
    else:
        print("\n❌ Database setup failed")
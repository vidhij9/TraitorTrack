#!/usr/bin/env python
"""
Diagnose database connection issue
"""
import os
import sys
import psycopg2
from urllib.parse import urlparse

# Add workspace to path
sys.path.insert(0, '/home/runner/workspace')

def check_actual_connection():
    """Check what database the Flask app is actually using"""
    from app_clean import app, db
    
    with app.app_context():
        # Get configured URI
        configured_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        print("=" * 60)
        print("Flask App Database Configuration")
        print("=" * 60)
        
        # Parse and display
        if configured_uri:
            parsed = urlparse(configured_uri)
            print(f"Configured DB URI Host: {parsed.hostname}")
            
            if 'amazonaws.com' in parsed.hostname:
                print("  → This is AWS RDS (Production)")
            elif 'neon.tech' in parsed.hostname:
                print("  → This is Replit Neon (Testing)")
            else:
                print("  → Unknown database type")
        
        # Try to query the database
        try:
            from models import Bag
            count = Bag.query.count()
            print(f"\nBag count in connected DB: {count:,}")
            
            # Get a sample bag to see which DB we're really connected to
            sample_bag = Bag.query.first()
            if sample_bag:
                print(f"Sample bag ID: {sample_bag.id}, QR: {sample_bag.qr_id}")
        except Exception as e:
            print(f"Error querying database: {e}")

def check_env_vars():
    """Check environment variables"""
    print("\n" + "=" * 60)
    print("Environment Variables")
    print("=" * 60)
    
    # Check DATABASE_URL
    db_url = os.environ.get('DATABASE_URL', '')
    if db_url:
        parsed = urlparse(db_url)
        print(f"DATABASE_URL (Replit): {parsed.hostname}")
        
        # Check bag count
        try:
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM bag")
            count = cur.fetchone()[0]
            print(f"  → Bag count: {count:,}")
            cur.close()
            conn.close()
        except Exception as e:
            print(f"  → Error: {e}")
    
    # Check PRODUCTION_DATABASE_URL
    prod_url = os.environ.get('PRODUCTION_DATABASE_URL', '')
    if prod_url:
        parsed = urlparse(prod_url)
        print(f"\nPRODUCTION_DATABASE_URL (AWS): {parsed.hostname}")
        
        # Check bag count
        try:
            conn = psycopg2.connect(prod_url)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM bag")
            count = cur.fetchone()[0]
            print(f"  → Bag count: {count:,}")
            cur.close()
            conn.close()
        except Exception as e:
            print(f"  → Error: {e}")

def check_imports():
    """Check if any modules are overriding the database"""
    print("\n" + "=" * 60)
    print("Import Chain Check")
    print("=" * 60)
    
    # Check if any imported modules might be overriding
    import sys
    modules_with_db = []
    
    for name, module in sys.modules.items():
        if hasattr(module, '__file__') and module.__file__ and '/workspace/' in module.__file__:
            # Check if module has database-related attributes
            if hasattr(module, 'DATABASE_URL') or hasattr(module, 'SQLALCHEMY_DATABASE_URI'):
                modules_with_db.append(name)
    
    if modules_with_db:
        print(f"Modules with DB config: {', '.join(modules_with_db)}")
    else:
        print("No modules found with explicit DB configuration")

# Main execution
if __name__ == "__main__":
    print("\n🔍 DATABASE CONNECTION DIAGNOSTIC")
    print("=" * 60)
    
    # Check environment variables
    check_env_vars()
    
    # Check Flask app configuration
    check_actual_connection()
    
    # Check imports
    check_imports()
    
    print("\n" + "=" * 60)
    print("DIAGNOSIS SUMMARY")
    print("=" * 60)
    
    # Get current environment
    from app_clean import get_current_environment
    env = get_current_environment()
    print(f"Detected environment: {env}")
    
    if env == 'development':
        print("✓ Should be using Replit Neon database")
        print("✗ But appears to be showing AWS RDS data!")
    else:
        print("In production mode - should use AWS RDS")
    
    print("\nPossible issues:")
    print("1. Database URL might be swapped in environment variables")
    print("2. Connection pooling might be caching old connections")
    print("3. Another module might be overriding the database URL")
    print("=" * 60)
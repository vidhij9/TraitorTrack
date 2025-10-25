#!/usr/bin/env python3
"""
Database Connection Verification Script
Run this to verify database connectivity before deployment
"""

import os
import sys
from sqlalchemy import create_engine, text

def verify_database_connection(db_url=None):
    """Verify database connection and print details"""
    if not db_url:
        db_url = os.environ.get('DATABASE_URL')
    
    if not db_url:
        print("❌ ERROR: DATABASE_URL not set")
        return False
    
    # Parse and mask password for display
    from urllib.parse import urlparse
    parsed = urlparse(db_url)
    masked_url = f"{parsed.scheme}://{parsed.username}:****@{parsed.hostname}:{parsed.port or 5432}{parsed.path}"
    
    print(f"🔍 Testing connection to: {masked_url}")
    
    try:
        # Create test engine
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10}
        )
        
        # Test connection
        with engine.connect() as conn:
            # Get PostgreSQL version
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            
            # Get database size
            result = conn.execute(text("""
                SELECT pg_database_size(current_database()) as size,
                       pg_size_pretty(pg_database_size(current_database())) as size_pretty
            """))
            size_info = result.fetchone()
            
            # Get connection info
            result = conn.execute(text("SELECT current_database(), current_user"))
            db_info = result.fetchone()
            
            print("\n✅ Connection successful!")
            print(f"   Database: {db_info[0]}")
            print(f"   User: {db_info[1]}")
            print(f"   Size: {size_info[1]}")
            print(f"   PostgreSQL: {version.split(',')[0]}")
            
            # Check for existing tables
            result = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            table_count = result.scalar()
            print(f"   Tables: {table_count}")
            
            if table_count == 0:
                print("\n⚠️  WARNING: No tables found. Database needs initialization.")
                print("   The app will create tables automatically on first run.")
            
            return True
            
    except Exception as e:
        print(f"\n❌ Connection failed: {str(e)}")
        print("\nCommon issues:")
        print("  • Security group doesn't allow connections from Replit")
        print("  • Incorrect username/password")
        print("  • Database doesn't exist")
        print("  • RDS instance not running")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TraceTrack - Database Connection Verification")
    print("=" * 60)
    
    # Check environment
    is_production = (
        os.environ.get('REPLIT_DEPLOYMENT') == '1' or
        os.environ.get('ENVIRONMENT') == 'production'
    )
    
    print(f"\n🌍 Environment: {'PRODUCTION' if is_production else 'DEVELOPMENT'}")
    
    # Test connection
    success = verify_database_connection()
    
    print("\n" + "=" * 60)
    sys.exit(0 if success else 1)

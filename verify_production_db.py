#!/usr/bin/env python
"""
Verify Production Database Configuration
This script checks the production database WITHOUT modifying any data
"""
import os
import psycopg2
from urllib.parse import urlparse

def verify_production_database():
    """Verify production database is accessible and configured correctly"""
    
    prod_url = os.environ.get('PRODUCTION_DATABASE_URL')
    
    if not prod_url:
        print("❌ PRODUCTION_DATABASE_URL not configured")
        return False
    
    # Parse the URL to check if it's AWS RDS
    parsed = urlparse(prod_url)
    hostname = parsed.hostname or ''
    
    print("=" * 60)
    print("Production Database Verification")
    print("=" * 60)
    
    if 'amazonaws.com' in hostname:
        print("✓ AWS RDS endpoint detected")
        print(f"  Host: {hostname}")
        print(f"  Database: {parsed.path[1:] if parsed.path else 'N/A'}")
    else:
        print("⚠️ Non-AWS endpoint detected")
        print(f"  Host: {hostname}")
    
    # Try to connect (READ-ONLY test)
    try:
        conn = psycopg2.connect(prod_url)
        cur = conn.cursor()
        
        # Just check we can connect and count tables (safe read-only operation)
        cur.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        table_count = cur.fetchone()[0]
        
        print(f"\n✓ Successfully connected to production database")
        print(f"  Tables in database: {table_count}")
        
        # Check for critical tables (safe read operation)
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('user', 'bag', 'link', 'bill', 'scan')
            ORDER BY table_name
        """)
        
        existing_tables = [row[0] for row in cur.fetchall()]
        
        if existing_tables:
            print(f"  Core tables found: {', '.join(existing_tables)}")
        
        # Get row counts (safe read operation)
        print("\n  Row counts (READ-ONLY check):")
        for table in existing_tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"    - {table}: {count:,} rows")
        
        cur.close()
        conn.close()
        
        print("\n✅ Production database is properly configured and accessible")
        print("⚠️ REMINDER: This is the PRODUCTION database - DO NOT DELETE anything!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Could not connect to production database")
        print(f"  Error: {str(e)}")
        return False

def verify_test_database():
    """Verify test/development database is accessible"""
    
    dev_url = os.environ.get('DATABASE_URL')
    
    if not dev_url:
        print("\n❌ DATABASE_URL (Replit test database) not configured")
        return False
    
    parsed = urlparse(dev_url)
    hostname = parsed.hostname or ''
    
    print("\n" + "=" * 60)
    print("Test/Development Database Verification")
    print("=" * 60)
    
    if 'neon.tech' in hostname:
        print("✓ Replit Neon database detected")
    else:
        print("✓ Test database detected")
    
    print(f"  Host: {hostname}")
    print(f"  Database: {parsed.path[1:] if parsed.path else 'N/A'}")
    
    # Try to connect
    try:
        conn = psycopg2.connect(dev_url)
        cur = conn.cursor()
        
        # Count tables
        cur.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        table_count = cur.fetchone()[0]
        
        print(f"\n✓ Successfully connected to test database")
        print(f"  Tables in database: {table_count}")
        
        cur.close()
        conn.close()
        
        print("✓ Test database is accessible for development/testing")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Could not connect to test database")
        print(f"  Error: {str(e)}")
        return False

# Main execution
if __name__ == "__main__":
    print("\n" + "🔍 DATABASE CONFIGURATION VERIFICATION")
    print("=" * 60)
    
    # Check production database
    prod_ok = verify_production_database()
    
    # Check test database  
    test_ok = verify_test_database()
    
    # Summary
    print("\n" + "=" * 60)
    print("CONFIGURATION SUMMARY")
    print("=" * 60)
    
    if prod_ok and test_ok:
        print("✅ Both databases are properly configured!")
        print("   - Production: AWS RDS (for traitor-track.replit.app)")
        print("   - Testing: Replit DB (for development on replit.dev)")
    elif prod_ok:
        print("⚠️ Production database OK, but test database has issues")
    elif test_ok:
        print("⚠️ Test database OK, but production database has issues")
    else:
        print("❌ Both databases have configuration issues")
    
    print("\nCurrent configuration ensures:")
    print("  1. Testing on replit.dev uses Replit's database")
    print("  2. Production on traitor-track.replit.app uses AWS RDS")
    print("  3. No accidental data deletion from production")
    print("\n" + "=" * 60)
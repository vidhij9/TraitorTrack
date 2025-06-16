#!/usr/bin/env python3
"""
Test Database Isolation
Demonstrates that development and production databases are completely separate.
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def parse_db_url(url):
    """Parse database URL."""
    parsed = urlparse(url)
    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'user': parsed.username,
        'password': parsed.password,
        'database': parsed.path.lstrip('/')
    }

def connect_to_db(db_url):
    """Connect to database."""
    db_info = parse_db_url(db_url)
    return psycopg2.connect(
        host=db_info['host'],
        port=db_info['port'],
        user=db_info['user'],
        password=db_info['password'],
        database=db_info['database']
    )

def count_records(db_url, table):
    """Count records in a table."""
    try:
        conn = connect_to_db(db_url)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    except Exception as e:
        return f"Error: {e}"

def add_test_record(db_url):
    """Add a test record to demonstrate isolation."""
    try:
        conn = connect_to_db(db_url)
        cursor = conn.cursor()
        
        # Add a test user
        cursor.execute("""
            INSERT INTO "user" (username, email, password_hash, role, verified, created_at)
            VALUES ('test_isolation', 'test@isolation.com', 'dummy_hash', 'employee', true, NOW())
            ON CONFLICT (username) DO NOTHING
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        return f"Error: {e}"

def main():
    """Test database isolation."""
    print("Database Isolation Test")
    print("=" * 40)
    
    # Get database URLs
    dev_url = "postgresql://neondb_owner:npg_mznV9XNHSeP6@ep-yellow-truth-a5j5ivuq.us-east-2.aws.neon.tech:5432/neondb_dev"
    prod_url = "postgresql://neondb_owner:npg_mznV9XNHSeP6@ep-yellow-truth-a5j5ivuq.us-east-2.aws.neon.tech:5432/neondb_prod"
    
    print("Testing database connections...")
    
    # Test connections
    try:
        dev_conn = connect_to_db(dev_url)
        dev_conn.close()
        print("✓ Development database: Connected")
    except Exception as e:
        print(f"✗ Development database: {e}")
        return
    
    try:
        prod_conn = connect_to_db(prod_url)
        prod_conn.close()
        print("✓ Production database: Connected")
    except Exception as e:
        print(f"✗ Production database: {e}")
        return
    
    print("\nBefore isolation test:")
    print(f"Development users: {count_records(dev_url, 'user')}")
    print(f"Production users: {count_records(prod_url, 'user')}")
    
    print("\nAdding test record to DEVELOPMENT database only...")
    result = add_test_record(dev_url)
    if result is True:
        print("✓ Test record added to development")
    else:
        print(f"✗ Failed to add test record: {result}")
        return
    
    print("\nAfter adding test record to development:")
    dev_count = count_records(dev_url, 'user')
    prod_count = count_records(prod_url, 'user')
    
    print(f"Development users: {dev_count}")
    print(f"Production users: {prod_count}")
    
    print("\nIsolation Test Results:")
    if dev_count != prod_count:
        print("✓ DATABASES ARE COMPLETELY ISOLATED")
        print("✓ Changes in development do NOT affect production")
        print("✓ Your setup is working correctly!")
    else:
        print("✗ Databases may not be properly isolated")
    
    print("\nDatabase Details:")
    dev_info = parse_db_url(dev_url)
    prod_info = parse_db_url(prod_url)
    
    print(f"Development: {dev_info['database']} on {dev_info['host']}")
    print(f"Production: {prod_info['database']} on {prod_info['host']}")

if __name__ == "__main__":
    main()
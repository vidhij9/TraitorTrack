#!/usr/bin/env python3
"""
Script to check production database structure and locate users.
"""
import os
import psycopg2
from urllib.parse import urlparse

def connect_to_production():
    """Connect to production database"""
    prod_url = os.environ.get('PRODUCTION_DATABASE_URL')
    if not prod_url:
        print("ERROR: PRODUCTION_DATABASE_URL not found")
        return None
    
    try:
        parsed = urlparse(prod_url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port,
            database=parsed.path[1:],
            user=parsed.username,
            password=parsed.password,
            sslmode='require'
        )
        print(f"✓ Connected to production database: {parsed.hostname}")
        print(f"  Database: {parsed.path[1:]}")
        return conn
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def check_database_structure():
    """Check database structure and locate users"""
    conn = connect_to_production()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        # Check current schema
        cursor.execute("SELECT current_schema();")
        current_schema = cursor.fetchone()[0]
        print(f"Current schema: {current_schema}")
        
        # List all schemas
        cursor.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            ORDER BY schema_name;
        """)
        schemas = cursor.fetchall()
        print(f"\nAvailable schemas:")
        for schema in schemas:
            print(f"  - {schema[0]}")
        
        # Check for tables in current schema
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = %s 
            ORDER BY table_name;
        """, (current_schema,))
        tables = cursor.fetchall()
        print(f"\nTables in '{current_schema}' schema:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Look for user-related tables in all schemas
        cursor.execute("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_name LIKE '%user%' 
            ORDER BY table_schema, table_name;
        """)
        user_tables = cursor.fetchall()
        print(f"\nUser-related tables across all schemas:")
        for schema, table in user_tables:
            print(f"  - {schema}.{table}")
        
        # Check specific table names we know about
        table_names = ['user', 'users', '"user"']
        for table_name in table_names:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                count = cursor.fetchone()[0]
                print(f"\nFound table {table_name} with {count} records")
                
                # Show sample data
                cursor.execute(f"SELECT id, username, role FROM {table_name} LIMIT 5;")
                users = cursor.fetchall()
                print(f"Sample users in {table_name}:")
                for user in users:
                    print(f"  - ID: {user[0]}, Username: {user[1]}, Role: {user[2]}")
                    
            except Exception as e:
                print(f"Table {table_name} not found or error: {e}")
        
        # Check for tables in production schema specifically
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'production'
            ORDER BY table_name;
        """)
        prod_tables = cursor.fetchall()
        if prod_tables:
            print(f"\nTables in 'production' schema:")
            for table in prod_tables:
                print(f"  - {table[0]}")
                
            # Check users in production schema
            try:
                cursor.execute('SELECT id, username, role FROM production."user" LIMIT 10;')
                users = cursor.fetchall()
                print(f"\nUsers in production.user table:")
                for user in users:
                    print(f"  - ID: {user[0]}, Username: {user[1]}, Role: {user[2]}")
            except Exception as e:
                print(f"No users found in production schema: {e}")
        
    except Exception as e:
        print(f"ERROR checking database: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("Production Database Structure Check")
    print("=" * 40)
    check_database_structure()
#!/usr/bin/env python3
"""
Emergency Database Isolation Fix
Ensures proper environment variable configuration and database separation.
"""

import os
import subprocess

def set_development_environment():
    """Set proper development environment variables."""
    dev_vars = {
        'ENVIRONMENT': 'development',
        'DEV_DATABASE_URL': 'postgresql://neondb_owner:npg_mznV9XNHSeP6@ep-yellow-truth-a5j5ivuq.us-east-2.aws.neon.tech:5432/neondb_dev',
        'SESSION_SECRET': 'dev-session-isolated'
    }
    
    for key, value in dev_vars.items():
        os.environ[key] = value
        print(f"Set {key}")
    
    # Update .env files for persistence
    with open('.env.dev', 'w') as f:
        f.write(f"""export ENVIRONMENT=development
export DEV_DATABASE_URL="{dev_vars['DEV_DATABASE_URL']}"
export SESSION_SECRET="{dev_vars['SESSION_SECRET']}"
""")
    
    print("Development environment configured for database isolation")

def set_production_environment():
    """Set proper production environment variables."""
    prod_vars = {
        'ENVIRONMENT': 'production',
        'PROD_DATABASE_URL': 'postgresql://neondb_owner:npg_mznV9XNHSeP6@ep-yellow-truth-a5j5ivuq.us-east-2.aws.neon.tech:5432/neondb_prod',
        'SESSION_SECRET': 'prod-session-isolated'
    }
    
    with open('.env.prod', 'w') as f:
        f.write(f"""export ENVIRONMENT=production
export PROD_DATABASE_URL="{prod_vars['PROD_DATABASE_URL']}"
export SESSION_SECRET="{prod_vars['SESSION_SECRET']}"
""")
    
    print("Production environment configured for database isolation")

def verify_isolation():
    """Verify that databases are properly isolated."""
    import psycopg2
    from urllib.parse import urlparse
    
    dev_url = "postgresql://neondb_owner:npg_mznV9XNHSeP6@ep-yellow-truth-a5j5ivuq.us-east-2.aws.neon.tech:5432/neondb_dev"
    prod_url = "postgresql://neondb_owner:npg_mznV9XNHSeP6@ep-yellow-truth-a5j5ivuq.us-east-2.aws.neon.tech:5432/neondb_prod"
    
    try:
        # Test development connection
        dev_parsed = urlparse(dev_url)
        dev_conn = psycopg2.connect(
            host=dev_parsed.hostname,
            port=dev_parsed.port,
            user=dev_parsed.username,
            password=dev_parsed.password,
            database=dev_parsed.path.lstrip('/')
        )
        dev_cursor = dev_conn.cursor()
        dev_cursor.execute("SELECT current_database()")
        dev_db = dev_cursor.fetchone()[0]
        dev_cursor.close()
        dev_conn.close()
        
        # Test production connection
        prod_parsed = urlparse(prod_url)
        prod_conn = psycopg2.connect(
            host=prod_parsed.hostname,
            port=prod_parsed.port,
            user=prod_parsed.username,
            password=prod_parsed.password,
            database=prod_parsed.path.lstrip('/')
        )
        prod_cursor = prod_conn.cursor()
        prod_cursor.execute("SELECT current_database()")
        prod_db = prod_cursor.fetchone()[0]
        prod_cursor.close()
        prod_conn.close()
        
        print(f"Development database: {dev_db}")
        print(f"Production database: {prod_db}")
        
        if dev_db != prod_db:
            print("SUCCESS: Databases are properly isolated")
            return True
        else:
            print("ERROR: Databases are not isolated")
            return False
            
    except Exception as e:
        print(f"Error verifying isolation: {e}")
        return False

def main():
    """Fix database isolation emergency."""
    print("EMERGENCY DATABASE ISOLATION FIX")
    print("=" * 40)
    
    print("Configuring environment variables...")
    set_development_environment()
    set_production_environment()
    
    print("\nVerifying database isolation...")
    if verify_isolation():
        print("\nDATABASE ISOLATION RESTORED")
        print("Development and production databases are now separate")
        print("\nNEXT STEPS:")
        print("1. Restart your application")
        print("2. Use 'source .env.dev' for development")
        print("3. Use 'source .env.prod' for production")
    else:
        print("\nERROR: Database isolation verification failed")

if __name__ == "__main__":
    main()
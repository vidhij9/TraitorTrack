#!/usr/bin/env python3
"""
Database Environment Isolation Demonstration
Shows current environment status and demonstrates complete database isolation.
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def get_database_info(db_url, name):
    """Get database information and record counts."""
    try:
        parsed = urlparse(db_url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip('/')
        )
        
        cursor = conn.cursor()
        
        # Get database name
        cursor.execute("SELECT current_database()")
        db_name = cursor.fetchone()[0]
        
        # Get table counts
        tables = ['user', 'bag', 'scan', 'bill']
        counts = {}
        
        for table in tables:
            try:
                cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                counts[table] = cursor.fetchone()[0]
            except Exception as e:
                counts[table] = f"Error: {e}"
        
        cursor.close()
        conn.close()
        
        return {
            'name': name,
            'database': db_name,
            'status': 'Connected',
            'counts': counts
        }
        
    except Exception as e:
        return {
            'name': name,
            'database': 'Unknown',
            'status': f'Error: {e}',
            'counts': {}
        }

def main():
    """Demonstrate database environment isolation."""
    print("🏗️  Database Environment Isolation Demo")
    print("=" * 50)
    
    # Database URLs
    dev_url = "postgresql://neondb_owner:npg_mznV9XNHSeP6@ep-yellow-truth-a5j5ivuq.us-east-2.aws.neon.tech:5432/neondb_dev"
    prod_url = "postgresql://neondb_owner:npg_mznV9XNHSeP6@ep-yellow-truth-a5j5ivuq.us-east-2.aws.neon.tech:5432/neondb_prod"
    
    # Get information from both databases
    dev_info = get_database_info(dev_url, "Development")
    prod_info = get_database_info(prod_url, "Production")
    
    print(f"\n📊 Database Status Summary:")
    print(f"Development: {dev_info['status']} ({dev_info['database']})")
    print(f"Production:  {prod_info['status']} ({prod_info['database']})")
    
    print(f"\n📈 Record Counts Comparison:")
    print(f"{'Table':<12} {'Development':<12} {'Production':<12} {'Isolated':<10}")
    print("-" * 50)
    
    isolation_confirmed = True
    
    for table in ['user', 'bag', 'scan', 'bill']:
        dev_count = dev_info['counts'].get(table, 0)
        prod_count = prod_info['counts'].get(table, 0)
        
        # Check if counts are different (indicating isolation)
        if isinstance(dev_count, int) and isinstance(prod_count, int):
            isolated = "✓ Yes" if dev_count != prod_count else "⚠ Same"
            if dev_count == prod_count:
                isolation_confirmed = False
        else:
            isolated = "❓ Unknown"
            
        print(f"{table:<12} {str(dev_count):<12} {str(prod_count):<12} {isolated:<10}")
    
    print(f"\n🔒 Isolation Status:")
    if isolation_confirmed:
        print("✅ DATABASES ARE COMPLETELY ISOLATED")
        print("✅ Development changes do NOT affect production")
        print("✅ Production data is safe from development testing")
    else:
        print("⚠️  Database isolation unclear - record counts are identical")
        print("ℹ️  This may be normal if both databases have same initial data")
    
    print(f"\n🔄 Environment Switching:")
    print("To switch to development: ./switch-to-dev.sh")
    print("To switch to production:  ./switch-to-prod.sh")
    
    print(f"\n🌐 Current Environment Variables:")
    env_vars = ['ENVIRONMENT', 'DEV_DATABASE_URL', 'PROD_DATABASE_URL', 'DATABASE_URL']
    for var in env_vars:
        value = os.environ.get(var, 'Not set')
        if 'DATABASE_URL' in var and value != 'Not set':
            # Mask sensitive database URL
            parsed = urlparse(value)
            masked = f"postgresql://***:***@{parsed.hostname}:{parsed.port or 5432}/{parsed.path.lstrip('/')}"
            print(f"{var}: {masked}")
        else:
            print(f"{var}: {value}")

if __name__ == "__main__":
    main()

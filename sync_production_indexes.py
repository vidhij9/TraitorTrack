#!/usr/bin/env python3
"""
Script to add missing indexes to production database.
This script compares development indexes with production and adds missing ones.

Usage:
    python sync_production_indexes.py
    
Requires PRODUCTION_DATABASE_URL environment variable to be set.
"""

import os
import sys
from sqlalchemy import create_engine, text

def get_indexes(engine):
    """Get all indexes from a database"""
    query = """
    SELECT 
        t.relname as table_name,
        i.relname as index_name,
        pg_get_indexdef(i.oid) as index_def
    FROM 
        pg_class t,
        pg_class i,
        pg_index ix
    WHERE 
        t.oid = ix.indrelid
        AND i.oid = ix.indexrelid
        AND t.relkind = 'r'
        AND t.relname IN ('user', 'bag', 'bill', 'bill_bag', 'link', 'notification', 'scan')
    ORDER BY t.relname, i.relname
    """
    with engine.connect() as conn:
        result = conn.execute(text(query))
        return {(row[0], row[1]): row[2] for row in result}

def main():
    dev_url = os.environ.get('DATABASE_URL')
    prod_url = os.environ.get('PRODUCTION_DATABASE_URL')
    
    if not dev_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)
    
    if not prod_url:
        print("ERROR: PRODUCTION_DATABASE_URL not set")
        sys.exit(1)
    
    print("Connecting to development database...")
    dev_engine = create_engine(dev_url)
    
    print("Connecting to production database...")
    prod_engine = create_engine(prod_url)
    
    print("\nFetching indexes from development...")
    dev_indexes = get_indexes(dev_engine)
    print(f"  Found {len(dev_indexes)} indexes")
    
    print("\nFetching indexes from production...")
    prod_indexes = get_indexes(prod_engine)
    print(f"  Found {len(prod_indexes)} indexes")
    
    # Find missing indexes
    missing = {}
    for key, index_def in dev_indexes.items():
        if key not in prod_indexes:
            table_name, index_name = key
            if table_name not in missing:
                missing[table_name] = []
            missing[table_name].append((index_name, index_def))
    
    if not missing:
        print("\n✅ All indexes are in sync!")
        return
    
    print(f"\n⚠️  Found {sum(len(v) for v in missing.values())} missing indexes in production:\n")
    
    for table, indexes in sorted(missing.items()):
        print(f"  {table}:")
        for idx_name, idx_def in indexes:
            print(f"    - {idx_name}")
    
    # Ask for confirmation
    print("\nWould you like to create the missing indexes? (yes/no)")
    answer = input().strip().lower()
    
    if answer != 'yes':
        print("Aborted.")
        return
    
    print("\nCreating missing indexes on production...")
    
    with prod_engine.connect() as conn:
        for table, indexes in sorted(missing.items()):
            for idx_name, idx_def in indexes:
                # Convert to CONCURRENTLY to avoid locking
                create_stmt = idx_def.replace('CREATE INDEX', 'CREATE INDEX CONCURRENTLY IF NOT EXISTS')
                create_stmt = create_stmt.replace('CREATE UNIQUE INDEX', 'CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS')
                
                print(f"  Creating {idx_name}...")
                try:
                    # CONCURRENTLY requires autocommit
                    conn.execute(text("COMMIT"))
                    conn.execute(text(create_stmt))
                    print(f"    ✅ Created {idx_name}")
                except Exception as e:
                    print(f"    ❌ Failed: {str(e)}")
    
    print("\n✅ Done! Verifying indexes...")
    
    # Verify
    prod_indexes_new = get_indexes(prod_engine)
    print(f"\nProduction now has {len(prod_indexes_new)} indexes (was {len(prod_indexes)})")

if __name__ == '__main__':
    main()

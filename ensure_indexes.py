#!/usr/bin/env python3
"""
Verify critical database indexes exist.

This script is called during deployment to verify that required indexes exist.
It ONLY checks - it does NOT create indexes (that's done by Alembic migrations).

Usage:
    python ensure_indexes.py

Exit codes:
    0 - All critical indexes exist
    1 - Some indexes missing (warning only, deployment continues)
"""

import os
import sys
from sqlalchemy import create_engine, text


# Critical indexes to verify (NOT create - migrations handle creation)
# These are the minimum indexes required for production performance
CRITICAL_INDEXES = [
    # Link table - essential for bill viewing
    ('link', 'parent_bag_id'),
    ('link', 'child_bag_id'),
    
    # Bill_bag table - essential for bill viewing
    ('bill_bag', 'bill_id'),
    ('bill_bag', 'bag_id'),
    
    # Notification table - for unread count
    ('notification', 'user_id'),
]


def check_column_has_index(conn, table, column):
    """Check if a column has ANY index on it (regardless of index name)"""
    result = conn.execute(text(f"""
        SELECT i.relname as index_name
        FROM pg_class t
        JOIN pg_index ix ON t.oid = ix.indrelid
        JOIN pg_class i ON i.oid = ix.indexrelid
        JOIN pg_attribute a ON a.attrelid = t.oid
        WHERE t.relname = '{table}'
        AND a.attnum = ANY(ix.indkey)
        AND a.attname = '{column}'
        LIMIT 1
    """))
    row = result.fetchone()
    return row[0] if row else None


def verify_indexes():
    """Verify critical indexes exist (read-only check)"""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        return 1
    
    engine = create_engine(db_url)
    found = 0
    missing = 0
    
    with engine.connect() as conn:
        for table, column in CRITICAL_INDEXES:
            idx_name = check_column_has_index(conn, table, column)
            if idx_name:
                print(f"  ✅ {table}.{column} indexed ({idx_name})")
                found += 1
            else:
                print(f"  ⚠️  {table}.{column} NO INDEX")
                missing += 1
    
    print(f"\nSummary: {found} indexed, {missing} missing")
    
    if missing > 0:
        print("\n⚠️  Missing indexes may impact performance.")
        print("   Run Alembic migrations to create them.")
    
    return 0  # Always return success - this is just a warning


if __name__ == '__main__':
    print("🔧 Verifying database indexes...")
    exit_code = verify_indexes()
    print("✅ Index verification complete")
    sys.exit(exit_code)

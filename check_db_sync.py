#!/usr/bin/env python3
"""
Database Schema Sync Checker for TraitorTrack

Compares development and production database schemas to ensure they are in sync.
Checks both Alembic migration revisions and actual database structure (tables, indexes).

Usage:
    python check_db_sync.py           # Human-readable output
    python check_db_sync.py --json    # JSON output for scripting
    python check_db_sync.py --verbose # Detailed comparison

Exit codes:
    0 - Databases are in sync
    1 - Databases are out of sync (migrations needed)
    2 - Error connecting to databases
"""

import os
import sys
import json
import argparse
from datetime import datetime


def get_alembic_revision(engine):
    """Get current Alembic revision from a database"""
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            return row[0] if row else None
    except Exception as e:
        return f"error: {str(e)}"


def get_table_info(engine):
    """Get table structure from a database"""
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name, column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
            """))
            return {(row[0], row[1]): {'type': row[2], 'nullable': row[3]} for row in result}
    except Exception as e:
        return {'error': str(e)}


def get_index_info(engine):
    """Get index information from a database"""
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT tablename, indexname
                FROM pg_indexes 
                WHERE schemaname = 'public'
                ORDER BY tablename, indexname
            """))
            return {(row[0], row[1]) for row in result}
    except Exception as e:
        return set()


def compare_databases(dev_url, prod_url, verbose=False):
    """Compare development and production databases"""
    from sqlalchemy import create_engine
    
    results = {
        'timestamp': datetime.utcnow().isoformat(),
        'in_sync': True,
        'alembic': {},
        'tables': {},
        'indexes': {},
        'errors': []
    }
    
    try:
        dev_engine = create_engine(dev_url)
        prod_engine = create_engine(prod_url)
    except Exception as e:
        results['errors'].append(f"Failed to create database engines: {str(e)}")
        results['in_sync'] = False
        return results
    
    # Compare Alembic revisions
    dev_rev = get_alembic_revision(dev_engine)
    prod_rev = get_alembic_revision(prod_engine)
    
    results['alembic'] = {
        'dev_revision': dev_rev,
        'prod_revision': prod_rev,
        'in_sync': dev_rev == prod_rev
    }
    
    if dev_rev != prod_rev:
        results['in_sync'] = False
    
    # Compare table structures
    dev_tables = get_table_info(dev_engine)
    prod_tables = get_table_info(prod_engine)
    
    if 'error' not in dev_tables and 'error' not in prod_tables:
        dev_only = set(dev_tables.keys()) - set(prod_tables.keys())
        prod_only = set(prod_tables.keys()) - set(dev_tables.keys())
        
        results['tables'] = {
            'dev_columns': len(dev_tables),
            'prod_columns': len(prod_tables),
            'dev_only': list(dev_only)[:10] if verbose else len(dev_only),
            'prod_only': list(prod_only)[:10] if verbose else len(prod_only),
            'in_sync': len(dev_only) == 0 and len(prod_only) == 0
        }
        
        if dev_only or prod_only:
            results['in_sync'] = False
    else:
        results['tables'] = {'error': 'Failed to compare tables'}
    
    # Compare indexes
    dev_indexes = get_index_info(dev_engine)
    prod_indexes = get_index_info(prod_engine)
    
    dev_only_idx = dev_indexes - prod_indexes
    prod_only_idx = prod_indexes - dev_indexes
    
    results['indexes'] = {
        'dev_count': len(dev_indexes),
        'prod_count': len(prod_indexes),
        'missing_in_prod': len(dev_only_idx),
        'extra_in_prod': len(prod_only_idx),
        'in_sync': len(dev_only_idx) == 0
    }
    
    if verbose and dev_only_idx:
        results['indexes']['missing_indexes'] = [f"{t}.{i}" for t, i in sorted(dev_only_idx)]
    
    if dev_only_idx:
        results['in_sync'] = False
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Check database sync status')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    dev_url = os.environ.get('DATABASE_URL')
    prod_url = os.environ.get('PRODUCTION_DATABASE_URL')
    
    if not dev_url:
        if args.json:
            print(json.dumps({'error': 'DATABASE_URL not set', 'in_sync': False}))
        else:
            print("❌ ERROR: DATABASE_URL not set")
        sys.exit(2)
    
    if not prod_url:
        if args.json:
            print(json.dumps({'error': 'PRODUCTION_DATABASE_URL not set', 'in_sync': False}))
        else:
            print("❌ ERROR: PRODUCTION_DATABASE_URL not set")
        sys.exit(2)
    
    results = compare_databases(dev_url, prod_url, verbose=args.verbose)
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print("=" * 50)
        print("TraitorTrack Database Sync Check")
        print("=" * 50)
        print()
        
        # Alembic
        alembic = results.get('alembic', {})
        if alembic.get('in_sync'):
            print(f"✅ Alembic: IN SYNC (revision: {alembic.get('dev_revision')})")
        else:
            print(f"❌ Alembic: OUT OF SYNC")
            print(f"   Development: {alembic.get('dev_revision')}")
            print(f"   Production:  {alembic.get('prod_revision')}")
        print()
        
        # Tables
        tables = results.get('tables', {})
        if tables.get('in_sync'):
            print(f"✅ Tables: IN SYNC ({tables.get('dev_columns')} columns)")
        else:
            print(f"❌ Tables: OUT OF SYNC")
            print(f"   Dev-only: {tables.get('dev_only')}")
            print(f"   Prod-only: {tables.get('prod_only')}")
        print()
        
        # Indexes
        indexes = results.get('indexes', {})
        if indexes.get('in_sync'):
            print(f"✅ Indexes: IN SYNC ({indexes.get('dev_count')} indexes)")
        else:
            print(f"⚠️  Indexes: {indexes.get('missing_in_prod')} missing in production")
            if args.verbose and 'missing_indexes' in indexes:
                for idx in indexes['missing_indexes'][:10]:
                    print(f"      - {idx}")
        print()
        
        # Summary
        if results['in_sync']:
            print("✅ RESULT: Databases are IN SYNC")
        else:
            print("❌ RESULT: Databases are OUT OF SYNC - run migrations")
    
    sys.exit(0 if results['in_sync'] else 1)


if __name__ == '__main__':
    main()

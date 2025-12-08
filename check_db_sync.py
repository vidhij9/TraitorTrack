#!/usr/bin/env python3
"""
Database Schema Sync Verification Tool

Compares development and production database schemas to ensure they are in sync.
Checks Alembic migration revisions and optionally validates table structures.

Usage:
    python check_db_sync.py              # Check sync status
    python check_db_sync.py --verbose    # Detailed comparison
    python check_db_sync.py --json       # Output as JSON (for CI/CD)

Exit Codes:
    0 - Databases are in sync
    1 - Databases are out of sync
    2 - Connection or configuration error

Environment Variables:
    DATABASE_URL - Development database connection string
    PRODUCTION_DATABASE_URL - Production database connection string
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('db_sync_check')


def get_alembic_revision(database_url, db_name="database"):
    """Get current Alembic revision for a database"""
    from sqlalchemy import create_engine, text
    from alembic.migration import MigrationContext
    
    try:
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={'connect_timeout': 10}
        )
        
        with engine.connect() as conn:
            # First check if alembic_version table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'alembic_version'
                )
            """))
            table_exists = result.scalar()
            
            if not table_exists:
                return None, "alembic_version table does not exist"
            
            context = MigrationContext.configure(conn)
            revision = context.get_current_revision()
            return revision, None
            
    except Exception as e:
        return None, str(e)


def get_alembic_head():
    """Get the head revision from local Alembic migrations"""
    from alembic.config import Config as AlembicConfig
    from alembic.script import ScriptDirectory
    
    try:
        migrations_path = os.path.join(os.path.dirname(__file__), 'migrations')
        alembic_ini = os.path.join(migrations_path, 'alembic.ini')
        
        if not os.path.exists(alembic_ini):
            return None, "alembic.ini not found"
        
        alembic_cfg = AlembicConfig(alembic_ini)
        alembic_cfg.set_main_option('script_location', migrations_path)
        
        script = ScriptDirectory.from_config(alembic_cfg)
        head = script.get_current_head()
        return head, None
        
    except Exception as e:
        return None, str(e)


def get_table_columns(database_url, table_name):
    """Get column definitions for a table"""
    from sqlalchemy import create_engine, text
    
    engine = create_engine(database_url, pool_pre_ping=True, connect_args={'connect_timeout': 10})
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = :table_name
            ORDER BY ordinal_position
        """), {'table_name': table_name})
        
        return {row[0]: {'type': row[1], 'nullable': row[2], 'default': row[3]} 
                for row in result.fetchall()}


def get_table_indexes(database_url, table_name):
    """Get index definitions for a table"""
    from sqlalchemy import create_engine, text
    
    engine = create_engine(database_url, pool_pre_ping=True, connect_args={'connect_timeout': 10})
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = :table_name
            ORDER BY indexname
        """), {'table_name': table_name})
        
        return {row[0]: row[1] for row in result.fetchall()}


def get_all_tables(database_url):
    """Get list of all user tables in the database"""
    from sqlalchemy import create_engine, text
    
    engine = create_engine(database_url, pool_pre_ping=True, connect_args={'connect_timeout': 10})
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            AND table_name != 'alembic_version'
            ORDER BY table_name
        """))
        
        return [row[0] for row in result.fetchall()]


def compare_schemas(dev_url, prod_url, verbose=False):
    """
    Compare development and production database schemas.
    
    Returns:
        dict: Comparison results with sync status and differences
    """
    results = {
        'sync_status': 'unknown',
        'timestamp': datetime.utcnow().isoformat(),
        'alembic': {
            'dev_revision': None,
            'prod_revision': None,
            'head_revision': None,
            'dev_at_head': False,
            'prod_at_head': False,
            'revisions_match': False
        },
        'tables': {
            'dev_only': [],
            'prod_only': [],
            'common': []
        },
        'column_differences': {},
        'errors': []
    }
    
    # Check Alembic revisions
    logger.info("Checking Alembic revisions...")
    
    dev_rev, dev_error = get_alembic_revision(dev_url, "development")
    prod_rev, prod_error = get_alembic_revision(prod_url, "production")
    head_rev, head_error = get_alembic_head()
    
    if dev_error:
        results['errors'].append(f"Development DB: {dev_error}")
    if prod_error:
        results['errors'].append(f"Production DB: {prod_error}")
    if head_error:
        results['errors'].append(f"Alembic head: {head_error}")
    
    results['alembic']['dev_revision'] = dev_rev
    results['alembic']['prod_revision'] = prod_rev
    results['alembic']['head_revision'] = head_rev
    results['alembic']['dev_at_head'] = dev_rev == head_rev
    results['alembic']['prod_at_head'] = prod_rev == head_rev
    results['alembic']['revisions_match'] = dev_rev == prod_rev
    
    logger.info(f"  Development revision: {dev_rev or 'None'}")
    logger.info(f"  Production revision:  {prod_rev or 'None'}")
    logger.info(f"  Head revision:        {head_rev or 'None'}")
    
    # Compare table lists
    logger.info("Comparing table structures...")
    
    try:
        dev_tables = set(get_all_tables(dev_url))
        prod_tables = set(get_all_tables(prod_url))
        
        results['tables']['dev_only'] = sorted(list(dev_tables - prod_tables))
        results['tables']['prod_only'] = sorted(list(prod_tables - dev_tables))
        results['tables']['common'] = sorted(list(dev_tables & prod_tables))
        
        logger.info(f"  Development tables: {len(dev_tables)}")
        logger.info(f"  Production tables:  {len(prod_tables)}")
        logger.info(f"  Common tables:      {len(results['tables']['common'])}")
        
        if results['tables']['dev_only']:
            logger.warning(f"  Dev-only tables: {results['tables']['dev_only']}")
        if results['tables']['prod_only']:
            logger.warning(f"  Prod-only tables: {results['tables']['prod_only']}")
        
        # Compare columns for common tables if verbose
        if verbose:
            logger.info("Comparing column structures...")
            for table in results['tables']['common']:
                try:
                    dev_cols = get_table_columns(dev_url, table)
                    prod_cols = get_table_columns(prod_url, table)
                    
                    dev_col_names = set(dev_cols.keys())
                    prod_col_names = set(prod_cols.keys())
                    
                    dev_only_cols = dev_col_names - prod_col_names
                    prod_only_cols = prod_col_names - dev_col_names
                    
                    if dev_only_cols or prod_only_cols:
                        results['column_differences'][table] = {
                            'dev_only': list(dev_only_cols),
                            'prod_only': list(prod_only_cols)
                        }
                        logger.warning(f"  Table '{table}' has column differences:")
                        if dev_only_cols:
                            logger.warning(f"    Dev-only: {dev_only_cols}")
                        if prod_only_cols:
                            logger.warning(f"    Prod-only: {prod_only_cols}")
                            
                except Exception as e:
                    results['errors'].append(f"Column comparison for {table}: {e}")
                    
    except Exception as e:
        results['errors'].append(f"Table comparison: {e}")
    
    # Determine overall sync status
    if results['errors']:
        results['sync_status'] = 'error'
    elif (results['alembic']['revisions_match'] and 
          not results['tables']['dev_only'] and 
          not results['tables']['prod_only'] and
          not results['column_differences']):
        results['sync_status'] = 'synced'
    else:
        results['sync_status'] = 'out_of_sync'
    
    return results


def check_sync():
    """Main sync check function"""
    dev_url = os.environ.get('DATABASE_URL')
    prod_url = os.environ.get('PRODUCTION_DATABASE_URL')
    
    if not dev_url:
        logger.error("DATABASE_URL not set")
        return None
    
    if not prod_url:
        logger.error("PRODUCTION_DATABASE_URL not set")
        return None
    
    return compare_schemas(dev_url, prod_url)


def main():
    parser = argparse.ArgumentParser(
        description='Check database schema sync between development and production'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed column-level comparison'
    )
    parser.add_argument(
        '--json', '-j',
        action='store_true',
        help='Output results as JSON'
    )
    args = parser.parse_args()
    
    dev_url = os.environ.get('DATABASE_URL')
    prod_url = os.environ.get('PRODUCTION_DATABASE_URL')
    
    if not dev_url:
        logger.error("DATABASE_URL not set")
        sys.exit(2)
    
    if not prod_url:
        logger.error("PRODUCTION_DATABASE_URL not set")
        sys.exit(2)
    
    logger.info("=" * 60)
    logger.info("Database Schema Sync Check")
    logger.info("=" * 60)
    
    results = compare_schemas(dev_url, prod_url, verbose=args.verbose)
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        logger.info("")
        logger.info("-" * 60)
        logger.info("RESULTS")
        logger.info("-" * 60)
        
        if results['sync_status'] == 'synced':
            logger.info("✅ Databases are IN SYNC")
        elif results['sync_status'] == 'out_of_sync':
            logger.warning("⚠️  Databases are OUT OF SYNC")
            
            if not results['alembic']['revisions_match']:
                logger.warning(f"   Alembic revisions differ:")
                logger.warning(f"     Dev:  {results['alembic']['dev_revision']}")
                logger.warning(f"     Prod: {results['alembic']['prod_revision']}")
            
            if results['tables']['dev_only']:
                logger.warning(f"   Tables only in dev: {results['tables']['dev_only']}")
            if results['tables']['prod_only']:
                logger.warning(f"   Tables only in prod: {results['tables']['prod_only']}")
            
            if not results['alembic']['prod_at_head']:
                logger.info("")
                logger.info("   To sync production, run:")
                logger.info("   python run_production_migrations.py")
        else:
            logger.error("❌ Error checking sync status")
            for error in results['errors']:
                logger.error(f"   {error}")
    
    # Exit with appropriate code
    if results['sync_status'] == 'synced':
        sys.exit(0)
    elif results['sync_status'] == 'out_of_sync':
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == '__main__':
    main()

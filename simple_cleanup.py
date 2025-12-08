#!/usr/bin/env python3
"""
Simple Production Database Cleanup Script
Deletes ALL data except admin users, using batch deletion to prevent timeouts.
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BATCH_SIZE = 10000

TABLES_TO_CLEAR = [
    'bill_return_event',
    'return_ticket_bag', 
    'return_ticket',
    'scan',
    'audit_log',
    'notification',
    'promotionrequest',
    'statistics_cache',
    'bill_bag',
    'link',
    'bill',
    'bag',
]

def get_connection():
    """Get production database connection"""
    from sqlalchemy import create_engine
    
    prod_url = os.environ.get('PRODUCTION_DATABASE_URL')
    if not prod_url:
        logger.error("PRODUCTION_DATABASE_URL not set!")
        sys.exit(1)
    
    engine = create_engine(prod_url, pool_pre_ping=True)
    return engine

def table_exists(conn, table_name):
    """Check if table exists"""
    from sqlalchemy import text
    result = conn.execute(text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = :table)"
    ), {'table': table_name})
    return result.scalar()

def get_count(conn, table_name):
    """Get row count for a table"""
    from sqlalchemy import text
    result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
    return result.scalar()

def batch_delete_table(conn, table_name):
    """Delete all rows from a table in batches"""
    from sqlalchemy import text
    
    if not table_exists(conn, table_name):
        logger.info(f"  {table_name}: table does not exist, skipping")
        return 0
    
    total_deleted = 0
    
    while True:
        result = conn.execute(text(f'''
            DELETE FROM "{table_name}" 
            WHERE ctid IN (
                SELECT ctid FROM "{table_name}" LIMIT {BATCH_SIZE}
            )
        '''))
        conn.commit()
        
        deleted = result.rowcount
        total_deleted += deleted
        
        if deleted > 0:
            logger.info(f"  {table_name}: deleted {total_deleted} rows so far...")
        
        if deleted < BATCH_SIZE:
            break
    
    return total_deleted

def batch_delete_users_except_admins(conn):
    """Delete all users except admin/superadmin"""
    from sqlalchemy import text
    
    result = conn.execute(text('''
        SELECT id, username FROM "user" WHERE role = 'admin' OR username IN ('admin', 'superadmin')
    '''))
    admin_users = result.fetchall()
    admin_ids = [u[0] for u in admin_users]
    admin_names = [u[1] for u in admin_users]
    
    logger.info(f"  Preserving {len(admin_ids)} admin users: {admin_names}")
    
    if not admin_ids:
        logger.warning("  No admin users found! Aborting user deletion for safety.")
        return 0
    
    total_deleted = 0
    id_list = ','.join(str(id) for id in admin_ids)
    
    while True:
        result = conn.execute(text(f'''
            DELETE FROM "user" 
            WHERE id NOT IN ({id_list})
            AND ctid IN (
                SELECT ctid FROM "user" WHERE id NOT IN ({id_list}) LIMIT {BATCH_SIZE}
            )
        '''))
        conn.commit()
        
        deleted = result.rowcount
        total_deleted += deleted
        
        if deleted > 0:
            logger.info(f"  user: deleted {total_deleted} rows so far...")
        
        if deleted < BATCH_SIZE:
            break
    
    return total_deleted

def main():
    dry_run = '--execute' not in sys.argv
    
    logger.info("=" * 70)
    logger.info("SIMPLE PRODUCTION CLEANUP")
    logger.info("=" * 70)
    logger.info(f"Mode: {'DRY-RUN (preview)' if dry_run else 'EXECUTE (will delete!)'}")
    logger.info(f"Batch size: {BATCH_SIZE} rows")
    logger.info("")
    
    engine = get_connection()
    
    with engine.connect() as conn:
        logger.info("Connected to production database")
        logger.info("")
        
        logger.info("-" * 70)
        logger.info("CURRENT COUNTS")
        logger.info("-" * 70)
        
        for table in TABLES_TO_CLEAR + ['user']:
            if table_exists(conn, table):
                count = get_count(conn, table)
                logger.info(f"  {table}: {count} rows")
            else:
                logger.info(f"  {table}: (table does not exist)")
        
        logger.info("")
        
        if dry_run:
            logger.info("=" * 70)
            logger.info("DRY-RUN COMPLETE - No data was deleted")
            logger.info("To execute: python simple_cleanup.py --execute")
            logger.info("=" * 70)
            return
        
        print("\n" + "!" * 70)
        print("WARNING: This will DELETE ALL production data except admin users!")
        print("!" * 70 + "\n")
        
        confirm = input("Type 'DELETE ALL' to confirm: ")
        if confirm != 'DELETE ALL':
            logger.info("Cancelled.")
            return
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("EXECUTING CLEANUP...")
        logger.info("=" * 70)
        
        total_deleted = 0
        
        for table in TABLES_TO_CLEAR:
            deleted = batch_delete_table(conn, table)
            total_deleted += deleted
            if deleted > 0:
                logger.info(f"  ✓ {table}: {deleted} rows deleted")
        
        user_deleted = batch_delete_users_except_admins(conn)
        total_deleted += user_deleted
        if user_deleted > 0:
            logger.info(f"  ✓ user: {user_deleted} rows deleted")
        
        logger.info("")
        logger.info("=" * 70)
        logger.info(f"CLEANUP COMPLETE - {total_deleted} total rows deleted")
        logger.info("=" * 70)
        
        logger.info("")
        logger.info("POST-CLEANUP COUNTS:")
        for table in TABLES_TO_CLEAR + ['user']:
            if table_exists(conn, table):
                count = get_count(conn, table)
                logger.info(f"  {table}: {count} rows")

if __name__ == '__main__':
    main()

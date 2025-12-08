#!/usr/bin/env python3
"""
Simple Production Database Cleanup Script
Deletes ALL data except admin users, using batch deletion to prevent timeouts.
Resets ID sequences and runs VACUUM ANALYZE for optimal performance.
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

TABLES_WITH_SEQUENCES = [
    'bill_return_event',
    'return_ticket_bag',
    'return_ticket',
    'scan',
    'audit_log',
    'notification',
    'promotionrequest',
    'bill_bag',
    'link',
    'bill',
    'bag',
]

PROTECTED_TABLES = ['alembic_version']

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

def sequence_exists(conn, seq_name):
    """Check if sequence exists"""
    from sqlalchemy import text
    result = conn.execute(text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.sequences WHERE sequence_name = :seq)"
    ), {'seq': seq_name})
    return result.scalar()

def get_count(conn, table_name):
    """Get row count for a table"""
    from sqlalchemy import text
    result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
    return result.scalar()

def get_max_id(conn, table_name):
    """Get max ID from a table"""
    from sqlalchemy import text
    result = conn.execute(text(f'SELECT COALESCE(MAX(id), 0) FROM "{table_name}"'))
    return result.scalar()

def batch_delete_table(conn, table_name):
    """Delete all rows from a table in batches"""
    from sqlalchemy import text
    
    if table_name in PROTECTED_TABLES:
        logger.info(f"  {table_name}: PROTECTED - skipping")
        return 0
    
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
        SELECT id, username, role, email FROM "user" 
        WHERE role = 'admin' OR username IN ('admin', 'superadmin')
    '''))
    admin_users = result.fetchall()
    admin_ids = [u[0] for u in admin_users]
    
    logger.info("")
    logger.info("-" * 70)
    logger.info("ADMIN USERS TO PRESERVE (will NOT be deleted)")
    logger.info("-" * 70)
    for user in admin_users:
        logger.info(f"  ID: {user[0]}, Username: {user[1]}, Role: {user[2]}, Email: {user[3]}")
    logger.info("-" * 70)
    logger.info("")
    
    if not admin_ids:
        logger.warning("  No admin users found! Aborting user deletion for safety.")
        return 0, []
    
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
    
    return total_deleted, admin_ids

def reset_sequence(conn, table_name, restart_value=1):
    """Reset the ID sequence for a table"""
    from sqlalchemy import text
    
    seq_name = f"{table_name}_id_seq"
    
    if not sequence_exists(conn, seq_name):
        return False
    
    try:
        conn.execute(text(f'ALTER SEQUENCE "{seq_name}" RESTART WITH {restart_value}'))
        conn.commit()
        return True
    except Exception as e:
        logger.warning(f"  Could not reset {seq_name}: {e}")
        return False

def reset_all_sequences(conn, preserved_user_ids):
    """Reset all ID sequences after cleanup"""
    from sqlalchemy import text
    
    logger.info("")
    logger.info("-" * 70)
    logger.info("RESETTING ID SEQUENCES")
    logger.info("-" * 70)
    
    for table in TABLES_WITH_SEQUENCES:
        if table_exists(conn, table):
            if reset_sequence(conn, table, 1):
                logger.info(f"  ✓ {table}_id_seq reset to 1")
    
    if preserved_user_ids:
        max_user_id = max(preserved_user_ids)
        next_id = max_user_id + 1
        if reset_sequence(conn, 'user', next_id):
            logger.info(f"  ✓ user_id_seq reset to {next_id} (after max preserved ID: {max_user_id})")
    
    logger.info("")

def run_vacuum_analyze(engine):
    """Run VACUUM ANALYZE to reclaim space and update statistics"""
    
    logger.info("-" * 70)
    logger.info("RUNNING VACUUM ANALYZE (reclaiming disk space)")
    logger.info("-" * 70)
    
    raw_conn = engine.raw_connection()
    try:
        raw_conn.set_isolation_level(0)
        cursor = raw_conn.cursor()
        
        for table in TABLES_TO_CLEAR + ['user']:
            try:
                cursor.execute(f'VACUUM ANALYZE "{table}"')
                logger.info(f"  ✓ {table}: vacuumed and analyzed")
            except Exception as e:
                logger.warning(f"  ⚠ {table}: {e}")
        
        cursor.close()
    finally:
        raw_conn.close()
    
    logger.info("")

def main():
    dry_run = '--execute' not in sys.argv
    
    logger.info("=" * 70)
    logger.info("SIMPLE PRODUCTION CLEANUP")
    logger.info("=" * 70)
    logger.info(f"Mode: {'DRY-RUN (preview)' if dry_run else 'EXECUTE (will delete!)'}")
    logger.info(f"Batch size: {BATCH_SIZE} rows")
    logger.info(f"Protected tables: {PROTECTED_TABLES}")
    logger.info("")
    
    engine = get_connection()
    
    with engine.connect() as conn:
        logger.info("Connected to production database")
        logger.info("")
        
        from sqlalchemy import text
        result = conn.execute(text('''
            SELECT id, username, role FROM "user" 
            WHERE role = 'admin' OR username IN ('admin', 'superadmin')
        '''))
        admin_users = result.fetchall()
        
        logger.info("-" * 70)
        logger.info("ADMIN USERS THAT WILL BE PRESERVED")
        logger.info("-" * 70)
        for user in admin_users:
            logger.info(f"  ID: {user[0]}, Username: {user[1]}, Role: {user[2]}")
        if not admin_users:
            logger.error("  NO ADMIN USERS FOUND! Cannot proceed safely.")
            sys.exit(1)
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
        print("It will also RESET all ID sequences so new records start from ID 1.")
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
        
        user_deleted, admin_ids = batch_delete_users_except_admins(conn)
        total_deleted += user_deleted
        if user_deleted > 0:
            logger.info(f"  ✓ user: {user_deleted} rows deleted")
        
        reset_all_sequences(conn, admin_ids)
    
    run_vacuum_analyze(engine)
    
    with engine.connect() as conn:
        logger.info("=" * 70)
        logger.info(f"CLEANUP COMPLETE - {total_deleted} total rows deleted")
        logger.info("=" * 70)
        
        logger.info("")
        logger.info("POST-CLEANUP COUNTS:")
        for table in TABLES_TO_CLEAR + ['user']:
            if table_exists(conn, table):
                count = get_count(conn, table)
                logger.info(f"  {table}: {count} rows")
        
        logger.info("")
        logger.info("NEXT STEPS:")
        logger.info("  Run the SQL in insert_600_parent_bags.sql via pgAdmin to add parent bags")
        logger.info("  New bags will start from ID 1")

if __name__ == '__main__':
    main()

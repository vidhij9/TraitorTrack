#!/usr/bin/env python3
"""
Safe Production Database Cleanup Script

This script safely deletes production data while preserving:
- Superadmin user(s)
- Parent bags M444-00001 to M444-00600
- All child bags linked to those parent bags
- All bills linked to those parent bags
- All related scans, links, and bill_bags for preserved data

SAFETY FEATURES:
- Runs in DRY-RUN mode by default (shows what would be deleted)
- Requires explicit --execute flag to perform deletions
- Uses a single transaction with rollback on error
- Creates a summary report before and after

Usage:
    python safe_production_cleanup.py              # Dry-run mode (shows counts)
    python safe_production_cleanup.py --execute    # Actually delete data
    python safe_production_cleanup.py --help       # Show help

Environment Variables:
    PRODUCTION_DATABASE_URL - Production database connection string
"""

import os
import sys
import argparse
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('production_cleanup')


def get_database_url():
    """Get production database URL"""
    url = os.environ.get('PRODUCTION_DATABASE_URL')
    if not url:
        logger.error("PRODUCTION_DATABASE_URL not set")
        logger.error("This script ONLY operates on production database for safety")
        return None
    return url


def get_preserved_parent_qr_ids():
    """Generate list of parent bag QR IDs to preserve: M444-00001 to M444-00600"""
    preserved = []
    for i in range(1, 601):  # 1 to 600 inclusive
        qr_id = f"M444-{i:05d}"  # Format: M444-00001, M444-00002, etc.
        preserved.append(qr_id)
    return preserved


def run_cleanup(execute=False):
    """
    Perform the cleanup operation.
    
    Args:
        execute: If True, actually delete data. If False, dry-run mode.
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    
    database_url = get_database_url()
    if not database_url:
        return False
    
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False
    )
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        logger.info("=" * 70)
        logger.info("PRODUCTION DATABASE CLEANUP")
        logger.info("=" * 70)
        logger.info(f"Mode: {'EXECUTE (will delete data)' if execute else 'DRY-RUN (preview only)'}")
        logger.info("")
        
        # Test connection
        session.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        
        # Get preserved parent bag QR IDs
        preserved_qr_ids = get_preserved_parent_qr_ids()
        logger.info(f"Preserving parent bags: M444-00001 to M444-00600 ({len(preserved_qr_ids)} bags)")
        
        # Step 1: Get IDs of preserved parent bags
        result = session.execute(text("""
            SELECT id, qr_id FROM bag 
            WHERE type = 'parent' 
            AND qr_id = ANY(:qr_ids)
        """), {'qr_ids': preserved_qr_ids})
        preserved_parent_bags = {row[0]: row[1] for row in result.fetchall()}
        preserved_parent_ids = list(preserved_parent_bags.keys())
        logger.info(f"Found {len(preserved_parent_ids)} preserved parent bags in database")
        
        # Step 2: Get IDs of child bags linked to preserved parents
        if preserved_parent_ids:
            result = session.execute(text("""
                SELECT DISTINCT child_bag_id FROM link 
                WHERE parent_bag_id = ANY(:parent_ids)
            """), {'parent_ids': preserved_parent_ids})
            preserved_child_ids = [row[0] for row in result.fetchall()]
        else:
            preserved_child_ids = []
        logger.info(f"Found {len(preserved_child_ids)} child bags linked to preserved parents")
        
        # Step 3: Get IDs of bills linked to preserved parent bags
        if preserved_parent_ids:
            result = session.execute(text("""
                SELECT DISTINCT bill_id FROM bill_bag 
                WHERE bag_id = ANY(:parent_ids)
            """), {'parent_ids': preserved_parent_ids})
            preserved_bill_ids = [row[0] for row in result.fetchall()]
        else:
            preserved_bill_ids = []
        logger.info(f"Found {len(preserved_bill_ids)} bills linked to preserved parent bags")
        
        # Step 4: Get superadmin user ID(s)
        result = session.execute(text("""
            SELECT id, username FROM "user" WHERE role = 'admin'
        """))
        admin_users = {row[0]: row[1] for row in result.fetchall()}
        preserved_user_ids = list(admin_users.keys())
        logger.info(f"Found {len(preserved_user_ids)} admin users to preserve: {list(admin_users.values())}")
        
        # Combine all preserved bag IDs
        all_preserved_bag_ids = list(set(preserved_parent_ids + preserved_child_ids))
        
        logger.info("")
        logger.info("-" * 70)
        logger.info("PRE-CLEANUP COUNTS")
        logger.info("-" * 70)
        
        # Get current counts - check which tables exist first
        all_tables = [
            'user', 'bag', 'link', 'bill', 'bill_bag', 'scan',
            'audit_log', 'notification', 'promotionrequest',
            'return_ticket', 'return_ticket_bag', 'bill_return_event',
            'statistics_cache'
        ]
        
        # Check which tables exist
        result = session.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """))
        existing_tables = {row[0] for row in result.fetchall()}
        
        current_counts = {}
        for table in all_tables:
            if table in existing_tables:
                result = session.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                count = result.scalar()
                current_counts[table] = count
                logger.info(f"  {table}: {count}")
            else:
                current_counts[table] = 0
                logger.info(f"  {table}: (table does not exist)")
        
        logger.info("")
        logger.info("-" * 70)
        logger.info("DELETION PLAN")
        logger.info("-" * 70)
        
        # Calculate what will be deleted (only for existing tables)
        deletion_counts = {}
        
        # BillReturnEvent - delete all not linked to preserved bills or bags
        if 'bill_return_event' in existing_tables:
            if preserved_bill_ids:
                result = session.execute(text("""
                    SELECT COUNT(*) FROM bill_return_event 
                    WHERE bill_id != ALL(:bill_ids) OR bill_id IS NULL
                """), {'bill_ids': preserved_bill_ids})
            else:
                result = session.execute(text("SELECT COUNT(*) FROM bill_return_event"))
            deletion_counts['bill_return_event'] = result.scalar()
        else:
            deletion_counts['bill_return_event'] = 0
        
        # ReturnTicketBag - delete all not linked to preserved bags
        if 'return_ticket_bag' in existing_tables:
            if all_preserved_bag_ids:
                result = session.execute(text("""
                    SELECT COUNT(*) FROM return_ticket_bag 
                    WHERE bag_id != ALL(:bag_ids) OR bag_id IS NULL
                """), {'bag_ids': all_preserved_bag_ids})
            else:
                result = session.execute(text("SELECT COUNT(*) FROM return_ticket_bag"))
            deletion_counts['return_ticket_bag'] = result.scalar()
        else:
            deletion_counts['return_ticket_bag'] = 0
        
        # ReturnTicket - delete all (no preservation needed for return tickets)
        if 'return_ticket' in existing_tables:
            result = session.execute(text("SELECT COUNT(*) FROM return_ticket"))
            deletion_counts['return_ticket'] = result.scalar()
        else:
            deletion_counts['return_ticket'] = 0
        
        # Scan - delete all not linked to preserved bags
        if 'scan' in existing_tables:
            if all_preserved_bag_ids:
                result = session.execute(text("""
                    SELECT COUNT(*) FROM scan 
                    WHERE (parent_bag_id IS NULL OR parent_bag_id != ALL(:bag_ids))
                    AND (child_bag_id IS NULL OR child_bag_id != ALL(:bag_ids))
                """), {'bag_ids': all_preserved_bag_ids})
            else:
                result = session.execute(text("SELECT COUNT(*) FROM scan"))
            deletion_counts['scan'] = result.scalar()
        else:
            deletion_counts['scan'] = 0
        
        # AuditLog - delete all (audit history not preserved)
        if 'audit_log' in existing_tables:
            result = session.execute(text("SELECT COUNT(*) FROM audit_log"))
            deletion_counts['audit_log'] = result.scalar()
        else:
            deletion_counts['audit_log'] = 0
        
        # Notification - delete all
        if 'notification' in existing_tables:
            result = session.execute(text("SELECT COUNT(*) FROM notification"))
            deletion_counts['notification'] = result.scalar()
        else:
            deletion_counts['notification'] = 0
        
        # PromotionRequest - delete all
        if 'promotionrequest' in existing_tables:
            result = session.execute(text("SELECT COUNT(*) FROM promotionrequest"))
            deletion_counts['promotionrequest'] = result.scalar()
        else:
            deletion_counts['promotionrequest'] = 0
        
        # StatisticsCache - delete all (will be regenerated)
        if 'statistics_cache' in existing_tables:
            result = session.execute(text("SELECT COUNT(*) FROM statistics_cache"))
            deletion_counts['statistics_cache'] = result.scalar()
        else:
            deletion_counts['statistics_cache'] = 0
        
        # BillBag - delete all not linking preserved bills to preserved bags
        if preserved_bill_ids and preserved_parent_ids:
            result = session.execute(text("""
                SELECT COUNT(*) FROM bill_bag 
                WHERE bill_id != ALL(:bill_ids) OR bag_id != ALL(:bag_ids)
            """), {'bill_ids': preserved_bill_ids, 'bag_ids': preserved_parent_ids})
        else:
            result = session.execute(text("SELECT COUNT(*) FROM bill_bag"))
        deletion_counts['bill_bag'] = result.scalar()
        
        # Link - delete all not linking preserved parent to child bags
        if preserved_parent_ids:
            result = session.execute(text("""
                SELECT COUNT(*) FROM link 
                WHERE parent_bag_id != ALL(:parent_ids)
            """), {'parent_ids': preserved_parent_ids})
        else:
            result = session.execute(text("SELECT COUNT(*) FROM link"))
        deletion_counts['link'] = result.scalar()
        
        # Bill - delete all not in preserved
        if preserved_bill_ids:
            result = session.execute(text("""
                SELECT COUNT(*) FROM bill WHERE id != ALL(:bill_ids)
            """), {'bill_ids': preserved_bill_ids})
        else:
            result = session.execute(text("SELECT COUNT(*) FROM bill"))
        deletion_counts['bill'] = result.scalar()
        
        # Bag - delete all not in preserved
        if all_preserved_bag_ids:
            result = session.execute(text("""
                SELECT COUNT(*) FROM bag WHERE id != ALL(:bag_ids)
            """), {'bag_ids': all_preserved_bag_ids})
        else:
            result = session.execute(text("SELECT COUNT(*) FROM bag"))
        deletion_counts['bag'] = result.scalar()
        
        # User - delete all non-admin users
        if preserved_user_ids:
            result = session.execute(text("""
                SELECT COUNT(*) FROM "user" WHERE id != ALL(:user_ids)
            """), {'user_ids': preserved_user_ids})
        else:
            result = session.execute(text('SELECT COUNT(*) FROM "user"'))
        deletion_counts['user'] = result.scalar()
        
        for table, count in deletion_counts.items():
            logger.info(f"  {table}: {count} rows to delete")
        
        total_deletions = sum(deletion_counts.values())
        logger.info(f"\n  TOTAL: {total_deletions} rows to delete")
        
        if not execute:
            logger.info("")
            logger.info("=" * 70)
            logger.info("DRY-RUN COMPLETE - No data was deleted")
            logger.info("To execute the cleanup, run: python safe_production_cleanup.py --execute")
            logger.info("=" * 70)
            session.rollback()
            return True
        
        # EXECUTE MODE - Actually delete data
        logger.info("")
        logger.info("=" * 70)
        logger.info("EXECUTING CLEANUP...")
        logger.info("=" * 70)
        
        # Delete in correct order (respecting foreign key constraints)
        
        # 1. BillReturnEvent
        if 'bill_return_event' in existing_tables:
            if preserved_bill_ids:
                session.execute(text("""
                    DELETE FROM bill_return_event 
                    WHERE bill_id != ALL(:bill_ids) OR bill_id IS NULL
                """), {'bill_ids': preserved_bill_ids})
            else:
                session.execute(text("DELETE FROM bill_return_event"))
            logger.info("  Deleted bill_return_event records")
        
        # 2. ReturnTicketBag
        if 'return_ticket_bag' in existing_tables:
            if all_preserved_bag_ids:
                session.execute(text("""
                    DELETE FROM return_ticket_bag 
                    WHERE bag_id != ALL(:bag_ids) OR bag_id IS NULL
                """), {'bag_ids': all_preserved_bag_ids})
            else:
                session.execute(text("DELETE FROM return_ticket_bag"))
            logger.info("  Deleted return_ticket_bag records")
        
        # 3. ReturnTicket
        if 'return_ticket' in existing_tables:
            session.execute(text("DELETE FROM return_ticket"))
            logger.info("  Deleted return_ticket records")
        
        # 4. Scan - must delete before bag
        if 'scan' in existing_tables:
            if all_preserved_bag_ids:
                session.execute(text("""
                    DELETE FROM scan 
                    WHERE (parent_bag_id IS NULL OR parent_bag_id != ALL(:bag_ids))
                    AND (child_bag_id IS NULL OR child_bag_id != ALL(:bag_ids))
                """), {'bag_ids': all_preserved_bag_ids})
            else:
                session.execute(text("DELETE FROM scan"))
            logger.info("  Deleted scan records")
        
        # 5. AuditLog
        if 'audit_log' in existing_tables:
            session.execute(text("DELETE FROM audit_log"))
            logger.info("  Deleted audit_log records")
        
        # 6. Notification
        if 'notification' in existing_tables:
            session.execute(text("DELETE FROM notification"))
            logger.info("  Deleted notification records")
        
        # 7. PromotionRequest
        if 'promotionrequest' in existing_tables:
            session.execute(text("DELETE FROM promotionrequest"))
            logger.info("  Deleted promotionrequest records")
        
        # 8. StatisticsCache
        if 'statistics_cache' in existing_tables:
            session.execute(text("DELETE FROM statistics_cache"))
            logger.info("  Deleted statistics_cache records")
        
        # 9. BillBag - delete links for non-preserved bills/bags
        if preserved_bill_ids and preserved_parent_ids:
            session.execute(text("""
                DELETE FROM bill_bag 
                WHERE bill_id != ALL(:bill_ids) OR bag_id != ALL(:bag_ids)
            """), {'bill_ids': preserved_bill_ids, 'bag_ids': preserved_parent_ids})
        else:
            session.execute(text("DELETE FROM bill_bag"))
        logger.info("  Deleted bill_bag records")
        
        # 10. Link - delete links for non-preserved parent bags
        if preserved_parent_ids:
            session.execute(text("""
                DELETE FROM link WHERE parent_bag_id != ALL(:parent_ids)
            """), {'parent_ids': preserved_parent_ids})
        else:
            session.execute(text("DELETE FROM link"))
        logger.info("  Deleted link records")
        
        # 11. Bill - delete non-preserved bills
        if preserved_bill_ids:
            session.execute(text("""
                DELETE FROM bill WHERE id != ALL(:bill_ids)
            """), {'bill_ids': preserved_bill_ids})
        else:
            session.execute(text("DELETE FROM bill"))
        logger.info("  Deleted bill records")
        
        # 12. Bag - delete non-preserved bags
        if all_preserved_bag_ids:
            session.execute(text("""
                DELETE FROM bag WHERE id != ALL(:bag_ids)
            """), {'bag_ids': all_preserved_bag_ids})
        else:
            session.execute(text("DELETE FROM bag"))
        logger.info("  Deleted bag records")
        
        # 13. User - delete non-admin users
        if preserved_user_ids:
            session.execute(text("""
                DELETE FROM "user" WHERE id != ALL(:user_ids)
            """), {'user_ids': preserved_user_ids})
        else:
            logger.warning("  No admin users found - skipping user deletion to preserve data integrity")
        logger.info("  Deleted user records")
        
        # Commit the transaction
        session.commit()
        logger.info("")
        logger.info("Transaction committed successfully")
        
        # Post-cleanup counts
        logger.info("")
        logger.info("-" * 70)
        logger.info("POST-CLEANUP COUNTS")
        logger.info("-" * 70)
        
        for table in all_tables:
            if table in existing_tables:
                result = session.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                count = result.scalar()
                logger.info(f"  {table}: {count}")
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("CLEANUP COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)
        return True
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        session.rollback()
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(
        description='Safely clean production database while preserving specific data'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually execute the cleanup. Without this flag, runs in dry-run mode.'
    )
    args = parser.parse_args()
    
    if args.execute:
        print("\n" + "!" * 70)
        print("WARNING: This will DELETE production data!")
        print("Preserved data: superadmin user, M444-00001 to M444-00600 parent bags")
        print("and their related child bags, bills, links, bill_bags, and scans")
        print("!" * 70)
        confirmation = input("\nType 'DELETE PRODUCTION DATA' to confirm: ")
        if confirmation != 'DELETE PRODUCTION DATA':
            print("Aborted. No data was deleted.")
            sys.exit(1)
    
    success = run_cleanup(execute=args.execute)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

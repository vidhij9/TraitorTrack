#!/usr/bin/env python3
"""
Production Database Fix Script
Run this script to prepare an existing production database for migrations.
This script adds missing columns and syncs the schema with the code.
"""

import os
import sys
import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import ProgrammingError

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def add_column_if_missing(conn, inspector, table_name, col_name, col_type, default_value=None):
    """Helper to safely add a column if it doesn't exist."""
    existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
    
    if col_name not in existing_columns:
        try:
            sql = text(f'ALTER TABLE "{table_name}" ADD COLUMN {col_name} {col_type}')
            conn.execute(sql)
            conn.commit()
            logger.info(f"✅ Added column: {table_name}.{col_name}")
            return True
        except ProgrammingError as e:
            if 'already exists' in str(e):
                logger.info(f"✓ Column already exists: {table_name}.{col_name}")
                return False
            else:
                raise
    else:
        logger.info(f"✓ Column already exists: {table_name}.{col_name}")
        return False


def fix_production_database():
    """
    Prepare production database for safe migration by:
    1. Adding missing columns to user table
    2. Adding missing columns to bill table (CRITICAL for bill management)
    3. Backfilling precomputed values for bills
    4. Stamping the database with the correct migration version
    """
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("❌ DATABASE_URL environment variable not set!")
        return False
    
    # Replace postgres:// with postgresql:// for SQLAlchemy compatibility
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    try:
        # Create engine and connect
        engine = create_engine(database_url)
        inspector = inspect(engine)
        
        with engine.connect() as conn:
            # Step 1: Check if required tables exist
            tables = inspector.get_table_names()
            if 'user' not in tables:
                logger.error("❌ User table not found in database!")
                return False
            if 'bill' not in tables:
                logger.error("❌ Bill table not found in database!")
                return False
            
            logger.info("="*60)
            logger.info("STEP 1: Fixing USER table columns")
            logger.info("="*60)
            
            # User table columns
            user_columns = [
                ('failed_login_attempts', 'INTEGER DEFAULT 0'),
                ('locked_until', 'TIMESTAMP'),
                ('last_failed_login', 'TIMESTAMP'),
                ('password_reset_token', 'VARCHAR(100)'),
                ('password_reset_token_expires', 'TIMESTAMP'),
                ('totp_secret', 'VARCHAR(32)'),
                ('two_fa_enabled', 'BOOLEAN DEFAULT FALSE')
            ]
            
            for col_name, col_type in user_columns:
                add_column_if_missing(conn, inspector, 'user', col_name, col_type)
            
            logger.info("\n" + "="*60)
            logger.info("STEP 2: Fixing BILL table columns (CRITICAL)")
            logger.info("="*60)
            
            # Bill table columns - CRITICAL for bill management to work
            bill_columns = [
                ('linked_parent_count', 'INTEGER DEFAULT 0'),
                ('total_child_bags', 'INTEGER DEFAULT 0'),
                ('total_weight_kg', 'DOUBLE PRECISION DEFAULT 0.0'),
                ('expected_weight_kg', 'DOUBLE PRECISION DEFAULT 0.0'),
            ]
            
            bill_columns_added = []
            for col_name, col_type in bill_columns:
                if add_column_if_missing(conn, inspector, 'bill', col_name, col_type):
                    bill_columns_added.append(col_name)
            
            # Step 3: Backfill bill precomputed values if columns were added
            if bill_columns_added:
                logger.info("\n" + "="*60)
                logger.info("STEP 3: Backfilling bill precomputed values")
                logger.info("="*60)
                
                # Backfill linked_parent_count
                if 'linked_parent_count' in bill_columns_added:
                    logger.info("Backfilling linked_parent_count...")
                    conn.execute(text("""
                        UPDATE bill b SET linked_parent_count = COALESCE((
                            SELECT COUNT(*) FROM bill_bag bb WHERE bb.bill_id = b.id
                        ), 0)
                    """))
                    conn.commit()
                    logger.info("✅ Backfilled linked_parent_count")
                
                # Backfill total_child_bags
                if 'total_child_bags' in bill_columns_added:
                    logger.info("Backfilling total_child_bags...")
                    conn.execute(text("""
                        UPDATE bill b SET total_child_bags = COALESCE((
                            SELECT COUNT(DISTINCT l.child_bag_id)
                            FROM bill_bag bb
                            JOIN bag parent ON bb.bag_id = parent.id AND parent.type = 'parent'
                            JOIN link l ON parent.id = l.parent_bag_id
                            WHERE bb.bill_id = b.id
                        ), 0)
                    """))
                    conn.commit()
                    logger.info("✅ Backfilled total_child_bags")
                
                # Backfill total_weight_kg
                if 'total_weight_kg' in bill_columns_added:
                    logger.info("Backfilling total_weight_kg...")
                    conn.execute(text("""
                        UPDATE bill SET total_weight_kg = COALESCE(total_child_bags, 0) * 1.0
                    """))
                    conn.commit()
                    logger.info("✅ Backfilled total_weight_kg")
                
                # Backfill expected_weight_kg
                if 'expected_weight_kg' in bill_columns_added:
                    logger.info("Backfilling expected_weight_kg...")
                    conn.execute(text("""
                        UPDATE bill b SET expected_weight_kg = COALESCE((
                            SELECT SUM(
                                CASE 
                                    WHEN parent.qr_id ~ '^M[0-9]{3,4}-[0-9]+' THEN 15.0
                                    ELSE 30.0
                                END
                            )
                            FROM bill_bag bb
                            JOIN bag parent ON bb.bag_id = parent.id AND parent.type = 'parent'
                            WHERE bb.bill_id = b.id
                        ), 0.0)
                    """))
                    conn.commit()
                    logger.info("✅ Backfilled expected_weight_kg")
            else:
                logger.info("✓ All bill columns already exist, no backfill needed")
            
            # Step 4: Create alembic_version table if it doesn't exist
            logger.info("\n" + "="*60)
            logger.info("STEP 4: Updating migration version")
            logger.info("="*60)
            
            if 'alembic_version' not in tables:
                conn.execute(text("""
                    CREATE TABLE alembic_version (
                        version_num VARCHAR(32) NOT NULL PRIMARY KEY
                    )
                """))
                conn.commit()
                logger.info("✅ Created alembic_version table")
            
            # Check current alembic version
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            current = result.fetchone()
            
            target_revision = 'f2g3h4i5j6k7'  # The latest migration that includes all bill columns
            
            if current and current[0] == target_revision:
                logger.info(f"✅ Database already at target revision: {target_revision}")
            else:
                # Stamp database with target revision
                conn.execute(text("DELETE FROM alembic_version"))
                conn.execute(text("INSERT INTO alembic_version (version_num) VALUES (:rev)"), 
                           {'rev': target_revision})
                conn.commit()
                logger.info(f"✅ Stamped database with revision: {target_revision}")
            
            logger.info("\n" + "="*60)
            logger.info("✅ PRODUCTION DATABASE FIX COMPLETED SUCCESSFULLY!")
            logger.info("="*60)
            logger.info("\nThe database now has:")
            logger.info("1. All required columns in the user table")
            logger.info("2. All required columns in the bill table")
            logger.info("3. Precomputed values backfilled for bills")
            logger.info("4. Correct migration version stamped")
            logger.info("\nYou can now safely republish your application.")
            logger.info("="*60)
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Check if we're in production
    is_production = (
        os.environ.get('REPLIT_DEPLOYMENT') == '1' or
        os.environ.get('REPLIT_ENVIRONMENT') == 'production'
    )
    
    if not is_production:
        logger.warning("⚠️  This script should only be run in production environment!")
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Script cancelled.")
            sys.exit(0)
    
    success = fix_production_database()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Production Database Fix Script
Run this script to prepare an existing production database for migrations.
This script should be run ONCE before republishing the app.
"""

import os
import sys
import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import ProgrammingError

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_production_database():
    """
    Prepare production database for safe migration by:
    1. Adding missing columns to user table
    2. Stamping the database with the correct migration version
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
            # Step 1: Check if user table exists
            tables = inspector.get_table_names()
            if 'user' not in tables:
                logger.error("❌ User table not found in database!")
                return False
            
            # Step 2: Get existing columns
            existing_columns = [col['name'] for col in inspector.get_columns('user')]
            logger.info(f"Existing user columns: {existing_columns}")
            
            # Step 3: Add missing columns (if needed)
            required_columns = [
                ('failed_login_attempts', 'INTEGER DEFAULT 0'),
                ('locked_until', 'TIMESTAMP'),
                ('last_failed_login', 'TIMESTAMP'),
                ('password_reset_token', 'VARCHAR(100)'),
                ('password_reset_token_expires', 'TIMESTAMP'),
                ('totp_secret', 'VARCHAR(32)'),
                ('two_fa_enabled', 'BOOLEAN DEFAULT FALSE')
            ]
            
            columns_added = False
            for col_name, col_type in required_columns:
                if col_name not in existing_columns:
                    try:
                        sql = text(f'ALTER TABLE "user" ADD COLUMN {col_name} {col_type}')
                        conn.execute(sql)
                        conn.commit()
                        logger.info(f"✅ Added column: {col_name}")
                        columns_added = True
                    except ProgrammingError as e:
                        if 'already exists' in str(e):
                            logger.info(f"✓ Column already exists: {col_name}")
                        else:
                            logger.error(f"❌ Failed to add column {col_name}: {str(e)}")
                            return False
                else:
                    logger.info(f"✓ Column already exists: {col_name}")
            
            # Step 4: Create alembic_version table if it doesn't exist
            if 'alembic_version' not in tables:
                conn.execute(text("""
                    CREATE TABLE alembic_version (
                        version_num VARCHAR(32) NOT NULL PRIMARY KEY
                    )
                """))
                conn.commit()
                logger.info("✅ Created alembic_version table")
            
            # Step 5: Check current alembic version
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            current = result.fetchone()
            
            target_revision = '986e81b92e8e'  # The latest migration
            
            if current and current[0] == target_revision:
                logger.info(f"✅ Database already at target revision: {target_revision}")
            else:
                # Step 6: Stamp database with target revision
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
            logger.info("2. Correct migration version stamped")
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
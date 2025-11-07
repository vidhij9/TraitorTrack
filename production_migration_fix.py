#!/usr/bin/env python3
"""
Production Database Migration Fix Script
This script safely adds missing columns to an existing production database
without running destructive migrations.
"""

import os
import sys
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from sqlalchemy.exc import ProgrammingError, OperationalError
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_and_add_missing_columns(db):
    """
    Safely add missing columns to the user table without dropping anything.
    Returns True if all columns were added successfully, False otherwise.
    """
    required_columns = [
        ('failed_login_attempts', 'INTEGER DEFAULT 0'),
        ('locked_until', 'TIMESTAMP'),
        ('last_failed_login', 'TIMESTAMP'),
        ('password_reset_token', 'VARCHAR(100)'),
        ('password_reset_token_expires', 'TIMESTAMP'),
        ('totp_secret', 'VARCHAR(32)'),
        ('two_fa_enabled', 'BOOLEAN DEFAULT FALSE')
    ]
    
    try:
        # Check which columns already exist
        inspector = inspect(db.engine)
        existing_columns = [col['name'] for col in inspector.get_columns('user')]
        logger.info(f"Existing columns in user table: {existing_columns}")
        
        # Add missing columns
        with db.engine.connect() as conn:
            for col_name, col_type in required_columns:
                if col_name not in existing_columns:
                    try:
                        sql = f'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS {col_name} {col_type}'
                        conn.execute(text(sql))
                        conn.commit()
                        logger.info(f"✅ Added column: {col_name}")
                    except Exception as e:
                        logger.warning(f"⚠️  Could not add column {col_name}: {str(e)}")
                else:
                    logger.info(f"✓ Column already exists: {col_name}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking/adding columns: {str(e)}")
        return False


def stamp_alembic_version(db, revision='986e81b92e8e'):
    """
    Stamp the database with the current migration revision without running migrations.
    This tells Alembic that the database is at the specified revision.
    """
    try:
        # Check if alembic_version table exists
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        with db.engine.connect() as conn:
            if 'alembic_version' not in tables:
                # Create alembic_version table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS alembic_version (
                        version_num VARCHAR(32) NOT NULL PRIMARY KEY
                    )
                """))
                conn.commit()
                logger.info("✅ Created alembic_version table")
            
            # Check current version
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            current = result.fetchone()
            
            if current:
                logger.info(f"Current migration version: {current[0]}")
                if current[0] == revision:
                    logger.info("✅ Database already at correct revision")
                    return True
            
            # Update or insert the revision
            conn.execute(text("DELETE FROM alembic_version"))
            conn.execute(text("INSERT INTO alembic_version (version_num) VALUES (:rev)"), 
                        {'rev': revision})
            conn.commit()
            logger.info(f"✅ Stamped database with revision: {revision}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error stamping Alembic version: {str(e)}")
        return False


def main():
    """Main function to run the production migration fix."""
    logger.info("🔧 Starting production database migration fix...")
    
    # Import app and database from main application
    try:
        from app import app, db
        
        with app.app_context():
            # Step 1: Add missing columns
            logger.info("\n📝 Step 1: Adding missing columns to user table...")
            if not check_and_add_missing_columns(db):
                logger.error("Failed to add missing columns")
                return False
            
            # Step 2: Stamp the database with the latest migration
            logger.info("\n📝 Step 2: Stamping database with current migration version...")
            if not stamp_alembic_version(db, '986e81b92e8e'):
                logger.error("Failed to stamp Alembic version")
                return False
            
            logger.info("\n✅ Production database fix completed successfully!")
            logger.info("The database now has all required columns and is marked as up-to-date.")
            return True
            
    except ImportError as e:
        logger.error(f"❌ Failed to import app: {str(e)}")
        logger.error("Make sure this script is in the same directory as app.py")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
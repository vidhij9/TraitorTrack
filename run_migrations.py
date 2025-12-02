#!/usr/bin/env python3
"""
Pre-deployment database migration script.

This script runs database migrations BEFORE the web server starts.
It's designed to be called during the build/deploy phase to avoid
blocking the server startup (which must open port 5000 within 2 minutes
for Autoscale deployments).

Usage:
    python run_migrations.py

This script:
1. Checks for pending migrations
2. Applies any pending migrations
3. Verifies critical columns exist (Bill table schema check)
4. Exits with code 0 on success, non-zero on failure
"""

import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('migrations')


def run_migrations():
    """Run database migrations and schema verification."""
    
    logger.info("=" * 60)
    logger.info("Starting pre-deployment database migrations...")
    logger.info("=" * 60)
    
    try:
        from app import app, db
        from flask_migrate import upgrade as flask_migrate_upgrade
        from alembic.script import ScriptDirectory
        from alembic.config import Config as AlembicConfig
        from alembic.migration import MigrationContext
        from sqlalchemy import inspect, text
        
        with app.app_context():
            logger.info("🔄 Checking for pending database migrations...")
            
            migrations_path = os.path.join(os.path.dirname(__file__), 'migrations')
            alembic_cfg = AlembicConfig(os.path.join(migrations_path, 'alembic.ini'))
            alembic_cfg.set_main_option('script_location', migrations_path)
            
            engine = db.engine
            conn = engine.connect()
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()
            conn.close()
            
            script = ScriptDirectory.from_config(alembic_cfg)
            head_rev = script.get_current_head()
            
            if current_rev == head_rev:
                logger.info(f"✅ Database schema is up-to-date (revision: {current_rev or 'base'})")
            else:
                logger.info(f"📝 Applying pending migrations: {current_rev or 'base'} → {head_rev}")
                flask_migrate_upgrade()
                logger.info(f"✅ Database migrations applied successfully! Current revision: {head_rev}")
            
            logger.info("🔍 Verifying Bill table schema...")
            inspector = inspect(db.engine)
            bill_columns = [col['name'] for col in inspector.get_columns('bill')]
            
            required_columns = {
                'linked_parent_count': 'INTEGER DEFAULT 0',
                'total_child_bags': 'INTEGER DEFAULT 0',
                'total_weight_kg': 'DOUBLE PRECISION DEFAULT 0.0',
                'expected_weight_kg': 'DOUBLE PRECISION DEFAULT 0.0'
            }
            
            missing_columns = [col for col in required_columns if col not in bill_columns]
            
            if missing_columns:
                logger.warning(f"⚠️  Bill table missing columns: {missing_columns}")
                logger.info("🔧 Adding missing Bill columns...")
                
                with db.engine.connect() as conn:
                    for col_name in missing_columns:
                        col_type = required_columns[col_name]
                        try:
                            conn.execute(text(f'ALTER TABLE bill ADD COLUMN {col_name} {col_type}'))
                            conn.commit()
                            logger.info(f"✅ Added missing column: bill.{col_name}")
                        except Exception as col_error:
                            if 'already exists' in str(col_error).lower():
                                logger.info(f"✓ Column bill.{col_name} already exists")
                            else:
                                logger.error(f"❌ Failed to add bill.{col_name}: {col_error}")
                    
                    if 'linked_parent_count' in missing_columns:
                        logger.info("🔄 Backfilling linked_parent_count...")
                        conn.execute(text("""
                            UPDATE bill b SET linked_parent_count = COALESCE((
                                SELECT COUNT(*) FROM bill_bag bb WHERE bb.bill_id = b.id
                            ), 0) WHERE linked_parent_count IS NULL OR linked_parent_count = 0
                        """))
                        conn.commit()
                        logger.info("✅ Backfilled linked_parent_count")
                
                logger.info("✅ Bill table schema fix completed")
            else:
                logger.info("✅ Bill table has all required columns")
            
            logger.info("=" * 60)
            logger.info("✅ Pre-deployment migrations completed successfully!")
            logger.info("=" * 60)
            return True
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == '__main__':
    success = run_migrations()
    sys.exit(0 if success else 1)

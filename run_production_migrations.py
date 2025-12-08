#!/usr/bin/env python3
"""
Production Database Migration Runner

This script runs migrations against the production database.
It's designed to be called from deploy.sh before starting the application.

Usage:
    python run_production_migrations.py

Environment Variables:
    PRODUCTION_DATABASE_URL or DATABASE_URL - Database connection string
    
Exit Codes:
    0 - Success (migrations completed or already up-to-date)
    1 - Error (migration failed)
"""

import os
import sys
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('production_migrations')


def get_database_url():
    """Get database URL with production preference"""
    url = os.environ.get('PRODUCTION_DATABASE_URL') or os.environ.get('DATABASE_URL')
    if not url:
        logger.error("No database URL configured")
        logger.error("Set PRODUCTION_DATABASE_URL or DATABASE_URL environment variable")
        return None
    return url


def run_migrations():
    """Run all pending migrations using Alembic directly"""
    start_time = time.time()
    
    database_url = get_database_url()
    if not database_url:
        return False
    
    os.environ['DATABASE_URL'] = database_url
    
    db_host = database_url.split('@')[-1].split('/')[0] if '@' in database_url else 'configured'
    logger.info(f"Database host: {db_host}")
    
    try:
        from sqlalchemy import create_engine, text
        from alembic.script import ScriptDirectory
        from alembic.config import Config as AlembicConfig
        from alembic.migration import MigrationContext
        from alembic import command
        
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=300
        )
        
        logger.info("Testing database connection...")
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            logger.info("Database connection successful")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
        
        migrations_path = os.path.join(os.path.dirname(__file__), 'migrations')
        if not os.path.exists(migrations_path):
            logger.warning("No migrations directory found")
            return False
        
        alembic_ini = os.path.join(migrations_path, 'alembic.ini')
        if not os.path.exists(alembic_ini):
            logger.warning("No alembic.ini found")
            return False
        
        alembic_cfg = AlembicConfig(alembic_ini)
        alembic_cfg.set_main_option('script_location', migrations_path)
        alembic_cfg.set_main_option('sqlalchemy.url', database_url)
        
        logger.info("Checking current migration state...")
        
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()
        
        script = ScriptDirectory.from_config(alembic_cfg)
        head_rev = script.get_current_head()
        
        logger.info(f"Current revision: {current_rev or 'None (no migrations applied)'}")
        logger.info(f"Target revision: {head_rev}")
        
        if current_rev == head_rev:
            logger.info("Database is already up-to-date!")
        else:
            pending_count = 0
            if current_rev is None:
                for _ in script.walk_revisions():
                    pending_count += 1
            else:
                try:
                    for rev in script.walk_revisions(head_rev, current_rev):
                        if rev.revision != current_rev:
                            pending_count += 1
                except Exception:
                    pending_count = -1
            
            if pending_count >= 0:
                logger.info(f"Pending migrations: {pending_count}")
            else:
                logger.info("Pending migrations: multiple (count unavailable)")
            
            logger.info("Applying migrations using Alembic...")
            command.upgrade(alembic_cfg, 'head')
            logger.info("Migrations applied successfully!")
        
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Migration process completed in {duration_ms}ms")
        return True
        
    except ImportError as e:
        logger.error(f"Missing required package: {e}")
        return False
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Production Database Migration Runner")
    logger.info("=" * 60)
    
    success = run_migrations()
    
    if success:
        logger.info("Migration completed successfully")
        sys.exit(0)
    else:
        logger.error("Migration failed - check logs above for details")
        sys.exit(1)


if __name__ == '__main__':
    main()

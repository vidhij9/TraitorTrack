#!/usr/bin/env python3
"""
Background database migration runner.

Runs migrations in a background thread AFTER the server starts,
ensuring port 5000 opens immediately for Autoscale health checks.

Usage:
    from background_migrations import start_background_migrations
    start_background_migrations(app)
"""

import os
import threading
import logging
import time

logger = logging.getLogger('background_migrations')

_migration_status = {
    'started': False,
    'completed': False,
    'error': None,
    'duration_ms': None
}


def get_migration_status():
    """Get current migration status for health checks"""
    return _migration_status.copy()


def run_migrations_background(app):
    """Run database migrations in background thread"""
    global _migration_status
    
    _migration_status['started'] = True
    start_time = time.time()
    
    try:
        with app.app_context():
            from flask_migrate import upgrade as flask_migrate_upgrade
            from alembic.script import ScriptDirectory
            from alembic.config import Config as AlembicConfig
            from alembic.migration import MigrationContext
            from app import db
            
            logger.info("Background migrations starting...")
            
            migrations_path = os.path.join(os.path.dirname(__file__), 'migrations')
            if not os.path.exists(migrations_path):
                logger.info("No migrations directory - skipping")
                _migration_status['completed'] = True
                return
            
            alembic_ini = os.path.join(migrations_path, 'alembic.ini')
            if not os.path.exists(alembic_ini):
                logger.info("No alembic.ini - skipping migrations")
                _migration_status['completed'] = True
                return
            
            alembic_cfg = AlembicConfig(alembic_ini)
            alembic_cfg.set_main_option('script_location', migrations_path)
            
            engine = db.engine
            conn = engine.connect()
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()
            conn.close()
            
            script = ScriptDirectory.from_config(alembic_cfg)
            head_rev = script.get_current_head()
            
            if current_rev == head_rev:
                logger.info(f"Database up-to-date (revision: {current_rev or 'base'})")
            else:
                logger.info(f"Applying migrations: {current_rev or 'base'} -> {head_rev}")
                flask_migrate_upgrade()
                logger.info(f"Migrations applied successfully: {head_rev}")
            
            _migration_status['completed'] = True
            _migration_status['duration_ms'] = int((time.time() - start_time) * 1000)
            logger.info(f"Background migrations completed in {_migration_status['duration_ms']}ms")
            
    except Exception as e:
        _migration_status['error'] = str(e)
        _migration_status['duration_ms'] = int((time.time() - start_time) * 1000)
        logger.error(f"Background migration error: {e}")


def start_background_migrations(app, delay_seconds=2):
    """
    Start migrations in a background thread after a short delay.
    
    Args:
        app: Flask application
        delay_seconds: Seconds to wait before starting migrations (allows server to fully start)
    """
    def delayed_start():
        time.sleep(delay_seconds)
        run_migrations_background(app)
    
    thread = threading.Thread(target=delayed_start, daemon=True, name='background-migrations')
    thread.start()
    logger.info(f"Background migrations scheduled (starting in {delay_seconds}s)")
    return thread

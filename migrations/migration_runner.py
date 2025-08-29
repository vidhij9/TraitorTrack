#!/usr/bin/env python3
"""
Migration Runner - Automatically runs database migrations on startup
Ensures production and development databases stay in sync
"""

import os
import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.exc import OperationalError, ProgrammingError
import glob

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MigrationRunner:
    def __init__(self, database_url=None):
        self.database_url = database_url or os.environ.get("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        self.engine = create_engine(self.database_url)
        self.migrations_dir = os.path.join(os.path.dirname(__file__))
        
    def create_migrations_table(self):
        """Create migrations tracking table if it doesn't exist"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        id SERIAL PRIMARY KEY,
                        migration_name VARCHAR(255) UNIQUE NOT NULL,
                        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        success BOOLEAN DEFAULT TRUE
                    )
                """))
                conn.commit()
                logger.info("✅ Schema migrations table ready")
        except Exception as e:
            logger.error(f"❌ Error creating migrations table: {e}")
            raise
    
    def get_executed_migrations(self):
        """Get list of already executed migrations"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT migration_name FROM schema_migrations 
                    WHERE success = TRUE 
                    ORDER BY executed_at
                """))
                return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.warning(f"Could not fetch executed migrations: {e}")
            return []
    
    def get_pending_migrations(self):
        """Get list of migration files that haven't been executed"""
        # Get all .sql files in migrations directory
        migration_files = glob.glob(os.path.join(self.migrations_dir, "*.sql"))
        migration_files.sort()  # Execute in alphabetical order
        
        executed = self.get_executed_migrations()
        pending = []
        
        for file_path in migration_files:
            migration_name = os.path.basename(file_path)
            if migration_name not in executed:
                pending.append(file_path)
        
        return pending
    
    def execute_migration(self, migration_path):
        """Execute a single migration file"""
        migration_name = os.path.basename(migration_path)
        logger.info(f"🔄 Executing migration: {migration_name}")
        
        try:
            # Read migration file
            with open(migration_path, 'r') as f:
                sql_content = f.read()
            
            # Execute migration in transaction
            with self.engine.connect() as conn:
                trans = conn.begin()
                try:
                    # Split and execute SQL statements
                    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
                    
                    for stmt in statements:
                        if stmt:
                            conn.execute(text(stmt))
                    
                    # Record successful migration
                    conn.execute(text("""
                        INSERT INTO schema_migrations (migration_name, executed_at, success)
                        VALUES (:name, :timestamp, TRUE)
                        ON CONFLICT (migration_name) DO NOTHING
                    """), {
                        'name': migration_name,
                        'timestamp': datetime.utcnow()
                    })
                    
                    trans.commit()
                    logger.info(f"✅ Migration completed: {migration_name}")
                    return True
                    
                except Exception as e:
                    trans.rollback()
                    logger.error(f"❌ Migration failed: {migration_name} - {e}")
                    
                    # Record failed migration
                    try:
                        with self.engine.connect() as conn2:
                            conn2.execute(text("""
                                INSERT INTO schema_migrations (migration_name, executed_at, success)
                                VALUES (:name, :timestamp, FALSE)
                                ON CONFLICT (migration_name) DO UPDATE SET
                                executed_at = :timestamp, success = FALSE
                            """), {
                                'name': migration_name,
                                'timestamp': datetime.utcnow()
                            })
                            conn2.commit()
                    except Exception:
                        pass  # Don't fail on logging errors
                    
                    raise
                    
        except Exception as e:
            logger.error(f"❌ Error reading migration file {migration_path}: {e}")
            return False
    
    def run_migrations(self):
        """Run all pending migrations"""
        logger.info("🚀 Starting migration runner")
        
        try:
            # Ensure migrations table exists
            self.create_migrations_table()
            
            # Get pending migrations
            pending = self.get_pending_migrations()
            
            if not pending:
                logger.info("✅ No pending migrations")
                return True
            
            logger.info(f"📋 Found {len(pending)} pending migrations")
            
            # Execute each migration
            for migration_path in pending:
                if not self.execute_migration(migration_path):
                    logger.error("❌ Migration execution failed, stopping")
                    return False
            
            logger.info("🎉 All migrations completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration runner failed: {e}")
            return False

def run_migrations():
    """Entry point for running migrations"""
    try:
        runner = MigrationRunner()
        return runner.run_migrations()
    except Exception as e:
        logger.error(f"❌ Failed to initialize migration runner: {e}")
        return False

if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
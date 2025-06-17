#!/usr/bin/env python3
"""
Database Manager - Comprehensive database operations for development and production environments
"""

import os
import sys
import json
import hashlib
import subprocess
from datetime import datetime
from urllib.parse import urlparse
from pathlib import Path

class DatabaseManager:
    def __init__(self):
        self.dev_db_url = os.environ.get('DEV_DATABASE_URL')
        self.prod_db_url = os.environ.get('PROD_DATABASE_URL')
        self.current_env = os.environ.get('FLASK_ENV', 'development')
        self.migrations_dir = Path('database_migrations')
        self.migrations_dir.mkdir(exist_ok=True)
        
    def get_current_database_url(self):
        """Get database URL for current environment"""
        if self.current_env == 'production':
            return self.prod_db_url or os.environ.get('DATABASE_URL')
        else:
            return self.dev_db_url or os.environ.get('DATABASE_URL')
    
    def run_sql_command(self, sql, database_url=None):
        """Execute SQL command safely"""
        if not database_url:
            database_url = self.get_current_database_url()
        
        if not database_url:
            raise ValueError(f"No database URL configured for environment: {self.current_env}")
        
        try:
            cmd = f'psql "{database_url}" -c "{sql}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"SQL Error: {result.stderr}")
            return result.stdout
        except Exception as e:
            raise Exception(f"Failed to execute SQL: {str(e)}")
    
    def backup_database(self, backup_name=None):
        """Create database backup"""
        database_url = self.get_current_database_url()
        if not database_url:
            raise ValueError("No database URL configured")
        
        parsed = urlparse(database_url)
        if not backup_name:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{parsed.path[1:]}_{self.current_env}_{timestamp}.sql"
        
        backup_path = Path('database_backups')
        backup_path.mkdir(exist_ok=True)
        full_backup_path = backup_path / backup_name
        
        print(f"Creating backup: {full_backup_path}")
        cmd = f'pg_dump "{database_url}" > "{full_backup_path}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Backup failed: {result.stderr}")
        
        print(f"Backup created successfully: {full_backup_path}")
        return str(full_backup_path)
    
    def get_schema_hash(self, database_url=None):
        """Get hash of current database schema"""
        if not database_url:
            database_url = self.get_current_database_url()
        
        schema_sql = """
        SELECT table_name, column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_schema = 'public' 
        ORDER BY table_name, ordinal_position;
        """
        
        try:
            result = self.run_sql_command(schema_sql, database_url)
            return hashlib.md5(result.encode()).hexdigest()
        except Exception as e:
            print(f"Warning: Could not get schema hash: {e}")
            return None
    
    def compare_schemas(self):
        """Compare development and production schemas"""
        if not self.dev_db_url or not self.prod_db_url:
            print("Both DEV_DATABASE_URL and PROD_DATABASE_URL must be set for schema comparison")
            return
        
        print("Comparing database schemas...")
        
        dev_hash = self.get_schema_hash(self.dev_db_url)
        prod_hash = self.get_schema_hash(self.prod_db_url)
        
        if dev_hash and prod_hash:
            if dev_hash == prod_hash:
                print("✅ Development and production schemas are identical")
            else:
                print("⚠️  Development and production schemas differ")
                print(f"Development hash: {dev_hash}")
                print(f"Production hash: {prod_hash}")
        else:
            print("Could not compare schemas - check database connections")
    
    def create_migration_record(self, migration_name, sql_content):
        """Create migration record"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        migration_id = f"{timestamp}_{migration_name}"
        
        migration_file = self.migrations_dir / f"{migration_id}.sql"
        with open(migration_file, 'w') as f:
            f.write(f"-- Migration: {migration_name}\n")
            f.write(f"-- Created: {datetime.now().isoformat()}\n")
            f.write(f"-- Environment: {self.current_env}\n\n")
            f.write(sql_content)
        
        # Create migration metadata
        metadata = {
            'id': migration_id,
            'name': migration_name,
            'created': datetime.now().isoformat(),
            'environment': self.current_env,
            'applied': False,
            'hash': hashlib.md5(sql_content.encode()).hexdigest()
        }
        
        metadata_file = self.migrations_dir / f"{migration_id}.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Migration created: {migration_file}")
        return migration_id
    
    def initialize_migration_tracking(self):
        """Initialize migration tracking table"""
        sql = """
        CREATE TABLE IF NOT EXISTS database_migrations (
            id SERIAL PRIMARY KEY,
            migration_id VARCHAR(255) UNIQUE NOT NULL,
            migration_name VARCHAR(255) NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            environment VARCHAR(50) NOT NULL,
            hash VARCHAR(32) NOT NULL
        );
        """
        
        try:
            self.run_sql_command(sql)
            print("Migration tracking initialized")
        except Exception as e:
            print(f"Failed to initialize migration tracking: {e}")
    
    def get_applied_migrations(self):
        """Get list of applied migrations"""
        sql = "SELECT migration_id FROM database_migrations ORDER BY applied_at;"
        try:
            result = self.run_sql_command(sql)
            return [line.strip() for line in result.split('\n') if line.strip() and not line.startswith('-')]
        except:
            return []
    
    def apply_migration(self, migration_id):
        """Apply a specific migration"""
        migration_file = self.migrations_dir / f"{migration_id}.sql"
        metadata_file = self.migrations_dir / f"{migration_id}.json"
        
        if not migration_file.exists():
            raise FileNotFoundError(f"Migration file not found: {migration_file}")
        
        # Read migration content
        with open(migration_file, 'r') as f:
            migration_content = f.read()
        
        # Read metadata
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {'name': migration_id, 'hash': ''}
        
        print(f"Applying migration: {migration_id}")
        
        # Apply migration
        self.run_sql_command(migration_content)
        
        # Record migration
        record_sql = f"""
        INSERT INTO database_migrations (migration_id, migration_name, environment, hash)
        VALUES ('{migration_id}', '{metadata.get('name', migration_id)}', '{self.current_env}', '{metadata.get('hash', '')}')
        ON CONFLICT (migration_id) DO NOTHING;
        """
        
        self.run_sql_command(record_sql)
        print(f"Migration applied successfully: {migration_id}")
    
    def sync_development_to_production(self):
        """Sync development schema to production (DANGEROUS - use with caution)"""
        if self.current_env != 'production':
            print("This operation can only be run in production environment")
            return
        
        if not self.dev_db_url or not self.prod_db_url:
            print("Both DEV_DATABASE_URL and PROD_DATABASE_URL must be set")
            return
        
        print("⚠️  WARNING: This will overwrite production database structure!")
        print("This operation should only be used for initial deployment or with extreme caution")
        
        confirm = input("Type 'CONFIRM_SYNC' to proceed: ")
        if confirm != 'CONFIRM_SYNC':
            print("Sync cancelled")
            return
        
        # Create backup first
        backup_path = self.backup_database()
        print(f"Production backup created: {backup_path}")
        
        # Get development schema
        print("Extracting development schema...")
        dev_schema_cmd = f'pg_dump --schema-only "{self.dev_db_url}"'
        result = subprocess.run(dev_schema_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Failed to extract development schema: {result.stderr}")
        
        dev_schema = result.stdout
        
        # Apply to production
        print("Applying schema to production...")
        restore_cmd = f'psql "{self.prod_db_url}"'
        process = subprocess.Popen(restore_cmd, shell=True, stdin=subprocess.PIPE, 
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        stdout, stderr = process.communicate(dev_schema)
        
        if process.returncode != 0:
            print(f"Schema sync failed: {stderr}")
            print(f"Production backup available at: {backup_path}")
        else:
            print("Schema sync completed successfully")
    
    def status(self):
        """Show current database status"""
        print(f"Environment: {self.current_env}")
        print(f"Database URL: {self.get_current_database_url()}")
        
        if self.dev_db_url:
            print(f"Development DB: Configured")
        else:
            print(f"Development DB: Not configured")
            
        if self.prod_db_url:
            print(f"Production DB: Configured")
        else:
            print(f"Production DB: Not configured")
        
        # Show applied migrations
        try:
            applied = self.get_applied_migrations()
            print(f"Applied migrations: {len(applied)}")
            for migration in applied[-5:]:  # Show last 5
                print(f"  - {migration}")
        except:
            print("Migration tracking not initialized")

def main():
    """Command line interface"""
    if len(sys.argv) < 2:
        print("Usage: python database_manager.py <command>")
        print("Commands:")
        print("  status              - Show database status")
        print("  init                - Initialize migration tracking")
        print("  backup [name]       - Create database backup")
        print("  compare             - Compare dev and prod schemas")
        print("  sync-to-prod        - Sync development schema to production (DANGEROUS)")
        sys.exit(1)
    
    manager = DatabaseManager()
    command = sys.argv[1].lower()
    
    try:
        if command == 'status':
            manager.status()
        elif command == 'init':
            manager.initialize_migration_tracking()
        elif command == 'backup':
            backup_name = sys.argv[2] if len(sys.argv) > 2 else None
            manager.backup_database(backup_name)
        elif command == 'compare':
            manager.compare_schemas()
        elif command == 'sync-to-prod':
            manager.sync_development_to_production()
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

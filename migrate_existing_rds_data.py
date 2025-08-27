#!/usr/bin/env python3
"""
RDS Data Migration Script for TraceTrack
This script migrates existing RDS PostgreSQL data to the new schema structure
"""

import os
import sys
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RDSDataMigrator:
    def __init__(self, source_db_url, target_db_url=None):
        self.source_db_url = source_db_url
        self.target_db_url = target_db_url or source_db_url
        self.migration_log = []
        
    def connect_to_database(self, db_url):
        """Connect to PostgreSQL database"""
        try:
            conn = psycopg2.connect(db_url)
            conn.autocommit = False
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def get_existing_schema(self, conn):
        """Analyze existing database schema"""
        schema_info = {
            'tables': {},
            'columns': {},
            'constraints': {},
            'indexes': {}
        }
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Get all tables
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                """)
                tables = [row['table_name'] for row in cursor.fetchall()]
                
                for table in tables:
                    # Get table columns
                    cursor.execute("""
                        SELECT column_name, data_type, is_nullable, column_default
                        FROM information_schema.columns 
                        WHERE table_name = %s AND table_schema = 'public'
                        ORDER BY ordinal_position
                    """, (table,))
                    columns = cursor.fetchall()
                    
                    schema_info['tables'][table] = {
                        'exists': True,
                        'columns': {col['column_name']: col for col in columns}
                    }
                    
                    # Get constraints
                    cursor.execute("""
                        SELECT constraint_name, constraint_type
                        FROM information_schema.table_constraints 
                        WHERE table_name = %s AND table_schema = 'public'
                    """, (table,))
                    constraints = cursor.fetchall()
                    schema_info['constraints'][table] = constraints
                    
                    # Get indexes
                    cursor.execute("""
                        SELECT indexname, indexdef
                        FROM pg_indexes 
                        WHERE tablename = %s AND schemaname = 'public'
                    """, (table,))
                    indexes = cursor.fetchall()
                    schema_info['indexes'][table] = indexes
                    
        except Exception as e:
            logger.error(f"Error analyzing schema: {e}")
            raise
            
        return schema_info
    
    def backup_existing_data(self, conn, backup_file):
        """Create a backup of existing data"""
        logger.info(f"Creating backup to {backup_file}")
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Get all data from existing tables
                backup_data = {}
                
                # Common tables that might exist
                potential_tables = [
                    'user', 'users', 'bag', 'bags', 'scan', 'scans', 
                    'bill', 'bills', 'link', 'links', 'location', 'locations',
                    'promotionrequest', 'promotion_requests', 'audit_log', 'audit_logs'
                ]
                
                for table in potential_tables:
                    try:
                        cursor.execute(f"SELECT * FROM {table}")
                        rows = cursor.fetchall()
                        if rows:
                            backup_data[table] = [dict(row) for row in rows]
                            logger.info(f"Backed up {len(rows)} rows from {table}")
                    except psycopg2.Error:
                        # Table doesn't exist, skip
                        continue
                
                # Save backup to file
                with open(backup_file, 'w') as f:
                    json.dump(backup_data, f, indent=2, default=str)
                
                logger.info(f"Backup completed: {backup_file}")
                return backup_data
                
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            raise
    
    def create_new_schema(self, conn):
        """Create new schema structure"""
        logger.info("Creating new schema structure...")
        
        try:
            with conn.cursor() as cursor:
                # Create new tables with updated schema
                
                # User table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS "user" (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(64) UNIQUE NOT NULL,
                        email VARCHAR(120) UNIQUE NOT NULL,
                        password_hash VARCHAR(256) NOT NULL,
                        role VARCHAR(20) DEFAULT 'dispatcher',
                        dispatch_area VARCHAR(30),
                        verification_token VARCHAR(100),
                        verified BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Bag table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS bag (
                        id SERIAL PRIMARY KEY,
                        qr_id VARCHAR(255) UNIQUE NOT NULL,
                        type VARCHAR(10) NOT NULL,
                        name VARCHAR(100),
                        child_count INTEGER,
                        parent_id INTEGER,
                        user_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
                        dispatch_area VARCHAR(30),
                        status VARCHAR(20) DEFAULT 'pending',
                        weight_kg FLOAT DEFAULT 0.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Link table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS link (
                        id SERIAL PRIMARY KEY,
                        parent_bag_id INTEGER NOT NULL REFERENCES bag(id) ON DELETE CASCADE,
                        child_bag_id INTEGER NOT NULL REFERENCES bag(id) ON DELETE CASCADE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(parent_bag_id, child_bag_id)
                    )
                """)
                
                # Bill table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS bill (
                        id SERIAL PRIMARY KEY,
                        bill_id VARCHAR(50) UNIQUE NOT NULL,
                        description TEXT,
                        parent_bag_count INTEGER DEFAULT 1,
                        total_weight_kg FLOAT DEFAULT 0.0,
                        total_child_bags INTEGER DEFAULT 0,
                        status VARCHAR(20) DEFAULT 'new',
                        created_by_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # BillBag table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS bill_bag (
                        id SERIAL PRIMARY KEY,
                        bill_id INTEGER NOT NULL REFERENCES bill(id) ON DELETE CASCADE,
                        bag_id INTEGER NOT NULL REFERENCES bag(id) ON DELETE CASCADE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(bill_id, bag_id)
                    )
                """)
                
                # Scan table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS scan (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        parent_bag_id INTEGER REFERENCES bag(id),
                        child_bag_id INTEGER REFERENCES bag(id),
                        user_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL
                    )
                """)
                
                # PromotionRequest table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS promotionrequest (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                        reason TEXT NOT NULL,
                        status VARCHAR(20) DEFAULT 'pending',
                        admin_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
                        admin_notes TEXT,
                        requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        processed_at TIMESTAMP
                    )
                """)
                
                # AuditLog table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        user_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
                        action VARCHAR(50) NOT NULL,
                        entity_type VARCHAR(20) NOT NULL,
                        entity_id INTEGER,
                        details TEXT,
                        ip_address VARCHAR(45)
                    )
                """)
                
                # Create indexes for performance
                self.create_indexes(cursor)
                
                conn.commit()
                logger.info("New schema created successfully")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating schema: {e}")
            raise
    
    def create_indexes(self, cursor):
        """Create performance indexes"""
        indexes = [
            # Bag indexes
            "CREATE INDEX IF NOT EXISTS idx_bag_qr_id ON bag(qr_id)",
            "CREATE INDEX IF NOT EXISTS idx_bag_type ON bag(type)",
            "CREATE INDEX IF NOT EXISTS idx_bag_created_at ON bag(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_bag_type_created ON bag(type, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_bag_parent_id ON bag(parent_id)",
            "CREATE INDEX IF NOT EXISTS idx_bag_user_id ON bag(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_bag_dispatch_area ON bag(dispatch_area)",
            
            # Link indexes
            "CREATE INDEX IF NOT EXISTS idx_link_parent_id ON link(parent_bag_id)",
            "CREATE INDEX IF NOT EXISTS idx_link_child_id ON link(child_bag_id)",
            "CREATE INDEX IF NOT EXISTS idx_link_parent_child ON link(parent_bag_id, child_bag_id)",
            
            # Bill indexes
            "CREATE INDEX IF NOT EXISTS idx_bill_id ON bill(bill_id)",
            "CREATE INDEX IF NOT EXISTS idx_bill_status ON bill(status)",
            "CREATE INDEX IF NOT EXISTS idx_bill_created ON bill(created_at)",
            
            # BillBag indexes
            "CREATE INDEX IF NOT EXISTS idx_bill_bag_bill_id ON bill_bag(bill_id)",
            "CREATE INDEX IF NOT EXISTS idx_bill_bag_bag_id ON bill_bag(bag_id)",
            
            # Scan indexes
            "CREATE INDEX IF NOT EXISTS idx_scan_timestamp ON scan(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_scan_parent_bag ON scan(parent_bag_id)",
            "CREATE INDEX IF NOT EXISTS idx_scan_child_bag ON scan(child_bag_id)",
            "CREATE INDEX IF NOT EXISTS idx_scan_user ON scan(user_id)",
            
            # Audit log indexes
            "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)",
            "CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id)"
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except Exception as e:
                logger.warning(f"Could not create index: {e}")
    
    def migrate_users(self, conn, backup_data):
        """Migrate user data"""
        logger.info("Migrating user data...")
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Check for existing user data
                user_data = backup_data.get('user') or backup_data.get('users') or []
                
                if not user_data:
                    logger.info("No existing user data found, creating default admin user")
                    cursor.execute("""
                        INSERT INTO "user" (username, email, password_hash, role, verified)
                        VALUES ('admin', 'admin@tracetrack.com', 
                                'pbkdf2:sha256:600000$dev-secret-key$admin', 'admin', TRUE)
                        ON CONFLICT (username) DO NOTHING
                    """)
                else:
                    logger.info(f"Migrating {len(user_data)} users")
                    for user in user_data:
                        # Map old fields to new schema
                        username = user.get('username') or user.get('name') or f"user_{user.get('id', 'unknown')}"
                        email = user.get('email') or f"{username}@tracetrack.com"
                        password_hash = user.get('password_hash') or user.get('password') or 'pbkdf2:sha256:600000$dev-secret-key$default'
                        role = user.get('role') or 'dispatcher'
                        dispatch_area = user.get('dispatch_area') or user.get('area')
                        verified = user.get('verified', True)
                        
                        cursor.execute("""
                            INSERT INTO "user" (username, email, password_hash, role, dispatch_area, verified)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (username) DO UPDATE SET
                                email = EXCLUDED.email,
                                role = EXCLUDED.role,
                                dispatch_area = EXCLUDED.dispatch_area
                        """, (username, email, password_hash, role, dispatch_area, verified))
                
                conn.commit()
                logger.info("User migration completed")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error migrating users: {e}")
            raise
    
    def migrate_bags(self, conn, backup_data):
        """Migrate bag data"""
        logger.info("Migrating bag data...")
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Check for existing bag data
                bag_data = backup_data.get('bag') or backup_data.get('bags') or []
                
                if bag_data:
                    logger.info(f"Migrating {len(bag_data)} bags")
                    for bag in bag_data:
                        # Map old fields to new schema
                        qr_id = bag.get('qr_id') or bag.get('qr_code') or bag.get('id')
                        bag_type = bag.get('type') or 'parent'  # Default to parent
                        name = bag.get('name') or bag.get('bag_name')
                        child_count = bag.get('child_count') or bag.get('children_count') or 0
                        parent_id = bag.get('parent_id') or bag.get('parent_bag_id')
                        user_id = bag.get('user_id') or bag.get('owner_id')
                        dispatch_area = bag.get('dispatch_area') or bag.get('area')
                        status = bag.get('status') or 'pending'
                        weight_kg = bag.get('weight_kg') or bag.get('weight') or 0.0
                        
                        cursor.execute("""
                            INSERT INTO bag (qr_id, type, name, child_count, parent_id, user_id, 
                                           dispatch_area, status, weight_kg, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (qr_id) DO UPDATE SET
                                name = EXCLUDED.name,
                                child_count = EXCLUDED.child_count,
                                parent_id = EXCLUDED.parent_id,
                                user_id = EXCLUDED.user_id,
                                dispatch_area = EXCLUDED.dispatch_area,
                                status = EXCLUDED.status,
                                weight_kg = EXCLUDED.weight_kg
                        """, (qr_id, bag_type, name, child_count, parent_id, user_id, 
                              dispatch_area, status, weight_kg, bag.get('created_at') or datetime.now()))
                
                conn.commit()
                logger.info("Bag migration completed")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error migrating bags: {e}")
            raise
    
    def migrate_scans(self, conn, backup_data):
        """Migrate scan data"""
        logger.info("Migrating scan data...")
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Check for existing scan data
                scan_data = backup_data.get('scan') or backup_data.get('scans') or []
                
                if scan_data:
                    logger.info(f"Migrating {len(scan_data)} scans")
                    for scan in scan_data:
                        # Map old fields to new schema
                        timestamp = scan.get('timestamp') or scan.get('created_at') or datetime.now()
                        parent_bag_id = scan.get('parent_bag_id') or scan.get('parent_id')
                        child_bag_id = scan.get('child_bag_id') or scan.get('child_id')
                        user_id = scan.get('user_id') or scan.get('scanner_id')
                        
                        cursor.execute("""
                            INSERT INTO scan (timestamp, parent_bag_id, child_bag_id, user_id)
                            VALUES (%s, %s, %s, %s)
                        """, (timestamp, parent_bag_id, child_bag_id, user_id))
                
                conn.commit()
                logger.info("Scan migration completed")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error migrating scans: {e}")
            raise
    
    def migrate_bills(self, conn, backup_data):
        """Migrate bill data"""
        logger.info("Migrating bill data...")
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Check for existing bill data
                bill_data = backup_data.get('bill') or backup_data.get('bills') or []
                
                if bill_data:
                    logger.info(f"Migrating {len(bill_data)} bills")
                    for bill in bill_data:
                        # Map old fields to new schema
                        bill_id = bill.get('bill_id') or bill.get('id')
                        description = bill.get('description') or bill.get('bill_description')
                        parent_bag_count = bill.get('parent_bag_count') or bill.get('bag_count') or 1
                        total_weight_kg = bill.get('total_weight_kg') or bill.get('weight') or 0.0
                        total_child_bags = bill.get('total_child_bags') or bill.get('child_count') or 0
                        status = bill.get('status') or 'new'
                        created_by_id = bill.get('created_by_id') or bill.get('user_id')
                        
                        cursor.execute("""
                            INSERT INTO bill (bill_id, description, parent_bag_count, total_weight_kg,
                                            total_child_bags, status, created_by_id, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (bill_id) DO UPDATE SET
                                description = EXCLUDED.description,
                                parent_bag_count = EXCLUDED.parent_bag_count,
                                total_weight_kg = EXCLUDED.total_weight_kg,
                                total_child_bags = EXCLUDED.total_child_bags,
                                status = EXCLUDED.status
                        """, (bill_id, description, parent_bag_count, total_weight_kg,
                              total_child_bags, status, created_by_id, bill.get('created_at') or datetime.now()))
                
                conn.commit()
                logger.info("Bill migration completed")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error migrating bills: {e}")
            raise
    
    def migrate_links(self, conn, backup_data):
        """Migrate link data"""
        logger.info("Migrating link data...")
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Check for existing link data
                link_data = backup_data.get('link') or backup_data.get('links') or []
                
                if link_data:
                    logger.info(f"Migrating {len(link_data)} links")
                    for link in link_data:
                        parent_bag_id = link.get('parent_bag_id') or link.get('parent_id')
                        child_bag_id = link.get('child_bag_id') or link.get('child_id')
                        
                        if parent_bag_id and child_bag_id:
                            cursor.execute("""
                                INSERT INTO link (parent_bag_id, child_bag_id, created_at)
                                VALUES (%s, %s, %s)
                                ON CONFLICT (parent_bag_id, child_bag_id) DO NOTHING
                            """, (parent_bag_id, child_bag_id, link.get('created_at') or datetime.now()))
                
                conn.commit()
                logger.info("Link migration completed")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Error migrating links: {e}")
            raise
    
    def run_migration(self, backup_file=None):
        """Run the complete migration process"""
        logger.info("Starting RDS data migration...")
        
        if not backup_file:
            backup_file = f"rds_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            # Connect to source database
            source_conn = self.connect_to_database(self.source_db_url)
            
            # Analyze existing schema
            logger.info("Analyzing existing schema...")
            schema_info = self.get_existing_schema(source_conn)
            
            # Create backup
            backup_data = self.backup_existing_data(source_conn, backup_file)
            
            # Close source connection
            source_conn.close()
            
            # Connect to target database (could be same as source)
            target_conn = self.connect_to_database(self.target_db_url)
            
            # Create new schema
            self.create_new_schema(target_conn)
            
            # Migrate data
            self.migrate_users(target_conn, backup_data)
            self.migrate_bags(target_conn, backup_data)
            self.migrate_scans(target_conn, backup_data)
            self.migrate_bills(target_conn, backup_data)
            self.migrate_links(target_conn, backup_data)
            
            # Close target connection
            target_conn.close()
            
            logger.info("Migration completed successfully!")
            logger.info(f"Backup saved to: {backup_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Migrate existing RDS data to new schema')
    parser.add_argument('--source-db-url', required=True, help='Source database URL')
    parser.add_argument('--target-db-url', help='Target database URL (defaults to source)')
    parser.add_argument('--backup-file', help='Backup file path')
    
    args = parser.parse_args()
    
    migrator = RDSDataMigrator(args.source_db_url, args.target_db_url)
    success = migrator.run_migration(args.backup_file)
    
    if success:
        print("✅ Migration completed successfully!")
        sys.exit(0)
    else:
        print("❌ Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
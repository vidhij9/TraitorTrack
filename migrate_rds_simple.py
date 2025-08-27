#!/usr/bin/env python3
"""
Simple RDS Migration Script
This script handles migration of existing RDS data to the new schema
"""

import os
import sys
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_rds_data(db_url):
    """Migrate existing RDS data to new schema"""
    logger.info("Starting RDS data migration...")
    
    try:
        # Connect to database
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
        
        # Create backup
        backup_file = f"rds_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_data = create_backup(conn, backup_file)
        
        # Create new schema (if not exists)
        create_new_schema(conn)
        
        # Migrate data
        migrate_users(conn, backup_data)
        migrate_bags(conn, backup_data)
        migrate_scans(conn, backup_data)
        migrate_bills(conn, backup_data)
        migrate_links(conn, backup_data)
        
        conn.close()
        logger.info("✅ RDS migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ RDS migration failed: {e}")
        return False

def create_backup(conn, backup_file):
    """Create backup of existing data"""
    logger.info(f"Creating backup: {backup_file}")
    
    backup_data = {}
    potential_tables = [
        'user', 'users', 'bag', 'bags', 'scan', 'scans', 
        'bill', 'bills', 'link', 'links', 'location', 'locations'
    ]
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        for table in potential_tables:
            try:
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                if rows:
                    backup_data[table] = [dict(row) for row in rows]
                    logger.info(f"Backed up {len(rows)} rows from {table}")
            except psycopg2.Error:
                continue
    
    # Save backup
    with open(backup_file, 'w') as f:
        json.dump(backup_data, f, indent=2, default=str)
    
    return backup_data

def create_new_schema(conn):
    """Create new schema structure"""
    logger.info("Creating new schema...")
    
    with conn.cursor() as cursor:
        # Create tables with IF NOT EXISTS
        tables = [
            # User table
            """
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
            """,
            
            # Bag table
            """
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
            """,
            
            # Link table
            """
            CREATE TABLE IF NOT EXISTS link (
                id SERIAL PRIMARY KEY,
                parent_bag_id INTEGER NOT NULL REFERENCES bag(id) ON DELETE CASCADE,
                child_bag_id INTEGER NOT NULL REFERENCES bag(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(parent_bag_id, child_bag_id)
            )
            """,
            
            # Bill table
            """
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
            """,
            
            # BillBag table
            """
            CREATE TABLE IF NOT EXISTS bill_bag (
                id SERIAL PRIMARY KEY,
                bill_id INTEGER NOT NULL REFERENCES bill(id) ON DELETE CASCADE,
                bag_id INTEGER NOT NULL REFERENCES bag(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(bill_id, bag_id)
            )
            """,
            
            # Scan table
            """
            CREATE TABLE IF NOT EXISTS scan (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                parent_bag_id INTEGER REFERENCES bag(id),
                child_bag_id INTEGER REFERENCES bag(id),
                user_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL
            )
            """,
            
            # PromotionRequest table
            """
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
            """,
            
            # AuditLog table
            """
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
            """
        ]
        
        for table_sql in tables:
            cursor.execute(table_sql)
        
        # Create indexes
        create_indexes(cursor)
        
        conn.commit()

def create_indexes(cursor):
    """Create performance indexes"""
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_bag_qr_id ON bag(qr_id)",
        "CREATE INDEX IF NOT EXISTS idx_bag_type ON bag(type)",
        "CREATE INDEX IF NOT EXISTS idx_bag_created_at ON bag(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_bag_parent_id ON bag(parent_id)",
        "CREATE INDEX IF NOT EXISTS idx_bag_user_id ON bag(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_bag_dispatch_area ON bag(dispatch_area)",
        "CREATE INDEX IF NOT EXISTS idx_link_parent_id ON link(parent_bag_id)",
        "CREATE INDEX IF NOT EXISTS idx_link_child_id ON link(child_bag_id)",
        "CREATE INDEX IF NOT EXISTS idx_bill_id ON bill(bill_id)",
        "CREATE INDEX IF NOT EXISTS idx_bill_status ON bill(status)",
        "CREATE INDEX IF NOT EXISTS idx_scan_timestamp ON scan(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_scan_parent_bag ON scan(parent_bag_id)",
        "CREATE INDEX IF NOT EXISTS idx_scan_child_bag ON scan(child_bag_id)",
        "CREATE INDEX IF NOT EXISTS idx_scan_user ON scan(user_id)"
    ]
    
    for index_sql in indexes:
        try:
            cursor.execute(index_sql)
        except Exception as e:
            logger.warning(f"Could not create index: {e}")

def migrate_users(conn, backup_data):
    """Migrate user data"""
    logger.info("Migrating users...")
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        user_data = backup_data.get('user') or backup_data.get('users') or []
        
        if not user_data:
            # Create default admin user
            cursor.execute("""
                INSERT INTO "user" (username, email, password_hash, role, verified)
                VALUES ('admin', 'admin@tracetrack.com', 
                        'pbkdf2:sha256:600000$dev-secret-key$admin', 'admin', TRUE)
                ON CONFLICT (username) DO NOTHING
            """)
        else:
            for user in user_data:
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

def migrate_bags(conn, backup_data):
    """Migrate bag data"""
    logger.info("Migrating bags...")
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        bag_data = backup_data.get('bag') or backup_data.get('bags') or []
        
        for bag in bag_data:
            qr_id = bag.get('qr_id') or bag.get('qr_code') or bag.get('id')
            bag_type = bag.get('type') or 'parent'
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

def migrate_scans(conn, backup_data):
    """Migrate scan data"""
    logger.info("Migrating scans...")
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        scan_data = backup_data.get('scan') or backup_data.get('scans') or []
        
        for scan in scan_data:
            timestamp = scan.get('timestamp') or scan.get('created_at') or datetime.now()
            parent_bag_id = scan.get('parent_bag_id') or scan.get('parent_id')
            child_bag_id = scan.get('child_bag_id') or scan.get('child_id')
            user_id = scan.get('user_id') or scan.get('scanner_id')
            
            cursor.execute("""
                INSERT INTO scan (timestamp, parent_bag_id, child_bag_id, user_id)
                VALUES (%s, %s, %s, %s)
            """, (timestamp, parent_bag_id, child_bag_id, user_id))
        
        conn.commit()

def migrate_bills(conn, backup_data):
    """Migrate bill data"""
    logger.info("Migrating bills...")
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        bill_data = backup_data.get('bill') or backup_data.get('bills') or []
        
        for bill in bill_data:
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

def migrate_links(conn, backup_data):
    """Migrate link data"""
    logger.info("Migrating links...")
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        link_data = backup_data.get('link') or backup_data.get('links') or []
        
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

if __name__ == "__main__":
    # Get database URL from environment
    db_url = os.environ.get('AWS_DATABASE_URL') or os.environ.get('DATABASE_URL')
    
    if not db_url:
        print("❌ No database URL found. Set AWS_DATABASE_URL or DATABASE_URL environment variable.")
        sys.exit(1)
    
    success = migrate_rds_data(db_url)
    sys.exit(0 if success else 1)
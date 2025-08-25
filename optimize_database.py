#!/usr/bin/env python3
"""
Database Optimization Script - Add critical indexes and optimize tables
"""

import os
import logging
from app_clean import app, db
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_critical_indexes():
    """Add missing critical indexes for performance"""
    
    indexes = [
        # Scan table indexes for ultra-fast queries
        ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_user_timestamp ON scan (user_id, timestamp DESC)", "idx_scan_user_timestamp"),
        ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_parent_timestamp ON scan (parent_bag_id, timestamp DESC)", "idx_scan_parent_timestamp"),
        ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_child_timestamp ON scan (child_bag_id, timestamp DESC)", "idx_scan_child_timestamp"),
        ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_user_parent_child ON scan (user_id, parent_bag_id, child_bag_id)", "idx_scan_user_parent_child"),
        
        # Bill and bill_bag indexes
        ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_billbag_bill_bag ON bill_bag (bill_id, bag_id)", "idx_billbag_bill_bag"),
        ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_billbag_bag_bill ON bill_bag (bag_id, bill_id)", "idx_billbag_bag_bill"),
        
        # User authentication indexes
        ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_username_password ON \"user\" (username, password_hash)", "idx_user_username_password"),
        ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_email_verified ON \"user\" (email, verified)", "idx_user_email_verified"),
        
        # Bag composite indexes for complex queries
        ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_qr_type_status ON bag (qr_id, type, status)", "idx_bag_qr_type_status"),
        ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_user_area_type ON bag (user_id, dispatch_area, type)", "idx_bag_user_area_type"),
        
        # Partial indexes for specific queries
        ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_parent_pending ON bag (id) WHERE type='parent' AND status='pending'", "idx_bag_parent_pending"),
        ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_child_unlinked ON bag (id) WHERE type='child' AND parent_id IS NULL", "idx_bag_child_unlinked"),
        ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_verified_active ON \"user\" (id, username) WHERE verified=true", "idx_user_verified_active"),
        
        # Date-based indexes for statistics
        ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_date ON scan (DATE(timestamp))", "idx_scan_date"),
        ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_date ON bill (DATE(created_at))", "idx_bill_date"),
    ]
    
    with app.app_context():
        for query, index_name in indexes:
            try:
                logger.info(f"Creating index: {index_name}")
                db.session.execute(text(query))
                db.session.commit()
                logger.info(f"✅ Created index: {index_name}")
            except Exception as e:
                db.session.rollback()
                if "already exists" in str(e).lower():
                    logger.info(f"Index already exists: {index_name}")
                else:
                    logger.error(f"Failed to create index {index_name}: {e}")

def optimize_tables():
    """Run VACUUM ANALYZE on all tables"""
    
    tables = ['user', 'bag', 'link', 'scan', 'bill', 'bill_bag', 'audit_log', 'promotion_request']
    
    with app.app_context():
        for table in tables:
            try:
                logger.info(f"Optimizing table: {table}")
                db.session.execute(text(f"VACUUM ANALYZE {table}"))
                db.session.commit()
                logger.info(f"✅ Optimized table: {table}")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Failed to optimize table {table}: {e}")

def update_statistics():
    """Update database statistics for query planner"""
    
    with app.app_context():
        try:
            logger.info("Updating database statistics...")
            db.session.execute(text("ANALYZE"))
            db.session.commit()
            logger.info("✅ Updated database statistics")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update statistics: {e}")

def configure_connection_pool():
    """Log current connection pool configuration"""
    
    logger.info("\n" + "="*60)
    logger.info("DATABASE CONNECTION POOL CONFIGURATION")
    logger.info("="*60)
    
    with app.app_context():
        engine = db.engine
        pool = engine.pool
        
        logger.info(f"Pool Size: {pool.size()}")
        logger.info(f"Overflow: {pool.overflow()}")
        logger.info(f"Total Connections: {pool.size() + pool.overflow()}")
        logger.info(f"Checked Out Connections: {pool.checkedout()}")
        
        # Check database connection limit
        try:
            result = db.session.execute(text("SHOW max_connections"))
            max_conn = result.fetchone()[0]
            logger.info(f"PostgreSQL max_connections: {max_conn}")
            
            result = db.session.execute(text("SELECT count(*) FROM pg_stat_activity"))
            current_conn = result.fetchone()[0]
            logger.info(f"Current active connections: {current_conn}")
            
        except Exception as e:
            logger.error(f"Failed to check connection stats: {e}")

def main():
    """Main optimization routine"""
    
    logger.info("\n" + "="*60)
    logger.info("STARTING DATABASE OPTIMIZATION")
    logger.info("="*60)
    
    # Add indexes
    add_critical_indexes()
    
    # Optimize tables
    optimize_tables()
    
    # Update statistics
    update_statistics()
    
    # Show connection pool config
    configure_connection_pool()
    
    logger.info("\n" + "="*60)
    logger.info("DATABASE OPTIMIZATION COMPLETE")
    logger.info("="*60)
    logger.info("The database is now optimized for high-performance operations.")
    logger.info("Indexes have been created and tables have been analyzed.")

if __name__ == "__main__":
    main()
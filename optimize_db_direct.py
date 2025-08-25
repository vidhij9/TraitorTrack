#!/usr/bin/env python3
"""
Direct Database Optimization - Create indexes without CONCURRENTLY
"""

import os
import psycopg2
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def optimize_database():
    """Optimize database with direct connection"""
    
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL not found")
        return
    
    conn = psycopg2.connect(db_url)
    conn.autocommit = True  # Important for CREATE INDEX and VACUUM
    cur = conn.cursor()
    
    logger.info("Starting database optimization...")
    
    # Create indexes without CONCURRENTLY
    indexes = [
        ("idx_scan_user_timestamp", "scan", "(user_id, timestamp DESC)"),
        ("idx_scan_parent_timestamp", "scan", "(parent_bag_id, timestamp DESC)"),
        ("idx_scan_child_timestamp", "scan", "(child_bag_id, timestamp DESC)"),
        ("idx_scan_user_parent_child", "scan", "(user_id, parent_bag_id, child_bag_id)"),
        ("idx_billbag_bill_bag", "bill_bag", "(bill_id, bag_id)"),
        ("idx_billbag_bag_bill", "bill_bag", "(bag_id, bill_id)"),
        ("idx_user_username_password", '"user"', "(username, password_hash)"),
        ("idx_user_email_verified", '"user"', "(email, verified)"),
        ("idx_bag_qr_type_status", "bag", "(qr_id, type, status)"),
        ("idx_bag_user_area_type", "bag", "(user_id, dispatch_area, type)"),
        ("idx_scan_date", "scan", "(DATE(timestamp))"),
        ("idx_bill_date", "bill", "(DATE(created_at))"),
    ]
    
    for index_name, table, columns in indexes:
        try:
            # Check if index exists
            cur.execute("""
                SELECT 1 FROM pg_indexes 
                WHERE indexname = %s
            """, (index_name,))
            
            if not cur.fetchone():
                query = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} {columns}"
                logger.info(f"Creating index: {index_name}")
                cur.execute(query)
                logger.info(f"✅ Created index: {index_name}")
            else:
                logger.info(f"Index already exists: {index_name}")
        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {e}")
    
    # Create partial indexes
    partial_indexes = [
        ("idx_bag_parent_pending", "bag", "(id)", "type='parent' AND status='pending'"),
        ("idx_bag_child_unlinked", "bag", "(id)", "type='child' AND parent_id IS NULL"),
        ("idx_user_verified_active", '"user"', "(id, username)", "verified=true"),
    ]
    
    for index_name, table, columns, condition in partial_indexes:
        try:
            cur.execute("""
                SELECT 1 FROM pg_indexes 
                WHERE indexname = %s
            """, (index_name,))
            
            if not cur.fetchone():
                query = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} {columns} WHERE {condition}"
                logger.info(f"Creating partial index: {index_name}")
                cur.execute(query)
                logger.info(f"✅ Created partial index: {index_name}")
            else:
                logger.info(f"Partial index already exists: {index_name}")
        except Exception as e:
            logger.error(f"Failed to create partial index {index_name}: {e}")
    
    # Vacuum and analyze tables
    tables = ['"user"', 'bag', 'link', 'scan', 'bill', 'bill_bag', 'audit_log', 'promotion_request']
    
    for table in tables:
        try:
            logger.info(f"Optimizing table: {table}")
            cur.execute(f"VACUUM ANALYZE {table}")
            logger.info(f"✅ Optimized table: {table}")
        except Exception as e:
            logger.error(f"Failed to optimize table {table}: {e}")
    
    # Update statistics
    try:
        logger.info("Updating database statistics...")
        cur.execute("ANALYZE")
        logger.info("✅ Updated database statistics")
    except Exception as e:
        logger.error(f"Failed to update statistics: {e}")
    
    # Check connection stats
    try:
        cur.execute("SHOW max_connections")
        max_conn = cur.fetchone()[0]
        logger.info(f"PostgreSQL max_connections: {max_conn}")
        
        cur.execute("SELECT count(*) FROM pg_stat_activity")
        current_conn = cur.fetchone()[0]
        logger.info(f"Current active connections: {current_conn}")
        
        # Get table sizes
        cur.execute("""
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
            FROM pg_tables
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            LIMIT 10
        """)
        
        logger.info("\nTop 10 largest tables:")
        for row in cur.fetchall():
            logger.info(f"  {row[0]}.{row[1]}: {row[2]}")
        
        # Get index usage stats
        cur.execute("""
            SELECT 
                schemaname,
                tablename,
                indexname,
                idx_scan,
                idx_tup_read,
                idx_tup_fetch
            FROM pg_stat_user_indexes
            ORDER BY idx_scan DESC
            LIMIT 10
        """)
        
        logger.info("\nTop 10 most used indexes:")
        for row in cur.fetchall():
            logger.info(f"  {row[2]} on {row[0]}.{row[1]}: {row[3]} scans")
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
    
    cur.close()
    conn.close()
    
    logger.info("\n" + "="*60)
    logger.info("DATABASE OPTIMIZATION COMPLETE")
    logger.info("="*60)

if __name__ == "__main__":
    optimize_database()
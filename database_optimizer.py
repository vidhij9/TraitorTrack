"""
Database optimization and performance tuning utilities
"""
import logging
from app_clean import db
from sqlalchemy import text, Index
from models import User, Bag, Scan, Bill, BillBag, Link

logger = logging.getLogger(__name__)

def create_optimized_indexes():
    """Create optimized database indexes for better query performance"""
    try:
        # Create composite indexes for frequently used query patterns
        indexes_to_create = [
            # Bag table optimizations
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_qr_type_status ON bag(qr_id, type, status) WHERE status = 'active'",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_parent_type_active ON bag(parent_id, type) WHERE status = 'active' AND parent_id IS NOT NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_created_desc ON bag(created_at DESC)",
            
            # Scan table optimizations for high-frequency queries
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_timestamp_desc ON scan(timestamp DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_parent_timestamp ON scan(parent_bag_id, timestamp DESC) WHERE parent_bag_id IS NOT NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_child_timestamp ON scan(child_bag_id, timestamp DESC) WHERE child_bag_id IS NOT NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_user_date ON scan(user_id, DATE(timestamp))",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_daily_stats ON scan(DATE(timestamp), scan_type)",
            
            # User table optimizations
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_username_verified ON user(username, verified)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_role_created ON user(role, created_at DESC)",
            
            # Bill table optimizations
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_status_updated ON bill(status, updated_at DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_created_status ON bill(created_at DESC, status)",
            
            # Link table optimizations
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_parent_status ON link(parent_bag_id, status) WHERE status = 'active'",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_child_unique ON link(child_bag_id) WHERE status = 'active'",
            
            # BillBag optimizations
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_billbag_bill_created ON billbag(bill_id, created_at DESC)",
        ]
        
        for index_sql in indexes_to_create:
            try:
                db.session.execute(text(index_sql))
                db.session.commit()
                logger.info(f"Created index: {index_sql.split()[-1]}")
            except Exception as e:
                db.session.rollback()
                logger.warning(f"Index creation skipped (may already exist): {str(e)}")
        
        logger.info("Database index optimization completed")
        return True
        
    except Exception as e:
        logger.error(f"Database index optimization failed: {str(e)}")
        db.session.rollback()
        return False

def optimize_database_settings():
    """Apply PostgreSQL performance optimizations"""
    try:
        optimizations = [
            # Connection and memory settings
            "SET shared_preload_libraries = 'pg_stat_statements'",
            "SET max_connections = 200",
            "SET shared_buffers = '256MB'",
            "SET effective_cache_size = '1GB'",
            "SET maintenance_work_mem = '64MB'",
            "SET checkpoint_completion_target = 0.9",
            "SET wal_buffers = '16MB'",
            "SET default_statistics_target = 100",
            
            # Query optimization
            "SET random_page_cost = 1.1",
            "SET effective_io_concurrency = 200",
            "SET work_mem = '4MB'",
            
            # Enable query planning optimizations
            "SET enable_seqscan = on",
            "SET enable_indexscan = on",
            "SET enable_bitmapscan = on",
            "SET enable_hashjoin = on",
            "SET enable_mergejoin = on",
            "SET enable_nestloop = on",
        ]
        
        for setting in optimizations:
            try:
                db.session.execute(text(setting))
                logger.debug(f"Applied setting: {setting}")
            except Exception as e:
                logger.warning(f"Setting not applied: {setting} - {str(e)}")
        
        db.session.commit()
        logger.info("Database settings optimization completed")
        return True
        
    except Exception as e:
        logger.error(f"Database settings optimization failed: {str(e)}")
        db.session.rollback()
        return False

def analyze_table_statistics():
    """Update table statistics for better query planning"""
    try:
        tables = ['bag', 'scan', 'user', 'bill', 'billbag', 'link']
        
        for table in tables:
            db.session.execute(text(f"ANALYZE {table}"))
            logger.debug(f"Analyzed table: {table}")
        
        db.session.commit()
        logger.info("Table statistics analysis completed")
        return True
        
    except Exception as e:
        logger.error(f"Table statistics analysis failed: {str(e)}")
        db.session.rollback()
        return False

def get_slow_queries(limit=10):
    """Get slowest queries from pg_stat_statements"""
    try:
        query = text("""
            SELECT 
                query,
                calls,
                total_time,
                mean_time,
                rows,
                100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
            FROM pg_stat_statements 
            WHERE query NOT LIKE '%pg_stat_statements%'
            ORDER BY total_time DESC 
            LIMIT :limit
        """)
        
        result = db.session.execute(query, {'limit': limit})
        return result.fetchall()
        
    except Exception as e:
        logger.error(f"Failed to get slow queries: {str(e)}")
        return []

def get_index_usage():
    """Get index usage statistics"""
    try:
        query = text("""
            SELECT 
                schemaname,
                tablename,
                indexname,
                idx_tup_read,
                idx_tup_fetch,
                idx_scan
            FROM pg_stat_user_indexes 
            ORDER BY idx_scan DESC
        """)
        
        result = db.session.execute(query)
        return result.fetchall()
        
    except Exception as e:
        logger.error(f"Failed to get index usage: {str(e)}")
        return []

def vacuum_and_reindex():
    """Perform database maintenance operations"""
    try:
        # Get all user tables
        tables_query = text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename NOT LIKE 'pg_%'
        """)
        
        result = db.session.execute(tables_query)
        tables = [row[0] for row in result.fetchall()]
        
        for table in tables:
            try:
                # Vacuum analyze each table
                db.session.execute(text(f"VACUUM ANALYZE {table}"))
                logger.debug(f"Vacuumed table: {table}")
            except Exception as e:
                logger.warning(f"Failed to vacuum table {table}: {str(e)}")
        
        db.session.commit()
        logger.info("Database vacuum and reindex completed")
        return True
        
    except Exception as e:
        logger.error(f"Database maintenance failed: {str(e)}")
        db.session.rollback()
        return False

def get_database_size_info():
    """Get database size and table information"""
    try:
        size_query = text("""
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        """)
        
        result = db.session.execute(size_query)
        return result.fetchall()
        
    except Exception as e:
        logger.error(f"Failed to get database size info: {str(e)}")
        return []

def optimize_scan_queries():
    """Create specific optimizations for scan-heavy queries"""
    try:
        # Create functional indexes for common scan patterns
        scan_optimizations = [
            # Daily scan counts
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_date_func ON scan(DATE(timestamp))",
            
            # Recent scans with user info
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_recent_with_user ON scan(timestamp DESC, user_id) WHERE timestamp > NOW() - INTERVAL '7 days'",
            
            # Bag scan counts
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_parent_count ON scan(parent_bag_id) WHERE parent_bag_id IS NOT NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_child_count ON scan(child_bag_id) WHERE child_bag_id IS NOT NULL",
            
            # User activity tracking
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_user_activity ON scan(user_id, timestamp DESC, scan_type)",
        ]
        
        for optimization in scan_optimizations:
            try:
                db.session.execute(text(optimization))
                db.session.commit()
                logger.info(f"Applied scan optimization: {optimization.split()[-1]}")
            except Exception as e:
                db.session.rollback()
                logger.warning(f"Scan optimization skipped: {str(e)}")
        
        return True
        
    except Exception as e:
        logger.error(f"Scan query optimization failed: {str(e)}")
        return False

def run_full_optimization():
    """Run complete database optimization suite"""
    logger.info("Starting full database optimization...")
    
    results = {
        'indexes': create_optimized_indexes(),
        'settings': optimize_database_settings(),
        'statistics': analyze_table_statistics(),
        'scan_optimizations': optimize_scan_queries(),
        'maintenance': vacuum_and_reindex()
    }
    
    success_count = sum(results.values())
    total_count = len(results)
    
    logger.info(f"Database optimization completed: {success_count}/{total_count} operations successful")
    
    return results

if __name__ == "__main__":
    # Run optimization when script is executed directly
    logging.basicConfig(level=logging.INFO)
    run_full_optimization()

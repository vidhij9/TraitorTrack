"""
Database Performance Setup for 4+ Lakh Bags
===========================================

Sets up PostgreSQL extensions and optimizations for ultra-fast search
on databases with 400,000+ bags.
"""

import logging
from sqlalchemy import text
from app import db

logger = logging.getLogger(__name__)

def setup_postgresql_extensions():
    """Enable PostgreSQL extensions for high-performance search"""
    try:
        extensions = [
            # Trigram similarity for fuzzy search
            "CREATE EXTENSION IF NOT EXISTS pg_trgm",
            
            # Statistics for query optimization
            "CREATE EXTENSION IF NOT EXISTS pg_stat_statements",
            
            # Additional performance extensions
            "CREATE EXTENSION IF NOT EXISTS btree_gin",
            "CREATE EXTENSION IF NOT EXISTS btree_gist",
        ]
        
        for extension_sql in extensions:
            try:
                db.session.execute(text(extension_sql))
                db.session.commit()
                extension_name = extension_sql.split()[-1]
                logger.info(f"Enabled PostgreSQL extension: {extension_name}")
            except Exception as e:
                db.session.rollback()
                logger.warning(f"Extension setup skipped (may already exist): {str(e)}")
        
        logger.info("PostgreSQL extensions setup completed")
        return True
        
    except Exception as e:
        logger.error(f"PostgreSQL extensions setup failed: {str(e)}")
        db.session.rollback()
        return False

def create_ultra_fast_indexes():
    """Create ultra-fast indexes optimized for 4+ lakh bags"""
    try:
        # Ultra-fast indexes for massive scale operations
        ultra_indexes = [
            # Primary search indexes with case insensitive support
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_qr_upper ON bag(UPPER(qr_id))",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_qr_trgm ON bag USING gin(qr_id gin_trgm_ops)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_name_trgm ON bag USING gin(name gin_trgm_ops)",
            
            # Composite indexes for complex queries
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_type_qr ON bag(type, UPPER(qr_id))",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_area_type ON bag(dispatch_area, type) WHERE dispatch_area IS NOT NULL",
            
            # Optimized relationship indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_parent_child_fast ON link(parent_bag_id, child_bag_id) WHERE status = 'active'",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_child_parent_fast ON link(child_bag_id, parent_bag_id) WHERE status = 'active'",
            
            # Time-series optimized indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_created_desc_fast ON bag(created_at DESC) WHERE created_at IS NOT NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_timestamp_fast ON scan(timestamp DESC)",
            
            # Bill relationship indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_billbag_bag_bill ON billbag(bag_id, bill_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_status_created ON bill(status, created_at DESC)",
            
            # User-based indexes for role filtering
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_role_area ON \"user\"(role, dispatch_area) WHERE dispatch_area IS NOT NULL",
        ]
        
        for index_sql in ultra_indexes:
            try:
                db.session.execute(text(index_sql))
                db.session.commit()
                index_name = index_sql.split()[-1] if 'ON' in index_sql else "unnamed"
                logger.info(f"Created ultra-fast index: {index_name}")
            except Exception as e:
                db.session.rollback()
                logger.warning(f"Ultra-fast index creation skipped (may already exist): {str(e)}")
        
        logger.info("Ultra-fast indexes creation completed")
        return True
        
    except Exception as e:
        logger.error(f"Ultra-fast indexes creation failed: {str(e)}")
        db.session.rollback()
        return False

def optimize_postgresql_for_scale():
    """Configure PostgreSQL for handling 4+ lakh bags efficiently"""
    try:
        # High-performance settings for large scale operations
        scale_optimizations = [
            # Memory and connection optimization
            "SET max_connections = 300",
            "SET shared_buffers = '512MB'",
            "SET effective_cache_size = '2GB'",
            "SET maintenance_work_mem = '128MB'",
            "SET work_mem = '8MB'",
            
            # Query optimization
            "SET random_page_cost = 1.1",
            "SET effective_io_concurrency = 300", 
            "SET default_statistics_target = 500",
            
            # Write optimization
            "SET wal_buffers = '32MB'",
            "SET checkpoint_completion_target = 0.9",
            "SET checkpoint_timeout = '15min'",
            "SET max_wal_size = '4GB'",
            "SET min_wal_size = '1GB'",
            
            # Vacuum and autovacuum optimization
            "SET autovacuum_max_workers = 6",
            "SET autovacuum_naptime = '30s'",
            "SET autovacuum_vacuum_scale_factor = 0.1",
            "SET autovacuum_analyze_scale_factor = 0.05",
            
            # Advanced query optimization
            "SET enable_seqscan = on",
            "SET enable_indexscan = on", 
            "SET enable_bitmapscan = on",
            "SET enable_hashjoin = on",
            "SET enable_mergejoin = on",
            "SET enable_nestloop = on",
            
            # Parallel processing
            "SET max_parallel_workers_per_gather = 4",
            "SET max_parallel_workers = 8",
            "SET parallel_tuple_cost = 0.1",
            "SET parallel_setup_cost = 1000.0",
        ]
        
        for setting in scale_optimizations:
            try:
                db.session.execute(text(setting))
                logger.debug(f"Applied scale optimization: {setting.split('=')[0].strip()}")
            except Exception as e:
                logger.warning(f"Scale optimization not applied: {setting} - {str(e)}")
        
        db.session.commit()
        logger.info("PostgreSQL scale optimization completed")
        return True
        
    except Exception as e:
        logger.error(f"PostgreSQL scale optimization failed: {str(e)}")
        db.session.rollback()
        return False

def update_table_statistics():
    """Update table statistics for optimal query planning"""
    try:
        # Update statistics for all major tables
        tables = ['bag', 'scan', 'user', 'bill', 'billbag', 'link']
        
        for table in tables:
            # Update statistics with higher detail level
            db.session.execute(text(f"ANALYZE {table}"))
            logger.debug(f"Updated statistics for table: {table}")
        
        # Update global statistics
        db.session.execute(text("ANALYZE"))
        
        db.session.commit()
        logger.info("Table statistics update completed")
        return True
        
    except Exception as e:
        logger.error(f"Table statistics update failed: {str(e)}")
        db.session.rollback()
        return False

def setup_ultra_fast_database():
    """Complete setup for ultra-fast database performance"""
    logger.info("Starting ultra-fast database setup for 4+ lakh bags...")
    
    success_count = 0
    total_steps = 4
    
    # Step 1: Enable PostgreSQL extensions
    if setup_postgresql_extensions():
        success_count += 1
    
    # Step 2: Create ultra-fast indexes  
    if create_ultra_fast_indexes():
        success_count += 1
    
    # Step 3: Optimize PostgreSQL settings
    if optimize_postgresql_for_scale():
        success_count += 1
        
    # Step 4: Update table statistics
    if update_table_statistics():
        success_count += 1
    
    if success_count == total_steps:
        logger.info(f"✅ Ultra-fast database setup completed successfully ({success_count}/{total_steps} steps)")
        return True
    else:
        logger.warning(f"⚠️  Ultra-fast database setup completed with warnings ({success_count}/{total_steps} steps)")
        return False

if __name__ == '__main__':
    setup_ultra_fast_database()
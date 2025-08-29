#!/usr/bin/env python3
"""
Database Optimization Script for 800,000+ Bags
Creates optimized indexes and runs performance tuning
"""

import time
import logging
from sqlalchemy import text
from app_clean import app, db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_optimized_indexes():
    """Create all performance-critical indexes"""
    
    indexes = [
        # Primary indexes for bag lookups (case-insensitive)
        ("idx_bag_qr_upper", "CREATE INDEX IF NOT EXISTS idx_bag_qr_upper ON bag(UPPER(qr_id))"),
        ("idx_bag_qr_lower", "CREATE INDEX IF NOT EXISTS idx_bag_qr_lower ON bag(LOWER(qr_id))"),
        
        # Type and status filtering (most common queries)
        ("idx_bag_type", "CREATE INDEX  IF NOT EXISTS idx_bag_type ON bag(type)"),
        ("idx_bag_status", "CREATE INDEX  IF NOT EXISTS idx_bag_status ON bag(status)"),
        ("idx_bag_type_status", "CREATE INDEX  IF NOT EXISTS idx_bag_type_status ON bag(type, status)"),
        
        # Temporal queries
        ("idx_bag_created_desc", "CREATE INDEX  IF NOT EXISTS idx_bag_created_desc ON bag(created_at DESC)"),
        ("idx_bag_updated_desc", "CREATE INDEX  IF NOT EXISTS idx_bag_updated_desc ON bag(updated_at DESC)"),
        
        # Area-based filtering for dispatchers
        ("idx_bag_dispatch_area", "CREATE INDEX  IF NOT EXISTS idx_bag_dispatch_area ON bag(dispatch_area) WHERE dispatch_area IS NOT NULL"),
        ("idx_bag_type_area", "CREATE INDEX  IF NOT EXISTS idx_bag_type_area ON bag(type, dispatch_area)"),
        
        # Parent-child relationships
        ("idx_bag_parent_id", "CREATE INDEX  IF NOT EXISTS idx_bag_parent_id ON bag(parent_id) WHERE parent_id IS NOT NULL"),
        
        # User ownership
        ("idx_bag_user_id", "CREATE INDEX  IF NOT EXISTS idx_bag_user_id ON bag(user_id) WHERE user_id IS NOT NULL"),
        
        # Composite indexes for complex queries
        ("idx_bag_type_created", "CREATE INDEX  IF NOT EXISTS idx_bag_type_created ON bag(type, created_at DESC)"),
        ("idx_bag_type_area_status", "CREATE INDEX  IF NOT EXISTS idx_bag_type_area_status ON bag(type, dispatch_area, status)"),
        ("idx_bag_user_type_status", "CREATE INDEX  IF NOT EXISTS idx_bag_user_type_status ON bag(user_id, type, status)"),
        
        # Partial indexes for common filters
        ("idx_bag_parent_pending", "CREATE INDEX  IF NOT EXISTS idx_bag_parent_pending ON bag(id) WHERE type = 'parent' AND status = 'pending'"),
        ("idx_bag_parent_completed", "CREATE INDEX  IF NOT EXISTS idx_bag_parent_completed ON bag(id) WHERE type = 'parent' AND status = 'completed'"),
        ("idx_bag_child_unlinked", "CREATE INDEX  IF NOT EXISTS idx_bag_child_unlinked ON bag(id) WHERE type = 'child' AND parent_id IS NULL"),
        
        # Link table indexes for fast joins
        ("idx_link_parent", "CREATE INDEX  IF NOT EXISTS idx_link_parent ON link(parent_bag_id)"),
        ("idx_link_child", "CREATE INDEX  IF NOT EXISTS idx_link_child ON link(child_bag_id)"),
        ("idx_link_parent_child", "CREATE INDEX  IF NOT EXISTS idx_link_parent_child ON link(parent_bag_id, child_bag_id)"),
        ("idx_link_created", "CREATE INDEX  IF NOT EXISTS idx_link_created ON link(created_at DESC)"),
        
        # Scan table indexes for activity tracking
        ("idx_scan_timestamp_desc", "CREATE INDEX  IF NOT EXISTS idx_scan_timestamp_desc ON scan(timestamp DESC)"),
        ("idx_scan_user_id", "CREATE INDEX  IF NOT EXISTS idx_scan_user_id ON scan(user_id)"),
        ("idx_scan_parent_bag", "CREATE INDEX  IF NOT EXISTS idx_scan_parent_bag ON scan(parent_bag_id) WHERE parent_bag_id IS NOT NULL"),
        ("idx_scan_child_bag", "CREATE INDEX  IF NOT EXISTS idx_scan_child_bag ON scan(child_bag_id) WHERE child_bag_id IS NOT NULL"),
        ("idx_scan_user_timestamp", "CREATE INDEX  IF NOT EXISTS idx_scan_user_timestamp ON scan(user_id, timestamp DESC)"),
        
        # Partial index for recent scans (last 7 days)
        ("idx_scan_recent", "CREATE INDEX  IF NOT EXISTS idx_scan_recent ON scan(timestamp DESC) WHERE timestamp > CURRENT_DATE - INTERVAL '7 days'"),
        
        # Bill table indexes
        ("idx_bill_id_upper", "CREATE INDEX  IF NOT EXISTS idx_bill_id_upper ON bill(UPPER(bill_id))"),
        ("idx_bill_status", "CREATE INDEX  IF NOT EXISTS idx_bill_status ON bill(status)"),
        ("idx_bill_created", "CREATE INDEX  IF NOT EXISTS idx_bill_created ON bill(created_at DESC)"),
        ("idx_bill_status_created", "CREATE INDEX  IF NOT EXISTS idx_bill_status_created ON bill(status, created_at DESC)"),
        
        # Bill-bag relationship indexes
        ("idx_bill_bag_bill", "CREATE INDEX  IF NOT EXISTS idx_bill_bag_bill ON bill_bag(bill_id)"),
        ("idx_bill_bag_bag", "CREATE INDEX  IF NOT EXISTS idx_bill_bag_bag ON bill_bag(bag_id)"),
        
        # User table indexes
        ("idx_user_username_lower", "CREATE INDEX  IF NOT EXISTS idx_user_username_lower ON \"user\"(LOWER(username))"),
        ("idx_user_email_lower", "CREATE INDEX  IF NOT EXISTS idx_user_email_lower ON \"user\"(LOWER(email))"),
        ("idx_user_role", "CREATE INDEX  IF NOT EXISTS idx_user_role ON \"user\"(role)"),
        ("idx_user_dispatch_area", "CREATE INDEX  IF NOT EXISTS idx_user_dispatch_area ON \"user\"(dispatch_area) WHERE dispatch_area IS NOT NULL"),
        
        # Audit log indexes
        ("idx_audit_timestamp", "CREATE INDEX  IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC)"),
        ("idx_audit_user", "CREATE INDEX  IF NOT EXISTS idx_audit_user ON audit_log(user_id)"),
        ("idx_audit_action", "CREATE INDEX  IF NOT EXISTS idx_audit_action ON audit_log(action)"),
        ("idx_audit_entity", "CREATE INDEX  IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id)"),
    ]
    
    with app.app_context():
        successful = 0
        failed = 0
        
        for index_name, index_sql in indexes:
            try:
                logger.info(f"Creating index: {index_name}")
                start_time = time.time()
                db.session.execute(text(index_sql))
                db.session.commit()
                elapsed = time.time() - start_time
                logger.info(f"✅ Created {index_name} in {elapsed:.2f}s")
                successful += 1
            except Exception as e:
                db.session.rollback()
                if "already exists" in str(e):
                    logger.info(f"ℹ️ Index {index_name} already exists")
                    successful += 1
                else:
                    logger.error(f"❌ Failed to create {index_name}: {e}")
                    failed += 1
        
        logger.info(f"\n📊 Index creation complete: {successful} successful, {failed} failed")
        return successful, failed

def analyze_tables():
    """Update table statistics for query optimizer"""
    
    tables = ['bag', 'link', 'scan', 'bill', 'bill_bag', '"user"', 'audit_log']
    
    with app.app_context():
        logger.info("\n🔍 Analyzing tables for query optimization...")
        
        for table in tables:
            try:
                logger.info(f"Analyzing {table}...")
                db.session.execute(text(f"ANALYZE {table}"))
                db.session.commit()
                logger.info(f"✅ Analyzed {table}")
            except Exception as e:
                db.session.rollback()
                logger.error(f"❌ Failed to analyze {table}: {e}")

def get_table_statistics():
    """Get current table statistics"""
    
    with app.app_context():
        try:
            result = db.session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    n_live_tup as row_count,
                    n_dead_tup as dead_rows,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    last_autoanalyze
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                ORDER BY n_live_tup DESC
            """))
            
            logger.info("\n📊 Table Statistics:")
            logger.info("-" * 80)
            
            for row in result:
                logger.info(f"""
Table: {row.tablename}
  - Rows: {row.row_count:,}
  - Dead rows: {row.dead_rows:,}
  - Size: {row.total_size}
  - Last vacuum: {row.last_vacuum or 'Never'}
  - Last analyze: {row.last_analyze or 'Never'}
                """.strip())
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")

def check_index_usage():
    """Check which indexes are being used"""
    
    with app.app_context():
        try:
            result = db.session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan as index_scans,
                    idx_tup_read as tuples_read,
                    idx_tup_fetch as tuples_fetched,
                    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
                FROM pg_stat_user_indexes
                WHERE schemaname = 'public'
                ORDER BY idx_scan DESC
                LIMIT 20
            """))
            
            logger.info("\n📈 Top 20 Most Used Indexes:")
            logger.info("-" * 80)
            
            for row in result:
                efficiency = (row.tuples_fetched / row.index_scans) if row.index_scans > 0 else 0
                logger.info(f"{row.indexname:40} | Scans: {row.index_scans:8,} | Size: {row.index_size:10} | Efficiency: {efficiency:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to check index usage: {e}")

def optimize_for_bulk_operations():
    """Optimize settings for bulk operations"""
    
    with app.app_context():
        try:
            # Temporarily adjust settings for bulk operations
            optimizations = [
                "SET work_mem = '256MB'",
                "SET maintenance_work_mem = '512MB'",
                "SET checkpoint_completion_target = 0.9",
                "SET wal_buffers = '16MB'",
                "SET default_statistics_target = 100",
                "SET random_page_cost = 1.1",
                "SET effective_io_concurrency = 200",
                "SET max_parallel_workers_per_gather = 4",
            ]
            
            logger.info("\n⚡ Applying bulk operation optimizations...")
            
            for optimization in optimizations:
                try:
                    db.session.execute(text(optimization))
                    logger.info(f"✅ Applied: {optimization}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not apply {optimization}: {e}")
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to optimize for bulk operations: {e}")

def create_materialized_views():
    """Create materialized views for complex queries"""
    
    views = [
        ("mv_dashboard_stats", """
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_dashboard_stats AS
            SELECT 
                COUNT(*) FILTER (WHERE type = 'parent') as parent_count,
                COUNT(*) FILTER (WHERE type = 'child') as child_count,
                COUNT(*) FILTER (WHERE status = 'completed') as completed_count,
                COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
                COUNT(*) as total_bags,
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(DISTINCT dispatch_area) as active_areas
            FROM bag
            WITH DATA
        """),
        
        ("mv_hourly_activity", """
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_hourly_activity AS
            SELECT 
                DATE_TRUNC('hour', timestamp) as hour,
                COUNT(*) as scan_count,
                COUNT(DISTINCT user_id) as active_users,
                COUNT(DISTINCT parent_bag_id) as parent_bags_scanned,
                COUNT(DISTINCT child_bag_id) as child_bags_scanned
            FROM scan
            WHERE timestamp > CURRENT_DATE - INTERVAL '7 days'
            GROUP BY DATE_TRUNC('hour', timestamp)
            WITH DATA
        """),
        
        ("mv_user_performance", """
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_user_performance AS
            SELECT 
                u.id as user_id,
                u.username,
                u.role,
                COUNT(DISTINCT s.id) as total_scans,
                COUNT(DISTINCT b.id) as bags_created,
                COUNT(DISTINCT s.parent_bag_id) as parents_scanned,
                COUNT(DISTINCT s.child_bag_id) as children_scanned,
                MAX(s.timestamp) as last_activity
            FROM "user" u
            LEFT JOIN scan s ON u.id = s.user_id
            LEFT JOIN bag b ON u.id = b.user_id
            GROUP BY u.id, u.username, u.role
            WITH DATA
        """),
    ]
    
    with app.app_context():
        logger.info("\n🔮 Creating materialized views...")
        
        for view_name, view_sql in views:
            try:
                # Drop existing view if it exists
                db.session.execute(text(f"DROP MATERIALIZED VIEW IF EXISTS {view_name}"))
                
                # Create the view
                db.session.execute(text(view_sql))
                
                # Create index on the view
                db.session.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{view_name}_unique ON {view_name}((1))"))
                
                db.session.commit()
                logger.info(f"✅ Created materialized view: {view_name}")
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"❌ Failed to create view {view_name}: {e}")

def refresh_materialized_views():
    """Refresh all materialized views"""
    
    views = ['mv_dashboard_stats', 'mv_hourly_activity', 'mv_user_performance']
    
    with app.app_context():
        logger.info("\n🔄 Refreshing materialized views...")
        
        for view_name in views:
            try:
                start_time = time.time()
                db.session.execute(text(f"REFRESH MATERIALIZED VIEW  {view_name}"))
                db.session.commit()
                elapsed = time.time() - start_time
                logger.info(f"✅ Refreshed {view_name} in {elapsed:.2f}s")
            except Exception as e:
                db.session.rollback()
                logger.warning(f"⚠️ Could not refresh {view_name}: {e}")

def main():
    """Run all optimization tasks"""
    
    logger.info("=" * 80)
    logger.info("🚀 DATABASE OPTIMIZATION FOR 800,000+ BAGS")
    logger.info("=" * 80)
    
    # Create indexes
    create_optimized_indexes()
    
    # Analyze tables
    analyze_tables()
    
    # Get statistics
    get_table_statistics()
    
    # Check index usage
    check_index_usage()
    
    # Optimize for bulk operations
    optimize_for_bulk_operations()
    
    # Create materialized views
    create_materialized_views()
    
    # Refresh views
    refresh_materialized_views()
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ DATABASE OPTIMIZATION COMPLETE!")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
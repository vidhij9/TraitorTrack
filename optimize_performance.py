"""
Performance optimization script for TraceTrack application
Run this to optimize database queries and add proper indexing
"""
import logging
from app_clean import app, db
from sqlalchemy import text
from database_optimizer import run_full_optimization

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_performance_indexes():
    """Add specific indexes for the slowest queries"""
    try:
        with app.app_context():
            # Critical performance indexes for the slowest queries
            performance_indexes = [
                # Optimize /bags endpoint (currently 2.5s)
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_type_dispatch_created ON bag(type, dispatch_area, created_at DESC)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_search ON bag USING gin(to_tsvector('english', qr_id || ' ' || COALESCE(name, '')))",
                
                # Optimize /bills endpoint (currently 1.4s)
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_status_created ON bill(status, created_at DESC)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_billbag_bill_bag ON billbag(bill_id, bag_id)",
                
                # Optimize scan queries
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_user_timestamp ON scan(user_id, timestamp DESC)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_bags ON scan(parent_bag_id, child_bag_id, timestamp DESC)",
                
                # Optimize link queries
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_parent_child ON link(parent_bag_id, child_bag_id)",
                
                # Optimize user queries
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_role_dispatch ON \"user\"(role, dispatch_area) WHERE verified = true",
                
                # Partial indexes for active records
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_active_parent ON bag(qr_id, dispatch_area) WHERE type = 'parent' AND status = 'active'",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_active_child ON bag(qr_id, parent_id) WHERE type = 'child' AND status = 'active'",
                
                # Covering indexes for common queries
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_covering ON bag(id, qr_id, name, type, dispatch_area, created_at)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_covering ON scan(id, timestamp, user_id, parent_bag_id, child_bag_id)"
            ]
            
            for index_sql in performance_indexes:
                try:
                    logger.info(f"Creating index: {index_sql.split('idx_')[1].split(' ')[0]}")
                    db.session.execute(text(index_sql))
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    logger.warning(f"Index may already exist: {str(e)}")
            
            logger.info("Performance indexes created successfully")
            return True
            
    except Exception as e:
        logger.error(f"Failed to create performance indexes: {str(e)}")
        return False

def optimize_database_config():
    """Apply database configuration optimizations"""
    try:
        with app.app_context():
            # PostgreSQL performance tuning
            optimizations = [
                # Connection pooling
                "ALTER SYSTEM SET max_connections = 200",
                "ALTER SYSTEM SET shared_buffers = '256MB'",
                
                # Query planning
                "ALTER SYSTEM SET random_page_cost = 1.1",
                "ALTER SYSTEM SET effective_cache_size = '1GB'",
                "ALTER SYSTEM SET work_mem = '8MB'",
                
                # Write performance
                "ALTER SYSTEM SET checkpoint_completion_target = 0.9",
                "ALTER SYSTEM SET wal_buffers = '16MB'",
                
                # Statistics
                "ALTER SYSTEM SET default_statistics_target = 100",
                "ALTER SYSTEM SET track_counts = on",
                "ALTER SYSTEM SET track_functions = 'all'",
                
                # Autovacuum tuning
                "ALTER SYSTEM SET autovacuum = on",
                "ALTER SYSTEM SET autovacuum_max_workers = 4",
                "ALTER SYSTEM SET autovacuum_naptime = '30s'"
            ]
            
            for optimization in optimizations:
                try:
                    db.session.execute(text(optimization))
                    logger.info(f"Applied: {optimization}")
                except Exception as e:
                    logger.warning(f"Could not apply {optimization}: {str(e)}")
            
            # Reload configuration
            try:
                db.session.execute(text("SELECT pg_reload_conf()"))
                db.session.commit()
                logger.info("Database configuration reloaded")
            except Exception as e:
                logger.warning(f"Could not reload config: {str(e)}")
            
            return True
            
    except Exception as e:
        logger.error(f"Database config optimization failed: {str(e)}")
        return False

def analyze_and_vacuum():
    """Run ANALYZE and VACUUM on all tables"""
    try:
        with app.app_context():
            tables = ['bag', 'scan', 'user', 'bill', 'billbag', 'link']
            
            for table in tables:
                try:
                    # ANALYZE for query planner statistics
                    db.session.execute(text(f'ANALYZE "{table}"'))
                    logger.info(f"Analyzed table: {table}")
                    
                    # VACUUM for dead tuple cleanup
                    db.session.execute(text(f'VACUUM (ANALYZE) "{table}"'))
                    logger.info(f"Vacuumed table: {table}")
                except Exception as e:
                    logger.warning(f"Could not vacuum/analyze {table}: {str(e)}")
            
            db.session.commit()
            return True
            
    except Exception as e:
        logger.error(f"Vacuum/analyze failed: {str(e)}")
        return False

def get_slow_queries():
    """Identify slow queries for optimization"""
    try:
        with app.app_context():
            # Check if pg_stat_statements is available
            check_query = text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                )
            """)
            
            result = db.session.execute(check_query).fetchone()
            
            if not result[0]:
                logger.info("pg_stat_statements not available, skipping slow query analysis")
                return []
            
            # Get top 10 slowest queries
            slow_queries = text("""
                SELECT 
                    substring(query, 1, 100) as query_preview,
                    calls,
                    round(total_exec_time::numeric, 2) as total_time_ms,
                    round(mean_exec_time::numeric, 2) as mean_time_ms,
                    round(stddev_exec_time::numeric, 2) as stddev_time_ms
                FROM pg_stat_statements
                WHERE query NOT LIKE '%pg_stat_statements%'
                  AND mean_exec_time > 100  -- Queries taking more than 100ms
                ORDER BY mean_exec_time DESC
                LIMIT 10
            """)
            
            result = db.session.execute(slow_queries)
            slow_list = []
            
            for row in result:
                slow_list.append({
                    'query': row.query_preview,
                    'calls': row.calls,
                    'total_time': row.total_time_ms,
                    'mean_time': row.mean_time_ms,
                    'stddev': row.stddev_time_ms
                })
                logger.warning(f"Slow query detected: {row.query_preview[:50]}... (avg: {row.mean_time_ms}ms)")
            
            return slow_list
            
    except Exception as e:
        logger.info(f"Could not analyze slow queries: {str(e)}")
        return []

def main():
    """Run all performance optimizations"""
    logger.info("=" * 60)
    logger.info("Starting performance optimization...")
    logger.info("=" * 60)
    
    results = {
        'indexes': add_performance_indexes(),
        'config': optimize_database_config(),
        'vacuum': analyze_and_vacuum(),
        'database_optimizer': False
    }
    
    # Run the comprehensive database optimizer
    try:
        with app.app_context():
            optimizer_results = run_full_optimization()
            results['database_optimizer'] = all(optimizer_results.values())
    except Exception as e:
        logger.error(f"Database optimizer failed: {str(e)}")
    
    # Check for slow queries
    slow_queries = get_slow_queries()
    if slow_queries:
        logger.warning(f"Found {len(slow_queries)} slow queries that need optimization")
    
    # Summary
    logger.info("=" * 60)
    logger.info("Performance Optimization Summary:")
    for key, value in results.items():
        status = "✓ Success" if value else "✗ Failed"
        logger.info(f"  {key.capitalize()}: {status}")
    logger.info("=" * 60)
    
    if all(results.values()):
        logger.info("✅ All optimizations completed successfully!")
        logger.info("The application should now be significantly faster.")
    else:
        logger.warning("⚠️ Some optimizations failed. Check logs for details.")
    
    return results

if __name__ == "__main__":
    main()
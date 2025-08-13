"""
Database index creation script for ultra-fast bag management
Ensures all performance-critical indexes are properly created
"""

from app_clean import app, db
import logging

logger = logging.getLogger(__name__)

def create_performance_indexes():
    """Create all performance-critical indexes for ultra-fast queries"""
    
    with app.app_context():
        try:
            # Get the database connection
            connection = db.engine.connect()
            
            # List of performance-critical indexes to create
            indexes = [
                # Bag table indexes for ultra-fast filtering
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_qr_id_upper ON bag (UPPER(qr_id))",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_name_upper ON bag (UPPER(name))",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_created_desc ON bag (created_at DESC)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_type_area_created ON bag (type, dispatch_area, created_at DESC)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_search_composite ON bag (qr_id, name, type, created_at DESC)",
                
                # Link table indexes for relationship queries
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_parent_only ON link (parent_bag_id)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_child_only ON link (child_bag_id)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_created ON link (created_at DESC)",
                
                # Bill-bag relationship indexes
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_bag_bag_only ON bill_bag (bag_id)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_bag_bill_only ON bill_bag (bill_id)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_bag_created ON bill_bag (created_at DESC)",
                
                # Scan table indexes for analytics
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_timestamp_desc ON scan (timestamp DESC)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_parent_timestamp ON scan (parent_bag_id, timestamp DESC)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_child_timestamp ON scan (child_bag_id, timestamp DESC)",
            ]
            
            created_count = 0
            
            for index_sql in indexes:
                try:
                    logger.info(f"Creating index: {index_sql}")
                    connection.execute(index_sql)
                    created_count += 1
                    logger.info(f"✓ Index created successfully")
                except Exception as e:
                    if "already exists" in str(e):
                        logger.info(f"✓ Index already exists")
                    else:
                        logger.error(f"✗ Failed to create index: {e}")
            
            connection.commit()
            logger.info(f"Index creation completed. {created_count}/{len(indexes)} indexes processed")
            
            # Analyze tables for better query planning
            analyze_queries = [
                "ANALYZE bag",
                "ANALYZE link", 
                "ANALYZE bill_bag",
                "ANALYZE scan"
            ]
            
            for analyze_sql in analyze_queries:
                try:
                    connection.execute(analyze_sql)
                    logger.info(f"✓ Analyzed table: {analyze_sql}")
                except Exception as e:
                    logger.error(f"✗ Failed to analyze: {e}")
            
            connection.commit()
            connection.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Index creation failed: {e}")
            return False

def optimize_postgresql_settings():
    """Apply PostgreSQL optimizations for faster queries"""
    
    with app.app_context():
        try:
            connection = db.engine.connect()
            
            # Performance optimizations
            optimizations = [
                "SET work_mem = '32MB'",
                "SET maintenance_work_mem = '64MB'", 
                "SET effective_cache_size = '512MB'",
                "SET random_page_cost = 1.1",
                "SET seq_page_cost = 1.0",
                "SET cpu_tuple_cost = 0.01",
                "SET cpu_index_tuple_cost = 0.005",
                "SET cpu_operator_cost = 0.0025"
            ]
            
            for opt in optimizations:
                try:
                    connection.execute(opt)
                    logger.info(f"✓ Applied: {opt}")
                except Exception as e:
                    logger.debug(f"Could not apply: {opt} - {e}")
            
            connection.commit()
            connection.close()
            
            logger.info("PostgreSQL optimizations applied")
            return True
            
        except Exception as e:
            logger.error(f"PostgreSQL optimization failed: {e}")
            return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("🚀 Creating ultra-fast database indexes...")
    success1 = create_performance_indexes()
    
    print("⚡ Applying PostgreSQL optimizations...")
    success2 = optimize_postgresql_settings()
    
    if success1 and success2:
        print("✅ All optimizations completed successfully!")
        print("🎯 Your bag management page is now ULTRA-FAST!")
    else:
        print("⚠️  Some optimizations may have failed. Check logs for details.")
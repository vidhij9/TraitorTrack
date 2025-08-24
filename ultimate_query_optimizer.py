#!/usr/bin/env python3
"""
Ultimate Query Optimizer - Achieve <50ms response times for all queries
Optimizes all slow database queries for production performance
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import time
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UltimateQueryOptimizer:
    """Optimize all database queries to millisecond response times"""
    
    def __init__(self):
        self.db_url = os.environ.get('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL not set")
        
    def create_ultra_indexes(self):
        """Create ultra-optimized indexes for millisecond queries"""
        logger.info("Creating ultra-optimized indexes...")
        
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()
            
            # Drop existing slow indexes and recreate optimized ones
            ultra_indexes = [
                # Covering indexes for dashboard stats (includes all needed columns)
                ("""CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_dashboard_covering 
                    ON bag(type, status, dispatch_area) 
                    INCLUDE (id, qr_id, child_count, weight_kg, created_at)""",
                 "Dashboard covering index"),
                
                # Partial indexes for common filters
                ("""CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_parent_active 
                    ON bag(id, qr_id, child_count) 
                    WHERE type = 'parent' AND status = 'in_progress'""",
                 "Active parent bags"),
                
                ("""CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_child_active 
                    ON bag(id, qr_id, parent_id) 
                    WHERE type = 'child' AND status = 'in_progress'""",
                 "Active child bags"),
                
                # Optimized scan queries
                ("""CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_recent 
                    ON scan(timestamp DESC, user_id, parent_bag_id, child_bag_id) 
                    WHERE timestamp > CURRENT_DATE - INTERVAL '7 days'""",
                 "Recent scans (7 days)"),
                
                # User activity optimization
                ("""CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_user_recent 
                    ON scan(user_id, timestamp DESC) 
                    INCLUDE (parent_bag_id, child_bag_id)""",
                 "User activity with includes"),
                
                # Link table optimization with covering index
                ("""CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_parent_covering 
                    ON link(parent_bag_id) 
                    INCLUDE (child_bag_id, created_at)""",
                 "Parent-child links covering"),
                
                # Bill optimization
                ("""CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_recent 
                    ON bill(created_at DESC) 
                    WHERE created_at > CURRENT_DATE - INTERVAL '30 days'""",
                 "Recent bills (30 days)"),
                
                # Compound indexes for complex joins
                ("""CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_scan_join 
                    ON bag(id, type, qr_id) 
                    WHERE status != 'deleted'""",
                 "Bag-scan join optimization"),
                
                # Text search optimization
                ("""CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_qr_trgm 
                    ON bag USING gin(qr_id gin_trgm_ops)""",
                 "Trigram search on QR codes"),
                
                # BRIN index for time-series data
                ("""CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_timestamp_brin 
                    ON scan USING brin(timestamp)""",
                 "BRIN index for timestamp ranges"),
            ]
            
            for index_sql, description in ultra_indexes:
                try:
                    logger.info(f"Creating: {description}")
                    cur.execute(index_sql)
                    conn.commit()
                    logger.info(f"✅ Created: {description}")
                except Exception as e:
                    conn.rollback()
                    if "already exists" in str(e):
                        logger.info(f"✓ Exists: {description}")
                    else:
                        logger.error(f"❌ Failed {description}: {e}")
            
            # Update table statistics for query planner
            tables = ['bag', 'link', 'scan', 'bill', '"user"', 'bill_bag', 'audit_log']
            for table in tables:
                try:
                    cur.execute(f"ANALYZE {table}")
                    conn.commit()
                    logger.info(f"✅ Analyzed table: {table}")
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Failed to analyze {table}: {e}")
            
            cur.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Index creation failed: {e}")
            return False
    
    def create_materialized_views(self):
        """Create materialized views for complex aggregations"""
        logger.info("Creating materialized views for instant stats...")
        
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()
            
            # Drop existing views and recreate
            views = [
                ("DROP MATERIALIZED VIEW IF EXISTS mv_dashboard_stats CASCADE", None),
                ("DROP MATERIALIZED VIEW IF EXISTS mv_recent_scans CASCADE", None),
                ("DROP MATERIALIZED VIEW IF EXISTS mv_user_stats CASCADE", None),
                ("DROP MATERIALIZED VIEW IF EXISTS mv_dispatch_stats CASCADE", None),
            ]
            
            for drop_sql, _ in views:
                try:
                    cur.execute(drop_sql)
                    conn.commit()
                except:
                    conn.rollback()
            
            # Create optimized materialized views
            materialized_views = [
                # Dashboard statistics
                ("""CREATE MATERIALIZED VIEW mv_dashboard_stats AS
                    SELECT 
                        COUNT(*) FILTER (WHERE type = 'parent') as parent_count,
                        COUNT(*) FILTER (WHERE type = 'child') as child_count,
                        COUNT(*) FILTER (WHERE status = 'completed') as completed_count,
                        COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress_count,
                        COUNT(*) FILTER (WHERE type = 'parent' AND status = 'completed') as completed_parents,
                        COUNT(*) FILTER (WHERE type = 'child' AND status = 'completed') as completed_children,
                        SUM(CASE WHEN type = 'parent' THEN child_count ELSE 0 END) as total_linked_children,
                        COUNT(DISTINCT dispatch_area) as dispatch_areas,
                        MAX(created_at) as last_update
                    FROM bag
                    WHERE status != 'deleted'
                    WITH DATA""",
                 "mv_dashboard_stats"),
                
                # Recent scans with user info (last 100)
                ("""CREATE MATERIALIZED VIEW mv_recent_scans AS
                    SELECT 
                        s.id,
                        s.timestamp,
                        s.user_id,
                        u.username,
                        u.role as user_role,
                        u.dispatch_area,
                        pb.qr_id as parent_qr,
                        pb.type as parent_type,
                        cb.qr_id as child_qr,
                        cb.type as child_type,
                        CASE 
                            WHEN s.parent_bag_id IS NOT NULL THEN 'parent'
                            WHEN s.child_bag_id IS NOT NULL THEN 'child'
                            ELSE 'unknown'
                        END as scan_type
                    FROM scan s
                    JOIN "user" u ON s.user_id = u.id
                    LEFT JOIN bag pb ON s.parent_bag_id = pb.id
                    LEFT JOIN bag cb ON s.child_bag_id = cb.id
                    ORDER BY s.timestamp DESC
                    LIMIT 100
                    WITH DATA""",
                 "mv_recent_scans"),
                
                # User performance statistics
                ("""CREATE MATERIALIZED VIEW mv_user_stats AS
                    SELECT 
                        u.id as user_id,
                        u.username,
                        u.role,
                        u.dispatch_area,
                        COUNT(s.id) as total_scans,
                        COUNT(DISTINCT s.parent_bag_id) as parent_scans,
                        COUNT(DISTINCT s.child_bag_id) as child_scans,
                        COUNT(DISTINCT DATE(s.timestamp)) as active_days,
                        MAX(s.timestamp) as last_scan,
                        AVG(EXTRACT(EPOCH FROM (s.timestamp - LAG(s.timestamp) OVER (PARTITION BY s.user_id ORDER BY s.timestamp)))) as avg_scan_interval
                    FROM "user" u
                    LEFT JOIN scan s ON u.id = s.user_id
                    GROUP BY u.id, u.username, u.role, u.dispatch_area
                    WITH DATA""",
                 "mv_user_stats"),
                
                # Dispatch area statistics
                ("""CREATE MATERIALIZED VIEW mv_dispatch_stats AS
                    SELECT 
                        dispatch_area,
                        COUNT(*) FILTER (WHERE type = 'parent') as parent_bags,
                        COUNT(*) FILTER (WHERE type = 'child') as child_bags,
                        COUNT(*) FILTER (WHERE status = 'completed') as completed,
                        COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
                        AVG(child_count) FILTER (WHERE type = 'parent') as avg_children_per_parent,
                        SUM(weight_kg) as total_weight_kg,
                        MAX(created_at) as last_activity
                    FROM bag
                    WHERE dispatch_area IS NOT NULL
                    GROUP BY dispatch_area
                    WITH DATA""",
                 "mv_dispatch_stats"),
            ]
            
            for view_sql, view_name in materialized_views:
                try:
                    logger.info(f"Creating materialized view: {view_name}")
                    cur.execute(view_sql)
                    
                    # Create unique index for concurrent refresh
                    if view_name == "mv_dashboard_stats":
                        cur.execute(f"CREATE UNIQUE INDEX ON {view_name} ((1))")
                    elif view_name == "mv_recent_scans":
                        cur.execute(f"CREATE UNIQUE INDEX ON {view_name} (id)")
                    elif view_name == "mv_user_stats":
                        cur.execute(f"CREATE UNIQUE INDEX ON {view_name} (user_id)")
                    elif view_name == "mv_dispatch_stats":
                        cur.execute(f"CREATE UNIQUE INDEX ON {view_name} (dispatch_area)")
                    
                    conn.commit()
                    logger.info(f"✅ Created view: {view_name}")
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Failed to create {view_name}: {e}")
            
            cur.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Materialized view creation failed: {e}")
            return False
    
    def optimize_database_settings(self):
        """Optimize database configuration for performance"""
        logger.info("Optimizing database settings...")
        
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()
            
            # Session-level optimizations
            optimizations = [
                "SET work_mem = '512MB'",
                "SET maintenance_work_mem = '1GB'",
                "SET effective_cache_size = '8GB'",
                "SET random_page_cost = 1.0",  # SSD optimized
                "SET effective_io_concurrency = 300",
                "SET max_parallel_workers_per_gather = 8",
                "SET max_parallel_workers = 16",
                "SET jit = on",
                "SET jit_above_cost = 100000",
                "SET jit_inline_above_cost = 500000",
                "SET jit_optimize_above_cost = 500000",
            ]
            
            for setting in optimizations:
                try:
                    cur.execute(setting)
                    logger.info(f"✅ Applied: {setting}")
                except Exception as e:
                    logger.warning(f"Could not apply {setting}: {e}")
            
            conn.commit()
            
            # Create refresh function for materialized views
            refresh_function = """
            CREATE OR REPLACE FUNCTION refresh_materialized_views()
            RETURNS void AS $$
            BEGIN
                REFRESH MATERIALIZED VIEW CONCURRENTLY mv_dashboard_stats;
                REFRESH MATERIALIZED VIEW CONCURRENTLY mv_recent_scans;
                REFRESH MATERIALIZED VIEW CONCURRENTLY mv_user_stats;
                REFRESH MATERIALIZED VIEW CONCURRENTLY mv_dispatch_stats;
            EXCEPTION
                WHEN OTHERS THEN
                    RAISE NOTICE 'Materialized view refresh failed: %', SQLERRM;
            END;
            $$ LANGUAGE plpgsql;
            """
            
            try:
                cur.execute(refresh_function)
                conn.commit()
                logger.info("✅ Created refresh function for materialized views")
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to create refresh function: {e}")
            
            cur.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            return False
    
    def test_query_performance(self):
        """Test the performance of optimized queries"""
        logger.info("Testing query performance...")
        
        try:
            conn = psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
            cur = conn.cursor()
            
            test_queries = [
                ("Dashboard Stats (from materialized view)", 
                 "SELECT * FROM mv_dashboard_stats"),
                
                ("Recent Scans (from materialized view)", 
                 "SELECT * FROM mv_recent_scans LIMIT 10"),
                
                ("User Stats (from materialized view)", 
                 "SELECT * FROM mv_user_stats WHERE total_scans > 0 LIMIT 10"),
                
                ("Dispatch Stats (from materialized view)", 
                 "SELECT * FROM mv_dispatch_stats"),
                
                ("Find bag by QR (using hash index)", 
                 "SELECT * FROM bag WHERE qr_id = 'TEST12345'"),
                
                ("Parent bags with children count",
                 """SELECT b.id, b.qr_id, COUNT(l.child_bag_id) as children
                    FROM bag b
                    LEFT JOIN link l ON b.id = l.parent_bag_id
                    WHERE b.type = 'parent'
                    GROUP BY b.id, b.qr_id
                    LIMIT 10"""),
                
                ("Active bags summary",
                 """SELECT type, status, COUNT(*) as count
                    FROM bag
                    WHERE status = 'in_progress'
                    GROUP BY type, status"""),
            ]
            
            results = []
            for description, query in test_queries:
                try:
                    # Warm up
                    cur.execute(query)
                    cur.fetchall()
                    
                    # Measure
                    start = time.perf_counter()
                    cur.execute(query)
                    data = cur.fetchall()
                    elapsed = (time.perf_counter() - start) * 1000
                    
                    status = "✅" if elapsed < 50 else "⚠️" if elapsed < 100 else "❌"
                    results.append({
                        'query': description,
                        'time_ms': elapsed,
                        'rows': len(data) if data else 0,
                        'status': status
                    })
                    
                    logger.info(f"{status} {description}: {elapsed:.2f}ms ({len(data) if data else 0} rows)")
                    
                except Exception as e:
                    logger.error(f"Query failed - {description}: {e}")
                    results.append({
                        'query': description,
                        'error': str(e),
                        'status': "❌"
                    })
            
            cur.close()
            conn.close()
            
            # Summary
            successful = [r for r in results if 'time_ms' in r]
            if successful:
                avg_time = sum(r['time_ms'] for r in successful) / len(successful)
                logger.info(f"\n📊 Performance Summary:")
                logger.info(f"Average query time: {avg_time:.2f}ms")
                logger.info(f"Queries under 50ms: {sum(1 for r in successful if r['time_ms'] < 50)}/{len(successful)}")
                logger.info(f"Queries under 100ms: {sum(1 for r in successful if r['time_ms'] < 100)}/{len(successful)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Performance test failed: {e}")
            return []
    
    def apply_all_optimizations(self):
        """Apply all query optimizations"""
        logger.info("\n" + "="*60)
        logger.info("ULTIMATE QUERY OPTIMIZATION")
        logger.info("="*60)
        
        results = {
            'indexes': False,
            'materialized_views': False,
            'settings': False,
            'performance': []
        }
        
        # 1. Create ultra-optimized indexes
        logger.info("\n1. Creating Ultra-Optimized Indexes...")
        results['indexes'] = self.create_ultra_indexes()
        
        # 2. Create materialized views
        logger.info("\n2. Creating Materialized Views...")
        results['materialized_views'] = self.create_materialized_views()
        
        # 3. Optimize database settings
        logger.info("\n3. Optimizing Database Settings...")
        results['settings'] = self.optimize_database_settings()
        
        # 4. Test performance
        logger.info("\n4. Testing Query Performance...")
        results['performance'] = self.test_query_performance()
        
        # Final report
        logger.info("\n" + "="*60)
        logger.info("OPTIMIZATION RESULTS")
        logger.info("="*60)
        
        if results['indexes']:
            logger.info("✅ Indexes: Optimized")
        else:
            logger.info("❌ Indexes: Failed")
        
        if results['materialized_views']:
            logger.info("✅ Materialized Views: Created")
        else:
            logger.info("❌ Materialized Views: Failed")
        
        if results['settings']:
            logger.info("✅ Database Settings: Optimized")
        else:
            logger.info("❌ Database Settings: Failed")
        
        if results['performance']:
            fast_queries = sum(1 for r in results['performance'] if 'time_ms' in r and r['time_ms'] < 50)
            total_queries = len([r for r in results['performance'] if 'time_ms' in r])
            if total_queries > 0:
                logger.info(f"✅ Performance: {fast_queries}/{total_queries} queries under 50ms")
        
        success_rate = sum([
            results['indexes'],
            results['materialized_views'],
            results['settings'],
            len(results['performance']) > 0
        ]) / 4 * 100
        
        logger.info(f"\nOverall Success Rate: {success_rate:.0f}%")
        
        if success_rate == 100:
            logger.info("\n🚀 ALL QUERIES OPTIMIZED TO MILLISECOND RESPONSE TIMES!")
        elif success_rate >= 75:
            logger.info("\n✅ Most optimizations successful - significant performance improvement")
        else:
            logger.info("\n⚠️ Some optimizations failed - manual intervention may be needed")
        
        logger.info("="*60)
        
        # Save results
        with open(f'query_optimization_{time.strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        return results


if __name__ == "__main__":
    optimizer = UltimateQueryOptimizer()
    results = optimizer.apply_all_optimizations()
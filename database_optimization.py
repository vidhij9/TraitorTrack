#!/usr/bin/env python3
"""
Database optimization script for TraceTrack
Analyzes and optimizes database performance for production readiness
"""

import os
import time
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def optimize_database():
    """Run database optimizations"""
    database_url = os.environ.get('DATABASE_URL')
    
    # Use NullPool to avoid connection pooling issues
    engine = create_engine(database_url, poolclass=NullPool)
    
    logger.info("Starting database optimization...")
    
    with engine.connect() as conn:
        # 1. Update table statistics
        logger.info("Updating table statistics...")
        tables = ['bag', 'scan', 'link', 'bill', 'user']
        for table in tables:
            try:
                conn.execute(text(f"ANALYZE {table}"))
                logger.info(f"  ✓ Analyzed {table}")
            except Exception as e:
                logger.error(f"  ✗ Failed to analyze {table}: {e}")
        
        # 2. Check for missing indexes on foreign keys
        logger.info("\nChecking for missing indexes on foreign keys...")
        missing_indexes = conn.execute(text("""
            SELECT
                c.conname AS constraint_name,
                cl.relname AS table_name,
                a.attname AS column_name
            FROM
                pg_constraint c
                JOIN pg_class cl ON c.conrelid = cl.oid
                JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
            WHERE
                c.contype = 'f'
                AND NOT EXISTS (
                    SELECT 1
                    FROM pg_index i
                    WHERE i.indrelid = c.conrelid
                    AND a.attnum = ANY(i.indkey)
                )
        """)).fetchall()
        
        if missing_indexes:
            logger.warning(f"Found {len(missing_indexes)} missing indexes on foreign keys")
            for idx in missing_indexes:
                logger.warning(f"  - {idx.table_name}.{idx.column_name}")
        else:
            logger.info("  ✓ All foreign keys have indexes")
        
        # 3. Check for unused indexes
        logger.info("\nChecking for unused indexes...")
        unused = conn.execute(text("""
            SELECT
                schemaname,
                tablename,
                indexname,
                idx_scan
            FROM pg_stat_user_indexes
            WHERE idx_scan = 0
            AND indexname NOT LIKE '%_pkey'
            ORDER BY tablename, indexname
        """)).fetchall()
        
        if unused:
            logger.info(f"Found {len(unused)} unused indexes (consider removing):")
            for idx in unused[:5]:  # Show first 5
                logger.info(f"  - {idx.tablename}.{idx.indexname}")
        
        # 4. Check query performance
        logger.info("\nTesting optimized queries...")
        
        # Optimized queries
        queries = [
            ("Count parent bags", "SELECT COUNT(*) FROM bag WHERE type = 'parent'"),
            ("Count child bags", "SELECT COUNT(*) FROM bag WHERE type = 'child'"),
            ("Recent scans (limited)", "SELECT * FROM scan ORDER BY timestamp DESC LIMIT 10"),
            ("Bag by QR (exact)", "SELECT * FROM bag WHERE qr_id = 'TEST' LIMIT 1"),
        ]
        
        for name, query in queries:
            start = time.time()
            conn.execute(text(query))
            elapsed = (time.time() - start) * 1000
            
            if elapsed < 50:
                logger.info(f"  ✓ {name}: {elapsed:.2f}ms")
            elif elapsed < 100:
                logger.warning(f"  ⚠ {name}: {elapsed:.2f}ms")
            else:
                logger.error(f"  ✗ {name}: {elapsed:.2f}ms")
        
        # 5. Connection pool recommendations
        logger.info("\nConnection pool analysis...")
        
        # Check current connections
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE state = 'active') as active,
                COUNT(*) FILTER (WHERE state = 'idle') as idle,
                COUNT(*) FILTER (WHERE state = 'idle in transaction') as idle_in_trans
            FROM pg_stat_activity
            WHERE datname = current_database()
        """)).fetchone()
        
        logger.info(f"Current connections: Total={result.total}, Active={result.active}, Idle={result.idle}")
        
        if result.total > 20:
            logger.warning("⚠ High connection count detected. Consider connection pooling.")
        
        # 6. Table bloat check
        logger.info("\nChecking table bloat...")
        bloat = conn.execute(text("""
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                n_dead_tup as dead_tuples,
                n_live_tup as live_tuples,
                ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) as dead_percent
            FROM pg_stat_user_tables
            WHERE n_dead_tup > 100
            ORDER BY n_dead_tup DESC
            LIMIT 5
        """)).fetchall()
        
        if bloat:
            logger.warning("Tables with dead tuples (consider VACUUM):")
            for b in bloat:
                logger.warning(f"  - {b.tablename}: {b.dead_tuples} dead ({b.dead_percent}%)")
        
        # 7. Recommendations
        logger.info("\n" + "="*60)
        logger.info("OPTIMIZATION RECOMMENDATIONS")
        logger.info("="*60)
        
        recommendations = []
        
        # Check if we're on a remote database
        if 'neon.tech' in database_url or 'amazonaws' in database_url:
            recommendations.append("Consider using a local database or edge location for lower latency")
            recommendations.append("Implement Redis caching for frequently accessed data")
        
        if result.total > 20:
            recommendations.append("Implement PgBouncer for connection pooling")
            recommendations.append("Reduce pool_size in SQLAlchemy to 10-15")
        
        if unused:
            recommendations.append(f"Remove {len(unused)} unused indexes to improve write performance")
        
        if bloat:
            recommendations.append("Run VACUUM ANALYZE on tables with high dead tuple count")
        
        recommendations.append("Use prepared statements for frequently executed queries")
        recommendations.append("Consider partitioning large tables (>1M rows)")
        recommendations.append("Implement query result caching for dashboard stats")
        
        for i, rec in enumerate(recommendations, 1):
            logger.info(f"{i}. {rec}")
        
        return recommendations


if __name__ == "__main__":
    optimize_database()
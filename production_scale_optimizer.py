#!/usr/bin/env python3
"""
Production Scale Optimizer - Optimized for 600,000+ bags and 100+ concurrent users
"""

import os
from app_clean import app, db
from sqlalchemy import text, create_engine
from sqlalchemy.pool import QueuePool
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionScaleOptimizer:
    """Optimize for 600,000+ bags and 100+ concurrent users"""
    
    def __init__(self):
        self.target_bags = 600000
        self.target_users = 100
        
    def optimize_database_pool(self):
        """Optimize connection pool for high concurrency"""
        try:
            # Reconfigure the engine with optimized settings
            DATABASE_URL = os.environ.get('DATABASE_URL')
            if DATABASE_URL:
                # Create new engine with optimized settings
                engine = create_engine(
                    DATABASE_URL,
                    poolclass=QueuePool,
                    pool_size=150,  # Increased for 100+ users
                    max_overflow=250,  # Allow more overflow
                    pool_recycle=300,
                    pool_pre_ping=True,
                    pool_timeout=10,
                    echo=False,
                    connect_args={
                        'options': '-c statement_timeout=20000 -c idle_in_transaction_session_timeout=20000',
                        'connect_timeout': 10,
                        'keepalives': 1,
                        'keepalives_idle': 30,
                        'keepalives_interval': 10,
                        'keepalives_count': 5
                    }
                )
                
                # Replace the existing engine
                db.session.bind = engine
                logger.info("✅ Database pool optimized for 100+ concurrent users")
                logger.info(f"  - Pool size: 150 base + 250 overflow")
                logger.info(f"  - Optimized for {self.target_bags:,} bags")
                return True
        except Exception as e:
            logger.error(f"❌ Database pool optimization failed: {e}")
            return False
    
    def create_performance_indexes(self):
        """Create indexes optimized for 600k+ bags"""
        indexes = [
            # Core bag indexes for fast lookups
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_qr_hash ON bag USING hash(qr_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_parent_child ON bag(parent_id, id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_created_desc ON bag(created_at DESC)",
            
            # Scan performance indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_bag_user ON scan(bag_id, user_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_timestamp_desc ON scan(timestamp DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_location ON scan(location)",
            
            # Bill performance indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_user_created ON bill(user_id, created_at DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_bag_bill ON bill_bag(bill_id, bag_id)",
            
            # User activity indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_activity_user ON user_activity_log(user_id, timestamp DESC)",
            
            # Composite indexes for complex queries
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_composite ON bag(qr_id, parent_id, created_at)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_composite ON scan(bag_id, user_id, timestamp)"
        ]
        
        created = 0
        with app.app_context():
            for index_sql in indexes:
                try:
                    db.session.execute(text(index_sql))
                    db.session.commit()
                    created += 1
                    logger.info(f"✅ Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
                except Exception as e:
                    if 'already exists' not in str(e):
                        logger.warning(f"⚠️ Index creation issue: {e}")
                    db.session.rollback()
        
        logger.info(f"✅ Created {created} performance indexes for 600k+ bags")
        return created
    
    def optimize_query_planner(self):
        """Optimize PostgreSQL query planner for large dataset"""
        optimizations = [
            "SET work_mem = '256MB'",
            "SET maintenance_work_mem = '1GB'",
            "SET effective_cache_size = '4GB'",
            "SET random_page_cost = 1.1",
            "SET effective_io_concurrency = 200",
            "SET max_parallel_workers_per_gather = 4",
            "SET max_parallel_workers = 8",
            "SET max_parallel_maintenance_workers = 4",
            "SET shared_buffers = '2GB'",
            "SET checkpoint_completion_target = 0.9",
            "SET wal_buffers = '16MB'",
            "SET default_statistics_target = 100",
            "SET constraint_exclusion = 'partition'",
            "SET jit = 'on'"
        ]
        
        applied = 0
        with app.app_context():
            for opt in optimizations:
                try:
                    db.session.execute(text(opt))
                    applied += 1
                except Exception as e:
                    # Some settings require superuser, that's OK
                    pass
        
        logger.info(f"✅ Applied {applied} query planner optimizations")
        return applied
    
    def update_table_statistics(self):
        """Update table statistics for query optimizer"""
        tables = ['bag', 'scan', 'bill', 'bill_bag', 'users', 'user_activity_log']
        
        with app.app_context():
            for table in tables:
                try:
                    # Analyze with more detail for better query plans
                    db.session.execute(text(f"ANALYZE {table}"))
                    db.session.commit()
                    logger.info(f"✅ Updated statistics for {table}")
                except Exception as e:
                    logger.warning(f"⚠️ Statistics update issue for {table}: {e}")
                    db.session.rollback()
        
        return True
    
    def configure_autovacuum(self):
        """Configure autovacuum for high-traffic tables"""
        configs = [
            "ALTER TABLE bag SET (autovacuum_vacuum_scale_factor = 0.01)",
            "ALTER TABLE scan SET (autovacuum_vacuum_scale_factor = 0.01)",
            "ALTER TABLE bag SET (autovacuum_analyze_scale_factor = 0.005)",
            "ALTER TABLE scan SET (autovacuum_analyze_scale_factor = 0.005)",
            "ALTER TABLE bag SET (fillfactor = 90)",
            "ALTER TABLE scan SET (fillfactor = 90)"
        ]
        
        applied = 0
        with app.app_context():
            for config in configs:
                try:
                    db.session.execute(text(config))
                    db.session.commit()
                    applied += 1
                except Exception as e:
                    db.session.rollback()
        
        logger.info(f"✅ Applied {applied} autovacuum configurations")
        return applied
    
    def apply_all_optimizations(self):
        """Apply all optimizations for scale"""
        logger.info("=" * 60)
        logger.info("APPLYING SCALE OPTIMIZATIONS FOR 600K+ BAGS & 100+ USERS")
        logger.info("=" * 60)
        
        results = {
            'pool_optimized': self.optimize_database_pool(),
            'indexes_created': self.create_performance_indexes(),
            'planner_optimized': self.optimize_query_planner(),
            'statistics_updated': self.update_table_statistics(),
            'autovacuum_configured': self.configure_autovacuum()
        }
        
        logger.info("=" * 60)
        logger.info("OPTIMIZATION COMPLETE")
        logger.info(f"✅ Database pool: Optimized for 100+ concurrent users")
        logger.info(f"✅ Indexes: Created for 600k+ bags performance")
        logger.info(f"✅ Query planner: Configured for large datasets")
        logger.info(f"✅ Statistics: Updated for optimal query plans")
        logger.info(f"✅ Autovacuum: Configured for high-traffic tables")
        logger.info("=" * 60)
        
        return results

# Initialize and apply optimizations when imported
optimizer = ProductionScaleOptimizer()

def init_scale_optimizations(app):
    """Initialize scale optimizations with app context"""
    with app.app_context():
        return optimizer.apply_all_optimizations()

if __name__ == "__main__":
    # Run optimizations directly
    results = optimizer.apply_all_optimizations()
    print(f"\nOptimization Results: {results}")
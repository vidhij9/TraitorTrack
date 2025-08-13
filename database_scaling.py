"""
Database Scaling and Optimization for 50+ Lakh Records
Implements connection pooling, query optimization, and partitioning strategies
"""

import os
import logging
from sqlalchemy import create_engine, text, event, pool
from sqlalchemy.pool import QueuePool, NullPool
from contextlib import contextmanager
import time

logger = logging.getLogger(__name__)

class DatabaseScaler:
    """Advanced database scaling for millions of records"""
    
    def __init__(self, app=None):
        self.app = app
        self.engines = {}
        self.read_replicas = []
        
    def init_app(self, app):
        """Initialize database scaling with Flask app"""
        self.app = app
        self._setup_connection_pooling()
        self._setup_read_replicas()
        self._setup_query_optimization()
        
    def _setup_connection_pooling(self):
        """Configure advanced connection pooling"""
        database_url = os.environ.get('DATABASE_URL')
        
        # Primary write connection pool
        self.engines['primary'] = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=50,  # Base connections
            max_overflow=100,  # Additional connections for peaks
            pool_timeout=30,  # Wait time for connection
            pool_recycle=3600,  # Recycle connections hourly
            pool_pre_ping=True,  # Test connections before use
            echo_pool=False,  # Disable pool logging for performance
            connect_args={
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 5,
                "keepalives_count": 5,
                "connect_timeout": 10,
                "application_name": "TraceTrack_Primary",
                "options": "-c statement_timeout=60000"  # 60 second timeout
            }
        )
        
        # Read replica pools (if configured)
        read_urls = os.environ.get('READ_REPLICA_URLS', '').split(',')
        for url in read_urls:
            if url:
                engine = create_engine(
                    url,
                    poolclass=QueuePool,
                    pool_size=30,
                    max_overflow=50,
                    pool_timeout=20,
                    pool_recycle=3600,
                    pool_pre_ping=True,
                    connect_args={
                        "application_name": "TraceTrack_ReadReplica",
                        "options": "-c statement_timeout=30000"
                    }
                )
                self.read_replicas.append(engine)
        
        logger.info(f"Database scaling initialized with {len(self.read_replicas)} read replicas")
    
    def _setup_read_replicas(self):
        """Setup read replica load balancing"""
        if not self.read_replicas:
            # Use primary for reads if no replicas
            self.read_replicas = [self.engines['primary']]
    
    def _setup_query_optimization(self):
        """Setup automatic query optimization"""
        # Add query execution listeners
        @event.listens_for(self.engines['primary'], "before_execute")
        def receive_before_execute(conn, clauseelement, multiparams, params, execution_options):
            conn.info.setdefault('query_start_time', []).append(time.time())
        
        @event.listens_for(self.engines['primary'], "after_execute")
        def receive_after_execute(conn, clauseelement, multiparams, params, execution_options, result):
            total = time.time() - conn.info['query_start_time'].pop(-1)
            if total > 1.0:  # Log slow queries
                logger.warning(f"Slow query detected ({total:.2f}s): {str(clauseelement)[:100]}")
    
    def get_read_connection(self):
        """Get a read connection with load balancing"""
        import random
        return random.choice(self.read_replicas)
    
    def get_write_connection(self):
        """Get a write connection"""
        return self.engines['primary']
    
    @contextmanager
    def read_session(self):
        """Context manager for read operations"""
        engine = self.get_read_connection()
        connection = engine.connect()
        try:
            yield connection
        finally:
            connection.close()
    
    @contextmanager
    def write_session(self):
        """Context manager for write operations"""
        engine = self.get_write_connection()
        connection = engine.connect()
        trans = connection.begin()
        try:
            yield connection
            trans.commit()
        except Exception:
            trans.rollback()
            raise
        finally:
            connection.close()
    
    def create_partitions(self):
        """Create table partitions for better performance with large datasets"""
        try:
            with self.write_session() as conn:
                # Create partitioned tables for bags (by creation date)
                conn.execute(text("""
                    -- Create parent table for partitioning if not exists
                    CREATE TABLE IF NOT EXISTS bag_partitioned (
                        LIKE bag INCLUDING ALL
                    ) PARTITION BY RANGE (created_at);
                """))
                
                # Create monthly partitions for current and next 3 months
                from datetime import datetime, timedelta
                current_date = datetime.utcnow()
                
                for i in range(4):
                    partition_date = current_date + timedelta(days=30*i)
                    partition_name = f"bag_{partition_date.strftime('%Y_%m')}"
                    start_date = partition_date.replace(day=1)
                    
                    if i < 3:
                        end_date = (start_date + timedelta(days=32)).replace(day=1)
                        end_clause = f"'{end_date.strftime('%Y-%m-%d')}'"
                    else:
                        end_clause = "MAXVALUE"
                    
                    conn.execute(text(f"""
                        CREATE TABLE IF NOT EXISTS {partition_name}
                        PARTITION OF bag_partitioned
                        FOR VALUES FROM ('{start_date.strftime('%Y-%m-%d')}') 
                        TO ({end_clause});
                    """))
                
                logger.info("Database partitions created successfully")
                
        except Exception as e:
            logger.error(f"Failed to create partitions: {e}")
    
    def optimize_indexes(self):
        """Create and optimize indexes for large-scale operations"""
        optimization_queries = [
            # Composite indexes for common queries
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_composite_1 ON bag(type, dispatch_area, created_at DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_composite_2 ON bag(qr_id, type) WHERE type = 'parent'",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_composite_3 ON bag(parent_id, created_at DESC) WHERE parent_id IS NOT NULL",
            
            # Partial indexes for better performance
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_parent_active ON bag(qr_id) WHERE type = 'parent' AND dispatch_area IS NOT NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_child_unlinked ON bag(qr_id) WHERE type = 'child' AND parent_id IS NULL",
            
            # BRIN indexes for time-series data
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_timestamp_brin ON scan USING brin(timestamp)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_created_brin ON bag USING brin(created_at)",
            
            # Hash indexes for exact matches
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_username_hash ON \"user\" USING hash(username)",
            
            # GIN indexes for text search
            "CREATE EXTENSION IF NOT EXISTS pg_trgm",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_name_gin ON bag USING gin(name gin_trgm_ops)",
            
            # Update statistics for query planner
            "ANALYZE bag",
            "ANALYZE scan",
            "ANALYZE \"user\"",
            "ANALYZE link",
            "ANALYZE bill"
        ]
        
        try:
            with self.write_session() as conn:
                for query in optimization_queries:
                    try:
                        conn.execute(text(query))
                        logger.info(f"Executed: {query[:50]}...")
                    except Exception as e:
                        logger.warning(f"Index optimization warning: {e}")
                
                # Set optimal configuration for large datasets
                conn.execute(text("ALTER SYSTEM SET shared_buffers = '2GB'"))
                conn.execute(text("ALTER SYSTEM SET effective_cache_size = '6GB'"))
                conn.execute(text("ALTER SYSTEM SET maintenance_work_mem = '512MB'"))
                conn.execute(text("ALTER SYSTEM SET work_mem = '64MB'"))
                conn.execute(text("ALTER SYSTEM SET max_connections = 500"))
                conn.execute(text("ALTER SYSTEM SET random_page_cost = 1.1"))
                conn.execute(text("ALTER SYSTEM SET effective_io_concurrency = 200"))
                conn.execute(text("ALTER SYSTEM SET max_parallel_workers_per_gather = 4"))
                conn.execute(text("ALTER SYSTEM SET max_parallel_workers = 8"))
                
                logger.info("Database indexes and configuration optimized")
                
        except Exception as e:
            logger.error(f"Failed to optimize indexes: {e}")
    
    def setup_monitoring(self):
        """Setup database monitoring and statistics"""
        monitoring_queries = [
            # Enable statistics collection
            "CREATE EXTENSION IF NOT EXISTS pg_stat_statements",
            
            # Create monitoring views
            """
            CREATE OR REPLACE VIEW database_health AS
            SELECT 
                (SELECT count(*) FROM pg_stat_activity) as active_connections,
                (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_queries,
                (SELECT count(*) FROM pg_stat_activity WHERE wait_event_type IS NOT NULL) as waiting_queries,
                (SELECT avg(extract(epoch from (now() - query_start))) 
                 FROM pg_stat_activity 
                 WHERE state = 'active' AND query_start IS NOT NULL) as avg_query_duration,
                (SELECT max(extract(epoch from (now() - query_start))) 
                 FROM pg_stat_activity 
                 WHERE state = 'active' AND query_start IS NOT NULL) as max_query_duration,
                pg_database_size(current_database()) as database_size_bytes
            """,
            
            """
            CREATE OR REPLACE VIEW slow_queries AS
            SELECT 
                query,
                calls,
                total_exec_time,
                mean_exec_time,
                max_exec_time,
                rows
            FROM pg_stat_statements
            WHERE mean_exec_time > 1000  -- Queries averaging over 1 second
            ORDER BY mean_exec_time DESC
            LIMIT 20
            """
        ]
        
        try:
            with self.write_session() as conn:
                for query in monitoring_queries:
                    try:
                        conn.execute(text(query))
                    except Exception as e:
                        logger.warning(f"Monitoring setup warning: {e}")
                
                logger.info("Database monitoring setup completed")
                
        except Exception as e:
            logger.error(f"Failed to setup monitoring: {e}")
    
    def get_health_metrics(self):
        """Get current database health metrics"""
        try:
            with self.read_session() as conn:
                result = conn.execute(text("SELECT * FROM database_health")).first()
                if result:
                    return dict(result._mapping)
        except Exception as e:
            logger.error(f"Failed to get health metrics: {e}")
        
        return {}
    
    def cleanup_old_data(self, days=90):
        """Archive or remove old data to maintain performance"""
        try:
            with self.write_session() as conn:
                cutoff_date = f"NOW() - INTERVAL '{days} days'"
                
                # Archive old scans
                archived = conn.execute(text(f"""
                    WITH archived AS (
                        DELETE FROM scan 
                        WHERE timestamp < {cutoff_date}
                        RETURNING *
                    )
                    SELECT count(*) FROM archived
                """)).scalar()
                
                logger.info(f"Archived {archived} old scan records")
                
                # Vacuum to reclaim space
                conn.execute(text("VACUUM ANALYZE"))
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")


# Global database scaler instance
db_scaler = DatabaseScaler()
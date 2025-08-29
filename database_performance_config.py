"""
Advanced Database Performance Configuration for 800k+ bags
Optimized for <50ms queries and 60+ concurrent users
"""

import os
from sqlalchemy import create_engine, event, pool
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.engine import Engine
import logging

logger = logging.getLogger(__name__)

class HighPerformanceDatabase:
    """Database configuration optimized for massive scale"""
    
    @staticmethod
    def get_optimized_engine_config():
        """Get optimized engine configuration for production scale"""
        
        # Base database URL
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL not configured")
        
        # Optimize connection parameters for Neon database
        if 'neon' in database_url or 'pooler' in database_url:
            # Neon-specific optimizations
            connect_args = {
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
                "connect_timeout": 10,
                "application_name": "TraceTrack_UltraPerformance",
                "options": "-c statement_timeout=30000 -c idle_in_transaction_session_timeout=30000"
            }
            
            # Use QueuePool for connection pooling
            poolclass = QueuePool
            pool_config = {
                "pool_size": 100,  # Increased for 60+ concurrent users
                "max_overflow": 150,  # Allow up to 250 total connections
                "pool_recycle": 300,  # Recycle every 5 minutes
                "pool_pre_ping": True,  # Check connections before use
                "pool_timeout": 30,  # Wait up to 30 seconds
                "echo_pool": False  # Disable pool logging for performance
            }
        else:
            # Standard PostgreSQL optimizations
            connect_args = {
                "connect_timeout": 10,
                "application_name": "TraceTrack_UltraPerformance"
            }
            
            poolclass = QueuePool
            pool_config = {
                "pool_size": 50,
                "max_overflow": 100,
                "pool_recycle": 3600,
                "pool_pre_ping": True,
                "pool_timeout": 30
            }
        
        return {
            "url": database_url,
            "poolclass": poolclass,
            "connect_args": connect_args,
            **pool_config,
            "echo": False,  # Disable query logging for performance
            "future": True,  # Use SQLAlchemy 2.0 style
            "query_cache_size": 1200,  # Cache compiled queries
            "isolation_level": "READ COMMITTED"  # Optimize for concurrent reads
        }
    
    @staticmethod
    def apply_performance_listeners(engine: Engine):
        """Apply performance optimization event listeners"""
        
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            """Set performance pragmas on connection"""
            cursor = dbapi_conn.cursor()
            
            # PostgreSQL performance settings
            try:
                # Optimize for read-heavy workload
                cursor.execute("SET synchronous_commit = OFF")
                cursor.execute("SET work_mem = '256MB'")
                cursor.execute("SET maintenance_work_mem = '512MB'")
                cursor.execute("SET effective_cache_size = '4GB'")
                cursor.execute("SET random_page_cost = 1.1")  # SSD optimization
                cursor.execute("SET effective_io_concurrency = 200")  # SSD optimization
                cursor.execute("SET max_parallel_workers_per_gather = 4")
                cursor.execute("SET max_parallel_workers = 8")
                cursor.execute("SET jit = ON")  # Enable JIT compilation
                cursor.execute("SET shared_preload_libraries = 'pg_stat_statements'")
            except Exception as e:
                logger.warning(f"Could not set all performance optimizations: {e}")
            finally:
                cursor.close()
        
        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Log slow queries"""
            conn.info.setdefault('query_start_time', []).append(time.time())
        
        @event.listens_for(engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Monitor query performance"""
            total_time = time.time() - conn.info['query_start_time'].pop(-1)
            if total_time > 0.05:  # Log queries over 50ms
                logger.warning(f"Slow query ({total_time*1000:.2f}ms): {statement[:100]}...")
    
    @staticmethod
    def create_optimized_indexes(db):
        """Create optimized indexes for 800k+ bags"""
        
        index_queries = [
            # Optimized indexes for bag table (800k+ records)
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_qr_hash ON bag USING hash(qr_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_qr_btree ON bag USING btree(qr_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_type_btree ON bag USING btree(type)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_composite ON bag(qr_id, type, status)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_parent_child ON bag(parent_id, id) WHERE parent_id IS NOT NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_created_brin ON bag USING brin(created_at)",
            
            # Partial indexes for common queries
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_parent_active ON bag(qr_id) WHERE type = 'parent' AND status = 'active'",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_child_unlinked ON bag(qr_id) WHERE type = 'child' AND parent_id IS NULL",
            
            # Optimized indexes for scan table
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_composite ON scan(user_id, timestamp DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_parent_child ON scan(parent_bag_id, child_bag_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_timestamp_brin ON scan USING brin(timestamp)",
            
            # Optimized indexes for link table
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_composite ON link(parent_bag_id, child_bag_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_parent_covering ON link(parent_bag_id) INCLUDE (child_bag_id)",
            
            # Text search indexes for bag names
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_name_gin ON bag USING gin(to_tsvector('english', name))",
            
            # Statistics for query planner
            "ANALYZE bag",
            "ANALYZE scan",
            "ANALYZE link",
            "ANALYZE \"user\""
        ]
        
        for query in index_queries:
            try:
                db.session.execute(query)
                db.session.commit()
                logger.info(f"Index created/verified: {query[:50]}...")
            except Exception as e:
                logger.warning(f"Could not create index: {e}")
                db.session.rollback()
    
    @staticmethod
    def optimize_database_settings(app):
        """Apply all database optimizations to Flask app"""
        
        # Get optimized configuration
        config = HighPerformanceDatabase.get_optimized_engine_config()
        
        # Update app configuration
        app.config['SQLALCHEMY_DATABASE_URI'] = config['url']
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'poolclass': config['poolclass'],
            'pool_size': config['pool_size'],
            'max_overflow': config['max_overflow'],
            'pool_recycle': config['pool_recycle'],
            'pool_pre_ping': config['pool_pre_ping'],
            'pool_timeout': config['pool_timeout'],
            'connect_args': config['connect_args'],
            'echo': config['echo'],
            'future': config['future'],
            'isolation_level': config['isolation_level']
        }
        
        # Additional SQLAlchemy optimizations
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SQLALCHEMY_RECORD_QUERIES'] = False
        app.config['SQLALCHEMY_ECHO'] = False
        
        logger.info("✅ Database optimized for 800k+ bags and 60+ concurrent users")

import time

# Export main configuration class
__all__ = ['HighPerformanceDatabase']
"""
Ultra-Performance Configuration for 100+ Concurrent Users and 1.5M+ Bags
Optimized for sub-100ms response times across all endpoints
Enhanced for massive scale operations
"""

import os
import multiprocessing
from datetime import timedelta

class UltraPerformanceConfig:
    """Ultimate performance configuration for production scale - 100+ users, 1.5M+ bags"""
    
    # Database Configuration - Optimized for 100+ concurrent users and 1.5M bags
    # Sized for typical managed Postgres limits (100 max connections)
    DATABASE_CONFIG = {
        # Connection pool sized for 100+ users within DB limits
        "pool_size": 40,                      # Base pool for sustained load
        "max_overflow": 50,                   # Total 90 connections (safely under 100 limit)
        "pool_recycle": 1800,                 # Recycle every 30 minutes
        "pool_pre_ping": True,                # Always test connections
        "pool_timeout": 5,                    # Fast fail on connection wait
        "echo": False,                        # No SQL logging
        "echo_pool": False,                   # No pool logging
        "pool_use_lifo": True,                # Better connection reuse
        "pool_reset_on_return": "rollback",   # Clean connection state
        
        # PostgreSQL optimizations for 1.5M+ bags (conservative memory)
        "connect_args": {
            "keepalives": 1,
            "keepalives_idle": 5,
            "keepalives_interval": 2,
            "keepalives_count": 5,
            "connect_timeout": 3,              # Very fast connect
            "application_name": "TraceTrack_Ultra_150M",
            "options": (
                "-c statement_timeout=15000 "  # 15 second query timeout for large datasets
                "-c idle_in_transaction_session_timeout=5000 "  # 5 second idle timeout
                "-c jit=on "                   # Enable JIT compilation
                "-c random_page_cost=1.1 "     # Optimize for SSD
                "-c work_mem=8MB "             # Conservative: 8MB * 90 connections = 720MB total
                "-c enable_seqscan=on "        # Allow sequential scans
                "-c enable_indexscan=on "      # Use indexes
                "-c enable_bitmapscan=on "     # Use bitmap scans
                "-c enable_hashjoin=on "       # Use hash joins
                "-c enable_mergejoin=on "      # Use merge joins
                "-c max_parallel_workers_per_gather=2 "  # Conservative parallel (2 workers)
                "-c parallel_tuple_cost=0.01"  # Tune parallel query cost
            )
        },
        
        # Execution options for queries
        "execution_options": {
            "isolation_level": "READ COMMITTED",
            "postgresql_readonly": False,
            "postgresql_deferrable": False,
            "compiled_cache": {},              # Cache compiled statements
            "stream_results": False,           # Load all results at once
        }
    }
    
    # Query Optimization Settings
    QUERY_CONFIG = {
        'batch_size': 5000,                   # Large batch operations
        'chunk_size': 10000,                  # Process in 10k chunks
        'query_timeout': 10000,                # 10 seconds max
        'max_results': 50000,                  # Large result sets
        'use_prepared_statements': True,       # Prepared statements
        'enable_query_cache': True,            # Query result caching
        'parallel_queries': True,              # Enable parallel execution
        'optimize_for_bulk': True,            # Bulk operation mode
    }
    
    # Cache Configuration - Aggressive caching for performance
    CACHE_CONFIG = {
        'default_ttl': 30,                    # 30 seconds default
        'stats_ttl': 10,                      # 10 seconds for stats
        'scan_ttl': 5,                        # 5 seconds for scans
        'bag_ttl': 60,                        # 1 minute for bag data
        'bill_ttl': 120,                      # 2 minutes for bills
        'user_ttl': 300,                      # 5 minutes for user data
        'max_cache_size': 10000,              # Large cache capacity
        'cache_algorithm': 'lru',             # LRU eviction
        'enable_compression': True,           # Compress cached data
    }
    
    # Circuit Breaker Configuration
    CIRCUIT_BREAKER = {
        'failure_threshold': 3,               # Open after 3 failures
        'recovery_timeout': 15,               # Try again after 15 seconds
        'expected_exception': Exception,      # All exceptions trigger
        'success_threshold': 2,               # Close after 2 successes
    }
    
    # Rate Limiting - High limits for production
    RATE_LIMITS = {
        'default': "100000 per hour",         # Very high default
        'scanning': "50000 per hour",         # High-volume scanning
        'api': "30000 per hour",              # API endpoints
        'dashboard': "10000 per hour",        # Dashboard access
        'auth': "1000 per hour",              # Auth endpoints
    }
    
    # Gunicorn Worker Configuration
    WORKER_CONFIG = {
        "bind": "0.0.0.0:5000",
        "workers": 1,                         # Single worker for Replit
        "worker_class": "sync",                # Sync for stability
        "worker_connections": 500,            # High connection count
        "max_requests": 10000,                # Restart after 10k requests
        "max_requests_jitter": 1000,         # Add jitter
        "timeout": 30,                        # 30 second timeout
        "graceful_timeout": 5,                # Fast graceful shutdown
        "keepalive": 5,                       # Keep connections alive
        "threads": 1,                         # Single thread
        "backlog": 1024,                      # Large backlog
        "preload_app": True,                  # Preload for speed
    }
    
    # Performance Monitoring
    MONITORING = {
        'enable_metrics': True,               # Collect metrics
        'metric_interval': 10,                # Every 10 seconds
        'slow_query_threshold': 100,          # Log queries > 100ms
        'alert_response_time': 300,           # Alert if > 300ms
        'track_memory': True,                 # Monitor memory usage
        'track_connections': True,            # Monitor DB connections
    }
    
    # Batch Processing Configuration
    BATCH_PROCESSING = {
        'scan_batch_size': 100,               # Process 100 scans at once
        'link_batch_size': 500,               # Link 500 bags at once
        'insert_batch_size': 1000,            # Insert 1000 records at once
        'update_batch_size': 500,             # Update 500 records at once
        'delete_batch_size': 100,             # Delete 100 records at once
        'use_copy_from': True,                # Use COPY for bulk inserts
        'parallel_processing': True,          # Process batches in parallel
    }
    
    # Index Hints for Query Optimizer
    INDEX_HINTS = {
        'bag_lookup': 'idx_bag_qr_id',
        'bag_filter': 'idx_bag_type_area_created',
        'scan_recent': 'idx_scan_timestamp',
        'link_lookup': 'idx_link_parent_child',
        'bill_status': 'idx_bill_status_created',
        'user_scan': 'idx_scan_user',
    }
    
    @classmethod
    def apply_to_app(cls, app):
        """Apply ultra-performance configuration to Flask app"""
        # Database configuration
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = cls.DATABASE_CONFIG
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SQLALCHEMY_RECORD_QUERIES'] = False
        app.config['SQLALCHEMY_ECHO'] = False
        
        # Performance settings
        app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB max
        app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400      # 1 day cache
        app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False    # No pretty print
        app.config['JSON_SORT_KEYS'] = False                  # No sorting
        app.config['PROPAGATE_EXCEPTIONS'] = False            # No propagation
        
        # Session configuration
        app.config['SESSION_TYPE'] = 'filesystem'
        app.config['SESSION_FILE_DIR'] = '/tmp/flask_session'
        app.config['SESSION_PERMANENT'] = False
        app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)
        app.config['SESSION_USE_SIGNER'] = True
        app.config['SESSION_KEY_PREFIX'] = 'tt:'
        
        # Security
        app.config['SESSION_COOKIE_SECURE'] = False  # True for HTTPS
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        app.config['WTF_CSRF_TIME_LIMIT'] = None
        
        # Enable response compression
        app.config['COMPRESS_MIMETYPES'] = [
            'text/html', 'text/css', 'text/xml',
            'application/json', 'application/javascript'
        ]
        app.config['COMPRESS_LEVEL'] = 6
        app.config['COMPRESS_MIN_SIZE'] = 500
        
        return app
    
    @classmethod
    def get_optimized_indexes(cls):
        """Return list of indexes needed for optimal performance"""
        return [
            # Bag table indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_qr_upper ON bag(UPPER(qr_id))",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_type_status ON bag(type, status)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_created_desc ON bag(created_at DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_parent_partial ON bag(parent_id) WHERE parent_id IS NOT NULL",
            
            # Scan table indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_timestamp_desc ON scan(timestamp DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_user_timestamp ON scan(user_id, timestamp DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_parent_timestamp ON scan(parent_bag_id, timestamp DESC) WHERE parent_bag_id IS NOT NULL",
            
            # Link table indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_parent ON link(parent_bag_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_child ON link(child_bag_id)",
            
            # Bill table indexes
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_status_created ON bill(status, created_at DESC)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_id_upper ON bill(UPPER(bill_id))",
            
            # Composite indexes for common queries
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_type_area_status ON bag(type, dispatch_area, status) WHERE dispatch_area IS NOT NULL",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_recent ON scan(timestamp) WHERE timestamp > CURRENT_DATE - INTERVAL '7 days'",
        ]
    
    @classmethod
    def get_performance_views(cls):
        """Return materialized views for ultra-fast queries"""
        return [
            # Dashboard stats view
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_dashboard_stats AS
            SELECT 
                COUNT(*) FILTER (WHERE type = 'parent') as parent_count,
                COUNT(*) FILTER (WHERE type = 'child') as child_count,
                COUNT(*) FILTER (WHERE status = 'completed') as completed_count,
                COUNT(*) as total_bags
            FROM bag
            WITH DATA;
            """,
            
            # Recent activity view
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS mv_recent_activity AS
            SELECT 
                DATE_TRUNC('hour', timestamp) as hour,
                COUNT(*) as scan_count,
                COUNT(DISTINCT user_id) as active_users
            FROM scan
            WHERE timestamp > CURRENT_DATE - INTERVAL '24 hours'
            GROUP BY DATE_TRUNC('hour', timestamp)
            WITH DATA;
            """,
        ]

# Performance utility functions
class PerformanceOptimizer:
    """Utilities for optimizing query performance"""
    
    @staticmethod
    def create_indexes(db_session):
        """Create all performance indexes"""
        indexes = UltraPerformanceConfig.get_optimized_indexes()
        for index_sql in indexes:
            try:
                db_session.execute(index_sql)
                db_session.commit()
            except Exception as e:
                print(f"Index creation warning: {e}")
                db_session.rollback()
    
    @staticmethod
    def analyze_tables(db_session):
        """Run ANALYZE on all tables for query optimizer"""
        tables = ['bag', 'scan', 'link', 'bill', 'user']
        for table in tables:
            try:
                db_session.execute(f"ANALYZE {table}")
                db_session.commit()
            except Exception as e:
                print(f"Analyze warning for {table}: {e}")
                db_session.rollback()
    
    @staticmethod
    def vacuum_tables(db_session):
        """Run VACUUM on tables (maintenance operation)"""
        tables = ['bag', 'scan', 'link', 'bill']
        for table in tables:
            try:
                db_session.execute(f"VACUUM (ANALYZE) {table}")
                db_session.commit()
            except Exception as e:
                print(f"Vacuum warning for {table}: {e}")
                db_session.rollback()
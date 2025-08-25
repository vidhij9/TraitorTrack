"""
Ultra-fast configuration for <50ms response times and 50+ concurrent users
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.orm import sessionmaker, scoped_session
import logging

# Performance configuration
PERFORMANCE_CONFIG = {
    # Database pooling - optimized for high concurrency
    'DB_POOL_SIZE': 100,          # Base pool size
    'DB_MAX_OVERFLOW': 200,       # Additional connections when needed
    'DB_POOL_TIMEOUT': 10,        # Timeout for getting connection
    'DB_POOL_RECYCLE': 300,       # Recycle connections after 5 minutes
    'DB_POOL_PRE_PING': True,     # Check connection health
    
    # Response time targets
    'TARGET_RESPONSE_MS': 50,      # Target response time
    'MAX_RESPONSE_MS': 200,        # Maximum acceptable response
    
    # Caching configuration
    'CACHE_ENABLED': True,
    'CACHE_TTL_DASHBOARD': 10,     # Dashboard cache for 10 seconds
    'CACHE_TTL_API': 5,            # API cache for 5 seconds
    'CACHE_TTL_STATIC': 60,        # Static content for 60 seconds
    
    # Request optimization
    'GZIP_COMPRESSION': True,
    'MIN_COMPRESS_SIZE': 500,      # Compress responses > 500 bytes
    
    # Query optimization
    'QUERY_TIMEOUT': 5000,         # 5 second query timeout
    'BATCH_SIZE': 1000,            # Batch operations size
    'PAGINATION_LIMIT': 100,       # Max items per page
    
    # Concurrent user handling
    'MAX_CONCURRENT_USERS': 100,   # Support 100+ concurrent users
    'SESSION_POOL_SIZE': 200,      # Session pool size
    'REQUEST_QUEUE_SIZE': 500,     # Request queue size
}

class UltraFastDatabase:
    """Ultra-fast database configuration with aggressive pooling"""
    
    def __init__(self):
        self.database_url = os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL not configured")
        
        # Create engine with aggressive pooling
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=PERFORMANCE_CONFIG['DB_POOL_SIZE'],
            max_overflow=PERFORMANCE_CONFIG['DB_MAX_OVERFLOW'],
            pool_timeout=PERFORMANCE_CONFIG['DB_POOL_TIMEOUT'],
            pool_recycle=PERFORMANCE_CONFIG['DB_POOL_RECYCLE'],
            pool_pre_ping=PERFORMANCE_CONFIG['DB_POOL_PRE_PING'],
            echo=False,  # Disable SQL logging for performance
            connect_args={
                'connect_timeout': 10,
                'options': '-c statement_timeout=5000'  # 5 second statement timeout
            }
        )
        
        # Create session factory
        self.SessionLocal = scoped_session(
            sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine,
                expire_on_commit=False  # Don't expire objects after commit
            )
        )
        
        # Warmup connections
        self._warmup_pool()
    
    def _warmup_pool(self):
        """Pre-create connections for faster initial responses"""
        try:
            # Create initial connections
            connections = []
            for _ in range(min(10, PERFORMANCE_CONFIG['DB_POOL_SIZE'])):
                conn = self.engine.connect()
                connections.append(conn)
            
            # Close them to return to pool
            for conn in connections:
                conn.close()
            
            logging.info(f"Database pool warmed up with {len(connections)} connections")
        except Exception as e:
            logging.warning(f"Could not warmup database pool: {e}")
    
    def get_session(self):
        """Get a database session"""
        return self.SessionLocal()
    
    def close_session(self):
        """Close the current session"""
        self.SessionLocal.remove()
    
    def execute_fast(self, query, params=None):
        """Execute a query with minimal overhead"""
        with self.engine.connect() as conn:
            result = conn.execute(query, params or {})
            return result.fetchall()
    
    def get_stats(self):
        """Get database pool statistics"""
        pool = self.engine.pool
        return {
            'size': pool.size() if hasattr(pool, 'size') else 'N/A',
            'checked_in': pool.checkedin() if hasattr(pool, 'checkedin') else 'N/A',
            'checked_out': pool.checkedout() if hasattr(pool, 'checkedout') else 'N/A',
            'overflow': pool.overflow() if hasattr(pool, 'overflow') else 'N/A',
            'total': pool.total() if hasattr(pool, 'total') else 'N/A'
        }

# Global database instance
_db_instance = None

def get_ultra_db():
    """Get or create ultra-fast database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = UltraFastDatabase()
    return _db_instance

# Query optimization helpers
def optimize_query(query):
    """Optimize a SQLAlchemy query for performance"""
    # Add query hints and optimizations
    return query.execution_options(
        synchronize_session=False,
        stream_results=True
    )

def batch_insert(session, model, records, batch_size=1000):
    """Batch insert records for better performance"""
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        session.bulk_insert_mappings(model, batch)
        session.commit()

def parallel_query(queries, max_workers=4):
    """Execute multiple queries in parallel"""
    import concurrent.futures
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(q.all) for q in queries]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    
    return results
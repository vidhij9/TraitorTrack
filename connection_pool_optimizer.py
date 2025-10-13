"""
Enhanced Connection Pool Management for 100+ Concurrent Users
Implements PgBouncer-like connection pooling and optimization strategies
"""

import os
import logging
from sqlalchemy import create_engine, event, pool
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import time
from threading import Lock
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ConnectionPoolOptimizer:
    """Advanced connection pool management for high concurrency"""
    
    def __init__(self):
        self.stats = {
            'total_checkouts': 0,
            'total_checkins': 0,
            'total_connects': 0,
            'total_disconnects': 0,
            'checkout_times': [],
        }
        self.stats_lock = Lock()
    
    def create_optimized_pool(self, database_url: str, pool_size: int = 40, max_overflow: int = 50) -> Dict[str, Any]:
        """Create optimized connection pool configuration"""
        
        # Determine if AWS RDS or local
        is_aws_rds = 'amazonaws.com' in database_url
        
        config = {
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_recycle": 280 if is_aws_rds else 1800,
            "pool_pre_ping": True,
            "pool_timeout": 10,
            "echo": False,
            "echo_pool": False,
            "pool_use_lifo": True,
            "pool_reset_on_return": "rollback",
            "poolclass": QueuePool,
            "connect_args": {
                "keepalives": 1,
                "keepalives_idle": 30 if is_aws_rds else 5,
                "keepalives_interval": 10 if is_aws_rds else 2,
                "keepalives_count": 5,
                "connect_timeout": 5,
                "application_name": "TraceTrack_100Plus",
                "options": (
                    "-c statement_timeout=15000 "
                    "-c idle_in_transaction_session_timeout=5000 "
                    "-c work_mem=8MB "
                    "-c jit=on "
                    "-c random_page_cost=1.1 "
                    "-c enable_seqscan=on "
                    "-c enable_indexscan=on "
                    "-c enable_bitmapscan=on "
                    "-c enable_hashjoin=on "
                    "-c enable_mergejoin=on "
                    "-c max_parallel_workers_per_gather=2 "
                    "-c parallel_tuple_cost=0.01"
                )
            }
        }
        
        logger.info(f"✅ Created optimized pool config: {pool_size} base + {max_overflow} overflow = {pool_size + max_overflow} total")
        return config
    
    def setup_pool_listeners(self, engine):
        """Setup SQLAlchemy pool event listeners for monitoring"""
        
        @event.listens_for(engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            with self.stats_lock:
                self.stats['total_connects'] += 1
        
        @event.listens_for(engine, "close")
        def receive_close(dbapi_conn, connection_record):
            with self.stats_lock:
                self.stats['total_disconnects'] += 1
        
        @event.listens_for(engine.pool, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            connection_record.info['checkout_time'] = time.time()
            with self.stats_lock:
                self.stats['total_checkouts'] += 1
        
        @event.listens_for(engine.pool, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            if 'checkout_time' in connection_record.info:
                checkout_time = connection_record.info['checkout_time']
                hold_time = time.time() - checkout_time
                
                with self.stats_lock:
                    self.stats['total_checkins'] += 1
                    self.stats['checkout_times'].append(hold_time)
                    
                    # Keep only last 1000 times
                    if len(self.stats['checkout_times']) > 1000:
                        self.stats['checkout_times'] = self.stats['checkout_times'][-1000:]
                
                # Log long-held connections
                if hold_time > 5:  # 5 seconds
                    logger.warning(f"Long connection hold time: {hold_time:.2f}s")
        
        logger.info("✅ Pool monitoring listeners configured")
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        with self.stats_lock:
            checkout_times = self.stats['checkout_times']
            avg_hold_time = sum(checkout_times) / len(checkout_times) if checkout_times else 0
            
            return {
                'total_checkouts': self.stats['total_checkouts'],
                'total_checkins': self.stats['total_checkins'],
                'total_connects': self.stats['total_connects'],
                'total_disconnects': self.stats['total_disconnects'],
                'avg_connection_hold_time': round(avg_hold_time, 3),
                'active_connections': self.stats['total_checkouts'] - self.stats['total_checkins'],
            }

class ReadWriteSplitter:
    """Read/Write query splitting for load distribution"""
    
    def __init__(self, write_engine, read_engine=None):
        self.write_engine = write_engine
        self.read_engine = read_engine or write_engine
        self._in_transaction = False
    
    @contextmanager
    def session(self, force_write=False):
        """Get appropriate session based on query type"""
        if force_write or self._in_transaction:
            engine = self.write_engine
        else:
            engine = self.read_engine
        
        connection = engine.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
    
    def begin_transaction(self):
        """Start transaction on write engine"""
        self._in_transaction = True
    
    def end_transaction(self):
        """End transaction"""
        self._in_transaction = False

class QueryBatcher:
    """Batch multiple queries for efficiency"""
    
    def __init__(self, batch_size=100):
        self.batch_size = batch_size
        self.pending_queries = []
        self.lock = Lock()
    
    def add_query(self, query, params):
        """Add query to batch"""
        with self.lock:
            self.pending_queries.append((query, params))
            
            if len(self.pending_queries) >= self.batch_size:
                return self.flush()
        return None
    
    def flush(self):
        """Execute all pending queries"""
        with self.lock:
            if not self.pending_queries:
                return []
            
            queries = self.pending_queries.copy()
            self.pending_queries.clear()
            
            # Execute queries in batch
            results = []
            # Implementation would execute all queries here
            return results

# Global optimizer instance
pool_optimizer = ConnectionPoolOptimizer()

def get_optimized_pool_config(database_url: str) -> Dict[str, Any]:
    """Get optimized pool configuration"""
    return pool_optimizer.create_optimized_pool(database_url)

def setup_pool_monitoring(engine):
    """Setup pool monitoring"""
    pool_optimizer.setup_pool_listeners(engine)

def get_pool_statistics() -> Dict[str, Any]:
    """Get pool statistics"""
    return pool_optimizer.get_pool_stats()

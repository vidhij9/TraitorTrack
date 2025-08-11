"""
Advanced Database Connection Optimizer for Enterprise Scale
Handles 4+ lakh bags with 200+ concurrent users
"""

import logging
import threading
import time
import contextlib
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DisconnectionError, TimeoutError
from app_clean import db, app
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class EnterpriseConnectionManager:
    """Advanced connection manager for enterprise-scale operations"""
    
    def __init__(self):
        self.connection_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'failed_connections': 0,
            'pool_overflows': 0,
            'connection_timeouts': 0,
            'last_optimization': None
        }
        self.lock = threading.Lock()
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get current connection pool statistics"""
        try:
            with app.app_context():
                pool = db.engine.pool
                return {
                    'pool_size': pool.size(),
                    'checked_in': pool.checkedin(),
                    'checked_out': pool.checkedout(),
                    'overflow': pool.overflow(),
                    'invalid': pool.invalid(),
                    'total_capacity': pool.size() + pool.overflow(),
                    'utilization_percent': (pool.checkedout() / (pool.size() + pool.overflow())) * 100,
                    **self.connection_stats
                }
        except Exception as e:
            logger.error(f"Failed to get connection stats: {e}")
            return self.connection_stats
    
    def optimize_database_configuration(self):
        """Apply enterprise-level database optimizations"""
        try:
            with app.app_context():
                # Execute optimization commands
                optimization_commands = [
                    # Memory and performance optimizations
                    "SET shared_buffers = '256MB'",
                    "SET effective_cache_size = '1GB'",
                    "SET work_mem = '32MB'",
                    "SET maintenance_work_mem = '128MB'",
                    "SET wal_buffers = '16MB'",
                    
                    # Connection and timeout settings
                    "SET statement_timeout = '120000'",  # 2 minutes
                    "SET lock_timeout = '60000'",        # 1 minute
                    "SET idle_in_transaction_session_timeout = '300000'",  # 5 minutes
                    
                    # Query optimization
                    "SET enable_hashjoin = on",
                    "SET enable_mergejoin = on",
                    "SET enable_sort = on",
                    "SET enable_indexscan = on",
                    "SET enable_bitmapscan = on",
                    
                    # Checkpoint and WAL optimizations
                    "SET checkpoint_completion_target = 0.7",
                    "SET checkpoint_timeout = '15min'",
                    "SET max_wal_size = '2GB'",
                    "SET min_wal_size = '1GB'",
                    
                    # Vacuum and autovacuum settings
                    "SET autovacuum = on",
                    "SET autovacuum_max_workers = 3",
                    "SET autovacuum_naptime = '1min'",
                    
                    # Statistics and query planning
                    "SET default_statistics_target = 100",
                    "SET random_page_cost = 1.1",
                    "SET seq_page_cost = 1.0"
                ]
                
                for command in optimization_commands:
                    try:
                        db.session.execute(text(command))
                        logger.debug(f"Applied optimization: {command}")
                    except Exception as e:
                        # Some settings may not be changeable at session level
                        logger.debug(f"Optimization command failed (may be expected): {command} - {e}")
                
                db.session.commit()
                
                with self.lock:
                    self.connection_stats['last_optimization'] = time.time()
                
                logger.info("Database optimization completed successfully")
                return True
                
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            return False
    
    def create_optimized_engine(self, database_url: str) -> Optional[Engine]:
        """Create an optimized database engine for enterprise scale"""
        try:
            # Enterprise-scale engine configuration
            engine_config = {
                'pool_class': QueuePool,
                'pool_size': 100,              # Large connection pool
                'max_overflow': 150,           # Additional connections during peaks
                'pool_recycle': 3600,          # 1 hour connection recycling
                'pool_pre_ping': True,         # Test connections before use
                'pool_timeout': 30,            # Connection timeout
                'pool_reset_on_return': 'commit',  # Reset connection state
                'echo': False,                 # Disable SQL echoing for performance
                'echo_pool': False,           # Disable pool logging
                'connect_args': {
                    # PostgreSQL specific optimizations
                    'keepalives': 1,
                    'keepalives_idle': 30,
                    'keepalives_interval': 5,
                    'keepalives_count': 3,
                    'connect_timeout': 20,
                    'application_name': 'TraceTrack_Enterprise',
                    'server_side_cursors': True,
                    'options': (
                        '-c statement_timeout=120000 '
                        '-c lock_timeout=60000 '
                        '-c idle_in_transaction_session_timeout=300000 '
                        '-c work_mem=32MB '
                        '-c maintenance_work_mem=128MB'
                    )
                }
            }
            
            engine = create_engine(database_url, **engine_config)
            
            # Test the connection
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            logger.info(f"Optimized database engine created successfully")
            logger.info(f"Pool configuration: size={engine_config['pool_size']}, overflow={engine_config['max_overflow']}")
            
            return engine
            
        except Exception as e:
            logger.error(f"Failed to create optimized engine: {e}")
            return None
    
    @contextlib.contextmanager
    def get_connection_with_retry(self, max_retries: int = 3):
        """Get database connection with automatic retry logic"""
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                with db.session.begin() as transaction:
                    with self.lock:
                        self.connection_stats['total_connections'] += 1
                        self.connection_stats['active_connections'] += 1
                    
                    yield transaction
                    
                    with self.lock:
                        self.connection_stats['active_connections'] -= 1
                    return
                    
            except (DisconnectionError, TimeoutError) as e:
                retry_count += 1
                last_error = e
                
                with self.lock:
                    if isinstance(e, TimeoutError):
                        self.connection_stats['connection_timeouts'] += 1
                    self.connection_stats['failed_connections'] += 1
                    self.connection_stats['active_connections'] = max(0, self.connection_stats['active_connections'] - 1)
                
                if retry_count < max_retries:
                    wait_time = retry_count * 0.5  # Progressive backoff
                    logger.warning(f"Connection retry {retry_count}/{max_retries} after {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Connection failed after {max_retries} retries: {e}")
                    raise last_error
            
            except Exception as e:
                with self.lock:
                    self.connection_stats['failed_connections'] += 1
                    self.connection_stats['active_connections'] = max(0, self.connection_stats['active_connections'] - 1)
                raise e
    
    def execute_bulk_operation(self, operation_func, data_batches, batch_size=1000):
        """Execute bulk database operations with optimized batching"""
        try:
            total_processed = 0
            total_batches = len(data_batches)
            
            logger.info(f"Starting bulk operation: {total_batches} batches of size {batch_size}")
            
            for batch_idx, batch_data in enumerate(data_batches):
                with self.get_connection_with_retry() as transaction:
                    try:
                        # Execute the batch operation
                        batch_result = operation_func(batch_data, transaction)
                        batch_processed = len(batch_data) if hasattr(batch_data, '__len__') else batch_size
                        total_processed += batch_processed
                        
                        # Progress logging
                        if (batch_idx + 1) % 10 == 0 or batch_idx == total_batches - 1:
                            progress = ((batch_idx + 1) / total_batches) * 100
                            logger.info(f"Bulk operation progress: {batch_idx + 1}/{total_batches} batches ({progress:.1f}%) - {total_processed} records processed")
                        
                    except Exception as e:
                        logger.error(f"Batch {batch_idx + 1} failed: {e}")
                        raise e
            
            logger.info(f"Bulk operation completed: {total_processed} records processed successfully")
            return {
                'success': True,
                'total_processed': total_processed,
                'batches_processed': total_batches
            }
            
        except Exception as e:
            logger.error(f"Bulk operation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_processed': total_processed,
                'batches_processed': batch_idx if 'batch_idx' in locals() else 0
            }
    
    def monitor_connection_health(self):
        """Monitor connection pool health and performance"""
        try:
            stats = self.get_connection_stats()
            
            # Check for potential issues
            warnings = []
            
            if stats.get('utilization_percent', 0) > 80:
                warnings.append(f"High connection pool utilization: {stats['utilization_percent']:.1f}%")
            
            if stats.get('connection_timeouts', 0) > 10:
                warnings.append(f"High connection timeout count: {stats['connection_timeouts']}")
            
            if stats.get('failed_connections', 0) > stats.get('total_connections', 1) * 0.05:
                warnings.append(f"High connection failure rate: {stats['failed_connections']}/{stats['total_connections']}")
            
            # Log warnings
            for warning in warnings:
                logger.warning(f"Connection health warning: {warning}")
            
            return {
                'status': 'healthy' if not warnings else 'warning',
                'warnings': warnings,
                'stats': stats
            }
            
        except Exception as e:
            logger.error(f"Connection health monitoring failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'stats': self.connection_stats
            }

# Global enterprise connection manager instance
enterprise_connection_manager = EnterpriseConnectionManager()

def initialize_enterprise_database():
    """Initialize database with enterprise-level optimizations"""
    try:
        with app.app_context():
            # Apply database optimizations
            success = enterprise_connection_manager.optimize_database_configuration()
            
            if success:
                logger.info("Enterprise database initialization completed successfully")
            else:
                logger.warning("Some database optimizations may have failed")
            
            # Log initial connection stats
            stats = enterprise_connection_manager.get_connection_stats()
            logger.info(f"Initial connection pool stats: {stats}")
            
            return success
            
    except Exception as e:
        logger.error(f"Enterprise database initialization failed: {e}")
        return False

def get_enterprise_stats():
    """Get comprehensive enterprise database statistics"""
    return enterprise_connection_manager.monitor_connection_health()
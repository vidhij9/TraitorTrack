import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Callable
from functools import wraps
import time
from sqlalchemy import text
from sqlalchemy.pool import NullPool, QueuePool
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    """Performance optimization utilities for high-concurrency operations"""
    
    def __init__(self, db_session):
        self.db = db_session
        self.executor = ThreadPoolExecutor(max_workers=50)  # Support 50+ concurrent operations
        
    @staticmethod
    def batch_operation(items: List[Any], batch_size: int = 100) -> List[List[Any]]:
        """Split items into batches for bulk operations"""
        return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    
    @contextmanager
    def bulk_insert_context(self):
        """Context manager for bulk insert operations"""
        from app_clean import db
        
        # Temporarily disable autoflush for bulk operations
        with db.session.no_autoflush:
            try:
                yield db.session
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.error(f"Bulk insert error: {e}")
                raise
    
    def bulk_insert_bills(self, bills_data: List[Dict]) -> bool:
        """Bulk insert bills with optimized performance"""
        from models import Bill
        
        try:
            with self.bulk_insert_context() as session:
                # Use bulk_insert_mappings for maximum performance
                session.bulk_insert_mappings(Bill, bills_data)
            return True
        except Exception as e:
            logger.error(f"Bulk bill insert error: {e}")
            return False
    
    def bulk_link_bags_to_bill(self, bill_id: int, bag_ids: List[int]) -> bool:
        """Bulk link bags to a bill"""
        from models import BillBag
        from datetime import datetime
        
        try:
            # Prepare bulk data
            bill_bags_data = [
                {'bill_id': bill_id, 'bag_id': bag_id, 'created_at': datetime.utcnow()}
                for bag_id in bag_ids
            ]
            
            with self.bulk_insert_context() as session:
                # Use bulk insert for performance
                session.bulk_insert_mappings(BillBag, bill_bags_data)
            return True
        except Exception as e:
            logger.error(f"Bulk bag linking error: {e}")
            return False
    
    def optimized_bill_query(self, search_term: str = None, status_filter: str = 'all', 
                            limit: int = 100) -> List[Dict]:
        """Optimized bill query with single database hit"""
        from app_clean import db
        
        try:
            # Build optimized query with CTEs
            query = """
                WITH bill_bag_counts AS (
                    SELECT 
                        bill_id,
                        COUNT(*) as bag_count,
                        array_agg(bag_id) as bag_ids
                    FROM bill_bag
                    GROUP BY bill_id
                ),
                bill_with_counts AS (
                    SELECT 
                        b.*,
                        COALESCE(bbc.bag_count, 0) as linked_bags,
                        bbc.bag_ids,
                        CASE 
                            WHEN COALESCE(bbc.bag_count, 0) = b.parent_bag_count THEN 'completed'
                            WHEN COALESCE(bbc.bag_count, 0) > 0 THEN 'in_progress'
                            ELSE 'empty'
                        END as computed_status
                    FROM bill b
                    LEFT JOIN bill_bag_counts bbc ON b.id = bbc.bill_id
                )
                SELECT * FROM bill_with_counts
                WHERE 1=1
            """
            
            params = {}
            
            # Add search filter
            if search_term:
                query += " AND bill_id ILIKE :search_term"
                params['search_term'] = f"%{search_term}%"
            
            # Add status filter
            if status_filter != 'all':
                query += " AND computed_status = :status"
                params['status'] = status_filter
            
            # Add ordering and limit
            query += " ORDER BY created_at DESC LIMIT :limit"
            params['limit'] = limit
            
            result = db.session.execute(text(query), params)
            
            bills = []
            for row in result:
                bills.append({
                    'id': row.id,
                    'bill_id': row.bill_id,
                    'parent_bag_count': row.parent_bag_count,
                    'linked_bags': row.linked_bags,
                    'status': row.computed_status,
                    'created_at': row.created_at,
                    'bag_ids': row.bag_ids or []
                })
            
            return bills
        except Exception as e:
            logger.error(f"Optimized bill query error: {e}")
            return []
    
    async def parallel_bag_validation(self, qr_codes: List[str]) -> Dict[str, bool]:
        """Validate multiple QR codes in parallel"""
        from models import Bag
        
        async def validate_single(qr_code):
            try:
                exists = Bag.query.filter_by(qr_id=qr_code).first() is not None
                return qr_code, exists
            except:
                return qr_code, False
        
        # Run validations in parallel
        tasks = [validate_single(qr) for qr in qr_codes]
        results = await asyncio.gather(*tasks)
        
        return dict(results)

class DatabaseConnectionPool:
    """Enhanced database connection pooling for high concurrency"""
    
    @staticmethod
    def get_optimized_engine_config():
        """Get optimized database engine configuration"""
        return {
            "pool_size": 100,           # Increased for 50+ concurrent users
            "max_overflow": 200,        # Allow up to 300 total connections
            "pool_recycle": 300,        # Recycle connections every 5 minutes
            "pool_pre_ping": True,      # Test connections before use
            "pool_timeout": 30,         # Wait up to 30 seconds for connection
            "echo": False,              # Disable SQL logging for performance
            "echo_pool": False,         # Disable pool logging
            "poolclass": QueuePool,     # Use QueuePool for better concurrency
            "connect_args": {
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
                "connect_timeout": 10,
                "application_name": "TraceTrack_HighPerf",
                "options": "-c statement_timeout=30000 -c idle_in_transaction_session_timeout=20000"
            }
        }

class RateLimiter:
    """Custom rate limiter for specific operations"""
    
    def __init__(self):
        self.operations = {}
    
    def check_rate_limit(self, operation: str, identifier: str, 
                         max_requests: int = 100, window: int = 60) -> bool:
        """Check if operation is within rate limit"""
        import time
        
        key = f"{operation}:{identifier}"
        current_time = time.time()
        
        if key not in self.operations:
            self.operations[key] = []
        
        # Remove old entries outside the window
        self.operations[key] = [
            t for t in self.operations[key] 
            if current_time - t < window
        ]
        
        # Check if under limit
        if len(self.operations[key]) < max_requests:
            self.operations[key].append(current_time)
            return True
        
        return False

def measure_performance(func):
    """Decorator to measure function performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        if execution_time > 1000:  # Log slow operations (> 1 second)
            logger.warning(f"Slow operation: {func.__name__} took {execution_time:.2f}ms")
        else:
            logger.debug(f"Operation: {func.__name__} took {execution_time:.2f}ms")
        
        return result
    return wrapper

def retry_on_db_error(max_retries: int = 3, delay: float = 0.5):
    """Decorator to retry database operations on transient errors"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from sqlalchemy.exc import OperationalError, DatabaseError
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, DatabaseError) as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Database operation failed after {max_retries} attempts: {e}")
                        raise
                    
                    logger.warning(f"Database error, retrying ({attempt + 1}/{max_retries}): {e}")
                    time.sleep(delay * (2 ** attempt))  # Exponential backoff
            
            return None
        return wrapper
    return decorator
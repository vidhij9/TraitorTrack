"""
Async request handler for heavy operations
Implements request queuing and background processing
"""
import threading
import queue
import time
import functools
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

class AsyncOperationHandler:
    """Handles heavy operations asynchronously to prevent blocking"""
    
    def __init__(self, max_workers=8, queue_size=100):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.operation_queue = queue.Queue(maxsize=queue_size)
        self.results_cache = {}
        self.pending_operations = {}
        
    def submit_operation(self, operation_id, func, *args, **kwargs):
        """Submit an operation for async execution"""
        if operation_id in self.pending_operations:
            # Operation already pending
            return self.pending_operations[operation_id]
        
        # Submit to executor
        future = self.executor.submit(func, *args, **kwargs)
        self.pending_operations[operation_id] = future
        
        # Cleanup when done
        def cleanup(f):
            if operation_id in self.pending_operations:
                del self.pending_operations[operation_id]
            self.results_cache[operation_id] = f.result()
        
        future.add_done_callback(cleanup)
        return future
    
    def get_result(self, operation_id, timeout=30):
        """Get result of an async operation"""
        if operation_id in self.results_cache:
            return self.results_cache[operation_id]
        
        if operation_id in self.pending_operations:
            future = self.pending_operations[operation_id]
            try:
                result = future.result(timeout=timeout)
                return result
            except Exception as e:
                logger.error(f"Operation {operation_id} failed: {e}")
                raise
        
        return None
    
    def cleanup_old_results(self, max_age=300):
        """Clean up old cached results"""
        # Implementation would track timestamps
        pass

# Global handler instance
async_handler = AsyncOperationHandler()

def async_operation(timeout=30):
    """Decorator for marking operations as async"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            operation_id = f"{func.__name__}_{time.time()}"
            return async_handler.submit_operation(operation_id, func, *args, **kwargs)
        return wrapper
    return decorator

class RequestQueue:
    """Queue for managing concurrent requests"""
    
    def __init__(self, max_concurrent=20, timeout=30):
        self.semaphore = threading.Semaphore(max_concurrent)
        self.timeout = timeout
        self.active_requests = 0
        self.total_processed = 0
        self.lock = threading.Lock()
        
    def acquire(self):
        """Acquire a slot for processing"""
        acquired = self.semaphore.acquire(timeout=self.timeout)
        if acquired:
            with self.lock:
                self.active_requests += 1
        return acquired
    
    def release(self):
        """Release a processing slot"""
        self.semaphore.release()
        with self.lock:
            self.active_requests -= 1
            self.total_processed += 1
    
    def get_stats(self):
        """Get queue statistics"""
        with self.lock:
            return {
                'active_requests': self.active_requests,
                'total_processed': self.total_processed,
                'available_slots': 20 - self.active_requests
            }

# Global request queue
request_queue = RequestQueue(max_concurrent=20)

def rate_limited_operation(func):
    """Decorator for rate limiting operations"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not request_queue.acquire():
            raise Exception("Request queue full - too many concurrent operations")
        try:
            return func(*args, **kwargs)
        finally:
            request_queue.release()
    return wrapper

class BatchProcessor:
    """Process operations in batches for efficiency"""
    
    def __init__(self, batch_size=10, flush_interval=1.0):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.pending_items = []
        self.lock = threading.Lock()
        self.last_flush = time.time()
        self.processor_thread = None
        self.running = True
        self.start_processor()
    
    def add_item(self, item):
        """Add item to batch"""
        with self.lock:
            self.pending_items.append(item)
            if len(self.pending_items) >= self.batch_size:
                self._flush_batch()
    
    def _flush_batch(self):
        """Process pending batch"""
        if not self.pending_items:
            return
        
        batch = self.pending_items[:self.batch_size]
        self.pending_items = self.pending_items[self.batch_size:]
        
        # Process batch (override in subclass)
        self.process_batch(batch)
        self.last_flush = time.time()
    
    def process_batch(self, batch):
        """Override to implement batch processing logic"""
        pass
    
    def start_processor(self):
        """Start background processor thread"""
        def processor():
            while self.running:
                time.sleep(self.flush_interval)
                with self.lock:
                    if time.time() - self.last_flush > self.flush_interval:
                        self._flush_batch()
        
        self.processor_thread = threading.Thread(target=processor, daemon=True)
        self.processor_thread.start()
    
    def stop(self):
        """Stop processor"""
        self.running = False
        with self.lock:
            self._flush_batch()  # Flush remaining items

# Optimized database batch operations
class DatabaseBatchProcessor(BatchProcessor):
    """Batch database operations for efficiency"""
    
    def __init__(self, db_session):
        super().__init__(batch_size=50, flush_interval=0.5)
        self.db_session = db_session
    
    def process_batch(self, batch):
        """Process database operations in batch"""
        try:
            for operation in batch:
                # Execute operation
                operation()
            self.db_session.commit()
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            self.db_session.rollback()
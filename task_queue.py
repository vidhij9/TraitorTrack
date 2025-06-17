"""
Task queue module for asynchronous processing of background tasks.
Implements a lightweight, high-performance task queue for better responsiveness.
"""

import logging
import threading
import time
import traceback
import uuid
from collections import deque
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Constants
MAX_QUEUE_SIZE = 1000
THREAD_SLEEP_TIME = 0.1  # Sleep time between checks when queue is empty
MAX_TASK_HISTORY = 500  # Maximum number of completed tasks to keep in history

# Task states
TASK_PENDING = 'pending'
TASK_RUNNING = 'running'
TASK_COMPLETED = 'completed'
TASK_FAILED = 'failed'

# Global state
_task_queue = deque()
_task_results = {}  # task_id -> result dict
_worker_thread = None
_worker_running = False
_queue_lock = threading.RLock()


def _worker_loop():
    """Background worker to process tasks from the queue"""
    global _worker_running
    
    logger.info("Background task worker thread started")
    
    while _worker_running:
        task = None
        
        # Check if we have tasks to process
        with _queue_lock:
            if _task_queue:
                task = _task_queue.popleft()
        
        if task:
            task_id, func, args, kwargs = task
            
            try:
                # Mark as running
                with _queue_lock:
                    _task_results[task_id].update({
                        'status': TASK_RUNNING,
                        'started_at': datetime.utcnow().isoformat()
                    })
                
                # Execute the task
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Store result
                with _queue_lock:
                    _task_results[task_id].update({
                        'status': TASK_COMPLETED,
                        'result': result,
                        'execution_time': execution_time,
                        'completed_at': datetime.utcnow().isoformat()
                    })
                
                logger.info(f"Task {task_id} completed in {execution_time:.2f}s")
                
            except Exception as e:
                # Log the exception
                logger.exception(f"Error executing task {task_id}: {str(e)}")
                
                # Store error details
                with _queue_lock:
                    _task_results[task_id].update({
                        'status': TASK_FAILED,
                        'error': str(e),
                        'traceback': traceback.format_exc(),
                        'completed_at': datetime.utcnow().isoformat()
                    })
            
            # Clean up old tasks periodically
            cleanup_old_tasks()
        
        else:
            # No tasks in queue, sleep briefly
            time.sleep(THREAD_SLEEP_TIME)


def start_worker():
    """Start the background worker thread if not already running"""
    global _worker_thread, _worker_running
    
    if _worker_thread is None or not _worker_thread.is_alive():
        _worker_running = True
        _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
        _worker_thread.start()
        logger.info("Background task worker started")


def stop_worker():
    """Stop the background worker thread"""
    global _worker_running
    
    if _worker_running:
        _worker_running = False
        
        # Wait for worker to exit
        if _worker_thread and _worker_thread.is_alive():
            _worker_thread.join(timeout=1.0)
            
        logger.info("Background task worker stopped")


def enqueue_task(func: Callable, *args, **kwargs) -> str:
    """
    Enqueue a task for asynchronous execution
    
    Args:
        func: The function to execute
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        str: Task ID for checking status
    """
    # Generate unique ID for this task
    task_id = str(uuid.uuid4())
    
    # Create task result entry
    task_info = {
        'id': task_id,
        'status': TASK_PENDING,
        'function': func.__name__,
        'queued_at': datetime.utcnow().isoformat()
    }
    
    # Add to queue and results dict
    with _queue_lock:
        # Check queue size
        if len(_task_queue) >= MAX_QUEUE_SIZE:
            # Remove the oldest task
            _task_queue.popleft()
            logger.warning("Task queue full, dropped oldest task")
            
        # Add to queue
        _task_queue.append((task_id, func, args, kwargs))
        _task_results[task_id] = task_info
    
    # Ensure worker is running
    if not _worker_running:
        start_worker()
    
    return task_id


def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the status of a task
    
    Args:
        task_id: The ID of the task to check
        
    Returns:
        Optional[Dict]: Task status information or None if not found
    """
    with _queue_lock:
        return _task_results.get(task_id)


def cleanup_old_tasks(max_tasks: int = MAX_TASK_HISTORY):
    """
    Clean up old completed tasks to prevent memory leaks
    
    Args:
        max_tasks: Maximum number of tasks to keep in memory
    """
    with _queue_lock:
        # Check if we need to clean up
        if len(_task_results) <= max_tasks:
            return
        
        # Get completed and failed tasks sorted by completion time
        completed_tasks = [
            (task_id, info.get('completed_at', ''))
            for task_id, info in _task_results.items()
            if info['status'] in (TASK_COMPLETED, TASK_FAILED)
        ]
        
        # Sort by completion time (oldest first)
        completed_tasks.sort(key=lambda x: x[1])
        
        # Calculate how many to remove
        to_remove = len(_task_results) - max_tasks
        
        # Remove oldest completed tasks
        for i in range(min(to_remove, len(completed_tasks))):
            task_id = completed_tasks[i][0]
            del _task_results[task_id]


def async_task(f):
    """
    Decorator to make a function execute asynchronously
    
    Usage:
        @async_task
        def long_running_function(arg1, arg2):
            # Do something time-consuming
            return result
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        return enqueue_task(f, *args, **kwargs)
    
    return wrapper


def get_queue_stats() -> Dict[str, Any]:
    """
    Get statistics about the task queue
    
    Returns:
        Dict: Task queue statistics
    """
    with _queue_lock:
        # Count tasks by status
        status_counts = {
            TASK_PENDING: 0,
            TASK_RUNNING: 0,
            TASK_COMPLETED: 0,
            TASK_FAILED: 0
        }
        
        for task in _task_results.values():
            status = task.get('status')
            if status in status_counts:
                status_counts[status] += 1
        
        return {
            'queue_size': len(_task_queue),
            'max_queue_size': MAX_QUEUE_SIZE,
            'utilization_percentage': round((len(_task_queue) / MAX_QUEUE_SIZE) * 100, 2),
            'task_counts': status_counts,
            'total_tracked_tasks': len(_task_results),
            'worker_running': _worker_running
        }

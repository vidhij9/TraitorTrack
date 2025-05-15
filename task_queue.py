"""
Task queue module for asynchronous processing of background tasks.
Implements a lightweight, high-performance task queue for better responsiveness.
"""

import logging
import threading
import time
import queue
import functools
import uuid
from typing import Dict, Any, Callable, List, Optional

logger = logging.getLogger(__name__)

# Main task queue for background processing
_task_queue = queue.Queue()

# Task status tracking
_task_results: Dict[str, Dict[str, Any]] = {}
_task_lock = threading.RLock()

# Worker thread status
_worker_running = False
_worker_thread = None

def _worker_loop():
    """Background worker to process tasks from the queue"""
    global _worker_running
    
    logger.info("Background task worker started")
    _worker_running = True
    
    while _worker_running:
        try:
            # Get a task with a timeout to allow clean shutdown
            task_id, func, args, kwargs = _task_queue.get(timeout=1.0)
            
            # Update task status to running
            with _task_lock:
                if task_id in _task_results:
                    _task_results[task_id]['status'] = 'running'
            
            try:
                # Execute the task
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()
                
                # Update task status to completed with result
                with _task_lock:
                    if task_id in _task_results:
                        _task_results[task_id].update({
                            'status': 'completed',
                            'result': result,
                            'execution_time': end_time - start_time
                        })
                
                logger.info(f"Task {task_id} completed successfully in {end_time - start_time:.2f}s")
                
            except Exception as e:
                # Update task status to failed with error
                logger.exception(f"Task {task_id} failed with error: {str(e)}")
                with _task_lock:
                    if task_id in _task_results:
                        _task_results[task_id].update({
                            'status': 'failed',
                            'error': str(e)
                        })
            
            # Mark the task as done in the queue
            _task_queue.task_done()
            
            # Clean up old completed tasks (keep the last 100)
            cleanup_old_tasks(100)
            
        except queue.Empty:
            # No tasks in the queue, continue
            pass
        except Exception as e:
            logger.exception(f"Error in worker loop: {str(e)}")

def start_worker():
    """Start the background worker thread if not already running"""
    global _worker_thread, _worker_running
    
    if _worker_thread is None or not _worker_thread.is_alive():
        _worker_running = True
        _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
        _worker_thread.start()
        logger.info("Background task worker thread started")

def stop_worker():
    """Stop the background worker thread"""
    global _worker_running
    _worker_running = False
    logger.info("Background task worker shutdown requested")

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
    # Generate a unique task ID
    task_id = str(uuid.uuid4())
    
    # Store initial task status
    with _task_lock:
        _task_results[task_id] = {
            'status': 'queued',
            'queued_at': time.time()
        }
    
    # Add the task to the queue
    _task_queue.put((task_id, func, args, kwargs))
    logger.debug(f"Task {task_id} added to queue")
    
    # Ensure the worker is running
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
    with _task_lock:
        return _task_results.get(task_id)

def cleanup_old_tasks(max_tasks: int = 1000):
    """
    Clean up old completed tasks to prevent memory leaks
    
    Args:
        max_tasks: Maximum number of tasks to keep in memory
    """
    with _task_lock:
        # Keep only the most recent tasks
        if len(_task_results) > max_tasks:
            # Sort by queued_at time
            sorted_tasks = sorted(
                _task_results.items(),
                key=lambda x: x[1].get('queued_at', 0)
            )
            
            # Remove the oldest tasks
            to_remove = len(_task_results) - max_tasks
            for task_id, _ in sorted_tasks[:to_remove]:
                if _task_results[task_id].get('status') in ('completed', 'failed'):
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
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return enqueue_task(f, *args, **kwargs)
    return wrapper

def get_queue_stats() -> Dict[str, Any]:
    """
    Get statistics about the task queue
    
    Returns:
        Dict: Task queue statistics
    """
    with _task_lock:
        total_tasks = len(_task_results)
        queued = sum(1 for t in _task_results.values() if t.get('status') == 'queued')
        running = sum(1 for t in _task_results.values() if t.get('status') == 'running')
        completed = sum(1 for t in _task_results.values() if t.get('status') == 'completed')
        failed = sum(1 for t in _task_results.values() if t.get('status') == 'failed')
    
    return {
        'total_tasks': total_tasks,
        'queue_size': _task_queue.qsize(),
        'queued': queued,
        'running': running,
        'completed': completed,
        'failed': failed,
        'worker_running': _worker_running and (_worker_thread is not None and _worker_thread.is_alive())
    }

# Start the worker thread automatically when this module is imported
start_worker()
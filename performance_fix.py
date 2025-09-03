"""
Performance optimization patches for TraceTrack
Fixes slow response times and concurrent user handling
"""

import time
from flask import jsonify, session, request
from sqlalchemy import text, create_engine
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import os
import logging

logger = logging.getLogger(__name__)

# Create optimized database connection pool
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Increase pool size for concurrent users
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=20,  # Increased from default 5
        max_overflow=30,  # Allow up to 50 total connections
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=300,  # Recycle connections every 5 minutes
        echo=False  # Disable SQL logging for performance
    )
else:
    engine = None

@contextmanager
def get_db_connection():
    """Get a database connection from the pool"""
    if not engine:
        raise Exception("Database not configured")
    conn = engine.connect()
    try:
        yield conn
    finally:
        conn.close()

# Optimized queries using raw SQL
OPTIMIZED_QUERIES = {
    'find_parent_case_insensitive': """
        SELECT id, qr_id, type, status, weight_kg, user_id, dispatch_area
        FROM bag 
        WHERE UPPER(qr_id) = UPPER(:qr_id) AND type = 'parent'
        LIMIT 1
    """,
    
    'find_child_case_insensitive': """
        SELECT id, qr_id, type, status
        FROM bag 
        WHERE UPPER(qr_id) = UPPER(:qr_id)
        LIMIT 1
    """,
    
    'count_children': """
        SELECT COUNT(*) as count
        FROM link
        WHERE parent_bag_id = :parent_id
    """,
    
    'check_duplicate_link': """
        SELECT 1
        FROM link
        WHERE parent_bag_id = :parent_id AND child_bag_id = :child_id
        LIMIT 1
    """,
    
    'create_child_bag': """
        INSERT INTO bag (qr_id, type, status, user_id, dispatch_area, created_at)
        VALUES (:qr_id, 'child', 'pending', :user_id, :dispatch_area, NOW())
        ON CONFLICT (qr_id) DO UPDATE SET qr_id = EXCLUDED.qr_id
        RETURNING id
    """,
    
    'create_link': """
        INSERT INTO link (parent_bag_id, child_bag_id)
        VALUES (:parent_id, :child_id)
        ON CONFLICT DO NOTHING
    """,
    
    'record_scan': """
        INSERT INTO scan (parent_bag_id, child_bag_id, user_id, timestamp)
        VALUES (:parent_id, :child_id, :user_id, NOW())
    """,
    
    'update_parent_complete': """
        UPDATE bag 
        SET status = 'completed', weight_kg = 30.0
        WHERE id = :parent_id AND type = 'parent'
    """
}

def optimized_child_scan_handler(qr_code, parent_qr, user_id, dispatch_area):
    """
    Optimized child scan handler using raw SQL and connection pooling
    Target: <50ms response time
    """
    start_time = time.time()
    
    try:
        with get_db_connection() as conn:
            # Start transaction for consistency
            trans = conn.begin()
            
            try:
                # 1. Find parent bag (case-insensitive)
                parent_result = conn.execute(
                    text(OPTIMIZED_QUERIES['find_parent_case_insensitive']),
                    {'qr_id': parent_qr}
                ).fetchone()
                
                if not parent_result:
                    return {
                        'success': False, 
                        'message': 'Parent bag not found',
                        'time_ms': round((time.time() - start_time) * 1000, 2)
                    }
                
                parent_id = parent_result.id
                
                # 2. Check current count (fast query)
                count_result = conn.execute(
                    text(OPTIMIZED_QUERIES['count_children']),
                    {'parent_id': parent_id}
                ).scalar()
                
                current_count = count_result or 0
                
                if current_count >= 30:
                    return {
                        'success': False,
                        'message': 'Maximum 30 child bags reached!',
                        'current_count': current_count,
                        'time_ms': round((time.time() - start_time) * 1000, 2)
                    }
                
                # 3. Find or create child bag (case-insensitive)
                child_result = conn.execute(
                    text(OPTIMIZED_QUERIES['find_child_case_insensitive']),
                    {'qr_id': qr_code}
                ).fetchone()
                
                if child_result:
                    child_id = child_result.id
                    
                    # Check if it's a parent trying to be linked as child
                    if child_result.type == 'parent':
                        return {
                            'success': False,
                            'message': f'{qr_code} is a parent bag, cannot link as child',
                            'time_ms': round((time.time() - start_time) * 1000, 2)
                        }
                    
                    # Check for duplicate link
                    duplicate = conn.execute(
                        text(OPTIMIZED_QUERIES['check_duplicate_link']),
                        {'parent_id': parent_id, 'child_id': child_id}
                    ).fetchone()
                    
                    if duplicate:
                        return {
                            'success': False,
                            'message': f'Child {qr_code} already linked to this parent',
                            'current_count': current_count,
                            'time_ms': round((time.time() - start_time) * 1000, 2)
                        }
                else:
                    # Create new child bag
                    child_id = conn.execute(
                        text(OPTIMIZED_QUERIES['create_child_bag']),
                        {
                            'qr_id': qr_code.upper(),  # Normalize to uppercase
                            'user_id': user_id,
                            'dispatch_area': dispatch_area
                        }
                    ).scalar()
                
                # 4. Create link
                conn.execute(
                    text(OPTIMIZED_QUERIES['create_link']),
                    {'parent_id': parent_id, 'child_id': child_id}
                )
                
                # 5. Record scan (async if needed)
                conn.execute(
                    text(OPTIMIZED_QUERIES['record_scan']),
                    {
                        'parent_id': parent_id,
                        'child_id': child_id,
                        'user_id': user_id
                    }
                )
                
                # 6. Check if parent is complete
                new_count = current_count + 1
                if new_count >= 30:
                    conn.execute(
                        text(OPTIMIZED_QUERIES['update_parent_complete']),
                        {'parent_id': parent_id}
                    )
                    message = f'Parent {parent_qr} COMPLETE! ({new_count}/30 bags)'
                else:
                    message = f'Child {qr_code} linked successfully ({new_count}/30)'
                
                # Commit transaction
                trans.commit()
                
                return {
                    'success': True,
                    'message': message,
                    'current_count': new_count,
                    'is_complete': new_count >= 30,
                    'time_ms': round((time.time() - start_time) * 1000, 2)
                }
                
            except Exception as e:
                trans.rollback()
                raise e
                
    except Exception as e:
        logger.error(f"Optimized child scan error: {str(e)}")
        return {
            'success': False,
            'message': 'Database error - please retry',
            'error': str(e),
            'time_ms': round((time.time() - start_time) * 1000, 2)
        }

# Export for use in routes
__all__ = ['optimized_child_scan_handler', 'get_db_connection', 'OPTIMIZED_QUERIES']
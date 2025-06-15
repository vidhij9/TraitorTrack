"""
API endpoints for traitor track.
Provides a set of REST API endpoints for accessing data and system diagnostics.
"""

import logging
import os
import time
import psutil
from datetime import datetime, timedelta
from functools import wraps
from sqlalchemy import func
from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user, login_required

from app import db
from models import User, Bag, BagType, Scan
from cache_utils import get_cache_stats
from task_queue import get_queue_stats

logger = logging.getLogger(__name__)

# Create blueprint for API endpoints
api = Blueprint('api', __name__, url_prefix='/api')


def admin_only(f):
    """Decorator to restrict access to admin users only"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            return jsonify({'error': 'Access denied', 'status': 403}), 403
        return f(*args, **kwargs)
    return decorated_function


def json_response(f):
    """Decorator to standardize API responses"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            if isinstance(result, tuple):
                data, status_code = result
                return jsonify(data), status_code
            return jsonify(result)
        except Exception as e:
            logger.exception(f"API error: {str(e)}")
            return jsonify({
                'error': str(e),
                'status': 500,
                'timestamp': datetime.utcnow().isoformat()
            }), 500
    return decorated_function


@api.route('/health')
@json_response
def health_check():
    """Basic health check endpoint"""
    return {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '2.0.0'
    }


@api.route('/system')
@login_required
@admin_only
@json_response
def system_stats():
    """System diagnostic information for administrators"""
    # Get system stats
    uptime = time.time() - psutil.boot_time()
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Get database connection stats
    db_stats = {
        'engine': str(db.engine.name),
        'pool_size': db.engine.pool.size if hasattr(db.engine.pool, 'size') else 'N/A',
        'checkedout_connections': 0,  # This will be updated in real implementations
        'overflow': 0,  # This will be updated in real implementations
    }
    
    return {
        'system': {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'disk_percent': disk.percent,
            'uptime_seconds': uptime
        },
        'database': db_stats,
        'cache': get_cache_stats(),
        'task_queue': get_queue_stats(),
        'timestamp': datetime.utcnow().isoformat()
    }


@api.route('/entity-counts')
@login_required
@json_response
def entity_counts():
    """Get counts of various entities in the system"""
    counts = {
        'users': db.session.query(func.count(User.id)).scalar(),
        'parent_bags': db.session.query(func.count(Bag.id)).filter(Bag.type == BagType.PARENT.value).scalar(),
        'child_bags': db.session.query(func.count(Bag.id)).filter(Bag.type == BagType.CHILD.value).scalar(),
        'scans': db.session.query(func.count(Scan.id)).scalar(),
        'scans': db.session.query(func.count(Scan.id)).scalar(),
        'timestamp': datetime.utcnow().isoformat()
    }
    
    return counts


@api.route('/activity/<int:days>')
@login_required
@admin_only
@json_response
def activity_stats(days):
    """Get activity statistics for the past X days"""
    if days < 1 or days > 365:
        return {'error': 'Days parameter must be between 1 and 365'}, 400
    
    # Calculate the date for filtering
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get scan counts grouped by day
    scan_counts = db.session.query(
        func.date(Scan.created_at).label('date'),
        func.count(Scan.id).label('count')
    ).filter(
        Scan.created_at >= cutoff_date
    ).group_by(
        func.date(Scan.created_at)
    ).all()
    
    # Convert to dict for JSON serialization
    scan_data = {str(date): count for date, count in scan_counts}
    
    # Get user registration counts by day
    user_counts = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= cutoff_date
    ).group_by(
        func.date(User.created_at)
    ).all()
    
    # Convert to dict
    user_data = {str(date): count for date, count in user_counts}
    
    return {
        'scan_activity': scan_data,
        'user_registrations': user_data,
        'period_days': days,
        'timestamp': datetime.utcnow().isoformat()
    }


@api.route('/async/task/<task_id>')
@login_required
@json_response
def get_task_status(task_id):
    """Get status of an asynchronous task"""
    from task_queue import get_task_status as get_status
    
    status = get_status(task_id)
    if not status:
        return {'error': 'Task not found'}, 404
    
    return {
        'task': status,
        'timestamp': datetime.utcnow().isoformat()
    }


@api.route('/cache/stats')
@login_required
@admin_only
@json_response
def cache_stats():
    """Get cache statistics"""
    return {
        'cache': get_cache_stats(),
        'timestamp': datetime.utcnow().isoformat()
    }


@api.route('/cache/clear', methods=['POST'])
@login_required
@admin_only
@json_response
def clear_cache():
    """Clear the application cache"""
    from cache_utils import invalidate_cache
    
    namespace = request.json.get('namespace')
    prefix = request.json.get('prefix')
    
    invalidate_cache(prefix=prefix, namespace=namespace)
    
    return {
        'success': True,
        'message': f"Cache cleared: namespace={namespace}, prefix={prefix}",
        'timestamp': datetime.utcnow().isoformat()
    }
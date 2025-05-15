"""
API endpoints for TraceTrack.
Provides a set of REST API endpoints for accessing data and system diagnostics.
"""

import logging
import time
import datetime
import psutil
import json
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from functools import wraps
from models import Bag, BagType, Link, Location, Scan, User
from cache_utils import get_cache_stats
from task_queue import get_queue_stats
from app import db

logger = logging.getLogger(__name__)

# Create API blueprint
api = Blueprint('api', __name__, url_prefix='/api')

def admin_only(f):
    """Decorator to restrict access to admin users only"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            return jsonify({
                'status': 'error',
                'message': 'Admin access required'
            }), 403
        return f(*args, **kwargs)
    return decorated_function

def json_response(f):
    """Decorator to standardize API responses"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        try:
            result = f(*args, **kwargs)
            response_time = time.time() - start_time
            
            # If result is already a tuple with (json, status_code)
            if isinstance(result, tuple) and len(result) == 2:
                response_data, status_code = result
                if isinstance(response_data, dict):
                    response_data['response_time_ms'] = round(response_time * 1000, 2)
                return jsonify(response_data), status_code
            
            # Add response time to standard JSON response
            if isinstance(result, dict):
                result['response_time_ms'] = round(response_time * 1000, 2)
                return jsonify(result)
            else:
                return jsonify({
                    'status': 'success',
                    'data': result,
                    'response_time_ms': round(response_time * 1000, 2)
                })
        except Exception as e:
            logger.exception(f"API error in {f.__name__}: {str(e)}")
            response_time = time.time() - start_time
            return jsonify({
                'status': 'error',
                'message': str(e),
                'response_time_ms': round(response_time * 1000, 2)
            }), 500
    return decorated_function

@api.route('/health')
@json_response
def health_check():
    """Basic health check endpoint"""
    return {
        'status': 'online',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'version': getattr(current_app, 'version', '1.0.0')
    }

@api.route('/system/stats')
@login_required
@admin_only
@json_response
def system_stats():
    """System diagnostic information for administrators"""
    # Get basic system information
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Get database connection stats
    db_stats = {
        'engine': str(db.engine.name),
        'pool_size': db.engine.pool.size(),
        'checkedout_connections': db.engine.pool.checkedout(),
        'overflow': db.engine.pool.overflow(),
    }
    
    return {
        'system': {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available_mb': round(memory.available / (1024 * 1024), 2),
            'disk_percent': disk.percent,
            'disk_free_gb': round(disk.free / (1024 * 1024 * 1024), 2),
        },
        'database': db_stats,
        'cache': get_cache_stats(),
        'task_queue': get_queue_stats(),
        'application': {
            'uptime_seconds': int(time.time() - psutil.Process().create_time())
        }
    }

@api.route('/stats/counts')
@login_required
@json_response
def entity_counts():
    """Get counts of various entities in the system"""
    return {
        'parent_bags': db.session.query(db.func.count(Bag.id)).filter(Bag.type == BagType.PARENT.value).scalar(),
        'child_bags': db.session.query(db.func.count(Bag.id)).filter(Bag.type == BagType.CHILD.value).scalar(),
        'scans': db.session.query(db.func.count(Scan.id)).scalar(),
        'locations': db.session.query(db.func.count(Location.id)).scalar(),
        'users': db.session.query(db.func.count(User.id)).scalar()
    }

@api.route('/stats/activity/<days>')
@login_required
@admin_only
@json_response
def activity_stats(days):
    """Get activity statistics for the past X days"""
    try:
        days = int(days)
        if days < 1:
            days = 7  # Default to 7 days
    except ValueError:
        days = 7
    
    cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    
    # Get scans by day
    query = db.session.query(
        db.func.date(Scan.timestamp).label('date'),
        db.func.count().label('count')
    ).filter(
        Scan.timestamp >= cutoff_date
    ).group_by(
        db.func.date(Scan.timestamp)
    ).order_by(
        db.func.date(Scan.timestamp)
    )
    
    scans_by_day = [
        {'date': row.date.isoformat(), 'count': row.count}
        for row in query.all()
    ]
    
    # Get scans by location
    query = db.session.query(
        Location.name.label('location'),
        db.func.count().label('count')
    ).join(
        Scan, Scan.location_id == Location.id
    ).filter(
        Scan.timestamp >= cutoff_date
    ).group_by(
        Location.name
    ).order_by(
        db.func.count().desc()
    )
    
    scans_by_location = [
        {'location': row.location, 'count': row.count}
        for row in query.all()
    ]
    
    # Get scans by user
    query = db.session.query(
        User.username.label('user'),
        db.func.count().label('count')
    ).join(
        Scan, Scan.user_id == User.id
    ).filter(
        Scan.timestamp >= cutoff_date
    ).group_by(
        User.username
    ).order_by(
        db.func.count().desc()
    )
    
    scans_by_user = [
        {'user': row.user, 'count': row.count}
        for row in query.all()
    ]
    
    return {
        'period_days': days,
        'scans_by_day': scans_by_day,
        'scans_by_location': scans_by_location,
        'scans_by_user': scans_by_user
    }
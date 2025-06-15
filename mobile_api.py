"""
Mobile API endpoints for traitor track.
Provides lightweight, efficient API for mobile application integration.
"""

import logging
import json
from datetime import datetime
from functools import wraps
from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user, login_user, logout_user
from werkzeug.security import check_password_hash

from app import db
from models import User, Bag, BagType, Scan
from cache_utils import cached_response
from async_processing import process_scan_async

logger = logging.getLogger(__name__)

# Create blueprint for mobile API endpoints
mobile_api = Blueprint('mobile_api', __name__, url_prefix='/mobile-api')

# Security and authentication
def require_api_key(f):
    """Decorator to require valid API key for mobile access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-TraceTrack-Api-Key')
        if not api_key:
            return jsonify({'error': 'API key required', 'status': 401}), 401
        
        # Simple check for demo purposes - in production would verify against stored keys
        if api_key != current_app.config.get('MOBILE_API_KEY', 'tracetrack-mobile-key'):
            return jsonify({'error': 'Invalid API key', 'status': 401}), 401
            
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
            logger.exception(f"Mobile API error: {str(e)}")
            return jsonify({
                'error': str(e),
                'status': 500,
                'timestamp': datetime.utcnow().isoformat()
            }), 500
    return decorated_function

# Mobile login and authentication
@mobile_api.route('/login', methods=['POST'])
@json_response
def mobile_login():
    """Login endpoint for mobile app"""
    data = request.get_json()
    
    if not data:
        return {'error': 'No data provided'}, 400
        
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return {'error': 'Username and password required'}, 400
    
    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password_hash, password):
        login_user(user)
        return {
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'is_admin': user.is_admin()
            },
            'timestamp': datetime.utcnow().isoformat()
        }
    
    return {'error': 'Invalid credentials'}, 401

@mobile_api.route('/logout', methods=['POST'])
@json_response
def mobile_logout():
    """Logout endpoint for mobile app"""
    logout_user()
    return {
        'success': True,
        'message': 'Logged out successfully',
        'timestamp': datetime.utcnow().isoformat()
    }

# Scanning endpoints
@mobile_api.route('/scan/parent', methods=['POST'])
@require_api_key
@json_response
def mobile_scan_parent():
    """Scan parent bag from mobile device with Camera API"""
    data = request.get_json()
    
    if not data:
        return {'error': 'No data provided'}, 400
    
    qr_id = data.get('qr_id')
    location_id = data.get('location_id')
    user_id = data.get('user_id')
    notes = data.get('notes', '')
    
    if not qr_id or not location_id or not user_id:
        return {'error': 'Required fields missing'}, 400
    
    # Process scan via async processing for better mobile experience
    from async_processing import process_scan_async
    
    # Extract child count from QR ID if in format P123-5 (where 5 is the count)
    child_count = 5  # Default
    if '-' in qr_id:
        parts = qr_id.split('-')
        if len(parts) == 2 and parts[1].isdigit():
            child_count = int(parts[1])
    
    # Prepare scan data
    scan_data = {
        'qr_id': qr_id,
        'user_id': user_id,
        'location_id': location_id,
        'scan_type': 'parent',
        'notes': notes,
        'name': f"Parent Bag {qr_id}",
        'child_count': child_count
    }
    
    # Start async processing
    task_id = process_scan_async(scan_data)
    
    return {
        'success': True,
        'task_id': task_id,
        'message': f'Parent bag scan processing started',
        'child_count': child_count,
        'timestamp': datetime.utcnow().isoformat()
    }

@mobile_api.route('/scan/child', methods=['POST'])
@require_api_key
@json_response
def mobile_scan_child():
    """Scan child bag from mobile device with Camera API"""
    data = request.get_json()
    
    if not data:
        return {'error': 'No data provided'}, 400
    
    qr_id = data.get('qr_id')
    parent_id = data.get('parent_id')
    location_id = data.get('location_id')
    user_id = data.get('user_id')
    notes = data.get('notes', '')
    
    if not qr_id or not parent_id or not location_id or not user_id:
        return {'error': 'Required fields missing'}, 400
    
    # Process scan via async processing
    scan_data = {
        'qr_id': qr_id,
        'user_id': user_id,
        'location_id': location_id,
        'scan_type': 'child',
        'notes': notes,
        'name': f"Child Bag {qr_id}",
        'parent_id': parent_id
    }
    
    # Start async processing
    task_id = process_scan_async(scan_data)
    
    return {
        'success': True,
        'task_id': task_id,
        'message': f'Child bag scan processing started',
        'timestamp': datetime.utcnow().isoformat()
    }

# Data retrieval endpoints
@mobile_api.route('/locations')
@require_api_key
@cached_response(timeout=300, namespace='mobile')
@json_response
def get_locations():
    """Get all locations for mobile app"""
    locations = Location.query.all()
    
    location_list = [{
        'id': loc.id,
        'name': loc.name,
        'address': loc.address
    } for loc in locations]
    
    return {
        'locations': location_list,
        'count': len(location_list),
        'timestamp': datetime.utcnow().isoformat()
    }

@mobile_api.route('/bags/parent/<qr_id>')
@require_api_key
@json_response
def get_parent_bag(qr_id):
    """Get parent bag details for mobile app"""
    parent_bag = Bag.query.filter_by(qr_id=qr_id, type=BagType.PARENT.value).first()
    
    if not parent_bag:
        return {'error': 'Parent bag not found'}, 404
    
    # Get associated child bags
    child_bags = Bag.query.filter_by(parent_id=parent_bag.id, type=BagType.CHILD.value).all()
    
    child_list = [{
        'id': bag.id,
        'qr_id': bag.qr_id,
        'name': bag.name
    } for bag in child_bags]
    
    # Get recent scans
    scans = Scan.query.filter_by(parent_bag_id=parent_bag.id).order_by(Scan.created_at.desc()).limit(10).all()
    
    scan_list = [{
        'id': scan.id,
        'timestamp': scan.created_at.isoformat() if scan.created_at else None,
        'location_id': scan.location_id,
        'user_id': scan.user_id
    } for scan in scans]
    
    return {
        'parent_bag': {
            'id': parent_bag.id,
            'qr_id': parent_bag.qr_id,
            'name': parent_bag.name,
            'child_count': parent_bag.child_count,
            'child_bags': child_list,
            'recent_scans': scan_list
        },
        'timestamp': datetime.utcnow().isoformat()
    }

@mobile_api.route('/task/<task_id>')
@require_api_key
@json_response
def get_task_status(task_id):
    """Get status of an asynchronous task from mobile app"""
    from task_queue import get_task_status as get_status
    
    status = get_status(task_id)
    if not status:
        return {'error': 'Task not found'}, 404
    
    return {
        'task': status,
        'timestamp': datetime.utcnow().isoformat()
    }
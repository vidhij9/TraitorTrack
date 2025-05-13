import logging
from flask import jsonify, request, Blueprint, make_response
from flask_login import login_required, current_user
from app import app, db
from models import User, Bag, BagType, Link, Location, Scan
from cache_utils import cached_response, invalidate_cache
import time

logger = logging.getLogger(__name__)

# API Routes
@app.route('/api/parent_bags')
@login_required
@cached_response(timeout=30)  # Cache for 30 seconds
def api_parent_bags():
    """Get all parent bags"""
    parent_bags = Bag.query.filter_by(type=BagType.PARENT.value).all()
    response = make_response(jsonify({
        'success': True,
        'parent_bags': [bag.to_dict() for bag in parent_bags],
        'timestamp': time.time(),
        'cached': False
    }))
    # Set appropriate cache headers
    response.headers['Cache-Control'] = 'public, max-age=30'
    return response

@app.route('/api/child_bags')
@login_required
@cached_response(timeout=30)  # Cache for 30 seconds
def api_child_bags():
    """Get all child bags"""
    child_bags = Bag.query.filter_by(type=BagType.CHILD.value).all()
    response = make_response(jsonify({
        'success': True,
        'child_bags': [bag.to_dict() for bag in child_bags],
        'timestamp': time.time(),
        'cached': False
    }))
    response.headers['Cache-Control'] = 'public, max-age=30'
    return response

@app.route('/api/parent_bag/<qr_id>')
@login_required
def api_parent_bag(qr_id):
    """Get parent bag details by QR ID"""
    parent_bag = Bag.query.filter_by(qr_id=qr_id, type=BagType.PARENT.value).first()
    
    if not parent_bag:
        return jsonify({
            'success': False,
            'error': 'Parent bag not found'
        }), 404
    
    # Get all child bags for this parent
    child_bags = Bag.query.filter_by(parent_id=parent_bag.id, type=BagType.CHILD.value).all()
    
    return jsonify({
        'success': True,
        'parent_bag': parent_bag.to_dict(),
        'child_bags': [bag.to_dict() for bag in child_bags]
    })

@app.route('/api/child_bag/<qr_id>')
@login_required
def api_child_bag(qr_id):
    """Get child bag details by QR ID"""
    child_bag = Bag.query.filter_by(qr_id=qr_id, type=BagType.CHILD.value).first()
    
    if not child_bag:
        return jsonify({
            'success': False,
            'error': 'Child bag not found'
        }), 404
    
    # Get parent bag if exists
    parent_data = None
    if child_bag.parent_id:
        parent_bag = Bag.query.filter_by(id=child_bag.parent_id, type=BagType.PARENT.value).first()
        if parent_bag:
            parent_data = parent_bag.to_dict()
    
    return jsonify({
        'success': True,
        'child_bag': child_bag.to_dict(),
        'parent_bag': parent_data
    })

@app.route('/api/parent_bag/<qr_id>/scans')
@login_required
def api_parent_bag_scans(qr_id):
    """Get scan history for a parent bag"""
    parent_bag = Bag.query.filter_by(qr_id=qr_id, type=BagType.PARENT.value).first()
    
    if not parent_bag:
        return jsonify({
            'success': False,
            'error': 'Parent bag not found'
        }), 404
    
    scans = Scan.query.filter_by(parent_bag_id=parent_bag.id).order_by(Scan.timestamp.desc()).all()
    
    return jsonify({
        'success': True,
        'parent_bag': parent_bag.to_dict(),
        'scans': [scan.to_dict() for scan in scans]
    })

@app.route('/api/child_bag/<qr_id>/scans')
@login_required
def api_child_bag_scans(qr_id):
    """Get scan history for a child bag"""
    child_bag = Bag.query.filter_by(qr_id=qr_id, type=BagType.CHILD.value).first()
    
    if not child_bag:
        return jsonify({
            'success': False,
            'error': 'Child bag not found'
        }), 404
    
    scans = Scan.query.filter_by(child_bag_id=child_bag.id).order_by(Scan.timestamp.desc()).all()
    
    return jsonify({
        'success': True,
        'child_bag': child_bag.to_dict(),
        'scans': [scan.to_dict() for scan in scans]
    })

@app.route('/api/locations')
@login_required
def api_locations():
    """Get all locations"""
    locations = Location.query.all()
    return jsonify({
        'success': True,
        'locations': [location.to_dict() for location in locations]
    })

@app.route('/api/scans')
@login_required
def api_scans():
    """Get recent scans, with optional filtering"""
    # Get query parameters
    limit = request.args.get('limit', 50, type=int)
    scan_type = request.args.get('scan_type')  # 'parent' or 'child'
    location_id = request.args.get('location_id', type=int)
    
    # Base query
    query = Scan.query
    
    # Apply filters if provided
    if scan_type:
        query = query.filter_by(scan_type=scan_type)
    if location_id:
        query = query.filter_by(location_id=location_id)
    
    # Get results ordered by timestamp (newest first)
    scans = query.order_by(Scan.timestamp.desc()).limit(limit).all()
    
    return jsonify({
        'success': True,
        'scans': [scan.to_dict() for scan in scans]
    })

@app.route('/api/stats')
@login_required
def api_stats():
    """Get system statistics"""
    total_parent_bags = Bag.query.filter_by(type=BagType.PARENT.value).count()
    total_child_bags = Bag.query.filter_by(type=BagType.CHILD.value).count()
    total_scans = Scan.query.count()
    total_locations = Location.query.count()
    
    # Recent scans by type
    scan_type_counts = {}
    scan_types = db.session.query(Scan.scan_type, db.func.count(Scan.id)).group_by(Scan.scan_type).all()
    for scan_type, count in scan_types:
        scan_type_counts[scan_type] = count
    
    # Scans per location
    location_stats = {}
    location_scans = db.session.query(
        Location.name, db.func.count(Scan.id)
    ).join(Scan).group_by(Location.name).all()
    
    for location_name, count in location_scans:
        location_stats[location_name] = count
    
    return jsonify({
        'success': True,
        'statistics': {
            'total_parent_bags': total_parent_bags,
            'total_child_bags': total_child_bags,
            'total_scans': total_scans,
            'total_locations': total_locations,
            'scan_type_counts': scan_type_counts,
            'location_stats': location_stats
        }
    })

@app.route('/api/cache_stats')
@login_required
def api_cache_stats():
    """Get cache statistics"""
    from cache_utils import get_cache_stats
    stats = get_cache_stats()
    return jsonify({
        'success': True,
        'cache_stats': stats
    })

@app.route('/api/clear_cache', methods=['POST'])
@login_required
def api_clear_cache():
    """Clear the application cache"""
    prefix = request.args.get('prefix')
    invalidate_cache(prefix)
    return jsonify({
        'success': True,
        'message': f"Cache {'with prefix ' + prefix if prefix else 'completely'} cleared"
    })

@app.route('/api/seed_test_data', methods=['POST'])
@login_required
def seed_test_data():
    """Seed the database with some test data - for development only"""
    try:
        # Create locations
        locations = []
        location_names = [
            {"name": "Warehouse A", "address": "123 Main St"},
            {"name": "Distribution Center", "address": "456 State St"},
            {"name": "Retail Store", "address": "789 Market St"}
        ]
        
        for loc_data in location_names:
            location = Location()
            location.name = loc_data["name"]
            location.address = loc_data["address"]
            existing = Location.query.filter_by(name=location.name).first()
            if not existing:
                locations.append(location)
                db.session.add(location)
        
        # Create a test admin user if none exists
        admin_user = User.query.filter_by(username="admin").first()
        if not admin_user:
            admin_user = User()
            admin_user.username = "admin"
            admin_user.email = "admin@example.com"
            admin_user.set_password("adminpassword")
            admin_user.role = UserRole.ADMIN.value
            admin_user.verified = True
            db.session.add(admin_user)
            
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Test data seeded successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error seeding test data: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

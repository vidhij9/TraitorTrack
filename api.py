import logging
from flask import jsonify, request, Blueprint
from flask_login import login_required
from app import app, db
from models import ParentBag, ChildBag, Location, Scan, User

logger = logging.getLogger(__name__)

# API Routes
@app.route('/api/parent_bags')
def api_parent_bags():
    """Get all parent bags"""
    parent_bags = ParentBag.query.all()
    return jsonify({
        'success': True,
        'parent_bags': [bag.to_dict() for bag in parent_bags]
    })

@app.route('/api/child_bags')
def api_child_bags():
    """Get all child bags"""
    child_bags = ChildBag.query.all()
    return jsonify({
        'success': True,
        'child_bags': [bag.to_dict() for bag in child_bags]
    })

@app.route('/api/parent_bag/<qr_id>')
def api_parent_bag(qr_id):
    """Get parent bag details by QR ID"""
    parent_bag = ParentBag.query.filter_by(qr_id=qr_id).first()
    
    if not parent_bag:
        return jsonify({
            'success': False,
            'error': 'Parent bag not found'
        }), 404
    
    # Get all child bags for this parent
    child_bags = ChildBag.query.filter_by(parent_id=parent_bag.id).all()
    
    return jsonify({
        'success': True,
        'parent_bag': parent_bag.to_dict(),
        'child_bags': [bag.to_dict() for bag in child_bags]
    })

@app.route('/api/child_bag/<qr_id>')
def api_child_bag(qr_id):
    """Get child bag details by QR ID"""
    child_bag = ChildBag.query.filter_by(qr_id=qr_id).first()
    
    if not child_bag:
        return jsonify({
            'success': False,
            'error': 'Child bag not found'
        }), 404
    
    # Get parent bag if exists
    parent_data = None
    if child_bag.parent_id:
        parent_bag = ParentBag.query.get(child_bag.parent_id)
        if parent_bag:
            parent_data = parent_bag.to_dict()
    
    return jsonify({
        'success': True,
        'child_bag': child_bag.to_dict(),
        'parent_bag': parent_data
    })

@app.route('/api/parent_bag/<qr_id>/scans')
def api_parent_bag_scans(qr_id):
    """Get scan history for a parent bag"""
    parent_bag = ParentBag.query.filter_by(qr_id=qr_id).first()
    
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
def api_child_bag_scans(qr_id):
    """Get scan history for a child bag"""
    child_bag = ChildBag.query.filter_by(qr_id=qr_id).first()
    
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
def api_locations():
    """Get all locations"""
    locations = Location.query.all()
    return jsonify({
        'success': True,
        'locations': [location.to_dict() for location in locations]
    })

@app.route('/api/scans')
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
def api_stats():
    """Get system statistics"""
    total_parent_bags = ParentBag.query.count()
    total_child_bags = ChildBag.query.count()
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

@app.route('/api/seed_test_data', methods=['POST'])
@login_required
def seed_test_data():
    """Seed the database with some test data - for development only"""
    try:
        # Create locations
        locations = [
            Location(name="Warehouse A", address="123 Main St"),
            Location(name="Distribution Center", address="456 State St"),
            Location(name="Retail Store", address="789 Market St")
        ]
        
        for location in locations:
            existing = Location.query.filter_by(name=location.name).first()
            if not existing:
                db.session.add(location)
        
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

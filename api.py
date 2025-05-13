import logging
from flask import jsonify, request, Blueprint
from flask_login import login_required
from app import app, db
from models import Product, Scan, Location

logger = logging.getLogger(__name__)

# API Routes
@app.route('/api/products')
def api_products():
    """Get all products"""
    products = Product.query.all()
    return jsonify({
        'success': True,
        'products': [product.to_dict() for product in products]
    })

@app.route('/api/product/<qr_id>')
def api_product(qr_id):
    """Get product details by QR ID"""
    product = Product.query.filter_by(qr_id=qr_id).first()
    
    if not product:
        return jsonify({
            'success': False,
            'error': 'Product not found'
        }), 404
    
    return jsonify({
        'success': True,
        'product': product.to_dict()
    })

@app.route('/api/product/<qr_id>/scans')
def api_product_scans(qr_id):
    """Get scan history for a product"""
    product = Product.query.filter_by(qr_id=qr_id).first()
    
    if not product:
        return jsonify({
            'success': False,
            'error': 'Product not found'
        }), 404
    
    scans = Scan.query.filter_by(product_id=product.id).order_by(Scan.timestamp.desc()).all()
    
    return jsonify({
        'success': True,
        'product': product.to_dict(),
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
    status = request.args.get('status')
    location_id = request.args.get('location_id', type=int)
    
    # Base query
    query = Scan.query
    
    # Apply filters if provided
    if status:
        query = query.filter_by(status=status)
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
    total_products = Product.query.count()
    total_scans = Scan.query.count()
    total_locations = Location.query.count()
    
    # Recent scans by status
    status_counts = {}
    statuses = db.session.query(Scan.status, db.func.count(Scan.id)).group_by(Scan.status).all()
    for status, count in statuses:
        status_counts[status] = count
    
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
            'total_products': total_products,
            'total_scans': total_scans,
            'total_locations': total_locations,
            'status_counts': status_counts,
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
            Location(name="Warehouse A", address="123 Main St", latitude=40.7128, longitude=-74.0060, location_type="warehouse"),
            Location(name="Distribution Center", address="456 State St", latitude=34.0522, longitude=-118.2437, location_type="distribution"),
            Location(name="Retail Store", address="789 Market St", latitude=37.7749, longitude=-122.4194, location_type="retail")
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

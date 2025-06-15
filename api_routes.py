from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import User, Bag, Scan, Link, BagType
from app import db
from sqlalchemy import desc, func
from datetime import datetime, timedelta

api_bp = Blueprint('api', __name__)

@api_bp.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

@api_bp.route('/stats')
@login_required
def stats():
    """Get system statistics"""
    stats = {
        'total_users': User.query.count(),
        'total_parent_bags': Bag.query.filter_by(type=BagType.PARENT.value).count(),
        'total_child_bags': Bag.query.filter_by(type=BagType.CHILD.value).count(),
        'total_scans': Scan.query.count(),
        'total_links': Link.query.count(),
        'today_scans': Scan.query.filter(
            func.date(Scan.timestamp) == datetime.utcnow().date()
        ).count()
    }
    
    return jsonify(stats)

@api_bp.route('/bags')
@login_required
def get_bags():
    """Get bags with optional filtering"""
    bag_type = request.args.get('type')
    limit = request.args.get('limit', 50, type=int)
    
    query = Bag.query
    if bag_type:
        query = query.filter_by(type=bag_type)
    
    bags = query.order_by(Bag.created_at.desc()).limit(limit).all()
    
    return jsonify([bag.to_dict() for bag in bags])

@api_bp.route('/bags/<qr_id>')
@login_required
def get_bag_by_qr(qr_id):
    """Get bag by QR ID"""
    bag = Bag.query.filter_by(qr_id=qr_id).first()
    
    if not bag:
        return jsonify({'error': 'Bag not found'}), 404
    
    result = bag.to_dict()
    
    # Add scan history
    if bag.type == BagType.PARENT.value:
        scans = Scan.query.filter_by(parent_bag_id=bag.id).order_by(Scan.timestamp.desc()).limit(10).all()
    else:
        scans = Scan.query.filter_by(child_bag_id=bag.id).order_by(Scan.timestamp.desc()).limit(10).all()
    
    result['recent_scans'] = [scan.to_dict() for scan in scans]
    
    return jsonify(result)

@api_bp.route('/scans')
@login_required
def get_scans():
    """Get recent scans"""
    limit = request.args.get('limit', 50, type=int)
    user_id = request.args.get('user_id', type=int)
    
    query = Scan.query
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    scans = query.order_by(Scan.timestamp.desc()).limit(limit).all()
    
    return jsonify([scan.to_dict() for scan in scans])

@api_bp.route('/scan', methods=['POST'])
@login_required
def create_scan():
    """Create a new scan via API"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    parent_qr_id = data.get('parent_qr_id')
    child_qr_id = data.get('child_qr_id')
    notes = data.get('notes', '')
    
    if not parent_qr_id:
        return jsonify({'error': 'Parent QR ID is required'}), 400
    
    try:
        # Find or create parent bag
        parent_bag = Bag.query.filter_by(qr_id=parent_qr_id).first()
        if not parent_bag:
            parent_bag = Bag(qr_id=parent_qr_id, type=BagType.PARENT.value)
            db.session.add(parent_bag)
            db.session.flush()
        
        child_bag = None
        if child_qr_id:
            # Find or create child bag
            child_bag = Bag.query.filter_by(qr_id=child_qr_id).first()
            if not child_bag:
                child_bag = Bag(qr_id=child_qr_id, type=BagType.CHILD.value, parent_id=parent_bag.id)
                db.session.add(child_bag)
                db.session.flush()
            
            # Create or update link
            link = Link.query.filter_by(parent_bag_id=parent_bag.id, child_bag_id=child_bag.id).first()
            if not link:
                link = Link(
                    parent_bag_id=parent_bag.id,
                    child_bag_id=child_bag.id,
                    linked_by=current_user.id
                )
                db.session.add(link)
        
        # Create scan record
        scan = Scan(
            parent_bag_id=parent_bag.id,
            child_bag_id=child_bag.id if child_bag else None,
            user_id=current_user.id,
            notes=notes
        )
        db.session.add(scan)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'scan_id': scan.id,
            'message': 'Scan created successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/user/profile')
@login_required
def get_user_profile():
    """Get current user profile"""
    user_data = current_user.to_dict()
    
    # Add user statistics
    user_data['total_scans'] = Scan.query.filter_by(user_id=current_user.id).count()
    user_data['today_scans'] = Scan.query.filter(
        Scan.user_id == current_user.id,
        func.date(Scan.timestamp) == datetime.utcnow().date()
    ).count()
    
    return jsonify(user_data)
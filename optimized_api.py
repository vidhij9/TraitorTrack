"""
High-performance API endpoints with optimized database queries and mobile-friendly responses
"""
import logging
from flask import jsonify, request, Blueprint, make_response, session
from app_clean import app, db
from models import User, Bag, BagType, Link, Scan, Bill, BillBag
from cache_utils import cached_response, invalidate_cache
from production_auth_fix import require_production_auth
import time
from datetime import datetime, timedelta
from sqlalchemy import func, text, desc, and_, or_
from sqlalchemy.orm import joinedload, selectinload, load_only

logger = logging.getLogger(__name__)

# =============================================================================
# OPTIMIZED BAG MANAGEMENT ENDPOINTS
# =============================================================================

@app.route('/api/v2/bags/parent/list')
@require_production_auth
@cached_response(timeout=60)
def get_optimized_parent_bags():
    """Get parent bags with optimized query and minimal data for mobile"""
    # Use optimized query with selective loading
    parent_bags = db.session.query(Bag)\
        .filter_by(type=BagType.PARENT.value)\
        .options(load_only(Bag.id, Bag.qr_id, Bag.name, Bag.child_count, Bag.created_at))\
        .order_by(desc(Bag.created_at))\
        .all()
    
    # Get scan counts efficiently in batch
    bag_ids = [bag.id for bag in parent_bags]
    scan_counts = {}
    if bag_ids:
        scan_data = db.session.query(Scan.parent_bag_id, func.count(Scan.id))\
            .filter(Scan.parent_bag_id.in_(bag_ids))\
            .group_by(Scan.parent_bag_id)\
            .all()
        scan_counts = {bag_id: count for bag_id, count in scan_data}
    
    # Build mobile-optimized response
    mobile_data = []
    for bag in parent_bags:
        mobile_data.append({
            'id': bag.id,
            'qr_id': bag.qr_id,
            'name': bag.name or f"Parent {bag.qr_id}",
            'child_count': bag.child_count or 5,
            'scan_count': scan_counts.get(bag.id, 0),
            'created_at': bag.created_at.isoformat() if bag.created_at else None
        })
    
    response = make_response(jsonify({
        'success': True,
        'data': mobile_data,
        'count': len(mobile_data),
        'timestamp': time.time(),
        'mobile_optimized': True
    }))
    response.headers['Cache-Control'] = 'public, max-age=60'
    return response

@app.route('/api/v2/bags/child/list')
@require_production_auth
@cached_response(timeout=60)
def get_optimized_child_bags():
    """Get child bags with optimized query and parent info for mobile"""
    # Optimized query with join to get parent info
    child_bags = db.session.query(Bag)\
        .filter_by(type=BagType.CHILD.value)\
        .options(load_only(Bag.id, Bag.qr_id, Bag.name, Bag.parent_id, Bag.created_at))\
        .order_by(desc(Bag.created_at))\
        .all()
    
    # Get parent QR IDs efficiently
    parent_ids = [bag.parent_id for bag in child_bags if bag.parent_id]
    parent_qrs = {}
    if parent_ids:
        parent_data = db.session.query(Bag.id, Bag.qr_id)\
            .filter(Bag.id.in_(parent_ids), Bag.type == BagType.PARENT.value)\
            .all()
        parent_qrs = {bag_id: qr_id for bag_id, qr_id in parent_data}
    
    # Get scan counts efficiently
    bag_ids = [bag.id for bag in child_bags]
    scan_counts = {}
    if bag_ids:
        scan_data = db.session.query(Scan.child_bag_id, func.count(Scan.id))\
            .filter(Scan.child_bag_id.in_(bag_ids))\
            .group_by(Scan.child_bag_id)\
            .all()
        scan_counts = {bag_id: count for bag_id, count in scan_data}
    
    # Build mobile-optimized response
    mobile_data = []
    for bag in child_bags:
        mobile_data.append({
            'id': bag.id,
            'qr_id': bag.qr_id,
            'name': bag.name or f"Child {bag.qr_id}",
            'parent_qr': parent_qrs.get(bag.parent_id, 'None'),
            'scan_count': scan_counts.get(bag.id, 0),
            'created_at': bag.created_at.isoformat() if bag.created_at else None
        })
    
    response = make_response(jsonify({
        'success': True,
        'data': mobile_data,
        'count': len(mobile_data),
        'timestamp': time.time(),
        'mobile_optimized': True
    }))
    response.headers['Cache-Control'] = 'public, max-age=60'
    return response

@app.route('/api/v2/bags/parent/<qr_id>/details')
@require_production_auth
def get_optimized_parent_details(qr_id):
    """Get parent bag details with optimized child loading"""
    # Single query to get parent with child info
    parent_bag = db.session.query(Bag)\
        .filter_by(qr_id=qr_id, type=BagType.PARENT.value, status='active')\
        .first()
    
    if not parent_bag:
        return jsonify({
            'success': False,
            'error': 'Parent bag not found',
            'error_code': 'PARENT_BAG_NOT_FOUND'
        }), 404
    
    # Get child bags with optimized query
    child_bags = db.session.query(Bag)\
        .filter_by(parent_id=parent_bag.id, type=BagType.CHILD.value, status='active')\
        .options(load_only(Bag.id, Bag.qr_id, Bag.name, Bag.created_at))\
        .order_by(Bag.created_at)\
        .all()
    
    # Get recent scans efficiently
    recent_scans = db.session.query(Scan)\
        .filter_by(parent_bag_id=parent_bag.id)\
        .options(joinedload(Scan.user).load_only(User.username))\
        .order_by(desc(Scan.timestamp))\
        .limit(5)\
        .all()
    
    # Get total scan count
    total_scans = db.session.query(func.count(Scan.id))\
        .filter_by(parent_bag_id=parent_bag.id)\
        .scalar()
    
    # Get associated bill
    bill_data = None
    bill_link = db.session.query(BillBag)\
        .filter_by(bag_id=parent_bag.id)\
        .options(joinedload(BillBag.bill).load_only(Bill.bill_id, Bill.status, Bill.description))\
        .first()
    if bill_link:
        bill_data = {
            'bill_id': bill_link.bill.bill_id,
            'status': bill_link.bill.status,
            'description': bill_link.bill.description
        }
    
    return jsonify({
        'success': True,
        'data': {
            'parent_bag': {
                'id': parent_bag.id,
                'qr_id': parent_bag.qr_id,
                'name': parent_bag.name,
                'child_count': parent_bag.child_count or 5,
                'created_at': parent_bag.created_at.isoformat() if parent_bag.created_at else None,
                'total_scans': total_scans
            },
            'child_bags': [
                {
                    'id': bag.id,
                    'qr_id': bag.qr_id,
                    'name': bag.name,
                    'created_at': bag.created_at.isoformat() if bag.created_at else None
                } for bag in child_bags
            ],
            'recent_scans': [
                {
                    'id': scan.id,
                    'timestamp': scan.timestamp.isoformat() if scan.timestamp else None,
                    'user': scan.user.username if scan.user else 'Unknown'
                } for scan in recent_scans
            ],
            'bill': bill_data,
            'child_count_actual': len(child_bags),
            'child_count_expected': parent_bag.child_count or 5
        }
    })

@app.route('/api/v2/scans/recent')
@require_production_auth
@cached_response(timeout=30)
def get_optimized_recent_scans():
    """Get recent scans with optimized query for mobile dashboard"""
    limit = min(int(request.args.get('limit', 20)), 100)  # Max 100 for performance
    
    # Single optimized query with all needed joins
    recent_scans = db.session.query(Scan)\
        .options(
            joinedload(Scan.user).load_only(User.username),
            joinedload(Scan.parent_bag).load_only(Bag.qr_id),
            joinedload(Scan.child_bag).load_only(Bag.qr_id)
        )\
        .order_by(desc(Scan.timestamp))\
        .limit(limit)\
        .all()
    
    # Build mobile-optimized response
    mobile_scans = []
    for scan in recent_scans:
        scan_data = {
            'id': scan.id,
            'timestamp': scan.timestamp.isoformat() if scan.timestamp else None,
            'user': scan.user.username if scan.user else 'Unknown',
            'type': 'parent' if scan.parent_bag_id else 'child',
            'bag_qr': (scan.parent_bag.qr_id if scan.parent_bag else 
                      scan.child_bag.qr_id if scan.child_bag else 'Unknown')
        }
        mobile_scans.append(scan_data)
    
    response = make_response(jsonify({
        'success': True,
        'data': mobile_scans,
        'count': len(mobile_scans),
        'timestamp': time.time(),
        'mobile_optimized': True
    }))
    response.headers['Cache-Control'] = 'public, max-age=30'
    return response

@app.route('/api/v2/dashboard/stats')
@require_production_auth
@cached_response(timeout=120)
def get_optimized_dashboard_stats():
    """Get dashboard statistics with single optimized queries"""
    # Get all stats in parallel queries
    stats_queries = {
        'total_parent_bags': db.session.query(func.count(Bag.id)).filter_by(type=BagType.PARENT.value),
        'total_child_bags': db.session.query(func.count(Bag.id)).filter_by(type=BagType.CHILD.value),
        'total_scans': db.session.query(func.count(Scan.id)),
        'total_bills': db.session.query(func.count(Bill.id)),
        'active_users': db.session.query(func.count(User.id))
    }
    
    # Execute all queries
    stats = {}
    for key, query in stats_queries.items():
        stats[key] = query.scalar() or 0
    
    # Get today's activity
    today = datetime.now().date()
    today_scans = db.session.query(func.count(Scan.id))\
        .filter(func.date(Scan.timestamp) == today)\
        .scalar() or 0
    
    # Get recent activity trend (last 7 days)
    week_ago = datetime.now() - timedelta(days=7)
    daily_scans = db.session.query(
        func.date(Scan.timestamp).label('scan_date'),
        func.count(Scan.id).label('scan_count')
    )\
        .filter(Scan.timestamp >= week_ago)\
        .group_by(func.date(Scan.timestamp))\
        .order_by(func.date(Scan.timestamp))\
        .all()
    
    activity_trend = [
        {
            'date': scan_date.isoformat() if scan_date else None,
            'count': scan_count
        } for scan_date, scan_count in daily_scans
    ]
    
    response = make_response(jsonify({
        'success': True,
        'data': {
            'overview': stats,
            'today_scans': today_scans,
            'activity_trend': activity_trend,
            'performance': {
                'avg_scans_per_day': sum(item['count'] for item in activity_trend) / max(len(activity_trend), 1),
                'active_bags_ratio': (stats['total_parent_bags'] + stats['total_child_bags']) / max(stats['total_scans'] / 10, 1) if stats['total_scans'] > 0 else 0
            }
        },
        'timestamp': time.time(),
        'mobile_optimized': True
    }))
    response.headers['Cache-Control'] = 'public, max-age=120'
    return response

# =============================================================================
# MOBILE-SPECIFIC ENDPOINTS
# =============================================================================

@app.route('/api/mobile/scan/submit', methods=['POST'])
@require_production_auth
def mobile_scan_submit():
    """Mobile-optimized scan submission endpoint"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        qr_code = data.get('qr_code', '').strip()
        scan_type = data.get('type', 'manual')  # manual, auto, bulk
        
        if not qr_code:
            return jsonify({'success': False, 'error': 'QR code is required'}), 400
        
        # Get user ID from session
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401
        
        # Determine bag type and find bag efficiently
        bag = None
        parent_bag_id = None
        child_bag_id = None
        
        # Check if it's a parent bag first (they usually start with 'P')
        if qr_code.upper().startswith('P'):
            bag = db.session.query(Bag)\
                .filter_by(qr_id=qr_code, type=BagType.PARENT.value, status='active')\
                .first()
            if bag:
                parent_bag_id = bag.id
        else:
            # Check for child bag
            bag = db.session.query(Bag)\
                .filter_by(qr_id=qr_code, type=BagType.CHILD.value, status='active')\
                .first()
            if bag:
                child_bag_id = bag.id
        
        if not bag:
            return jsonify({
                'success': False, 
                'error': f'Bag with QR code {qr_code} not found',
                'error_code': 'BAG_NOT_FOUND'
            }), 404
        
        # Create scan record
        new_scan = Scan(
            parent_bag_id=parent_bag_id,
            child_bag_id=child_bag_id,
            user_id=user_id,
            scan_type=scan_type,
            timestamp=datetime.utcnow()
        )
        
        db.session.add(new_scan)
        db.session.commit()
        
        # Clear relevant caches
        invalidate_cache(prefix='recent_scans')
        invalidate_cache(prefix='dashboard_stats')
        
        # Return mobile-optimized response
        return jsonify({
            'success': True,
            'data': {
                'scan_id': new_scan.id,
                'bag_type': bag.type,
                'bag_qr': bag.qr_id,
                'bag_name': bag.name,
                'timestamp': new_scan.timestamp.isoformat()
            },
            'message': f'Successfully scanned {bag.type} bag {bag.qr_id}'
        })
        
    except Exception as e:
        logger.error(f"Mobile scan submission error: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Scan submission failed',
            'error_code': 'SCAN_SUBMISSION_ERROR'
        }), 500

@app.route('/api/mobile/bags/search')
@require_production_auth
def mobile_bag_search():
    """Mobile-optimized bag search endpoint"""
    query = request.args.get('q', '').strip()
    bag_type = request.args.get('type', 'all')  # all, parent, child
    limit = min(int(request.args.get('limit', 10)), 50)
    
    if not query or len(query) < 2:
        return jsonify({
            'success': False,
            'error': 'Search query must be at least 2 characters'
        }), 400
    
    # Build search query
    search_filter = or_(
        Bag.qr_id.ilike(f'%{query}%'),
        Bag.name.ilike(f'%{query}%')
    )
    
    bags_query = db.session.query(Bag)\
        .filter(search_filter, Bag.status == 'active')\
        .options(load_only(Bag.id, Bag.qr_id, Bag.name, Bag.type, Bag.parent_id))
    
    if bag_type == 'parent':
        bags_query = bags_query.filter_by(type=BagType.PARENT.value)
    elif bag_type == 'child':
        bags_query = bags_query.filter_by(type=BagType.CHILD.value)
    
    bags = bags_query.order_by(Bag.qr_id).limit(limit).all()
    
    # Get parent QR IDs for child bags
    parent_ids = [bag.parent_id for bag in bags if bag.type == BagType.CHILD.value and bag.parent_id]
    parent_qrs = {}
    if parent_ids:
        parent_data = db.session.query(Bag.id, Bag.qr_id)\
            .filter(Bag.id.in_(parent_ids))\
            .all()
        parent_qrs = {bag_id: qr_id for bag_id, qr_id in parent_data}
    
    # Build mobile response
    results = []
    for bag in bags:
        bag_data = {
            'id': bag.id,
            'qr_id': bag.qr_id,
            'name': bag.name,
            'type': bag.type
        }
        if bag.type == BagType.CHILD.value and bag.parent_id:
            bag_data['parent_qr'] = parent_qrs.get(bag.parent_id, 'Unknown')
        
        results.append(bag_data)
    
    return jsonify({
        'success': True,
        'data': results,
        'count': len(results),
        'query': query,
        'mobile_optimized': True
    })

@app.route('/api/mobile/user/profile')
@require_production_auth
def mobile_user_profile():
    """Get user profile info for mobile app"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    # Get user with scan statistics
    user = db.session.query(User)\
        .options(load_only(User.id, User.username, User.email, User.role, User.created_at, User.last_login))\
        .filter_by(id=user_id)\
        .first()
    
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Get user's scan statistics
    total_scans = db.session.query(func.count(Scan.id)).filter_by(user_id=user_id).scalar() or 0
    
    today = datetime.now().date()
    today_scans = db.session.query(func.count(Scan.id))\
        .filter(Scan.user_id == user_id, func.date(Scan.timestamp) == today)\
        .scalar() or 0
    
    # Get recent activity
    recent_scans = db.session.query(Scan)\
        .filter_by(user_id=user_id)\
        .options(
            joinedload(Scan.parent_bag).load_only(Bag.qr_id),
            joinedload(Scan.child_bag).load_only(Bag.qr_id)
        )\
        .order_by(desc(Scan.timestamp))\
        .limit(5)\
        .all()
    
    recent_activity = [
        {
            'timestamp': scan.timestamp.isoformat() if scan.timestamp else None,
            'bag_qr': (scan.parent_bag.qr_id if scan.parent_bag else 
                      scan.child_bag.qr_id if scan.child_bag else 'Unknown'),
            'type': 'parent' if scan.parent_bag_id else 'child'
        } for scan in recent_scans
    ]
    
    return jsonify({
        'success': True,
        'data': {
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None
            },
            'statistics': {
                'total_scans': total_scans,
                'today_scans': today_scans,
                'recent_activity': recent_activity
            }
        },
        'mobile_optimized': True
    })

# =============================================================================
# SYSTEM HEALTH AND PERFORMANCE ENDPOINTS
# =============================================================================

@app.route('/api/system/health')
def system_health():
    """System health check for monitoring"""
    try:
        # Quick database connectivity test
        db.session.execute(text('SELECT 1')).fetchone()
        
        # Get basic system stats
        stats = {
            'database': 'connected',
            'cache': 'active',
            'timestamp': time.time(),
            'version': '2.0.0'
        }
        
        return jsonify({
            'status': 'healthy',
            'checks': stats
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/api/system/performance')
@require_production_auth
def system_performance():
    """Get system performance metrics"""
    try:
        # Database performance metrics
        db_stats = {
            'connection_pool_size': db.engine.pool.size(),
            'connection_pool_checked_out': db.engine.pool.checkedout(),
            'connection_pool_overflow': db.engine.pool.overflow(),
        }
        
        # Cache performance metrics
        from cache_utils import get_cache_stats
        cache_stats = get_cache_stats()
        
        return jsonify({
            'success': True,
            'data': {
                'database': db_stats,
                'cache': cache_stats,
                'timestamp': time.time()
            }
        })
    except Exception as e:
        logger.error(f"Performance metrics error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get performance metrics'
        }), 500

# Register error handlers for API endpoints
@app.errorhandler(400)
def bad_request_api(error):
    if request.path.startswith('/api/'):
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'error_code': 'BAD_REQUEST'
        }), 400
    return error

@app.errorhandler(404)
def not_found_api(error):
    if request.path.startswith('/api/'):
        return jsonify({
            'success': False,
            'error': 'Resource not found',
            'error_code': 'NOT_FOUND'
        }), 404
    return error

@app.errorhandler(500)
def internal_error_api(error):
    if request.path.startswith('/api/'):
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'error_code': 'INTERNAL_ERROR'
        }), 500
    return error
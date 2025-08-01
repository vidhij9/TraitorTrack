import logging
from flask import jsonify, request, Blueprint, make_response, session
from app_clean import app, db
from models import User, Bag, BagType, Link, Scan
from cache_manager import cached_response, invalidate_cache
from auth_utils import require_auth
import time
from datetime import datetime, timedelta
from sqlalchemy import func, or_, case

logger = logging.getLogger(__name__)

# =============================================================================
# IMPROVED API ENDPOINTS WITH DESCRIPTIVE NAMES
# =============================================================================

# BAG MANAGEMENT ENDPOINTS
@app.route('/api/bags/parent/list')
@require_auth
@cached_response(timeout=30)
def get_all_parent_bags():
    """Get paginated list of parent bags optimized for large datasets"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        search = request.args.get('search', '').strip()
        
        # Build efficient query with proper indexing
        query = db.session.query(Bag).filter(Bag.type == BagType.PARENT.value)
        
        if search:
            query = query.filter(
                or_(
                    Bag.qr_id.ilike(f'%{search}%'),
                    Bag.name.ilike(f'%{search}%')
                )
            )
        
        # Get total count efficiently
        total_count = query.count()
        
        # Apply pagination with proper ordering
        bags = query.order_by(Bag.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        # Convert to dict efficiently
        bag_data = []
        for bag in bags:
            bag_data.append({
                'id': bag.id,
                'qr_id': bag.qr_id,
                'name': bag.name,
                'type': bag.type,
                'created_at': bag.created_at.isoformat() if bag.created_at else None,
                'updated_at': bag.updated_at.isoformat() if bag.updated_at else None
            })
        
        response = make_response(jsonify({
            'success': True,
            'data': bag_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page,
                'has_next': page * per_page < total_count,
                'has_prev': page > 1
            },
            'timestamp': time.time(),
            'cached': False
        }))
        response.headers['Cache-Control'] = 'public, max-age=30'
        return response
        
    except Exception as e:
        logger.error(f"Error in get_all_parent_bags: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/bags/child/list')
@require_auth
@cached_response(timeout=30)
def get_all_child_bags():
    """Get paginated list of child bags optimized for large datasets"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        search = request.args.get('search', '').strip()
        
        # Build efficient query with proper indexing
        query = db.session.query(Bag).filter(Bag.type == BagType.CHILD.value)
        
        if search:
            query = query.filter(
                or_(
                    Bag.qr_id.ilike(f'%{search}%'),
                    Bag.name.ilike(f'%{search}%')
                )
            )
        
        # Get total count efficiently
        total_count = query.count()
        
        # Apply pagination with proper ordering
        bags = query.order_by(Bag.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        # Convert to dict efficiently
        bag_data = []
        for bag in bags:
            bag_data.append({
                'id': bag.id,
                'qr_id': bag.qr_id,
                'name': bag.name,
                'type': bag.type,
                'created_at': bag.created_at.isoformat() if bag.created_at else None,
                'updated_at': bag.updated_at.isoformat() if bag.updated_at else None
            })
        
        response = make_response(jsonify({
            'success': True,
            'data': bag_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page,
                'has_next': page * per_page < total_count,
                'has_prev': page > 1
            },
            'timestamp': time.time(),
            'cached': False
        }))
        response.headers['Cache-Control'] = 'public, max-age=30'
        return response
        
    except Exception as e:
        logger.error(f"Error in get_all_child_bags: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/bags/parent/<qr_id>/details')
@require_auth
def get_parent_bag_details(qr_id):
    """Get detailed information about a specific parent bag including its children"""
    parent_bag = Bag.query.filter_by(qr_id=qr_id, type=BagType.PARENT.value).first()
    
    if not parent_bag:
        return jsonify({
            'success': False,
            'error': 'Parent bag not found',
            'error_code': 'PARENT_BAG_NOT_FOUND'
        }), 404
    
    # Get all child bags linked to this parent
    child_bags = Bag.query.filter_by(parent_id=parent_bag.id, type=BagType.CHILD.value).all()
    
    return jsonify({
        'success': True,
        'data': {
            'parent_bag': parent_bag.to_dict(),
            'child_bags': [bag.to_dict() for bag in child_bags],
            'child_count': len(child_bags),
            'expected_child_count': parent_bag.child_count or 5
        }
    })

@app.route('/api/bags/child/<qr_id>/details')
@require_auth
def get_child_bag_details(qr_id):
    """Get detailed information about a specific child bag including its parent"""
    child_bag = Bag.query.filter_by(qr_id=qr_id, type=BagType.CHILD.value).first()
    
    if not child_bag:
        return jsonify({
            'success': False,
            'error': 'Child bag not found',
            'error_code': 'CHILD_BAG_NOT_FOUND'
        }), 404
    
    # Get parent bag information if exists
    parent_data = None
    if child_bag.parent_id:
        parent_bag = Bag.query.filter_by(id=child_bag.parent_id, type=BagType.PARENT.value).first()
        if parent_bag:
            parent_data = parent_bag.to_dict()
    
    return jsonify({
        'success': True,
        'data': {
            'child_bag': child_bag.to_dict(),
            'parent_bag': parent_data,
            'is_linked': parent_data is not None
        }
    })

# SCAN TRACKING ENDPOINTS
@app.route('/api/tracking/parent/<qr_id>/scan-history')
@require_auth
def get_parent_bag_scan_history(qr_id):
    """Get complete scan history for a parent bag"""
    parent_bag = Bag.query.filter_by(qr_id=qr_id, type=BagType.PARENT.value).first()
    
    if not parent_bag:
        return jsonify({
            'success': False,
            'error': 'Parent bag not found',
            'error_code': 'PARENT_BAG_NOT_FOUND'
        }), 404
    
    scans = Scan.query.filter_by(parent_bag_id=parent_bag.id).order_by(Scan.timestamp.desc()).all()
    
    return jsonify({
        'success': True,
        'data': {
            'parent_bag': parent_bag.to_dict(),
            'scan_history': [scan.to_dict() for scan in scans],
            'total_scans': len(scans),
            'last_scan': scans[0].to_dict() if scans else None
        }
    })

@app.route('/api/tracking/child/<qr_id>/scan-history')
@require_auth
def get_child_bag_scan_history(qr_id):
    """Get complete scan history for a child bag"""
    child_bag = Bag.query.filter_by(qr_id=qr_id, type=BagType.CHILD.value).first()
    
    if not child_bag:
        return jsonify({
            'success': False,
            'error': 'Child bag not found',
            'error_code': 'CHILD_BAG_NOT_FOUND'
        }), 404
    
    scans = Scan.query.filter_by(child_bag_id=child_bag.id).order_by(Scan.timestamp.desc()).all()
    
    return jsonify({
        'success': True,
        'data': {
            'child_bag': child_bag.to_dict(),
            'scan_history': [scan.to_dict() for scan in scans],
            'total_scans': len(scans),
            'last_scan': scans[0].to_dict() if scans else None
        }
    })

# Locations API removed - location tracking no longer supported

@app.route('/api/tracking/scans/recent')
@require_auth
def get_recent_scan_activity():
    """Get recent scan activity across the entire system with filtering options"""
    # Get query parameters for filtering
    limit = request.args.get('limit', 50, type=int)
    scan_type = request.args.get('type')  # 'parent' or 'child'
    user_id = request.args.get('user_id', type=int)
    days = request.args.get('days', type=int)
    
    # Base query
    query = Scan.query
    
    # Apply filters
    if scan_type == 'parent':
        query = query.filter(Scan.parent_bag_id.isnot(None))
    elif scan_type == 'child':
        query = query.filter(Scan.child_bag_id.isnot(None))
    
    if user_id:
        query = query.filter(Scan.user_id == user_id)
    
    if days:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(Scan.timestamp >= cutoff_date)
    
    # Get results ordered by timestamp (newest first)
    scans = query.order_by(Scan.timestamp.desc()).limit(limit).all()
    
    return jsonify({
        'success': True,
        'data': {
            'scans': [scan.to_dict() for scan in scans],
            'count': len(scans),
            'filters_applied': {
                'type': scan_type,
                'user_id': user_id,
                'days': days,
                'limit': limit
            }
        }
    })

# ANALYTICS & STATISTICS ENDPOINTS
@app.route('/api/analytics/system-overview')
@require_auth
@cached_response(timeout=120)
def get_system_analytics_overview():
    """Get comprehensive system statistics and analytics overview optimized for large datasets"""
    try:
        # Single efficient query for bag counts
        bag_stats = db.session.query(
            func.count(case((Bag.type == BagType.PARENT.value, 1))).label('parent_count'),
            func.count(case((Bag.type == BagType.CHILD.value, 1))).label('child_count'),
            func.count().label('total_bags')
        ).first()
        
        # Single efficient query for scan counts
        scan_stats = db.session.query(
            func.count(case((Scan.parent_bag_id.isnot(None), 1))).label('parent_scans'),
            func.count(case((Scan.child_bag_id.isnot(None), 1))).label('child_scans'),
            func.count().label('total_scans')
        ).first()
        
        # Total users count
        total_users = db.session.query(func.count(User.id)).scalar() or 0
        
        # Recent activity (last 7 days) - optimized
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_activity = db.session.query(
            func.count(Scan.id).label('recent_scans'),
            func.count(func.distinct(Scan.user_id)).label('active_users')
        ).filter(Scan.timestamp >= week_ago).first()
    
        response_data = {
            'success': True,
            'data': {
                'totals': {
                    'parent_bags': bag_stats.parent_count or 0,
                    'child_bags': bag_stats.child_count or 0,
                    'total_bags': bag_stats.total_bags or 0,
                    'total_scans': scan_stats.total_scans or 0,
                    'total_users': total_users
                },
                'scan_breakdown': {
                    'parent_scans': scan_stats.parent_scans or 0,
                    'child_scans': scan_stats.child_scans or 0
                },
                'recent_activity': {
                    'scans_last_7_days': recent_activity.recent_scans or 0,
                    'active_users_last_7_days': recent_activity.active_users or 0
                },
                'generated_at': datetime.utcnow().isoformat()
            },
            'timestamp': time.time(),
            'cached': False
        }
        
        response = make_response(jsonify(response_data))
        response.headers['Cache-Control'] = 'public, max-age=120'
        return response
        
    except Exception as e:
        logger.error(f"Error in get_system_analytics_overview: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

# SYSTEM MANAGEMENT ENDPOINTS
@app.route('/api/system/cache/status')
@require_auth
def get_cache_system_status():
    """Get detailed cache system performance statistics"""
    try:
        from cache_utils import get_cache_stats
        stats = get_cache_stats()
        hit_rate = stats.get('hit_rate', 0) if isinstance(stats, dict) and stats else 0
        return jsonify({
            'success': True,
            'data': {
                'cache_performance': stats or {},
                'cache_health': 'healthy' if hit_rate > 0.5 else 'needs_attention'
            }
        })
    except Exception as e:
        logger.error(f"Error in get_cache_system_status: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/system/cache/clear', methods=['POST'])
@require_auth
def clear_system_cache():
    """Clear application cache with optional prefix targeting"""
    cache_prefix = request.json.get('prefix') if request.is_json else request.args.get('prefix')
    invalidate_cache(cache_prefix)
    
    return jsonify({
        'success': True,
        'message': f"Cache {'with prefix ' + cache_prefix if cache_prefix else 'completely'} cleared",
        'cleared_scope': cache_prefix or 'all'
    })

@app.route('/api/system/health-check')
def get_system_health_status():
    """Comprehensive system health check endpoint"""
    try:
        # Test database connectivity
        db.session.execute(db.text('SELECT 1'))
        
        # Get basic system metrics
        recent_activity = Scan.query.filter(
            Scan.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {
                'database': 'connected',
                'recent_activity': f"{recent_activity} scans in last 24 hours"
            },
            'version': '2.0.0'
        }), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e),
            'checks': {
                'database': 'disconnected'
            }
        }), 503

# DEVELOPMENT & TESTING ENDPOINTS
@app.route('/api/development/seed-sample-data', methods=['POST'])
@require_auth
def create_sample_data():
    """Create sample data for development and testing"""
    try:
        # Create sample parent and child bags with relationships
        parent_bags_created = []
        child_bags_created = []
        scans_created = []
        
        for i in range(1, 4):  # Create 3 parent bags
            parent_qr = f"SAMPLE-P{100+i}"
            
            # Check if already exists
            existing_parent = Bag.query.filter_by(qr_id=parent_qr).first()
            if not existing_parent:
                parent_bag = Bag()
                parent_bag.qr_id = parent_qr
                parent_bag.name = f"Sample Parent Batch {i}"
                parent_bag.type = "parent"
                parent_bag.child_count = 5
                
                db.session.add(parent_bag)
                db.session.flush()  # Get ID without committing
                parent_bags_created.append(parent_qr)
                
                # Create 5 child bags for each parent
                for j in range(1, 6):
                    child_qr = f"SAMPLE-C{100+i}-{j}"
                    
                    existing_child = Bag.query.filter_by(qr_id=child_qr).first()
                    if not existing_child:
                        child_bag = Bag()
                        child_bag.qr_id = child_qr
                        child_bag.name = f"Sample Child Package {100+i}-{j}"
                        child_bag.type = "child"
                        child_bag.parent_id = parent_bag.id
                        
                        db.session.add(child_bag)
                        child_bags_created.append(child_qr)
                        
                        # Create scan record
                        scan = Scan()
                        scan.child_bag_id = child_bag.id
                        scan.parent_bag_id = parent_bag.id
                        scan.user_id = session.get('user_id', 1)
                        
                        db.session.add(scan)
                        scans_created.append(f"Scan for {child_qr}")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Sample data created successfully',
            'data': {
                'parent_bags_created': parent_bags_created,
                'child_bags_created': child_bags_created,
                'scans_created': len(scans_created),
                'relationships_established': len(parent_bags_created) * 5
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating sample data: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to create sample data: {str(e)}',
            'error_code': 'SAMPLE_DATA_CREATION_FAILED'
        }), 500

# =============================================================================
# LEGACY API COMPATIBILITY (Deprecated - Use new endpoints above)
# =============================================================================

# Maintain backward compatibility while encouraging migration to new endpoints
@app.route('/api/parent_bags')
@require_auth
def api_parent_bags():
    """[DEPRECATED] Use /api/bags/parent/list instead"""
    logger.warning("Deprecated endpoint /api/parent_bags used. Please migrate to /api/bags/parent/list")
    return get_all_parent_bags()

@app.route('/api/child_bags')
@require_auth
def api_child_bags():
    """[DEPRECATED] Use /api/bags/child/list instead"""
    logger.warning("Deprecated endpoint /api/child_bags used. Please migrate to /api/bags/child/list")
    return get_all_child_bags()

@app.route('/api/parent_bag/<qr_id>')
@require_auth
def api_parent_bag(qr_id):
    """[DEPRECATED] Use /api/bags/parent/<qr_id>/details instead"""
    logger.warning("Deprecated endpoint /api/parent_bag used. Please migrate to /api/bags/parent/<qr_id>/details")
    return get_parent_bag_details(qr_id)

@app.route('/api/child_bag/<qr_id>')
@require_auth
def api_child_bag(qr_id):
    """[DEPRECATED] Use /api/bags/child/<qr_id>/details instead"""
    logger.warning("Deprecated endpoint /api/child_bag used. Please migrate to /api/bags/child/<qr_id>/details")
    return get_child_bag_details(qr_id)

@app.route('/api/parent_bag/<qr_id>/scans')
@require_auth
def api_parent_bag_scans(qr_id):
    """[DEPRECATED] Use /api/tracking/parent/<qr_id>/scan-history instead"""
    logger.warning("Deprecated endpoint /api/parent_bag/<qr_id>/scans used. Please migrate to /api/tracking/parent/<qr_id>/scan-history")
    return get_parent_bag_scan_history(qr_id)

@app.route('/api/child_bag/<qr_id>/scans')
@require_auth
def api_child_bag_scans(qr_id):
    """[DEPRECATED] Use /api/tracking/child/<qr_id>/scan-history instead"""
    logger.warning("Deprecated endpoint /api/child_bag/<qr_id>/scans used. Please migrate to /api/tracking/child/<qr_id>/scan-history")
    return get_child_bag_scan_history(qr_id)

@app.route('/api/stats')
@require_auth
def api_stats():
    """[DEPRECATED] Use /api/analytics/system-overview instead"""
    logger.warning("Deprecated endpoint /api/stats used. Please migrate to /api/analytics/system-overview")
    return get_system_analytics_overview()

@app.route('/api/scans')
@require_auth
def api_scans():
    """[DEPRECATED] Use /api/tracking/scans/recent instead"""
    logger.warning("Deprecated endpoint /api/scans used. Please migrate to /api/tracking/scans/recent")
    return get_recent_scan_activity()

@app.route('/api/cache_stats')
@require_auth
def api_cache_stats():
    """[DEPRECATED] Use /api/system/cache/status instead"""
    logger.warning("Deprecated endpoint /api/cache_stats used. Please migrate to /api/system/cache/status")
    return get_cache_system_status()

@app.route('/api/clear_cache', methods=['POST'])
@require_auth
def api_clear_cache():
    """[DEPRECATED] Use /api/system/cache/clear instead"""
    logger.warning("Deprecated endpoint /api/clear_cache used. Please migrate to /api/system/cache/clear")
    return clear_system_cache()

@app.route('/api/seed_test_data', methods=['POST'])
@require_auth
def seed_test_data():
    """[DEPRECATED] Use /api/development/seed-sample-data instead"""
    logger.warning("Deprecated endpoint /api/seed_test_data used. Please migrate to /api/development/seed-sample-data")
    return create_sample_data()

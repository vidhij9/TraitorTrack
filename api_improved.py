"""
Improved API endpoints with clearer, more descriptive naming based on functionality.
This module provides a comprehensive REST API with intuitive endpoint names.
"""

import logging
from flask import jsonify, request, Blueprint, make_response
from flask_login import login_required, current_user
from app_clean import app, db
from models import User, Bag, BagType, Link, Scan
from cache_utils import cached_response, invalidate_cache
import time

logger = logging.getLogger(__name__)

# =============================================================================
# BAG MANAGEMENT API ENDPOINTS
# =============================================================================

@app.route('/api/bags/parent/list')
@login_required
@cached_response(timeout=30)
def get_all_parent_bags():
    """Get complete list of all parent bags in the system"""
    parent_bags = Bag.query.filter_by(type=BagType.PARENT.value).all()
    response = make_response(jsonify({
        'success': True,
        'data': [bag.to_dict() for bag in parent_bags],
        'count': len(parent_bags),
        'timestamp': time.time(),
        'cached': False
    }))
    response.headers['Cache-Control'] = 'public, max-age=30'
    return response

@app.route('/api/bags/child/list')
@login_required
@cached_response(timeout=30)
def get_all_child_bags():
    """Get complete list of all child bags in the system"""
    child_bags = Bag.query.filter_by(type=BagType.CHILD.value).all()
    response = make_response(jsonify({
        'success': True,
        'data': [bag.to_dict() for bag in child_bags],
        'count': len(child_bags),
        'timestamp': time.time(),
        'cached': False
    }))
    response.headers['Cache-Control'] = 'public, max-age=30'
    return response

@app.route('/api/bags/parent/<qr_id>/details')
@login_required
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
@login_required
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

# =============================================================================
# SCAN TRACKING API ENDPOINTS
# =============================================================================

@app.route('/api/tracking/parent/<qr_id>/scan-history')
@login_required
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
@login_required
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

@app.route('/api/tracking/scans/recent')
@login_required
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
        from datetime import datetime, timedelta
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

# =============================================================================
# ANALYTICS & STATISTICS API ENDPOINTS
# =============================================================================

@app.route('/api/analytics/system-overview')
@login_required
def get_system_analytics_overview():
    """Get comprehensive system statistics and analytics overview"""
    from datetime import datetime, timedelta
    
    # Basic counts
    total_parent_bags = Bag.query.filter_by(type=BagType.PARENT.value).count()
    total_child_bags = Bag.query.filter_by(type=BagType.CHILD.value).count()
    total_scans = Scan.query.count()
    total_users = User.query.count()
    
    # Scan activity breakdown
    parent_scans = Scan.query.filter(Scan.parent_bag_id.isnot(None)).count()
    child_scans = Scan.query.filter(Scan.child_bag_id.isnot(None)).count()
    
    # Recent activity (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_scans = Scan.query.filter(Scan.timestamp >= week_ago).count()
    
    # Active users (users who scanned in last 7 days)
    active_users = db.session.query(Scan.user_id).filter(
        Scan.timestamp >= week_ago
    ).distinct().count()
    
    return jsonify({
        'success': True,
        'data': {
            'totals': {
                'parent_bags': total_parent_bags,
                'child_bags': total_child_bags,
                'total_bags': total_parent_bags + total_child_bags,
                'total_scans': total_scans,
                'total_users': total_users
            },
            'scan_breakdown': {
                'parent_scans': parent_scans,
                'child_scans': child_scans
            },
            'recent_activity': {
                'scans_last_7_days': recent_scans,
                'active_users_last_7_days': active_users
            },
            'generated_at': datetime.utcnow().isoformat()
        }
    })

@app.route('/api/analytics/activity-trends')
@login_required
def get_activity_trends():
    """Get activity trends and patterns over time"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    days = request.args.get('days', 30, type=int)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Daily scan counts
    daily_scans = db.session.query(
        func.date(Scan.timestamp).label('date'),
        func.count(Scan.id).label('count')
    ).filter(
        Scan.timestamp >= start_date
    ).group_by(
        func.date(Scan.timestamp)
    ).order_by('date').all()
    
    # Hourly distribution (for current day patterns)
    hourly_distribution = db.session.query(
        func.extract('hour', Scan.timestamp).label('hour'),
        func.count(Scan.id).label('count')
    ).filter(
        Scan.timestamp >= start_date
    ).group_by(
        func.extract('hour', Scan.timestamp)
    ).order_by('hour').all()
    
    return jsonify({
        'success': True,
        'data': {
            'daily_activity': [
                {'date': str(day.date), 'scan_count': day.count} 
                for day in daily_scans
            ],
            'hourly_patterns': [
                {'hour': int(hour.hour), 'scan_count': hour.count} 
                for hour in hourly_distribution
            ],
            'period_analyzed': f"Last {days} days",
            'generated_at': datetime.utcnow().isoformat()
        }
    })

# =============================================================================
# SYSTEM MANAGEMENT API ENDPOINTS
# =============================================================================

@app.route('/api/system/cache/status')
@login_required
def get_cache_system_status():
    """Get detailed cache system performance statistics"""
    from cache_utils import get_cache_stats
    stats = get_cache_stats()
    return jsonify({
        'success': True,
        'data': {
            'cache_performance': stats,
            'cache_health': 'healthy' if stats.get('hit_rate', 0) > 0.5 else 'needs_attention'
        }
    })

@app.route('/api/system/cache/clear', methods=['POST'])
@login_required
def clear_system_cache():
    """Clear application cache with optional prefix targeting"""
    if not current_user.is_admin():
        return jsonify({
            'success': False,
            'error': 'Admin privileges required',
            'error_code': 'INSUFFICIENT_PRIVILEGES'
        }), 403
    
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
        from datetime import datetime, timedelta
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

# =============================================================================
# DEVELOPMENT & TESTING ENDPOINTS
# =============================================================================

@app.route('/api/development/seed-sample-data', methods=['POST'])
@login_required
def create_sample_data():
    """Create sample data for development and testing - Admin only"""
    if not current_user.is_admin():
        return jsonify({
            'success': False,
            'error': 'Admin privileges required for data seeding',
            'error_code': 'INSUFFICIENT_PRIVILEGES'
        }), 403
    
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
                        scan.user_id = current_user.id
                        
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
@login_required
def api_parent_bags():
    """[DEPRECATED] Use /api/bags/parent/list instead"""
    logger.warning("Deprecated endpoint /api/parent_bags used. Please migrate to /api/bags/parent/list")
    return get_all_parent_bags()

@app.route('/api/child_bags')
@login_required
def api_child_bags():
    """[DEPRECATED] Use /api/bags/child/list instead"""
    logger.warning("Deprecated endpoint /api/child_bags used. Please migrate to /api/bags/child/list")
    return get_all_child_bags()

@app.route('/api/stats')
@login_required
def api_stats():
    """[DEPRECATED] Use /api/analytics/system-overview instead"""
    logger.warning("Deprecated endpoint /api/stats used. Please migrate to /api/analytics/system-overview")
    return get_system_analytics_overview()

@app.route('/api/scans')
@login_required
def api_scans():
    """[DEPRECATED] Use /api/tracking/scans/recent instead"""
    logger.warning("Deprecated endpoint /api/scans used. Please migrate to /api/tracking/scans/recent")
    return get_recent_scan_activity()
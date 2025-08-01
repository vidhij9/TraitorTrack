"""
Optimized API endpoints - clean, fast, and consolidated
Replaces the original api.py with better performance and fewer dependencies
"""
import logging
import time
from datetime import datetime, timedelta
from flask import jsonify, request, make_response
from sqlalchemy import func, or_, desc
from app_clean import app, db, limiter
from models import User, Bag, BagType, Link, Scan, Bill, BillBag
from auth_utils import require_auth, current_user
from cache_manager import cached_response, invalidate_cache
from query_optimizer import query_optimizer

logger = logging.getLogger(__name__)

# =============================================================================
# OPTIMIZED BAG MANAGEMENT ENDPOINTS
# =============================================================================

@app.route('/api/bags/parent/list')
@require_auth
@limiter.limit("30 per minute")
@cached_response(timeout=30)
def get_all_parent_bags():
    """Optimized parent bags listing with pagination and search"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        search = request.args.get('search', '').strip()
        
        # Use optimized query
        pagination = query_optimizer.get_parent_bags_paginated(
            page=page, per_page=per_page, search=search
        )
        
        bag_data = []
        for bag in pagination.items:
            bag_data.append({
                'id': bag.id,
                'qr_id': bag.qr_id,
                'name': bag.name,
                'type': bag.type,
                'dispatch_area': bag.dispatch_area,
                'created_at': bag.created_at.isoformat() if bag.created_at else None,
                'updated_at': bag.updated_at.isoformat() if bag.updated_at else None
            })
        
        response = make_response(jsonify({
            'success': True,
            'data': bag_data,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            },
            'timestamp': time.time(),
            'cached': False
        }))
        response.headers['Cache-Control'] = 'public, max-age=30'
        return response
        
    except Exception as e:
        logger.error(f"Error in get_all_parent_bags: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load parent bags'}), 500

@app.route('/api/bags/<int:bag_id>/children')
@require_auth
@limiter.limit("60 per minute")
@cached_response(timeout=60)
def get_bag_children(bag_id):
    """Get all child bags for a specific parent bag"""
    try:
        # Use optimized query
        children = query_optimizer.get_child_bags_for_parent(bag_id)
        
        children_data = []
        for child in children:
            children_data.append({
                'id': child.id,
                'qr_id': child.qr_id,
                'name': child.name,
                'created_at': child.created_at.isoformat() if child.created_at else None
            })
        
        return jsonify({
            'success': True,
            'children': children_data,
            'count': len(children_data),
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error getting bag children: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load children'}), 500

# =============================================================================
# OPTIMIZED DASHBOARD AND STATS ENDPOINTS  
# =============================================================================

@app.route('/api/dashboard/stats')
@require_auth
@limiter.limit("20 per minute")
@cached_response(timeout=120)
def get_dashboard_statistics():
    """Single optimized endpoint for all dashboard data"""
    try:
        # Get comprehensive stats in one query
        stats = query_optimizer.get_dashboard_stats()
        
        # Get recent activity
        recent_scans = query_optimizer.get_recent_scans(limit=10)
        recent_activity = []
        
        for scan in recent_scans:
            activity_data = {
                'timestamp': scan.timestamp.isoformat(),
                'user': scan.scanned_by.username if scan.scanned_by else 'Unknown',
                'scan_type': 'parent' if scan.parent_bag_id else 'child'
            }
            
            if scan.parent_bag_id and scan.parent_bag:
                activity_data['qr_id'] = scan.parent_bag.qr_id
            elif scan.child_bag_id and scan.child_bag:
                activity_data['qr_id'] = scan.child_bag.qr_id
            else:
                activity_data['qr_id'] = 'Unknown'
                
            recent_activity.append(activity_data)
        
        response_data = {
            'success': True,
            'stats': stats,
            'recent_activity': recent_activity,
            'user_context': {
                'role': current_user.role,
                'dispatch_area': current_user.dispatch_area,
                'permissions': {
                    'can_edit_bills': current_user.can_edit_bills(),
                    'can_manage_users': current_user.can_manage_users(),
                    'is_admin': current_user.is_admin()
                }
            },
            'timestamp': time.time()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Dashboard stats error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load dashboard'}), 500

@app.route('/api/scans/recent')
@require_auth
@limiter.limit("30 per minute")
@cached_response(timeout=60)
def get_recent_scans():
    """Get recent scans with filtering options"""
    try:
        limit = min(request.args.get('limit', 20, type=int), 100)
        user_id = request.args.get('user_id', type=int)
        scan_type = request.args.get('type', '').lower()
        
        # Use optimized query
        scans = query_optimizer.get_recent_scans(limit=limit, user_id=user_id)
        
        scans_data = []
        for scan in scans:
            scan_data = {
                'id': scan.id,
                'timestamp': scan.timestamp.isoformat(),
                'user': scan.scanned_by.username if scan.scanned_by else 'Unknown',
                'type': 'parent' if scan.parent_bag_id else 'child'
            }
            
            if scan.parent_bag_id and scan.parent_bag:
                scan_data['bag_qr'] = scan.parent_bag.qr_id
                scan_data['bag_name'] = scan.parent_bag.name
            elif scan.child_bag_id and scan.child_bag:
                scan_data['bag_qr'] = scan.child_bag.qr_id
                scan_data['bag_name'] = scan.child_bag.name
            
            # Filter by type if specified
            if not scan_type or scan_data['type'] == scan_type:
                scans_data.append(scan_data)
        
        return jsonify({
            'success': True,
            'scans': scans_data,
            'count': len(scans_data),
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Recent scans error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load scans'}), 500

# =============================================================================
# OPTIMIZED SEARCH AND LOOKUP ENDPOINTS
# =============================================================================

@app.route('/api/search')
@require_auth
@limiter.limit("60 per minute")
def search_unified():
    """Unified search endpoint for all entities"""
    try:
        query_text = request.args.get('q', '').strip()
        entity_type = request.args.get('type', 'all').lower()
        limit = min(request.args.get('limit', 20, type=int), 50)
        
        if not query_text:
            return jsonify({'success': False, 'error': 'Search query required'}), 400
        
        results = {
            'bags': [],
            'bills': [],
            'users': []
        }
        
        # Search bags
        if entity_type in ['all', 'bags', 'bag']:
            bags = Bag.query.filter(
                or_(
                    Bag.qr_id.ilike(f'%{query_text}%'),
                    Bag.name.ilike(f'%{query_text}%')
                )
            ).limit(limit).all()
            
            for bag in bags:
                results['bags'].append({
                    'id': bag.id,
                    'qr_id': bag.qr_id,
                    'name': bag.name,
                    'type': bag.type,
                    'dispatch_area': bag.dispatch_area
                })
        
        # Search bills  
        if entity_type in ['all', 'bills', 'bill']:
            bills = Bill.query.filter(
                or_(
                    Bill.bill_id.ilike(f'%{query_text}%'),
                    Bill.description.ilike(f'%{query_text}%')
                )
            ).limit(limit).all()
            
            for bill in bills:
                results['bills'].append({
                    'id': bill.id,
                    'bill_id': bill.bill_id,
                    'description': bill.description,
                    'status': bill.status
                })
        
        # Search users (admin only)
        if current_user.is_admin() and entity_type in ['all', 'users', 'user']:
            users = User.query.filter(
                or_(
                    User.username.ilike(f'%{query_text}%'),
                    User.email.ilike(f'%{query_text}%')
                )
            ).limit(limit).all()
            
            for user in users:
                results['users'].append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role
                })
        
        return jsonify({
            'success': True,
            'query': query_text,
            'results': results,
            'total_found': sum(len(v) for v in results.values()),
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({'success': False, 'error': 'Search failed'}), 500

# =============================================================================
# CACHE MANAGEMENT ENDPOINTS
# =============================================================================

@app.route('/api/cache/clear', methods=['POST'])
@require_auth
@limiter.limit("5 per minute")
def clear_api_cache():
    """Clear API cache (admin only)"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    try:
        pattern = request.json.get('pattern') if request.json else None
        invalidate_cache(pattern)
        
        return jsonify({
            'success': True,
            'message': f'Cache cleared{" for pattern: " + pattern if pattern else " completely"}',
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Cache clear error: {str(e)}")
        return jsonify({'success': False, 'error': 'Cache clear failed'}), 500

@app.route('/api/system/health')
@require_auth
@limiter.limit("10 per minute")
def system_health():
    """System health check endpoint"""
    try:
        # Database connectivity test
        db_healthy = True
        try:
            db.session.execute('SELECT 1')
        except Exception:
            db_healthy = False
        
        # Cache statistics
        from cache_manager import cache_stats
        cache_info = cache_stats()
        
        return jsonify({
            'success': True,
            'health': {
                'database': 'healthy' if db_healthy else 'unhealthy',
                'cache': cache_info,
                'timestamp': time.time()
            }
        })
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({'success': False, 'error': 'Health check failed'}), 500
"""
Optimized API endpoints for high performance
This module provides optimized versions of the slowest API endpoints
"""
import logging
import time
from datetime import datetime, timedelta
from flask import jsonify, request, make_response
from sqlalchemy import func, or_, desc, and_, text
from sqlalchemy.orm import joinedload, selectinload, noload
from app_clean import app, db, limiter
from models import User, Bag, BagType, Link, Scan, Bill, BillBag
from auth_utils import require_auth, current_user
from optimized_cache import cached, invalidate_cache
from query_optimizer import query_optimizer

logger = logging.getLogger(__name__)

# ============================================================================
# OPTIMIZED STATS ENDPOINT
# ============================================================================

@app.route('/api/v2/stats')
@require_auth
@limiter.limit("30 per minute")
@cached(ttl=60, prefix='stats_v2')
def api_stats_v2():
    """Highly optimized stats endpoint using single query"""
    try:
        # Use a single optimized query to get all stats
        stats_query = text("""
            SELECT 
                COUNT(DISTINCT CASE WHEN type = 'parent' THEN id END) as parent_count,
                COUNT(DISTINCT CASE WHEN type = 'child' THEN id END) as child_count,
                COUNT(DISTINCT id) as total_bags,
                (SELECT COUNT(*) FROM scan) as total_scans,
                (SELECT COUNT(*) FROM bill) as total_bills,
                (SELECT COUNT(*) FROM scan WHERE DATE(timestamp) = CURRENT_DATE) as scans_today,
                (SELECT COUNT(*) FROM bag WHERE DATE(created_at) = CURRENT_DATE) as bags_created_today
            FROM bag
        """)
        
        result = db.session.execute(stats_query).fetchone()
        
        stats = {
            'total_parent_bags': result.parent_count or 0,
            'total_child_bags': result.child_count or 0,
            'total_bags': result.total_bags or 0,
            'total_scans': result.total_scans or 0,
            'total_bills': result.total_bills or 0,
            'scans_today': result.scans_today or 0,
            'bags_created_today': result.bags_created_today or 0,
            'total_products': result.total_bags or 0,
            'status_counts': {
                'active': result.total_bags or 0,
                'scanned': result.total_scans or 0
            }
        }
        
        response = make_response(jsonify({
            'success': True,
            'statistics': stats,
            'cached': False,
            'timestamp': time.time()
        }))
        response.headers['Cache-Control'] = 'public, max-age=60'
        return response
        
    except Exception as e:
        logger.error(f"Stats V2 error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load statistics'}), 500

# ============================================================================
# OPTIMIZED SCANS ENDPOINT
# ============================================================================

@app.route('/api/scans')
@require_auth
@limiter.limit("60 per minute")
@cached(ttl=30, prefix='scans')
def api_scans_optimized():
    """Optimized scans endpoint with eager loading"""
    try:
        limit = min(request.args.get('limit', 10, type=int), 100)
        offset = request.args.get('offset', 0, type=int)
        
        # Use optimized query with eager loading
        scans = db.session.query(Scan).options(
            joinedload(Scan.scanned_by),
            joinedload(Scan.parent_bag).noload('*'),
            joinedload(Scan.child_bag).noload('*')
        ).order_by(desc(Scan.timestamp))\
         .limit(limit)\
         .offset(offset)\
         .all()
        
        scans_data = []
        for scan in scans:
            scan_data = {
                'id': scan.id,
                'timestamp': scan.timestamp.isoformat() if scan.timestamp else None,
                'user': scan.scanned_by.username if scan.scanned_by else 'Unknown',
                'type': 'parent' if scan.parent_bag_id else 'child'
            }
            
            if scan.parent_bag_id and scan.parent_bag:
                scan_data['bag_qr'] = scan.parent_bag.qr_id
                scan_data['bag_name'] = scan.parent_bag.name
            elif scan.child_bag_id and scan.child_bag:
                scan_data['bag_qr'] = scan.child_bag.qr_id
                scan_data['bag_name'] = scan.child_bag.name
            else:
                scan_data['bag_qr'] = 'Unknown'
                scan_data['bag_name'] = 'Unknown'
            
            scans_data.append(scan_data)
        
        response = make_response(jsonify({
            'success': True,
            'scans': scans_data,
            'count': len(scans_data),
            'limit': limit,
            'offset': offset,
            'timestamp': time.time()
        }))
        response.headers['Cache-Control'] = 'public, max-age=30'
        return response
        
    except Exception as e:
        logger.error(f"Scans error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load scans'}), 500

# ============================================================================
# OPTIMIZED BAGS LISTING
# ============================================================================

@app.route('/api/bags/fast')
@require_auth
@limiter.limit("60 per minute")
def api_bags_fast():
    """Ultra-fast bags listing with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        bag_type = request.args.get('type', 'all')
        search = request.args.get('search', '').strip()
        
        # Build optimized query
        query = db.session.query(Bag)
        
        # Apply filters
        if bag_type == 'parent':
            query = query.filter(Bag.type == BagType.PARENT.value)
        elif bag_type == 'child':
            query = query.filter(Bag.type == BagType.CHILD.value)
        
        if search:
            query = query.filter(
                or_(
                    Bag.qr_id.ilike(f'%{search}%'),
                    Bag.name.ilike(f'%{search}%')
                )
            )
        
        # Area filtering for dispatchers
        if current_user.is_dispatcher() and current_user.dispatch_area:
            query = query.filter(Bag.dispatch_area == current_user.dispatch_area)
        
        # Get paginated results with count in single query
        total = query.count()
        bags = query.order_by(desc(Bag.created_at))\
                   .limit(per_page)\
                   .offset((page - 1) * per_page)\
                   .all()
        
        bags_data = []
        for bag in bags:
            bags_data.append({
                'id': bag.id,
                'qr_id': bag.qr_id,
                'name': bag.name,
                'type': bag.type,
                'dispatch_area': bag.dispatch_area,
                'created_at': bag.created_at.isoformat() if bag.created_at else None
            })
        
        return jsonify({
            'success': True,
            'bags': bags_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page,
                'has_next': page * per_page < total,
                'has_prev': page > 1
            },
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Fast bags error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load bags'}), 500

# ============================================================================
# OPTIMIZED BILLS LISTING
# ============================================================================

@app.route('/api/bills/fast')
@require_auth
@limiter.limit("60 per minute")
@cached(ttl=30, prefix='bills')
def api_bills_fast():
    """Optimized bills endpoint with efficient queries"""
    try:
        # Use raw SQL for maximum performance
        bills_query = text("""
            SELECT 
                b.id,
                b.bill_id,
                b.description,
                b.status,
                b.parent_bag_count,
                b.created_at,
                COUNT(DISTINCT bb.bag_id) as actual_bag_count
            FROM bill b
            LEFT JOIN billbag bb ON b.id = bb.bill_id
            GROUP BY b.id
            ORDER BY b.created_at DESC
            LIMIT 100
        """)
        
        result = db.session.execute(bills_query)
        bills_data = []
        
        for row in result:
            bills_data.append({
                'id': row.id,
                'bill_id': row.bill_id,
                'description': row.description,
                'status': row.status,
                'parent_bag_count': row.actual_bag_count,
                'created_at': row.created_at.isoformat() if row.created_at else None
            })
        
        return jsonify({
            'success': True,
            'bills': bills_data,
            'count': len(bills_data),
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Fast bills error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load bills'}), 500

# ============================================================================
# BATCH OPERATIONS
# ============================================================================

@app.route('/api/batch/create_bags', methods=['POST'])
@require_auth
@limiter.limit("10 per minute")
def batch_create_bags():
    """Optimized batch bag creation"""
    try:
        data = request.get_json()
        bags_data = data.get('bags', [])
        
        if not bags_data or len(bags_data) > 100:
            return jsonify({'success': False, 'error': 'Invalid batch size (1-100)'}), 400
        
        created_bags = []
        
        # Use bulk insert for efficiency
        for bag_data in bags_data:
            bag = Bag(
                qr_id=bag_data.get('qr_id'),
                name=bag_data.get('name'),
                type=bag_data.get('type', BagType.PARENT.value),
                dispatch_area=bag_data.get('dispatch_area')
            )
            created_bags.append(bag)
        
        db.session.bulk_save_objects(created_bags, return_defaults=True)
        db.session.commit()
        
        # Invalidate relevant caches
        invalidate_cache('bags')
        invalidate_cache('stats')
        
        return jsonify({
            'success': True,
            'created': len(created_bags),
            'message': f'Successfully created {len(created_bags)} bags'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Batch create error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================================
# DASHBOARD OPTIMIZATION
# ============================================================================

@app.route('/api/dashboard/fast')
@require_auth
@limiter.limit("30 per minute")
@cached(ttl=60, prefix='dashboard')
def dashboard_fast():
    """Single endpoint for all dashboard data - optimized"""
    try:
        # Get all dashboard data in parallel queries
        dashboard_query = text("""
            WITH stats AS (
                SELECT 
                    COUNT(DISTINCT CASE WHEN type = 'parent' THEN id END) as parent_count,
                    COUNT(DISTINCT CASE WHEN type = 'child' THEN id END) as child_count,
                    COUNT(*) as total_bags
                FROM bag
            ),
            scan_stats AS (
                SELECT 
                    COUNT(*) as total_scans,
                    COUNT(CASE WHEN DATE(timestamp) = CURRENT_DATE THEN 1 END) as scans_today,
                    COUNT(CASE WHEN timestamp > NOW() - INTERVAL '7 days' THEN 1 END) as scans_week
                FROM scan
            ),
            recent_scans AS (
                SELECT 
                    s.id,
                    s.timestamp,
                    u.username,
                    COALESCE(pb.qr_id, cb.qr_id) as bag_qr,
                    CASE WHEN s.parent_bag_id IS NOT NULL THEN 'parent' ELSE 'child' END as scan_type
                FROM scan s
                LEFT JOIN "user" u ON s.user_id = u.id
                LEFT JOIN bag pb ON s.parent_bag_id = pb.id
                LEFT JOIN bag cb ON s.child_bag_id = cb.id
                ORDER BY s.timestamp DESC
                LIMIT 10
            )
            SELECT 
                stats.*,
                scan_stats.*,
                json_agg(json_build_object(
                    'id', rs.id,
                    'timestamp', rs.timestamp,
                    'username', rs.username,
                    'bag_qr', rs.bag_qr,
                    'scan_type', rs.scan_type
                )) as recent_scans
            FROM stats, scan_stats, recent_scans rs
            GROUP BY stats.parent_count, stats.child_count, stats.total_bags,
                     scan_stats.total_scans, scan_stats.scans_today, scan_stats.scans_week
        """)
        
        result = db.session.execute(dashboard_query).fetchone()
        
        # Ensure all properties exist before accessing them
        parent_count = getattr(result, 'parent_count', 0) or 0
        child_count = getattr(result, 'child_count', 0) or 0
        total_bags = getattr(result, 'total_bags', 0) or 0
        total_scans = getattr(result, 'total_scans', 0) or 0
        scans_today = getattr(result, 'scans_today', 0) or 0
        scans_week = getattr(result, 'scans_week', 0) or 0
        recent_scans = getattr(result, 'recent_scans', []) or []
        
        dashboard_data = {
            'statistics': {
                'parent_bags': parent_count,
                'child_bags': child_count, 
                'total_bags': total_bags,
                'total_scans': total_scans,
                'scans_today': scans_today,
                'scans_week': scans_week
            },
            'recent_activity': recent_scans,
            'user_context': {
                'username': current_user.username,
                'role': current_user.role,
                'dispatch_area': current_user.dispatch_area
            },
            'timestamp': time.time()
        }
        
        response = make_response(jsonify({
            'success': True,
            'data': dashboard_data
        }))
        response.headers['Cache-Control'] = 'public, max-age=60'
        return response
        
    except Exception as e:
        logger.error(f"Dashboard fast error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load dashboard'}), 500
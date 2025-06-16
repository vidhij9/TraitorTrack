"""
Optimized bag management API endpoints designed for handling large datasets (lakhs of bags).
These endpoints use efficient database queries with proper indexing and pagination.
"""

import logging
from flask import jsonify, request, make_response
from sqlalchemy import func, and_, or_, case, select
from sqlalchemy.orm import selectinload, joinedload
from app_clean import app, db
from models import User, Bag, BagType, Link, Scan, Bill, BillBag
from cache_utils import cached_response, invalidate_cache
from production_auth_fix import require_production_auth
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# =============================================================================
# OPTIMIZED BAG MANAGEMENT API ENDPOINTS
# =============================================================================

@app.route('/api/bags/parent/list/optimized')
@require_production_auth
@cached_response(timeout=60)
def get_parent_bags_optimized():
    """Get paginated list of parent bags with optimized queries"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)  # Max 100 per page
        search = request.args.get('search', '').strip()
        
        # Build base query with proper indexing
        query = db.session.query(Bag).filter(Bag.type == BagType.PARENT.value)
        
        # Add search filter if provided
        if search:
            query = query.filter(
                or_(
                    Bag.qr_id.ilike(f'%{search}%'),
                    Bag.name.ilike(f'%{search}%')
                )
            )
        
        # Get total count efficiently
        total_count = query.count()
        
        # Apply pagination and ordering
        bags = query.order_by(Bag.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        # Get child counts efficiently in a single query
        bag_ids = [bag.id for bag in bags]
        child_counts = {}
        if bag_ids:
            child_count_query = db.session.query(
                Link.parent_bag_id,
                func.count(Link.child_bag_id).label('child_count')
            ).filter(Link.parent_bag_id.in_(bag_ids)).group_by(Link.parent_bag_id).all()
            
            child_counts = {parent_id: count for parent_id, count in child_count_query}
        
        # Prepare response data
        bag_data = []
        for bag in bags:
            bag_dict = {
                'id': bag.id,
                'qr_id': bag.qr_id,
                'name': bag.name,
                'type': bag.type,
                'child_count': child_counts.get(bag.id, 0),
                'created_at': bag.created_at.isoformat() if bag.created_at else None,
                'updated_at': bag.updated_at.isoformat() if bag.updated_at else None
            }
            bag_data.append(bag_dict)
        
        response_data = {
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
        }
        
        response = make_response(jsonify(response_data))
        response.headers['Cache-Control'] = 'public, max-age=60'
        return response
        
    except Exception as e:
        logger.error(f"Error in get_parent_bags_optimized: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/bags/child/list/optimized')
@require_production_auth
@cached_response(timeout=60)
def get_child_bags_optimized():
    """Get paginated list of child bags with parent information"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        search = request.args.get('search', '').strip()
        
        # Build optimized query with joins
        query = db.session.query(Bag).filter(Bag.type == BagType.CHILD.value)
        
        if search:
            query = query.filter(
                or_(
                    Bag.qr_id.ilike(f'%{search}%'),
                    Bag.name.ilike(f'%{search}%')
                )
            )
        
        total_count = query.count()
        
        # Get child bags with pagination
        child_bags = query.order_by(Bag.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        # Get parent information efficiently
        child_bag_ids = [bag.id for bag in child_bags]
        parent_info = {}
        if child_bag_ids:
            parent_query = db.session.query(
                Link.child_bag_id,
                Bag.qr_id.label('parent_qr_id'),
                Bag.name.label('parent_name')
            ).join(Bag, Link.parent_bag_id == Bag.id).filter(
                Link.child_bag_id.in_(child_bag_ids)
            ).all()
            
            parent_info = {
                child_id: {'qr_id': parent_qr_id, 'name': parent_name}
                for child_id, parent_qr_id, parent_name in parent_query
            }
        
        # Prepare response data
        bag_data = []
        for bag in child_bags:
            parent = parent_info.get(bag.id, {})
            bag_dict = {
                'id': bag.id,
                'qr_id': bag.qr_id,
                'name': bag.name,
                'type': bag.type,
                'parent_qr_id': parent.get('qr_id'),
                'parent_name': parent.get('name'),
                'created_at': bag.created_at.isoformat() if bag.created_at else None,
                'updated_at': bag.updated_at.isoformat() if bag.updated_at else None
            }
            bag_data.append(bag_dict)
        
        response_data = {
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
        }
        
        response = make_response(jsonify(response_data))
        response.headers['Cache-Control'] = 'public, max-age=60'
        return response
        
    except Exception as e:
        logger.error(f"Error in get_child_bags_optimized: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/bags/stats/optimized')
@require_production_auth
@cached_response(timeout=120)
def get_bag_stats_optimized():
    """Get bag statistics with optimized queries"""
    try:
        # Use efficient aggregate queries
        stats_query = db.session.query(
            func.count(case((Bag.type == BagType.PARENT.value, 1))).label('parent_count'),
            func.count(case((Bag.type == BagType.CHILD.value, 1))).label('child_count'),
            func.count().label('total_bags')
        ).first()
        
        # Get linked/unlinked counts efficiently
        linked_children = db.session.query(func.count(func.distinct(Link.child_bag_id))).scalar() or 0
        total_children = db.session.query(func.count(Bag.id)).filter(Bag.type == BagType.CHILD.value).scalar() or 0
        unlinked_children = total_children - linked_children
        
        # Get recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_scans = db.session.query(func.count(Scan.id)).filter(Scan.timestamp >= yesterday).scalar() or 0
        recent_bags = db.session.query(func.count(Bag.id)).filter(Bag.created_at >= yesterday).scalar() or 0
        
        response_data = {
            'success': True,
            'data': {
                'total_bags': stats_query.total_bags or 0,
                'parent_bags': stats_query.parent_count or 0,
                'child_bags': stats_query.child_count or 0,
                'linked_children': linked_children,
                'unlinked_children': unlinked_children,
                'recent_activity': {
                    'scans_24h': recent_scans,
                    'bags_created_24h': recent_bags
                }
            },
            'timestamp': time.time(),
            'cached': False
        }
        
        response = make_response(jsonify(response_data))
        response.headers['Cache-Control'] = 'public, max-age=120'
        return response
        
    except Exception as e:
        logger.error(f"Error in get_bag_stats_optimized: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/bags/search/optimized')
@require_production_auth
@cached_response(timeout=30)
def search_bags_optimized():
    """Fast search across all bags with proper indexing"""
    try:
        query_text = request.args.get('q', '').strip()
        bag_type = request.args.get('type', 'all')  # all, parent, child
        limit = min(request.args.get('limit', 20, type=int), 50)
        
        if not query_text:
            return jsonify({'success': False, 'error': 'Search query is required'}), 400
        
        # Build optimized search query
        search_filter = or_(
            Bag.qr_id.ilike(f'%{query_text}%'),
            Bag.name.ilike(f'%{query_text}%')
        )
        
        query = db.session.query(Bag).filter(search_filter)
        
        if bag_type != 'all':
            query = query.filter(Bag.type == bag_type)
        
        # Get results with limit
        bags = query.order_by(Bag.created_at.desc()).limit(limit).all()
        
        # Prepare response data
        bag_data = []
        for bag in bags:
            bag_dict = {
                'id': bag.id,
                'qr_id': bag.qr_id,
                'name': bag.name,
                'type': bag.type,
                'created_at': bag.created_at.isoformat() if bag.created_at else None
            }
            bag_data.append(bag_dict)
        
        response_data = {
            'success': True,
            'data': bag_data,
            'query': query_text,
            'type_filter': bag_type,
            'count': len(bag_data),
            'timestamp': time.time(),
            'cached': False
        }
        
        response = make_response(jsonify(response_data))
        response.headers['Cache-Control'] = 'public, max-age=30'
        return response
        
    except Exception as e:
        logger.error(f"Error in search_bags_optimized: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/bags/<qr_id>/details/optimized')
@require_production_auth
@cached_response(timeout=300)
def get_bag_details_optimized(qr_id):
    """Get detailed bag information with optimized queries"""
    try:
        # Find the bag efficiently using indexed qr_id
        bag = db.session.query(Bag).filter(Bag.qr_id == qr_id).first()
        if not bag:
            return jsonify({'success': False, 'error': 'Bag not found'}), 404
        
        bag_data = {
            'id': bag.id,
            'qr_id': bag.qr_id,
            'name': bag.name,
            'type': bag.type,
            'created_at': bag.created_at.isoformat() if bag.created_at else None,
            'updated_at': bag.updated_at.isoformat() if bag.updated_at else None
        }
        
        # Add type-specific information
        if bag.type == BagType.PARENT.value:
            # Get child bags efficiently
            children_query = db.session.query(Bag).join(Link, Link.child_bag_id == Bag.id).filter(
                Link.parent_bag_id == bag.id
            ).all()
            
            bag_data['children'] = [
                {
                    'id': child.id,
                    'qr_id': child.qr_id,
                    'name': child.name,
                    'created_at': child.created_at.isoformat() if child.created_at else None
                }
                for child in children_query
            ]
            bag_data['child_count'] = len(children_query)
            
        elif bag.type == BagType.CHILD.value:
            # Get parent information efficiently
            parent_query = db.session.query(Bag).join(Link, Link.parent_bag_id == Bag.id).filter(
                Link.child_bag_id == bag.id
            ).first()
            
            if parent_query:
                bag_data['parent'] = {
                    'id': parent_query.id,
                    'qr_id': parent_query.qr_id,
                    'name': parent_query.name,
                    'created_at': parent_query.created_at.isoformat() if parent_query.created_at else None
                }
        
        # Get recent scan count efficiently
        recent_scans = db.session.query(func.count(Scan.id)).filter(
            or_(Scan.parent_bag_id == bag.id, Scan.child_bag_id == bag.id)
        ).scalar() or 0
        
        bag_data['scan_count'] = recent_scans
        
        response_data = {
            'success': True,
            'data': bag_data,
            'timestamp': time.time(),
            'cached': False
        }
        
        response = make_response(jsonify(response_data))
        response.headers['Cache-Control'] = 'public, max-age=300'
        return response
        
    except Exception as e:
        logger.error(f"Error in get_bag_details_optimized: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

# =============================================================================
# BULK OPERATIONS FOR LARGE DATASETS
# =============================================================================

@app.route('/api/bags/bulk/validate')
@require_production_auth
def validate_bulk_bags():
    """Validate multiple bag QR codes efficiently"""
    try:
        qr_codes = request.json.get('qr_codes', [])
        if not qr_codes or len(qr_codes) > 100:  # Limit to 100 for performance
            return jsonify({'success': False, 'error': 'Invalid QR codes list (max 100)'}), 400
        
        # Single query to check all QR codes
        existing_bags = db.session.query(Bag.qr_id, Bag.type).filter(
            Bag.qr_id.in_(qr_codes)
        ).all()
        
        existing_dict = {qr_id: bag_type for qr_id, bag_type in existing_bags}
        
        results = []
        for qr_code in qr_codes:
            result = {
                'qr_code': qr_code,
                'exists': qr_code in existing_dict,
                'type': existing_dict.get(qr_code)
            }
            results.append(result)
        
        response_data = {
            'success': True,
            'data': results,
            'timestamp': time.time()
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in validate_bulk_bags: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
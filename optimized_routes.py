"""
Optimized routes - consolidated and performance-focused
Replaces multiple scattered route functions with optimized versions
"""
from flask import jsonify, request
from auth_utils import current_user, require_auth
from query_optimizer import query_optimizer
from app_clean import app, limiter
import logging

logger = logging.getLogger(__name__)

@app.route('/api/dashboard/stats')
@require_auth
@limiter.limit("30 per minute")
def optimized_dashboard_stats():
    """Single optimized endpoint for all dashboard statistics"""
    try:
        # Get all stats in one optimized query
        stats = query_optimizer.get_dashboard_stats()
        
        # Get recent activity efficiently
        recent_scans = query_optimizer.get_recent_scans(limit=5)
        recent_activity = []
        
        for scan in recent_scans:
            activity = {
                'timestamp': scan.timestamp.isoformat(),
                'user': scan.scanned_by.username if scan.scanned_by else 'Unknown',
                'type': 'parent' if scan.parent_bag_id else 'child',
                'qr_id': (scan.parent_bag.qr_id if scan.parent_bag_id else 
                         scan.child_bag.qr_id if scan.child_bag_id else 'Unknown')
            }
            recent_activity.append(activity)
        
        return jsonify({
            'success': True,
            'stats': stats,
            'recent_activity': recent_activity,
            'user_info': {
                'role': current_user.role,
                'dispatch_area': current_user.dispatch_area,
                'can_edit_bills': current_user.can_edit_bills(),
                'can_manage_users': current_user.can_manage_users()
            }
        })
        
    except Exception as e:
        logger.error(f"Dashboard stats error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to load dashboard data'}), 500

@app.route('/api/bags/search')
@require_auth 
@limiter.limit("60 per minute")
def optimized_bag_search():
    """Optimized bag search with pagination and filtering"""
    try:
        search_term = request.args.get('q', '').strip()
        bag_type = request.args.get('type', '').lower()
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        if bag_type == 'parent':
            pagination = query_optimizer.get_parent_bags_paginated(
                page=page, per_page=per_page, search=search_term
            )
        else:
            # Generic bag search for all types
            from models import Bag, BagType
            from sqlalchemy import or_
            
            query = Bag.query
            if search_term:
                query = query.filter(
                    or_(
                        Bag.qr_id.ilike(f'%{search_term}%'),
                        Bag.name.ilike(f'%{search_term}%')
                    )
                )
            if bag_type in ['parent', 'child']:
                query = query.filter_by(type=bag_type)
            
            pagination = query.order_by(Bag.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
        
        bags_data = []
        for bag in pagination.items:
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
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Bag search error: {str(e)}")
        return jsonify({'success': False, 'error': 'Search failed'}), 500

@app.route('/api/scan/bulk', methods=['POST'])
@require_auth
@limiter.limit("10 per minute")
def optimized_bulk_scan():
    """Optimized bulk scanning operation for multiple QR codes"""
    try:
        data = request.get_json()
        if not data or 'scans' not in data:
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400
        
        scans_data = data['scans'][:50]  # Limit to 50 scans per request
        parent_qr = data.get('parent_qr')
        
        if not parent_qr:
            return jsonify({'success': False, 'error': 'Parent QR required'}), 400
        
        # Get parent bag once
        parent_bag = query_optimizer.get_bag_by_qr(parent_qr, 'parent')
        if not parent_bag:
            return jsonify({'success': False, 'error': 'Parent bag not found'}), 404
        
        results = []
        success_count = 0
        
        for scan_data in scans_data:
            child_qr = scan_data.get('qr_id', '').strip()
            if not child_qr:
                continue
                
            try:
                # Check/create child bag
                existing_child = query_optimizer.get_bag_by_qr(child_qr)
                
                if existing_child and existing_child.type != 'child':
                    results.append({'qr_id': child_qr, 'success': False, 'error': 'QR exists as parent'})
                    continue
                
                if not existing_child:
                    child_bag = query_optimizer.create_bag_optimized(
                        qr_id=child_qr,
                        bag_type='child',
                        dispatch_area=parent_bag.dispatch_area
                    )
                else:
                    child_bag = existing_child
                
                # Create link
                link, created = query_optimizer.create_link_optimized(parent_bag.id, child_bag.id)
                if not created:
                    results.append({'qr_id': child_qr, 'success': False, 'error': 'Already linked'})
                    continue
                
                # Create scan record
                query_optimizer.create_scan_optimized(
                    user_id=current_user.id,
                    child_bag_id=child_bag.id
                )
                
                results.append({'qr_id': child_qr, 'success': True})
                success_count += 1
                
            except Exception as e:
                results.append({'qr_id': child_qr, 'success': False, 'error': str(e)})
        
        # Bulk commit all changes
        if query_optimizer.bulk_commit():
            return jsonify({
                'success': True,
                'processed': len(results),
                'successful': success_count,
                'failed': len(results) - success_count,
                'results': results
            })
        else:
            return jsonify({'success': False, 'error': 'Database commit failed'}), 500
            
    except Exception as e:
        logger.error(f"Bulk scan error: {str(e)}")
        return jsonify({'success': False, 'error': 'Bulk scan failed'}), 500
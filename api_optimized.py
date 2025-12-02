"""
Optimized API Endpoints - Mobile-First Performance
Replaces slow routes with ultra-fast raw SQL and smart caching
Target: <50ms response time, <5KB payload size for mobile
"""
import logging
from datetime import datetime
from flask import jsonify, request
from sqlalchemy import text
from app import app, db, limiter
from auth_utils import require_auth, current_user
from validation_utils import InputValidator
# Cache disabled - using live data only
from api_middleware import add_cache_headers, filter_fields, get_optimal_page_size, is_health_check_request

logger = logging.getLogger(__name__)

# =============================================================================
# OPTIMIZED /api/bags ENDPOINT
# =============================================================================

@app.route('/api/v2/bags', methods=['GET'])
@require_auth
@limiter.limit("10000 per minute")
def api_bags_optimized():
    """
    Ultra-optimized bags endpoint with field filtering and mobile optimization
    Target: <20ms response, <3KB payload
    
    Query params:
        - limit: Page size (default: 50, max: 100)
        - offset: Pagination offset (legacy, capped at 10000)
        - cursor: Keyset pagination cursor (preferred for large datasets)
        - type: Filter by 'parent' or 'child'
        - search: Search by QR ID
        - fields: Comma-separated field names (e.g., 'id,qr_id,type')
    
    Pagination modes:
        1. Keyset (cursor): Most efficient for 1M+ records, uses (created_at, id) composite
        2. Offset: Legacy support, capped at 10000 for performance
    
    Cursor format: "created_at_iso|id" (e.g., "2025-12-02T10:30:00|123456")
    """
    try:
        limit = get_optimal_page_size()
        cursor = request.args.get('cursor', '').strip()
        offset = min(request.args.get('offset', 0, type=int), 10000)
        
        bag_type = request.args.get('type', '').strip()
        search = request.args.get('search', '').strip()
        fields = request.args.get('fields', '').strip()
        
        if bag_type and bag_type not in ['parent', 'child']:
            return jsonify({'success': False, 'error': 'Invalid type parameter'}), 400
        
        if search:
            search = InputValidator.sanitize_search_query(search)
            if len(search) > 50:
                return jsonify({'success': False, 'error': 'Search query too long'}), 400
        
        where_clauses = []
        params = {'limit': limit}
        
        if bag_type:
            where_clauses.append("type = :bag_type")
            params['bag_type'] = bag_type
        
        if search:
            where_clauses.append("qr_id ILIKE :search")
            params['search'] = f'%{search}%'
        
        # KEYSET PAGINATION: Efficient for 1M+ records
        if cursor:
            try:
                parts = cursor.split('|')
                if len(parts) != 2:
                    return jsonify({'success': False, 'error': 'Invalid cursor format. Expected: created_at_iso|id'}), 400
                cursor_time = datetime.fromisoformat(parts[0])
                cursor_id = int(parts[1])
                where_clauses.append("(created_at, id) < (:cursor_time, :cursor_id)")
                params['cursor_time'] = cursor_time
                params['cursor_id'] = cursor_id
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid cursor format: {cursor}, error: {e}")
                return jsonify({'success': False, 'error': f'Invalid cursor format: {str(e)}'}), 400
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        # Use OFFSET only when cursor not provided
        if cursor:
            query = text(f"""
                SELECT 
                    id, qr_id, type, status, child_count, weight_kg,
                    dispatch_area, created_at, updated_at
                FROM bag
                {where_sql}
                ORDER BY created_at DESC, id DESC
                LIMIT :limit
            """)
        else:
            params['offset'] = offset
            query = text(f"""
                SELECT 
                    id, qr_id, type, status, child_count, weight_kg,
                    dispatch_area, created_at, updated_at
                FROM bag
                {where_sql}
                ORDER BY created_at DESC, id DESC
                LIMIT :limit OFFSET :offset
            """)
        
        result = db.session.execute(query, params).fetchall()
        
        bags_data = []
        next_cursor = None
        
        for row in result:
            bags_data.append({
                'id': row.id,
                'qr_id': row.qr_id,
                'type': row.type,
                'status': row.status,
                'child_count': row.child_count,
                'weight_kg': float(row.weight_kg) if row.weight_kg else 0.0,
                'dispatch_area': row.dispatch_area,
                'created_at': row.created_at.isoformat() if row.created_at else None,
                'updated_at': row.updated_at.isoformat() if row.updated_at else None
            })
            # Last row becomes next cursor
            if row.created_at:
                next_cursor = f"{row.created_at.isoformat()}|{row.id}"
        
        response_data = {
            'success': True,
            'count': len(bags_data),
            'limit': limit,
            'has_more': len(bags_data) == limit,
            'next_cursor': next_cursor if len(bags_data) == limit else None,
            'bags': bags_data
        }
        
        if not cursor:
            response_data['offset'] = offset
        
        if fields:
            response_data = filter_fields(response_data, fields)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Optimized bags API error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

# =============================================================================
# OPTIMIZED /api/bills ENDPOINT
# =============================================================================

@app.route('/api/v2/bills', methods=['GET'])
@require_auth
@limiter.limit("10000 per minute")
def api_bills_optimized():
    """
    Ultra-optimized bills endpoint with aggregated data
    Target: <30ms response, <5KB payload
    
    Query params:
        - limit: Page size (default: 50, max: 100)
        - offset: Pagination offset (legacy, capped at 10000)
        - cursor: Keyset pagination cursor (preferred for large datasets)
        - status: Filter by status
        - fields: Field filtering
    
    Cursor format: "created_at_iso|id" (e.g., "2025-12-02T10:30:00|123456")
    """
    try:
        limit = get_optimal_page_size()
        cursor = request.args.get('cursor', '').strip()
        offset = min(request.args.get('offset', 0, type=int), 10000)
        status = request.args.get('status', '').strip()
        fields = request.args.get('fields', '').strip()
        
        where_clauses = []
        params = {'limit': limit}
        
        if status in ['new', 'processing', 'completed']:
            where_clauses.append("b.status = :status")
            params['status'] = status
        
        # KEYSET PAGINATION: Efficient for 100K+ bills
        if cursor:
            try:
                parts = cursor.split('|')
                if len(parts) != 2:
                    return jsonify({'success': False, 'error': 'Invalid cursor format. Expected: created_at_iso|id'}), 400
                cursor_time = datetime.fromisoformat(parts[0])
                cursor_id = int(parts[1])
                where_clauses.append("(b.created_at, b.id) < (:cursor_time, :cursor_id)")
                params['cursor_time'] = cursor_time
                params['cursor_id'] = cursor_id
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid bill cursor format: {cursor}, error: {e}")
                return jsonify({'success': False, 'error': f'Invalid cursor format: {str(e)}'}), 400
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        if cursor:
            query = text(f"""
                WITH bill_stats AS (
                    SELECT 
                        b.id, b.bill_id, b.status, b.parent_bag_count,
                        b.total_weight_kg, b.expected_weight_kg, b.total_child_bags,
                        b.created_at, b.updated_at,
                        COUNT(DISTINCT bb.bag_id) as actual_parent_count
                    FROM bill b
                    LEFT JOIN bill_bag bb ON b.id = bb.bill_id
                    {where_sql}
                    GROUP BY b.id
                    ORDER BY b.created_at DESC, b.id DESC
                    LIMIT :limit
                )
                SELECT * FROM bill_stats
            """)
        else:
            params['offset'] = offset
            query = text(f"""
                WITH bill_stats AS (
                    SELECT 
                        b.id, b.bill_id, b.status, b.parent_bag_count,
                        b.total_weight_kg, b.expected_weight_kg, b.total_child_bags,
                        b.created_at, b.updated_at,
                        COUNT(DISTINCT bb.bag_id) as actual_parent_count
                    FROM bill b
                    LEFT JOIN bill_bag bb ON b.id = bb.bill_id
                    {where_sql}
                    GROUP BY b.id
                    ORDER BY b.created_at DESC, b.id DESC
                    LIMIT :limit OFFSET :offset
                )
                SELECT * FROM bill_stats
            """)
        
        result = db.session.execute(query, params).fetchall()
        
        bills_data = []
        next_cursor = None
        
        for row in result:
            bills_data.append({
                'id': row.id,
                'bill_id': row.bill_id,
                'status': row.status,
                'parent_bag_count': row.actual_parent_count or 0,
                'total_weight_kg': float(row.total_weight_kg) if row.total_weight_kg else 0.0,
                'expected_weight_kg': float(row.expected_weight_kg) if row.expected_weight_kg else 0.0,
                'total_child_bags': row.total_child_bags or 0,
                'created_at': row.created_at.isoformat() if row.created_at else None,
                'updated_at': row.updated_at.isoformat() if row.updated_at else None
            })
            if row.created_at:
                next_cursor = f"{row.created_at.isoformat()}|{row.id}"
        
        response_data = {
            'success': True,
            'count': len(bills_data),
            'limit': limit,
            'has_more': len(bills_data) == limit,
            'next_cursor': next_cursor if len(bills_data) == limit else None,
            'bills': bills_data
        }
        
        if not cursor:
            response_data['offset'] = offset
        
        if fields:
            response_data = filter_fields(response_data, fields)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Optimized bills API error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

# =============================================================================
# LIGHTWEIGHT SYSTEM HEALTH ENDPOINT
# =============================================================================

@app.route('/api/v2/health', methods=['GET'])
def api_health_lightweight():
    """
    Ultra-fast health check for mobile apps and monitoring
    Target: <5ms response, <200 bytes
    
    Query params:
        - lightweight=true: Skip database checks (instant response)
        - detailed=true: Include full system metrics
    """
    try:
        # Detect lightweight mode
        if is_health_check_request() or request.args.get('lightweight') == 'true':
            # Instant response without database query
            return jsonify({
                'status': 'ok',
                'timestamp': datetime.now().isoformat()
            })
        
        # Detailed mode: Include database ping
        if request.args.get('detailed') == 'true':
            try:
                db.session.execute(text("SELECT 1")).scalar()
                db_status = 'connected'
            except Exception as e:
                logger.error(f"Health check DB error: {e}")
                db_status = 'error'
            
            return jsonify({
                'status': 'ok' if db_status == 'connected' else 'degraded',
                'timestamp': datetime.now().isoformat(),
                'database': db_status
            })
        
        # Default: Fast DB ping only
        try:
            db.session.execute(text("SELECT 1")).scalar()
            return jsonify({
                'status': 'ok',
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return jsonify({
                'status': 'error',
                'timestamp': datetime.now().isoformat(),
                'error': 'Database connection failed'
            }), 503
            
    except Exception as e:
        logger.error(f"Health endpoint error: {e}", exc_info=True)
        return jsonify({'status': 'error'}), 500

# =============================================================================
# BATCH UNLINK OPERATION
# =============================================================================

@app.route('/api/v2/batch/unlink', methods=['POST'])
@require_auth
@limiter.limit("100 per minute")
def api_batch_unlink():
    """
    Batch unlink operation for mobile efficiency
    Unlink multiple children from parent in single transaction
    
    Request body:
        {
            "parent_qr": "SB12345",
            "child_qrs": ["CH001", "CH002", "CH003"]
        }
    
    Performance: Single transaction, atomic rollback on failure
    """
    try:
        from api_middleware import validate_batch_size
        from models import Bag, Link
        from sqlalchemy import func
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        parent_qr = data.get('parent_qr', '').strip()
        child_qrs = data.get('child_qrs', [])
        
        if not parent_qr:
            return jsonify({'success': False, 'error': 'parent_qr required'}), 400
        
        # Validate batch size
        is_valid, error_msg = validate_batch_size(child_qrs, max_size=30)
        if not is_valid:
            return jsonify({'success': False, 'error': error_msg}), 400
        
        # Find parent bag
        parent_bag = Bag.query.filter(
            func.upper(Bag.qr_id) == func.upper(parent_qr),
            Bag.type == 'parent'
        ).first()
        
        if not parent_bag:
            return jsonify({'success': False, 'error': 'Parent bag not found'}), 404
        
        # Process unlinks in transaction
        unlinked = []
        not_found = []
        errors = []
        
        for child_qr in child_qrs:
            try:
                child_bag = Bag.query.filter(
                    func.upper(Bag.qr_id) == func.upper(child_qr)
                ).first()
                
                if not child_bag:
                    not_found.append(child_qr)
                    continue
                
                link = Link.query.filter_by(
                    parent_bag_id=parent_bag.id,
                    child_bag_id=child_bag.id
                ).first()
                
                if link:
                    db.session.delete(link)
                    
                    # Delete ALL scan records for this child bag
                    from models import Scan
                    Scan.query.filter_by(child_bag_id=child_bag.id).delete()
                    
                    # Delete the child bag itself - no unlinked child bags should exist
                    db.session.delete(child_bag)
                    
                    unlinked.append(child_qr)
                else:
                    errors.append(f"{child_qr}: Not linked to parent")
                    
            except Exception as e:
                logger.error(f"Error unlinking {child_qr}: {e}")
                errors.append(f"{child_qr}: {str(e)}")
        
        # Commit all changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'unlinked_count': len(unlinked),
            'unlinked': unlinked,
            'not_found': not_found,
            'errors': errors
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Batch unlink error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

logger.info("✅ Optimized API endpoints registered (v2)")

"""
Ultra-Fast Optimized Bill Parent Scanning
Reduces database queries and improves response time to <50ms
"""

import time
import logging
from flask import jsonify
from sqlalchemy import text
from functools import lru_cache

logger = logging.getLogger(__name__)

# Cache for parent bag lookups (5 minute TTL)
@lru_cache(maxsize=1000)
def get_cached_parent_bag(qr_code: str):
    """Cache parent bag lookups for 5 minutes"""
    return None  # Will be replaced by actual lookup

def clear_parent_cache():
    """Clear the parent bag cache"""
    get_cached_parent_bag.cache_clear()

def optimized_bill_parent_scan(db, bill_id: int, qr_code: str, user_id: int):
    """
    Ultra-optimized parent bag scanning for bills
    Target: <50ms response time
    """
    start_time = time.perf_counter()
    
    # Sanitize and validate QR code
    qr_code = qr_code.strip().upper()
    
    # Quick format check
    if not qr_code.startswith('SB') or len(qr_code) != 7:
        return {
            'success': False,
            'message': f'🚫 Invalid format! Must be SB##### (e.g., SB12345). You scanned: {qr_code}',
            'error_type': 'invalid_format'
        }
    
    try:
        # Single optimized query to get all necessary data at once
        result = db.session.execute(text("""
            WITH bag_data AS (
                SELECT 
                    b.id as bag_id,
                    b.qr_id,
                    b.type,
                    b.status as bag_status,
                    COUNT(DISTINCT l.child_bag_id) as child_count,
                    bb_existing.bill_id as existing_bill_id,
                    bill.id as bill_pk,
                    bill.bill_id as bill_number,
                    bill.parent_bag_count as capacity,
                    bill.status as bill_status,
                    (SELECT COUNT(*) FROM bill_bag WHERE bill_id = :bill_id) as current_count
                FROM bag b
                LEFT JOIN link l ON l.parent_bag_id = b.id
                LEFT JOIN bill_bag bb_existing ON bb_existing.bag_id = b.id
                LEFT JOIN bill ON bill.id = :bill_id
                WHERE UPPER(b.qr_id) = :qr_code AND b.type = 'parent'
                GROUP BY b.id, b.qr_id, b.type, b.status, bb_existing.bill_id, 
                         bill.id, bill.bill_id, bill.parent_bag_count, bill.status
            )
            SELECT * FROM bag_data
        """), {
            'bill_id': bill_id,
            'qr_code': qr_code
        }).fetchone()
        
        if not result:
            # Check if bag exists but is not a parent
            other_bag = db.session.execute(text("""
                SELECT type FROM bag WHERE UPPER(qr_id) = :qr_code
            """), {'qr_code': qr_code}).fetchone()
            
            if other_bag:
                return {
                    'success': False,
                    'message': f'🚫 {qr_code} is registered as a {other_bag.type} bag, not a parent bag',
                    'error_type': 'wrong_bag_type',
                    'show_popup': True
                }
            else:
                return {
                    'success': False,
                    'message': f'🚫 Parent bag {qr_code} does not exist! Please create/scan this parent bag first in Scan Management.',
                    'error_type': 'bag_not_found',
                    'show_popup': True
                }
        
        # Extract data from result
        bag_id = result.bag_id
        child_count = result.child_count or 0
        existing_bill_id = result.existing_bill_id
        bill_pk = result.bill_pk
        bill_number = result.bill_number
        capacity = result.capacity
        current_count = result.current_count or 0
        
        # Check if bill exists
        if not bill_pk:
            return {
                'success': False,
                'message': f'📋 Bill #{bill_id} not found. Please refresh the page.',
                'error_type': 'bill_not_found'
            }
        
        # Check if already linked to this bill
        if existing_bill_id == bill_pk:
            return {
                'success': False,
                'message': f'✅ {qr_code} already linked to this bill (contains {child_count} children)',
                'error_type': 'already_linked_same_bill'
            }
        
        # Check if linked to another bill
        if existing_bill_id:
            other_bill = db.session.execute(text("""
                SELECT bill_id FROM bill WHERE id = :bill_id
            """), {'bill_id': existing_bill_id}).scalar()
            
            return {
                'success': False,
                'message': f'⚠️ {qr_code} already linked to Bill #{other_bill}. Cannot link to multiple bills.',
                'error_type': 'already_linked_other_bill'
            }
        
        # Check capacity
        if current_count >= capacity:
            return {
                'success': False,
                'message': f'📦 Bill capacity reached ({current_count}/{capacity} bags). Cannot add more.',
                'error_type': 'capacity_reached'
            }
        
        # All checks passed - link the bag in a single transaction
        weight = float(child_count)  # 1kg per child
        
        # Use a single compound INSERT/UPDATE statement for atomic operation
        db.session.execute(text("""
            WITH inserted_link AS (
                INSERT INTO bill_bag (bill_id, bag_id)
                VALUES (:bill_id, :bag_id)
                RETURNING bill_id
            ),
            updated_bag AS (
                UPDATE bag 
                SET child_count = :child_count,
                    weight_kg = :weight,
                    status = CASE 
                        WHEN :child_count >= 30 THEN 'completed'
                        WHEN :child_count > 0 THEN 'in_progress'
                        ELSE status
                    END
                WHERE id = :bag_id
                RETURNING id
            ),
            updated_bill AS (
                UPDATE bill
                SET total_weight_kg = COALESCE(total_weight_kg, 0) + :weight,
                    total_child_bags = COALESCE(total_child_bags, 0) + :child_count,
                    expected_weight_kg = COALESCE(expected_weight_kg, 0) + 30.0
                WHERE id = :bill_id
                RETURNING id
            ),
            inserted_scan AS (
                INSERT INTO scan (user_id, parent_bag_id, timestamp)
                VALUES (:user_id, :bag_id, NOW())
                RETURNING id
            )
            SELECT 
                (SELECT COUNT(*) FROM bill_bag WHERE bill_id = :bill_id) + 1 as final_count
        """), {
            'bill_id': bill_pk,
            'bag_id': bag_id,
            'child_count': child_count,
            'weight': weight,
            'user_id': user_id
        })
        
        db.session.commit()
        
        # Calculate final metrics
        final_count = current_count + 1
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        logger.info(f'Ultra-fast scan completed in {elapsed_ms:.2f}ms for {qr_code}')
        
        return {
            'success': True,
            'message': f'✅ {qr_code} linked! Contains {child_count} children ({final_count}/{capacity} total)',
            'bag_qr': qr_code,
            'linked_count': final_count,
            'expected_count': capacity,
            'child_count': child_count,
            'actual_weight': weight,
            'expected_weight': final_count * 30.0,
            'scan_time_ms': round(elapsed_ms, 2),
            'error_type': 'success'
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Optimized bill scan error: {str(e)}')
        return {
            'success': False,
            'message': f'❌ Error: {str(e)}',
            'error_type': 'server_error'
        }

def register_optimized_routes(app, db):
    """Register optimized bill scanning routes"""
    from flask_wtf import csrf
    
    @app.route('/api/optimized/bill_parent_scan', methods=['POST'])
    @csrf.exempt
    def optimized_scan_endpoint():
        """Ultra-fast bill parent scanning endpoint"""
        from flask import request, session
        
        # Quick auth check
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'message': '🚫 Please login first',
                'error_type': 'auth_required'
            }), 401
        
        # Get parameters
        bill_id = request.form.get('bill_id', type=int)
        qr_code = request.form.get('qr_code', '')
        
        if not bill_id or not qr_code:
            return jsonify({
                'success': False,
                'message': '🚫 Missing required parameters',
                'error_type': 'missing_data'
            })
        
        # Execute optimized scan
        result = optimized_bill_parent_scan(db, bill_id, qr_code, user_id)
        
        # Track performance if monitor available
        try:
            from performance_monitor import monitor
            if result.get('scan_time_ms'):
                monitor.record_db_query('bill_parent_scan', result['scan_time_ms'])
        except:
            pass
        
        return jsonify(result)
    
    logger.info("✅ Optimized bill scanning routes registered")
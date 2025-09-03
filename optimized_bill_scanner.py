"""
Ultra-Optimized Bill Parent Scanner
Handles 20+ concurrent users scanning 100+ bags per bill
"""
import time
import logging
from flask import jsonify, request, session
from sqlalchemy import text
from app_clean import app, db, csrf
from models import Bag, Bill, BillBag, Link, Scan, User
from datetime import datetime
import threading

logger = logging.getLogger(__name__)

# Thread-safe cache for active bills
BILL_CACHE = {}
CACHE_LOCK = threading.Lock()
CACHE_TTL = 60  # seconds

def get_cached_bill(bill_id):
    """Get bill from cache or database"""
    with CACHE_LOCK:
        if bill_id in BILL_CACHE:
            cached_time, bill_data = BILL_CACHE[bill_id]
            if time.time() - cached_time < CACHE_TTL:
                return bill_data
    
    # Load from database
    bill = Bill.query.get(bill_id)
    if bill:
        bill_data = {
            'id': bill.id,
            'bill_id': bill.bill_id,
            'parent_bag_count': bill.parent_bag_count,
            'status': bill.status
        }
        with CACHE_LOCK:
            BILL_CACHE[bill_id] = (time.time(), bill_data)
        return bill_data
    return None

def clear_bill_cache(bill_id):
    """Clear bill from cache when modified"""
    with CACHE_LOCK:
        if bill_id in BILL_CACHE:
            del BILL_CACHE[bill_id]

@app.route('/optimized/bill_parent_scan', methods=['POST'])
@csrf.exempt
def optimized_bill_parent_scan():
    """
    Optimized bill parent scanner for high concurrency
    Handles 20+ concurrent users with 100+ bags per bill
    """
    start_time = time.time()
    
    # Quick authentication check - use session
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            'success': False,
            'message': 'Authentication required',
            'error_type': 'auth_required'
        }), 401
    
    # Get parameters
    bill_id = request.form.get('bill_id')
    qr_code = request.form.get('qr_code', '').strip().upper()
    
    # Validate inputs
    if not bill_id or not qr_code:
        return jsonify({
            'success': False,
            'message': 'Missing bill ID or QR code',
            'error_type': 'missing_data',
            'time_ms': round((time.time() - start_time) * 1000, 2)
        })
    
    # Validate QR format (SB##### - case insensitive)
    import re
    if not re.match(r'^SB\d{5}$', qr_code):
        return jsonify({
            'success': False,
            'message': f'Invalid format! Must be SB##### (e.g., SB12345). Got: {qr_code}',
            'error_type': 'invalid_format',
            'time_ms': round((time.time() - start_time) * 1000, 2)
        })
    
    try:
        # Convert bill_id to integer
        bill_id = int(bill_id)
        
        # Get bill from cache
        bill_data = get_cached_bill(bill_id)
        if not bill_data:
            return jsonify({
                'success': False,
                'message': f'Bill #{bill_id} not found',
                'error_type': 'bill_not_found',
                'time_ms': round((time.time() - start_time) * 1000, 2)
            })
        
        # Use optimized query to check bag and link status
        result = db.session.execute(
            text("""
                WITH bag_check AS (
                    SELECT 
                        b.id, 
                        b.type,
                        b.status,
                        COUNT(DISTINCT l.child_bag_id) as child_count,
                        bb.bill_id as existing_bill_id
                    FROM bag b
                    LEFT JOIN link l ON l.parent_bag_id = b.id
                    LEFT JOIN bill_bag bb ON bb.bag_id = b.id
                    WHERE b.qr_id = :qr_code
                    GROUP BY b.id, b.type, b.status, bb.bill_id
                )
                SELECT * FROM bag_check
            """),
            {'qr_code': qr_code}
        ).fetchone()
        
        # Check if bag exists and is a parent
        if not result:
            # Create parent bag if it doesn't exist
            new_bag = Bag(
                qr_id=qr_code,
                type='parent',
                status='pending',
                user_id=user_id,
                dispatch_area=session.get('dispatch_area', 'Default'),
                created_at=datetime.now()
            )
            db.session.add(new_bag)
            db.session.flush()
            
            bag_id = new_bag.id
            child_count = 0
            existing_bill_id = None
        else:
            if result.type != 'parent':
                return jsonify({
                    'success': False,
                    'message': f'{qr_code} is a {result.type} bag, not a parent bag',
                    'error_type': 'wrong_bag_type',
                    'time_ms': round((time.time() - start_time) * 1000, 2)
                })
            
            bag_id = result.id
            child_count = result.child_count or 0
            existing_bill_id = result.existing_bill_id
        
        # Check if already linked to a bill
        if existing_bill_id:
            if existing_bill_id == bill_id:
                return jsonify({
                    'success': False,
                    'message': f'{qr_code} already linked to this bill',
                    'error_type': 'already_linked_same',
                    'time_ms': round((time.time() - start_time) * 1000, 2)
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'{qr_code} already linked to different bill #{existing_bill_id}',
                    'error_type': 'already_linked_other',
                    'time_ms': round((time.time() - start_time) * 1000, 2)
                })
        
        # Check current capacity - allow up to 200 bags for flexibility
        current_count = db.session.execute(
            text("SELECT COUNT(*) FROM bill_bag WHERE bill_id = :bill_id"),
            {'bill_id': bill_id}
        ).scalar()
        
        max_capacity = min(bill_data['parent_bag_count'], 200)  # Allow max 200 bags
        if current_count >= max_capacity:
            return jsonify({
                'success': False,
                'message': f'Bill capacity reached ({current_count}/{max_capacity} bags)',
                'error_type': 'capacity_reached',
                'time_ms': round((time.time() - start_time) * 1000, 2)
            })
        
        # Link bag to bill using optimized insert
        db.session.execute(
            text("""
                INSERT INTO bill_bag (bill_id, bag_id, status, created_at)
                VALUES (:bill_id, :bag_id, 'linked', NOW())
            """),
            {'bill_id': bill_id, 'bag_id': bag_id}
        )
        
        # Update bag weight based on child count
        weight_kg = float(child_count)  # 1kg per child
        db.session.execute(
            text("""
                UPDATE bag 
                SET weight_kg = :weight, 
                    child_count = :count,
                    status = CASE 
                        WHEN :count >= 30 THEN 'completed'
                        WHEN :count > 0 THEN 'in_progress'
                        ELSE 'pending'
                    END
                WHERE id = :bag_id
            """),
            {'weight': weight_kg, 'count': child_count, 'bag_id': bag_id}
        )
        
        # Update bill totals
        db.session.execute(
            text("""
                UPDATE bill 
                SET total_weight_kg = COALESCE(total_weight_kg, 0) + :weight,
                    expected_weight_kg = (
                        SELECT COUNT(*) * 30.0 FROM bill_bag WHERE bill_id = :bill_id
                    ) + 30.0
                WHERE id = :bill_id
            """),
            {'bill_id': bill_id, 'weight': weight_kg}
        )
        
        # Record scan
        db.session.execute(
            text("""
                INSERT INTO scan (user_id, parent_bag_id, timestamp)
                VALUES (:user_id, :bag_id, NOW())
            """),
            {'user_id': user_id, 'bag_id': bag_id}
        )
        
        # Commit transaction
        db.session.commit()
        
        # Clear bill cache
        clear_bill_cache(bill_id)
        
        # Get final count
        final_count = current_count + 1
        
        response_time = round((time.time() - start_time) * 1000, 2)
        logger.info(f'Successfully linked {qr_code} to bill {bill_id} in {response_time}ms')
        
        return jsonify({
            'success': True,
            'message': f'✅ {qr_code} linked successfully! ({child_count} children)',
            'bag_qr': qr_code,
            'linked_count': final_count,
            'expected_count': bill_data['parent_bag_count'],
            'child_count': child_count,
            'weight_kg': weight_kg,
            'time_ms': response_time
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Optimized bill scan error: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Error processing scan: {str(e)}',
            'error_type': 'server_error',
            'time_ms': round((time.time() - start_time) * 1000, 2)
        })

# Register the optimized endpoint
logger.info("✅ Optimized bill parent scanner loaded")
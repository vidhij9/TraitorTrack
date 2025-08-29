"""
Ultra-fast scanning routes optimized for millisecond response times
"""

from flask import jsonify, session, request, redirect, url_for, flash
from sqlalchemy import text
from datetime import datetime
import time
import re
from app_clean import app, db, csrf
from flask_login import current_user, login_required

# Helper function to check if user is logged in
def is_logged_in():
    """Check if user is logged in using session data"""
    return session.get('logged_in', False) and session.get('user_id') is not None

# Pre-compiled regex for validation (case-insensitive)
PARENT_QR_PATTERN = re.compile(r'^[sS][bB]\d{5}$')

# Optimized SQL queries
QUERIES = {
    'get_bag': """
        SELECT id, qr_id, type, status, weight_kg, user_id, dispatch_area
        FROM bag 
        WHERE UPPER(qr_id) = UPPER(:qr_id)
        LIMIT 1
    """,
    
    'create_parent': """
        INSERT INTO bag (qr_id, type, status, user_id, dispatch_area, created_at)
        VALUES (:qr_id, 'parent', 'pending', :user_id, :dispatch_area, NOW())
        ON CONFLICT (qr_id) DO NOTHING
        RETURNING id
    """,
    
    'create_child': """
        INSERT INTO bag (qr_id, type, status, user_id, dispatch_area, created_at)
        VALUES (:qr_id, 'child', 'pending', :user_id, :dispatch_area, NOW())
        ON CONFLICT (qr_id) DO NOTHING
        RETURNING id
    """,
    
    'get_child_count': """
        SELECT COUNT(DISTINCT child_bag_id) as count
        FROM link
        WHERE parent_bag_id = :parent_id
    """,
    
    'check_existing_link': """
        SELECT l.id, p.qr_id as parent_qr
        FROM link l
        JOIN bag p ON p.id = l.parent_bag_id
        JOIN bag c ON c.id = l.child_bag_id
        WHERE UPPER(c.qr_id) = UPPER(:child_qr)
        LIMIT 1
    """,
    
    'create_link': """
        INSERT INTO link (parent_bag_id, child_bag_id)
        VALUES (:parent_id, :child_id)
        ON CONFLICT DO NOTHING
    """,
    
    'update_parent_complete': """
        UPDATE bag 
        SET status = 'completed', weight_kg = 30.0
        WHERE id = :parent_id AND type = 'parent'
    """,
    
    'record_scan': """
        INSERT INTO scan (parent_bag_id, child_bag_id, user_id, timestamp)
        VALUES (:parent_id, :child_id, :user_id, NOW())
    """
}

@app.route('/fast/parent_scan', methods=['POST'])
@csrf.exempt
def fast_parent_scan():
    """Ultra-fast parent scan - < 50ms target"""
    start = time.time()
    
    # Check authentication using session
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    user_id = session.get('user_id')
    dispatch_area = session.get('dispatch_area', 'Default')
    
    qr_code = request.form.get('qr_code', '').strip()
    
    # Fast validation
    if not qr_code:
        return jsonify({
            'success': False, 
            'message': 'No QR code provided',
            'time_ms': round((time.time() - start) * 1000, 2)
        })
    
    # Validate format (case-insensitive) and normalize to uppercase
    if not PARENT_QR_PATTERN.match(qr_code):
        return jsonify({
            'success': False,
            'message': f'Invalid format! Must be SB##### (accepts: SB, Sb, sB, sb). Got: {qr_code}',
            'time_ms': round((time.time() - start) * 1000, 2)
        })
    
    # Normalize to uppercase for storage
    qr_code = qr_code.upper()
    
    try:
        # Use raw SQL for speed with retry logic
        for attempt in range(3):
            try:
                result = db.session.execute(
                    text(QUERIES['get_bag']),
                    {'qr_id': qr_code}
                ).fetchone()
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(0.5)
                    db.session.rollback()
                else:
                    raise
        
        if result:
            if result.type != 'parent':
                return jsonify({
                    'success': False,
                    'message': f'{qr_code} is already a {result.type} bag',
                    'time_ms': round((time.time() - start) * 1000, 2)
                })
            
            # Get child count with optimized query and better error handling
            count = 0
            try:
                # Ensure we get fresh data
                db.session.rollback()  # Clear any pending transaction
                count_result = db.session.execute(
                    text("SELECT COUNT(DISTINCT child_bag_id) FROM link WHERE parent_bag_id = :parent_id"),
                    {'parent_id': result.id}
                ).scalar()
                count = count_result if count_result is not None else 0
                app.logger.info(f'Parent {qr_code} (ID: {result.id}) has {count} children')
            except Exception as e:
                app.logger.error(f'Failed to get child count for parent {qr_code}: {str(e)}')
                db.session.rollback()
                # Try alternate query
                try:
                    from models import Link
                    count = Link.query.filter_by(parent_bag_id=result.id).count()
                    app.logger.info(f'Fallback count for {qr_code}: {count} children')
                except:
                    count = 0
            
            # Store in session
            session['current_parent_qr'] = qr_code
            session['current_parent_id'] = result.id
            
            return jsonify({
                'success': True,
                'parent_qr': qr_code,
                'existing': True,
                'child_count': count,
                'message': f'Parent {qr_code} ready ({count} children)',
                'redirect': url_for('scan_child'),
                'time_ms': round((time.time() - start) * 1000, 2)
            })
        else:
            # Create new parent
            new_id = db.session.execute(
                text(QUERIES['create_parent']),
                {
                    'qr_id': qr_code,
                    'user_id': user_id,
                    'dispatch_area': dispatch_area
                }
            ).scalar()
            
            # Skip scan recording for performance - can be added asynchronously later
            
            db.session.commit()
            
            # Cache invalidation handled elsewhere
            
            # Store in session
            session['current_parent_qr'] = qr_code
            session['current_parent_id'] = new_id
            
            return jsonify({
                'success': True,
                'parent_qr': qr_code,
                'existing': False,
                'child_count': 0,
                'message': f'New parent {qr_code} created',
                'redirect': url_for('scan_child'),
                'time_ms': round((time.time() - start) * 1000, 2)
            })
            
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Fast parent scan error: {str(e)}')
        # Provide more specific error message
        error_msg = 'Database connection error' if 'connection' in str(e).lower() else 'Scan failed - please retry'
        return jsonify({
            'success': False,
            'message': error_msg,
            'error_type': 'database' if 'connection' in str(e).lower() else 'general',
            'time_ms': round((time.time() - start) * 1000, 2)
        })

@app.route('/fast/child_scan', methods=['POST'])
@csrf.exempt
def fast_child_scan():
    """Ultra-fast child scan - < 50ms target"""
    start = time.time()
    
    # Check authentication using session
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    user_id = session.get('user_id')
    dispatch_area = session.get('dispatch_area', 'Default')
    
    qr_code = request.form.get('qr_code', '').strip()
    parent_qr = session.get('current_parent_qr')
    parent_id = session.get('current_parent_id')
    
    # Fast validation
    if not qr_code or len(qr_code) < 3:
        return jsonify({
            'success': False,
            'message': 'Invalid QR code',
            'time_ms': round((time.time() - start) * 1000, 2)
        })
    
    if not parent_qr or not parent_id:
        return jsonify({
            'success': False,
            'message': 'No parent bag selected',
            'time_ms': round((time.time() - start) * 1000, 2)
        })
    
    if qr_code == parent_qr:
        return jsonify({
            'success': False,
            'message': 'Cannot link bag to itself',
            'time_ms': round((time.time() - start) * 1000, 2)
        })
    
    try:
        # Check child count first with retry logic
        count = 0
        for attempt in range(3):
            try:
                count = db.session.execute(
                    text(QUERIES['get_child_count']),
                    {'parent_id': parent_id}
                ).scalar() or 0
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(0.5)
                    db.session.rollback()
                else:
                    app.logger.error(f'Failed to get child count: {str(e)}')
                    count = 0
        
        if count >= 30:
            return jsonify({
                'success': False,
                'message': 'Parent bag full (30/30)',
                'time_ms': round((time.time() - start) * 1000, 2)
            })
        
        # Check if child exists with retry logic
        child = None
        for attempt in range(3):
            try:
                child = db.session.execute(
                    text(QUERIES['get_bag']),
                    {'qr_id': qr_code}
                ).fetchone()
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(0.5)
                    db.session.rollback()
                else:
                    raise
        
        if child:
            if child.type == 'parent':
                # Get child count for this parent
                parent_children = db.session.execute(
                    text(QUERIES['get_child_count']),
                    {'parent_id': child.id}
                ).scalar() or 0
                
                return jsonify({
                    'success': False,
                    'message': f'{qr_code} is a parent bag with {parent_children} children',
                    'time_ms': round((time.time() - start) * 1000, 2)
                })
            
            # Check if already linked
            existing = db.session.execute(
                text(QUERIES['check_existing_link']),
                {'child_qr': qr_code}
            ).fetchone()
            
            if existing:
                return jsonify({
                    'success': False,
                    'message': f'{qr_code} already linked to parent {existing.parent_qr}',
                    'time_ms': round((time.time() - start) * 1000, 2)
                })
            
            child_id = child.id
        else:
            # Create new child
            child_id = db.session.execute(
                text(QUERIES['create_child']),
                {
                    'qr_id': qr_code,
                    'user_id': user_id,
                    'dispatch_area': dispatch_area
                }
            ).scalar()
        
        # Create link
        db.session.execute(
            text(QUERIES['create_link']),
            {
                'parent_id': parent_id,
                'child_id': child_id
            }
        )
        
        # Skip scan recording for performance - can be added asynchronously later
        
        new_count = count + 1
        
        # Auto-complete if 30
        if new_count == 30:
            db.session.execute(
                text(QUERIES['update_parent_complete']),
                {'parent_id': parent_id}
            )
        
        db.session.commit()
        
        # Cache invalidation handled elsewhere
        
        return jsonify({
            'success': True,
            'child_qr': qr_code,
            'parent_qr': parent_qr,
            'child_count': new_count,
            'message': f'Child linked ({new_count}/30)',
            'completed': new_count == 30,
            'time_ms': round((time.time() - start) * 1000, 2)
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Fast child scan error: {str(e)}')
        # Provide more specific error message
        error_msg = 'Database connection error' if 'connection' in str(e).lower() else 'Scan failed - please retry'
        # Try to get current count for better UX
        try:
            current_count = db.session.execute(
                text(QUERIES['get_child_count']),
                {'parent_id': parent_id}
            ).scalar() or 0
        except:
            current_count = 0
        return jsonify({
            'success': False,
            'message': error_msg,
            'child_count': current_count,
            'parent_qr': parent_qr,
            'error_type': 'database' if 'connection' in str(e).lower() else 'general',
            'time_ms': round((time.time() - start) * 1000, 2)
        })

# Bill parent scanning optimization
@app.route('/fast/bill_parent_scan', methods=['POST'])
@csrf.exempt  
def fast_bill_parent_scan():
    """Ultra-fast bill parent scanning"""
    start = time.time()
    
    # Check authentication using session
    if not is_logged_in():
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    user_id = session.get('user_id')
    dispatch_area = session.get('dispatch_area', 'Default')
    
    bill_id = request.form.get('bill_id', type=int)
    qr_code = request.form.get('qr_code', '').strip()
    
    if not bill_id or not qr_code:
        return jsonify({
            'success': False,
            'message': 'Missing bill ID or QR code',
            'time_ms': round((time.time() - start) * 1000, 2)
        })
    
    try:
        # Single optimized query to check everything at once
        result = db.session.execute(
            text("""
                WITH bag_info AS (
                    SELECT 
                        b.id, b.type, b.status,
                        COUNT(cb.id) as child_count,
                        bb.bill_id as existing_bill
                    FROM bag b
                    LEFT JOIN bag cb ON cb.parent_id = b.id
                    LEFT JOIN bill_bag bb ON bb.bag_id = b.id
                    WHERE UPPER(b.qr_id) = UPPER(:qr_id)
                    GROUP BY b.id, b.type, b.status, bb.bill_id
                )
                SELECT * FROM bag_info LIMIT 1
            """),
            {'qr_id': qr_code}
        ).fetchone()
        
        if not result:
            return jsonify({
                'success': False,
                'message': f'Parent bag {qr_code} not found',
                'time_ms': round((time.time() - start) * 1000, 2)
            })
        
        if result.type != 'parent':
            return jsonify({
                'success': False,
                'message': f'{qr_code} is not a parent bag',
                'time_ms': round((time.time() - start) * 1000, 2)
            })
        
        # Parent bag can be linked regardless of child count
        # No longer requiring 30 children
        
        if result.existing_bill:
            return jsonify({
                'success': False,
                'message': f'{qr_code} already linked to bill #{result.existing_bill}',
                'time_ms': round((time.time() - start) * 1000, 2)
            })
        
        # Link to bill and update weights
        db.session.execute(
            text("INSERT INTO bill_bag (bill_id, bag_id) VALUES (:bill_id, :parent_id)"),
            {'bill_id': bill_id, 'parent_id': result.id}
        )
        
        # Update both actual and expected weights
        # Actual weight: 30kg if parent has 30 children, otherwise child count
        actual_weight = 30 if result.child_count >= 30 else (result.child_count if result.child_count else 0)
        
        db.session.execute(
            text("""
                UPDATE bill 
                SET total_weight_kg = COALESCE(total_weight_kg, 0) + :actual_weight,
                    expected_weight_kg = COALESCE(expected_weight_kg, 0) + 30.0
                WHERE id = :bill_id
            """),
            {'bill_id': bill_id, 'actual_weight': actual_weight}
        )
        
        db.session.commit()
        
        # Cache invalidation handled elsewhere
        
        # Get updated count in the same transaction
        bag_count = db.session.execute(
            text("SELECT COUNT(*) FROM bill_bag WHERE bill_id = :bill_id"),
            {'bill_id': bill_id}
        ).scalar()
        
        return jsonify({
            'success': True,
            'bag_qr': qr_code,
            'linked_count': bag_count,
            'message': f'Parent bag {qr_code} added to bill',
            'time_ms': round((time.time() - start) * 1000, 2)
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Fast bill scan error: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'Failed to link bag to bill',
            'time_ms': round((time.time() - start) * 1000, 2)
        })
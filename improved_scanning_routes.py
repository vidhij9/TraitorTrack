"""
Improved scanning routes with enhanced stability and error handling
"""
from flask import request, jsonify, session, url_for, render_template_string
from flask_login import login_required
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, DBAPIError, IntegrityError
import time
import re
import logging
from app_clean import app, db, csrf
from models import Bag, Link, Scan, Bill, BillBag
from auth_helpers import is_logged_in
from connection_manager import connection_manager

logger = logging.getLogger(__name__)

# Pattern for parent bag QR codes
PARENT_QR_PATTERN = re.compile(r'^[sS][bB]\d{5}$')

class ScanningService:
    """Service class for improved scanning operations"""
    
    @staticmethod
    def execute_with_retry(query, params, fetch_type='fetchone', max_retries=3):
        """Execute database query with retry logic"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                result = db.session.execute(text(query), params)
                
                if fetch_type == 'fetchone':
                    return result.fetchone()
                elif fetch_type == 'fetchall':
                    return result.fetchall()
                elif fetch_type == 'scalar':
                    return result.scalar()
                else:
                    return result
                    
            except (OperationalError, DBAPIError) as e:
                last_error = e
                db.session.rollback()
                
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 5)
                    logger.warning(f"Database query failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                    time.sleep(wait_time)
                    
                    # Recreate session if needed
                    if "connection" in str(e).lower():
                        try:
                            db.session.remove()
                            db.session.configure(bind=db.engine)
                        except:
                            pass
                else:
                    logger.error(f"Query failed after {max_retries} attempts: {str(e)}")
                    
            except Exception as e:
                logger.error(f"Unexpected error in query execution: {str(e)}")
                db.session.rollback()
                raise
                
        if last_error:
            raise last_error
    
    @staticmethod
    def get_child_count(parent_id, retries=3):
        """Get child count with retry logic and error handling"""
        try:
            query = """
                SELECT COUNT(*) as count
                FROM link
                WHERE parent_bag_id = :parent_id
            """
            count = ScanningService.execute_with_retry(
                query, 
                {'parent_id': parent_id}, 
                fetch_type='scalar',
                max_retries=retries
            )
            return count or 0
        except Exception as e:
            logger.error(f"Failed to get child count for parent {parent_id}: {str(e)}")
            # Try alternative query
            try:
                count = Link.query.filter_by(parent_bag_id=parent_id).count()
                return count
            except:
                return 0
    
    @staticmethod
    def get_or_create_parent(qr_code, user_id, dispatch_area):
        """Get existing parent or create new one with proper error handling"""
        try:
            # First try to get existing
            query = """
                SELECT id, qr_id, type, status, weight_kg
                FROM bag 
                WHERE UPPER(qr_id) = UPPER(:qr_id)
                LIMIT 1
            """
            
            existing = ScanningService.execute_with_retry(
                query,
                {'qr_id': qr_code},
                fetch_type='fetchone'
            )
            
            if existing:
                if existing.type != 'parent':
                    return None, f"{qr_code} is already a {existing.type} bag"
                return existing.id, None
            
            # Create new parent
            create_query = """
                INSERT INTO bag (qr_id, type, status, user_id, dispatch_area, created_at)
                VALUES (:qr_id, 'parent', 'pending', :user_id, :dispatch_area, NOW())
                ON CONFLICT (qr_id) DO UPDATE
                SET type = 'parent'
                RETURNING id
            """
            
            new_id = ScanningService.execute_with_retry(
                create_query,
                {
                    'qr_id': qr_code,
                    'user_id': user_id,
                    'dispatch_area': dispatch_area
                },
                fetch_type='scalar'
            )
            
            return new_id, None
            
        except Exception as e:
            logger.error(f"Failed to get/create parent {qr_code}: {str(e)}")
            return None, "Database error - please try again"
    
    @staticmethod
    def link_child_to_parent(parent_id, parent_qr, child_qr, user_id, dispatch_area):
        """Link child to parent with comprehensive error handling"""
        try:
            # Validate not same QR
            if child_qr.upper() == parent_qr.upper():
                return False, "Cannot link bag to itself", 0
            
            # Get current count with retry
            current_count = ScanningService.get_child_count(parent_id)
            
            if current_count >= 30:
                return False, f"Parent bag full ({current_count}/30)", current_count
            
            # Check if child exists
            child_query = """
                SELECT id, type FROM bag 
                WHERE UPPER(qr_id) = UPPER(:qr_id)
                LIMIT 1
            """
            
            child = ScanningService.execute_with_retry(
                child_query,
                {'qr_id': child_qr},
                fetch_type='fetchone'
            )
            
            if child:
                if child.type == 'parent':
                    child_count = ScanningService.get_child_count(child.id)
                    return False, f"{child_qr} is a parent bag with {child_count} children", current_count
                
                # Check if already linked
                link_check = """
                    SELECT l.id, p.qr_id as parent_qr
                    FROM link l
                    JOIN bag p ON p.id = l.parent_bag_id
                    WHERE l.child_bag_id = :child_id
                    LIMIT 1
                """
                
                existing_link = ScanningService.execute_with_retry(
                    link_check,
                    {'child_id': child.id},
                    fetch_type='fetchone'
                )
                
                if existing_link:
                    if existing_link.parent_qr.upper() == parent_qr.upper():
                        # Already linked to this parent
                        return True, f"Already linked ({current_count}/30)", current_count
                    else:
                        return False, f"{child_qr} already linked to parent {existing_link.parent_qr}", current_count
                
                child_id = child.id
            else:
                # Create new child
                create_child = """
                    INSERT INTO bag (qr_id, type, status, user_id, dispatch_area, created_at)
                    VALUES (:qr_id, 'child', 'pending', :user_id, :dispatch_area, NOW())
                    ON CONFLICT (qr_id) DO UPDATE
                    SET type = 'child'
                    RETURNING id
                """
                
                child_id = ScanningService.execute_with_retry(
                    create_child,
                    {
                        'qr_id': child_qr,
                        'user_id': user_id,
                        'dispatch_area': dispatch_area
                    },
                    fetch_type='scalar'
                )
            
            # Create link
            create_link = """
                INSERT INTO link (parent_bag_id, child_bag_id)
                VALUES (:parent_id, :child_id)
                ON CONFLICT DO NOTHING
            """
            
            ScanningService.execute_with_retry(
                create_link,
                {
                    'parent_id': parent_id,
                    'child_id': child_id
                },
                fetch_type=None
            )
            
            # Update count
            new_count = current_count + 1
            
            # Auto-complete if 30
            if new_count == 30:
                complete_query = """
                    UPDATE bag 
                    SET status = 'completed', weight_kg = 30.0
                    WHERE id = :parent_id AND type = 'parent'
                """
                
                ScanningService.execute_with_retry(
                    complete_query,
                    {'parent_id': parent_id},
                    fetch_type=None
                )
            
            db.session.commit()
            
            return True, f"Child linked ({new_count}/30)", new_count
            
        except IntegrityError as e:
            db.session.rollback()
            # Likely duplicate, get current count
            current_count = ScanningService.get_child_count(parent_id)
            return True, f"Child linked ({current_count}/30)", current_count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to link child {child_qr} to parent {parent_qr}: {str(e)}")
            return False, "Failed to link child - please retry", 0

# Enhanced parent scanning endpoint
@app.route('/improved/parent_scan', methods=['POST'])
@csrf.exempt
def improved_parent_scan():
    """Improved parent scan with enhanced stability"""
    start = time.time()
    
    # Check authentication
    if not is_logged_in():
        return jsonify({
            'success': False, 
            'message': 'Please login first',
            'auth_required': True
        }), 401
    
    user_id = session.get('user_id')
    dispatch_area = session.get('dispatch_area', 'Default')
    
    # Get and validate QR code
    qr_code = request.form.get('qr_code', '').strip()
    
    if not qr_code:
        return jsonify({
            'success': False,
            'message': 'Please scan or enter a QR code',
            'time_ms': round((time.time() - start) * 1000, 2)
        }), 400
    
    # Validate format
    if not PARENT_QR_PATTERN.match(qr_code):
        return jsonify({
            'success': False,
            'message': f'Invalid parent bag format. Expected: SB##### (e.g., SB00001). Got: {qr_code}',
            'time_ms': round((time.time() - start) * 1000, 2)
        }), 400
    
    # Normalize to uppercase
    qr_code = qr_code.upper()
    
    try:
        # Get or create parent with retry logic
        parent_id, error = ScanningService.get_or_create_parent(qr_code, user_id, dispatch_area)
        
        if error:
            return jsonify({
                'success': False,
                'message': error,
                'time_ms': round((time.time() - start) * 1000, 2)
            }), 400
        
        # Get child count with retry
        child_count = ScanningService.get_child_count(parent_id)
        
        # Store in session with backup
        session['current_parent_qr'] = qr_code
        session['current_parent_id'] = parent_id
        session['parent_scan_time'] = time.time()
        session.modified = True
        
        # Also store as backup
        session['last_parent'] = {
            'qr': qr_code,
            'id': parent_id,
            'time': time.time()
        }
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'parent_qr': qr_code,
            'parent_id': parent_id,
            'child_count': child_count,
            'message': f'Parent {qr_code} ready ({child_count}/30 children)',
            'redirect': url_for('scan_child'),
            'time_ms': round((time.time() - start) * 1000, 2)
        })
        
    except Exception as e:
        logger.error(f"Parent scan error for {qr_code}: {str(e)}")
        db.session.rollback()
        
        return jsonify({
            'success': False,
            'message': 'Database connection error. Please try again.',
            'error_details': str(e) if app.debug else None,
            'time_ms': round((time.time() - start) * 1000, 2)
        }), 500

# Enhanced child scanning endpoint
@app.route('/improved/child_scan', methods=['POST'])
@csrf.exempt
def improved_child_scan():
    """Improved child scan with enhanced stability"""
    start = time.time()
    
    # Check authentication
    if not is_logged_in():
        return jsonify({
            'success': False,
            'message': 'Please login first',
            'auth_required': True
        }), 401
    
    user_id = session.get('user_id')
    dispatch_area = session.get('dispatch_area', 'Default')
    
    # Get QR code
    qr_code = request.form.get('qr_code', '').strip()
    
    if not qr_code or len(qr_code) < 3:
        return jsonify({
            'success': False,
            'message': 'Please scan or enter a valid QR code',
            'time_ms': round((time.time() - start) * 1000, 2)
        }), 400
    
    # Get parent from session with fallback
    parent_qr = session.get('current_parent_qr')
    parent_id = session.get('current_parent_id')
    
    # Try backup if primary not found
    if not parent_qr or not parent_id:
        last_parent = session.get('last_parent', {})
        if last_parent and (time.time() - last_parent.get('time', 0)) < 3600:  # Within 1 hour
            parent_qr = last_parent.get('qr')
            parent_id = last_parent.get('id')
    
    if not parent_qr or not parent_id:
        return jsonify({
            'success': False,
            'message': 'No parent bag selected. Please scan a parent bag first.',
            'need_parent': True,
            'time_ms': round((time.time() - start) * 1000, 2)
        }), 400
    
    try:
        # Link child with comprehensive error handling
        success, message, child_count = ScanningService.link_child_to_parent(
            parent_id, parent_qr, qr_code, user_id, dispatch_area
        )
        
        if not success:
            return jsonify({
                'success': False,
                'message': message,
                'child_count': child_count,
                'parent_qr': parent_qr,
                'time_ms': round((time.time() - start) * 1000, 2)
            }), 400
        
        # Check if completed
        completed = child_count >= 30
        
        if completed:
            # Clear session for next parent
            session.pop('current_parent_qr', None)
            session.pop('current_parent_id', None)
            message = f"Parent bag {parent_qr} completed with 30 children!"
        
        return jsonify({
            'success': True,
            'child_qr': qr_code,
            'parent_qr': parent_qr,
            'child_count': child_count,
            'message': message,
            'completed': completed,
            'time_ms': round((time.time() - start) * 1000, 2)
        })
        
    except Exception as e:
        logger.error(f"Child scan error for {qr_code}: {str(e)}")
        db.session.rollback()
        
        # Try to get current count for recovery
        try:
            current_count = ScanningService.get_child_count(parent_id)
        except:
            current_count = 0
        
        return jsonify({
            'success': False,
            'message': 'Database connection error. Please try again.',
            'child_count': current_count,
            'parent_qr': parent_qr,
            'error_details': str(e) if app.debug else None,
            'time_ms': round((time.time() - start) * 1000, 2)
        }), 500

# Status check endpoint
@app.route('/improved/scan_status', methods=['GET'])
def improved_scan_status():
    """Check current scanning session status"""
    try:
        parent_qr = session.get('current_parent_qr')
        parent_id = session.get('current_parent_id')
        
        if not parent_qr or not parent_id:
            return jsonify({
                'success': True,
                'has_parent': False,
                'message': 'No active parent bag session'
            })
        
        # Get current child count
        child_count = ScanningService.get_child_count(parent_id)
        
        return jsonify({
            'success': True,
            'has_parent': True,
            'parent_qr': parent_qr,
            'parent_id': parent_id,
            'child_count': child_count,
            'completed': child_count >= 30
        })
        
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error checking status',
            'error': str(e) if app.debug else None
        }), 500

# Register improved routes
logger.info("Improved scanning routes registered with enhanced stability")
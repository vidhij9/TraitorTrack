"""
Ultra-fast optimized routes for instant QR scanning
Designed for 100+ concurrent users with sub-second response times
"""
from flask import jsonify, session, request
from sqlalchemy import text
from sqlalchemy.orm import joinedload
from app_clean import app, db, csrf
from models import Bag, BagType, Link, Scan
from auth_utils import current_user, require_auth
import json

login_required = require_auth

# In-memory cache for active sessions (reduces DB lookups)
active_parents_cache = {}

@app.route('/api/ultra/scan/child', methods=['POST'])
@csrf.exempt
@login_required
def ultra_scan_child():
    """Simplified fast child scanning"""
    try:
        # Parse request
        data = request.get_json() if request.is_json else request.form
        qr_id = data.get('qr_code', '').strip()
        
        if not qr_id or len(qr_id) < 3:
            return jsonify({'success': False, 'message': 'Invalid QR'}), 400
        
        # Get parent from session
        parent_qr = session.get('current_parent_qr')
        if not parent_qr:
            return jsonify({'success': False, 'message': 'No parent selected'}), 400
        
        if qr_id == parent_qr:
            return jsonify({'success': False, 'message': 'Cannot self-link'}), 400
        
        # Simple queries using ORM for reliability
        from models import Bag, BagType, Link, Scan
        
        # Get parent bag
        parent_bag = Bag.query.filter_by(qr_id=parent_qr, type=BagType.PARENT.value).first()
        if not parent_bag:
            session.pop('current_parent_qr', None)
            return jsonify({'success': False, 'message': 'Parent not found'}), 400
        
        # Get or create child bag
        child_bag = Bag.query.filter_by(qr_id=qr_id).first()
        if not child_bag:
            child_bag = Bag(qr_id=qr_id, type=BagType.CHILD.value)
            db.session.add(child_bag)
            db.session.flush()
        elif child_bag.type == BagType.PARENT.value:
            return jsonify({'success': False, 'message': f'{qr_id} is a parent bag'}), 400
        
        # Check if already linked
        existing_link = Link.query.filter_by(
            parent_bag_id=parent_bag.id,
            child_bag_id=child_bag.id
        ).first()
        
        if existing_link:
            return jsonify({'success': False, 'message': 'Already linked'}), 400
        
        # Create link
        new_link = Link(parent_bag_id=parent_bag.id, child_bag_id=child_bag.id)
        db.session.add(new_link)
        
        # Create scan record
        scan = Scan(child_bag_id=child_bag.id, user_id=current_user.id)
        db.session.add(scan)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Linked {qr_id}',
            'child_id': qr_id,
            'child_name': child_bag.name or ''
        }), 200
        
    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"Error in ultra_scan_child: {e}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/ultra/scan/parent', methods=['POST'])
@csrf.exempt
@login_required  
def ultra_scan_parent():
    """Simplified fast parent scanning"""
    try:
        # Parse request
        data = request.get_json() if request.is_json else request.form
        qr_id = data.get('qr_code', '').strip()
        
        if not qr_id or len(qr_id) < 3:
            return jsonify({'success': False, 'message': 'Invalid QR'}), 400
        
        # Simple ORM queries
        from models import Bag, BagType, Link, Scan
        
        # Check if bag exists
        parent_bag = Bag.query.filter_by(qr_id=qr_id).first()
        
        if not parent_bag:
            # Create new parent
            parent_bag = Bag(qr_id=qr_id, type=BagType.PARENT.value)
            db.session.add(parent_bag)
            db.session.flush()
        elif parent_bag.type == BagType.CHILD.value:
            # Check if child is linked
            link = Link.query.filter_by(child_bag_id=parent_bag.id).first()
            if link:
                return jsonify({
                    'success': False,
                    'message': f'{qr_id} is already linked as child'
                }), 400
            # Convert to parent
            parent_bag.type = BagType.PARENT.value
        
        # Create scan record
        scan = Scan(parent_bag_id=parent_bag.id, user_id=current_user.id)
        db.session.add(scan)
        
        db.session.commit()
        
        # Store in session
        session['current_parent_qr'] = qr_id
        session['current_parent_id'] = parent_bag.id
        session.modified = True
        
        return jsonify({
            'success': True,
            'message': f'Parent {qr_id} ready',
            'parent_id': qr_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"Error in ultra_scan_parent: {e}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/ultra/scan/status', methods=['GET'])
@login_required
def scan_status():
    """Quick status check for scanner health"""
    try:
        # Quick DB ping
        db.session.execute(text("SELECT 1")).scalar()
        
        parent = session.get('current_parent_qr')
        cached_parent = active_parents_cache.get(current_user.id)
        
        return jsonify({
            'success': True,
            'database': 'connected',
            'current_parent': parent,
            'cached_parent': cached_parent,
            'user_id': current_user.id
        }), 200
    except:
        return jsonify({'success': False, 'database': 'error'}), 500
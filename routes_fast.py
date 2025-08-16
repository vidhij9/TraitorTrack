"""
Ultra-fast optimized routes for scanning
"""
from flask import jsonify, session, request
from sqlalchemy import or_
from app_clean import app, db, csrf
from models import Bag, BagType, Link, Scan
from auth_utils import current_user, require_auth
import traceback

login_required = require_auth

@app.route('/api/fast/scan/child', methods=['POST'])
@csrf.exempt
@login_required
def fast_scan_child():
    """Ultra-fast child scanning with single database query"""
    try:
        # Get QR code from request
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
            qr_id = data.get('qr_code', '').strip()
        else:
            qr_id = request.form.get('qr_code', '').strip()
        
        if not qr_id or len(qr_id) < 3:
            return jsonify({'success': False, 'message': 'Invalid QR code'})
        
        # Get parent from session
        parent_qr = session.get('current_parent_qr')
        if not parent_qr:
            return jsonify({'success': False, 'message': 'No parent bag selected. Scan parent first.'})
        
        # Self-link check
        if qr_id == parent_qr:
            return jsonify({'success': False, 'message': 'Cannot link to itself'})
        
        # Single optimized query to get both bags
        bags = db.session.query(Bag).filter(
            or_(Bag.qr_id == parent_qr, Bag.qr_id == qr_id)
        ).all()
        
        parent_bag = None
        child_bag = None
        
        for bag in bags:
            if bag.qr_id == parent_qr:
                parent_bag = bag
            elif bag.qr_id == qr_id:
                child_bag = bag
        
        if not parent_bag:
            session.pop('current_parent_qr', None)  # Clear invalid parent
            return jsonify({'success': False, 'message': 'Parent not found. Please scan parent again.'})
        
        # Create child if doesn't exist
        if not child_bag:
            child_bag = Bag(
                qr_id=qr_id,
                type=BagType.CHILD.value
            )
            db.session.add(child_bag)
            db.session.flush()
        elif child_bag.type == BagType.PARENT.value:
            return jsonify({'success': False, 'message': f'{qr_id} is a parent bag'})
        
        # Check if already linked
        existing_link = Link.query.filter_by(
            parent_bag_id=parent_bag.id,
            child_bag_id=child_bag.id
        ).first()
        
        if existing_link:
            return jsonify({'success': False, 'message': 'Already linked'})
        
        # Create link
        new_link = Link(
            parent_bag_id=parent_bag.id,
            child_bag_id=child_bag.id
        )
        db.session.add(new_link)
        
        # Create scan record
        scan = Scan(
            child_bag_id=child_bag.id,
            user_id=current_user.id
        )
        db.session.add(scan)
        
        # Single commit
        db.session.commit()
        
        # Fast response
        return jsonify({
            'success': True,
            'message': f'Linked {qr_id}',
            'child_id': qr_id,
            'child_name': child_bag.name if child_bag.name else ''
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Fast scan child error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/fast/scan/parent', methods=['POST'])
@csrf.exempt
@login_required
def fast_scan_parent():
    """Ultra-fast parent scanning"""
    try:
        # Get QR code
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
            qr_id = data.get('qr_code', '').strip()
        else:
            qr_id = request.form.get('qr_code', '').strip()
        
        if not qr_id or len(qr_id) < 3:
            return jsonify({'success': False, 'message': 'Invalid QR code'})
        
        # Single query to check/create parent
        parent_bag = Bag.query.filter_by(qr_id=qr_id).first()
        
        if not parent_bag:
            # Create new parent
            parent_bag = Bag(
                qr_id=qr_id,
                type=BagType.PARENT.value
            )
            db.session.add(parent_bag)
            db.session.flush()
        elif parent_bag.type == BagType.CHILD.value:
            # Check if child is linked
            link = Link.query.filter_by(child_bag_id=parent_bag.id).first()
            if link:
                return jsonify({
                    'success': False, 
                    'message': f'{qr_id} is already a child bag linked to another parent'
                })
            # Convert to parent
            parent_bag.type = BagType.PARENT.value
        
        # Create scan record
        scan = Scan(
            parent_bag_id=parent_bag.id,
            user_id=current_user.id
        )
        db.session.add(scan)
        
        # Single commit
        db.session.commit()
        
        # Store in session
        session['current_parent_qr'] = qr_id
        session['current_parent_id'] = parent_bag.id
        session.modified = True
        
        return jsonify({
            'success': True,
            'message': f'Parent {qr_id} ready',
            'parent_id': qr_id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Fast scan parent error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
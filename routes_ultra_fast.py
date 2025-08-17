"""
Ultra-fast optimized routes for instant QR scanning
Designed for 100+ concurrent users with sub-second response times
"""
from flask import jsonify, session, request, render_template
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
    """Ultra-optimized child scanning with minimal DB operations"""
    try:
        # Parse request data
        data = request.get_json() if request.is_json else request.form
        qr_id = data.get('qr_code', '').strip()
        
        if not qr_id or len(qr_id) < 3:
            return jsonify({'success': False, 'message': 'Invalid QR'}), 400
        
        # Get parent from session (ultra-fast)
        parent_qr = session.get('current_parent_qr')
        if not parent_qr:
            return jsonify({'success': False, 'message': 'No parent selected'}), 400
        
        # Self-link check
        if qr_id == parent_qr:
            return jsonify({'success': False, 'message': 'Cannot self-link'}), 400
        
        # Single optimized query using raw SQL for speed
        result = db.session.execute(
            text("""
                WITH parent AS (
                    SELECT id FROM bag WHERE qr_id = :parent_qr AND type = 'parent'
                ),
                child AS (
                    SELECT id, type, name FROM bag WHERE qr_id = :child_qr
                ),
                existing_link AS (
                    SELECT 1 FROM link l, parent p, child c 
                    WHERE l.parent_bag_id = p.id AND l.child_bag_id = c.id
                )
                SELECT 
                    (SELECT id FROM parent) as parent_id,
                    (SELECT id FROM child) as child_id,
                    (SELECT type FROM child) as child_type,
                    (SELECT name FROM child) as child_name,
                    EXISTS(SELECT 1 FROM existing_link) as already_linked
            """),
            {'parent_qr': parent_qr, 'child_qr': qr_id}
        ).fetchone()
        
        if not result or not result.parent_id:
            session.pop('current_parent_qr', None)
            return jsonify({'success': False, 'message': 'Parent not found'}), 400
        
        if result.already_linked:
            return jsonify({'success': False, 'message': 'Already linked'}), 400
        
        if result.child_type == 'parent':
            return jsonify({'success': False, 'message': f'{qr_id} is a parent'}), 400
        
        # Create child and link in single transaction
        if not result.child_id:
            # Insert child and link together
            db.session.execute(
                text("""
                    WITH new_child AS (
                        INSERT INTO bag (qr_id, type, created_at, updated_at)
                        VALUES (:qr_id, 'child', NOW(), NOW())
                        RETURNING id
                    ),
                    new_link AS (
                        INSERT INTO link (parent_bag_id, child_bag_id, created_at)
                        SELECT :parent_id, id, NOW() FROM new_child
                        RETURNING child_bag_id
                    )
                    INSERT INTO scan (child_bag_id, user_id, timestamp)
                    SELECT child_bag_id, :user_id, NOW() FROM new_link
                """),
                {'qr_id': qr_id, 'parent_id': result.parent_id, 'user_id': current_user.id}
            )
        else:
            # Just create the link
            db.session.execute(
                text("""
                    WITH new_link AS (
                        INSERT INTO link (parent_bag_id, child_bag_id, created_at)
                        VALUES (:parent_id, :child_id, NOW())
                        RETURNING child_bag_id
                    )
                    INSERT INTO scan (child_bag_id, user_id, timestamp)
                    VALUES (:child_id, :user_id, NOW())
                """),
                {'parent_id': result.parent_id, 'child_id': result.child_id, 'user_id': current_user.id}
            )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Linked {qr_id}',
            'child_id': qr_id,
            'child_name': result.child_name or ''
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error occurred'}), 500


@app.route('/api/ultra/scan/parent', methods=['POST'])
@csrf.exempt
@login_required  
def ultra_scan_parent():
    """Instant parent scanning - zero delay"""
    try:
        # Lightning-fast parsing
        qr_id = request.get_json().get('qr_code', '').strip() if request.is_json else request.form.get('qr_code', '').strip()
        
        if not qr_id or len(qr_id) < 3:
            return jsonify({'success': False, 'message': 'Invalid QR'}), 400
        
        # Ultra-fast single query check
        result = db.session.execute(
            text("SELECT id, type FROM bag WHERE qr_id = :qr_id LIMIT 1"),
            {'qr_id': qr_id}
        ).fetchone()
        
        # Instant upsert - single operation
        if not result:
            # Create new parent instantly
            db.session.execute(
                text("""
                    INSERT INTO bag (qr_id, type, created_at, updated_at)
                    VALUES (:qr_id, 'parent', NOW(), NOW())
                    ON CONFLICT (qr_id) DO UPDATE SET type = 'parent', updated_at = NOW()
                """),
                {'qr_id': qr_id}
            )
        elif result.type == 'child':
            # Quick type update
            db.session.execute(
                text("UPDATE bag SET type = 'parent' WHERE id = :id"),
                {'id': result.id}
            )
        
        db.session.commit()
        
        # Store in session
        session['current_parent_qr'] = qr_id
        session.modified = True
        
        # Cache for ultra-fast child scanning
        active_parents_cache[current_user.id] = qr_id
        
        return jsonify({
            'success': True,
            'message': f'Parent {qr_id} ready',
            'parent_id': qr_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error occurred'}), 500


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


@app.route('/scanner/test')
@login_required
def scanner_test():
    """Scanner performance test page"""
    return render_template('scanner_test.html')
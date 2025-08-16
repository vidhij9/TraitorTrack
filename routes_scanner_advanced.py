"""
Advanced scanner routes with server-side QR processing
Implements multi-library decoding and aggressive preprocessing
"""
from flask import jsonify, request, session
from app_clean import app, csrf
from auth_utils import current_user, require_auth
from qr_processor import qr_processor
import json
import time

login_required = require_auth

@app.route('/api/scanner/process', methods=['POST'])
@csrf.exempt
@login_required
def process_qr_image():
    """Process QR code image with advanced techniques"""
    try:
        data = request.get_json()
        image_data = data.get('image')
        scan_type = data.get('type', 'unknown')  # 'parent' or 'child'
        
        if not image_data:
            return jsonify({'success': False, 'message': 'No image data'}), 400
        
        # Process image with advanced techniques
        start_time = time.time()
        qr_code, method = qr_processor.process_image(image_data)
        processing_time = time.time() - start_time
        
        if qr_code:
            # Successfully decoded
            response = {
                'success': True,
                'qr_code': qr_code,
                'method': method,
                'processing_time': round(processing_time, 2),
                'scan_type': scan_type
            }
            
            # If this is a parent scan, store in session
            if scan_type == 'parent':
                session['current_parent_qr'] = qr_code
                session.modified = True
                response['message'] = f'Parent {qr_code} ready'
            elif scan_type == 'child':
                parent = session.get('current_parent_qr')
                if parent:
                    response['parent'] = parent
                    response['message'] = f'Child {qr_code} scanned'
                else:
                    response['message'] = 'No parent selected'
            
            return jsonify(response), 200
        else:
            # Failed to decode
            return jsonify({
                'success': False,
                'message': 'Could not decode QR code',
                'processing_time': round(processing_time, 2),
                'suggestion': 'Try auto-boost mode or manual entry'
            }), 200
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/scanner/process-boost', methods=['POST'])
@csrf.exempt
@login_required
def process_qr_image_boost():
    """Process QR with maximum preprocessing (slower but more accurate)"""
    try:
        data = request.get_json()
        image_data = data.get('image')
        scan_type = data.get('type', 'unknown')
        
        if not image_data:
            return jsonify({'success': False, 'message': 'No image data'}), 400
        
        # Process with maximum attempts
        start_time = time.time()
        qr_code, method = qr_processor.process_image(image_data, max_attempts=20)
        processing_time = time.time() - start_time
        
        if qr_code:
            response = {
                'success': True,
                'qr_code': qr_code,
                'method': method,
                'processing_time': round(processing_time, 2),
                'scan_type': scan_type,
                'boost_mode': True
            }
            
            if scan_type == 'parent':
                session['current_parent_qr'] = qr_code
                session.modified = True
                response['message'] = f'Parent {qr_code} ready (boost mode)'
            
            return jsonify(response), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Still could not decode. Please use manual entry.',
                'processing_time': round(processing_time, 2)
            }), 200
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/scanner/manual-entry', methods=['POST'])
@csrf.exempt
@login_required
def manual_qr_entry():
    """Manual QR code entry fallback"""
    try:
        data = request.get_json()
        qr_code = data.get('qr_code', '').strip()
        scan_type = data.get('type', 'unknown')
        
        if not qr_code or len(qr_code) < 3:
            return jsonify({'success': False, 'message': 'QR code too short'}), 400
        
        # Apply fuzzy correction to manual entry
        corrected = qr_processor.fuzzy_match_correction(qr_code)
        
        response = {
            'success': True,
            'qr_code': corrected,
            'method': 'manual_entry',
            'scan_type': scan_type
        }
        
        if scan_type == 'parent':
            session['current_parent_qr'] = corrected
            session.modified = True
            response['message'] = f'Parent {corrected} set manually'
        elif scan_type == 'child':
            response['message'] = f'Child {corrected} entered manually'
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
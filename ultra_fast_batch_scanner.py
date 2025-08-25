#!/usr/bin/env python3
"""
Ultra-Fast Batch Scanner for Parent-Child Bag Linking
Optimizes scanning of 30 child bags from 15-20 minutes to under 1 minute
"""

from flask import Blueprint, request, jsonify, session, render_template_string
from sqlalchemy import text
from models import db, Bag, Link, Scan
import time
import json
import logging
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

# Create blueprint for batch scanning
batch_scanner = Blueprint('batch_scanner', __name__)

# In-memory cache for active scanning sessions
SCANNING_SESSIONS = {}

# Optimized SQL queries for batch operations
BATCH_QUERIES = {
    'get_or_create_parent': """
        WITH parent_check AS (
            SELECT id, qr_id, type FROM bag 
            WHERE UPPER(qr_id) = UPPER(:qr_id)
            LIMIT 1
        ),
        parent_insert AS (
            INSERT INTO bag (qr_id, type, created_by, dispatch_area, created_at)
            SELECT :qr_id, 'parent', :user_id, :dispatch_area, NOW()
            WHERE NOT EXISTS (SELECT 1 FROM parent_check)
            RETURNING id, qr_id, type
        )
        SELECT * FROM parent_check
        UNION ALL
        SELECT * FROM parent_insert
    """,
    
    'batch_check_children': """
        SELECT qr_id, id, type 
        FROM bag 
        WHERE UPPER(qr_id) = ANY(:qr_codes)
    """,
    
    'batch_create_children': """
        INSERT INTO bag (qr_id, type, created_by, dispatch_area, created_at)
        SELECT unnest(:qr_codes), 'child', :user_id, :dispatch_area, NOW()
        ON CONFLICT (qr_id) DO NOTHING
        RETURNING id, qr_id
    """,
    
    'batch_create_links': """
        INSERT INTO link (parent_bag_id, child_bag_id, linked_by, linked_at)
        SELECT :parent_id, unnest(:child_ids), :user_id, NOW()
        ON CONFLICT (parent_bag_id, child_bag_id) DO NOTHING
        RETURNING child_bag_id
    """,
    
    'batch_record_scans': """
        INSERT INTO scan (
            parent_bag_id, child_bag_id, user_id, 
            scan_type, scan_duration_ms, created_at
        )
        SELECT 
            :parent_id, 
            unnest(:child_ids), 
            :user_id,
            'batch_link',
            :duration_ms,
            NOW()
    """,
    
    'get_existing_links': """
        SELECT child_bag_id 
        FROM link 
        WHERE parent_bag_id = :parent_id
    """
}

class BatchScanSession:
    """Manages a batch scanning session for ultra-fast processing"""
    
    def __init__(self, parent_qr, parent_id, user_id, dispatch_area):
        self.parent_qr = parent_qr
        self.parent_id = parent_id
        self.user_id = user_id
        self.dispatch_area = dispatch_area
        self.scanned_children = []
        self.pending_children = []
        self.errors = []
        self.start_time = time.time()
        self.last_activity = time.time()
        
    def add_child(self, qr_code):
        """Add a child to pending batch"""
        if qr_code not in self.scanned_children and qr_code != self.parent_qr:
            self.pending_children.append(qr_code)
            self.last_activity = time.time()
            return True
        return False
    
    def process_batch(self):
        """Process all pending children in a single batch operation"""
        if not self.pending_children:
            return {'processed': 0, 'errors': 0, 'time_ms': 0}
        
        start = time.time()
        processed = 0
        errors = 0
        
        try:
            # Batch check existing children
            qr_codes_upper = [qr.upper() for qr in self.pending_children]
            existing_bags = db.session.execute(
                text(BATCH_QUERIES['batch_check_children']),
                {'qr_codes': qr_codes_upper}
            ).fetchall()
            
            existing_map = {bag.qr_id.upper(): bag for bag in existing_bags}
            
            # Separate new and existing children
            new_qrs = []
            existing_child_ids = []
            parent_bags = []
            
            for qr in self.pending_children:
                qr_upper = qr.upper()
                if qr_upper in existing_map:
                    bag = existing_map[qr_upper]
                    if bag.type == 'parent':
                        parent_bags.append(qr)
                        self.errors.append(f"{qr} is a parent bag")
                    else:
                        existing_child_ids.append(bag.id)
                else:
                    new_qrs.append(qr)
            
            # Batch create new children
            if new_qrs:
                created = db.session.execute(
                    text(BATCH_QUERIES['batch_create_children']),
                    {
                        'qr_codes': new_qrs,
                        'user_id': self.user_id,
                        'dispatch_area': self.dispatch_area
                    }
                ).fetchall()
                
                for bag in created:
                    existing_child_ids.append(bag.id)
            
            # Batch create links
            if existing_child_ids:
                linked = db.session.execute(
                    text(BATCH_QUERIES['batch_create_links']),
                    {
                        'parent_id': self.parent_id,
                        'child_ids': existing_child_ids,
                        'user_id': self.user_id
                    }
                ).fetchall()
                
                processed = len(linked)
                
                # Batch record scans
                duration_ms = int((time.time() - start) * 1000)
                db.session.execute(
                    text(BATCH_QUERIES['batch_record_scans']),
                    {
                        'parent_id': self.parent_id,
                        'child_ids': [row.child_bag_id for row in linked],
                        'user_id': self.user_id,
                        'duration_ms': duration_ms
                    }
                )
            
            # Commit all changes at once
            db.session.commit()
            
            # Update session state
            self.scanned_children.extend(self.pending_children)
            self.pending_children = []
            
            errors = len(parent_bags)
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Batch processing error: {str(e)}")
            self.errors.append(f"Batch error: {str(e)}")
            errors = len(self.pending_children)
        
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            'processed': processed,
            'errors': errors,
            'time_ms': elapsed_ms
        }

@batch_scanner.route('/ultra_batch/start', methods=['POST'])
def start_batch_session():
    """Start a new ultra-fast batch scanning session"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    parent_qr = request.json.get('parent_qr', '').strip()
    if not parent_qr:
        return jsonify({'success': False, 'message': 'Parent QR required'}), 400
    
    dispatch_area = session.get('dispatch_area', 'Default')
    
    try:
        # Get or create parent bag in a single query
        result = db.session.execute(
            text(BATCH_QUERIES['get_or_create_parent']),
            {
                'qr_id': parent_qr,
                'user_id': user_id,
                'dispatch_area': dispatch_area
            }
        ).fetchone()
        
        if not result:
            return jsonify({'success': False, 'message': 'Failed to create parent'}), 500
        
        parent_id = result.id
        
        # Check existing children count
        existing_count = db.session.execute(
            text("SELECT COUNT(*) FROM link WHERE parent_bag_id = :parent_id"),
            {'parent_id': parent_id}
        ).scalar() or 0
        
        # Create batch session
        session_id = f"{user_id}_{parent_id}_{int(time.time())}"
        batch_session = BatchScanSession(parent_qr, parent_id, user_id, dispatch_area)
        SCANNING_SESSIONS[session_id] = batch_session
        
        # Store in Flask session
        session['batch_session_id'] = session_id
        session['current_parent_qr'] = parent_qr
        session['current_parent_id'] = parent_id
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'parent_qr': parent_qr,
            'existing_count': existing_count,
            'max_children': 30
        })
        
    except Exception as e:
        logger.error(f"Failed to start batch session: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to start session'}), 500

@batch_scanner.route('/ultra_batch/scan', methods=['POST'])
def scan_child_batch():
    """Add multiple children to batch for processing"""
    session_id = session.get('batch_session_id')
    if not session_id or session_id not in SCANNING_SESSIONS:
        return jsonify({'success': False, 'message': 'No active session'}), 400
    
    batch_session = SCANNING_SESSIONS[session_id]
    
    # Accept both single QR and array of QRs
    data = request.get_json()
    qr_codes = data.get('qr_codes', [])
    if isinstance(qr_codes, str):
        qr_codes = [qr_codes]
    
    # Add all QRs to pending batch
    added = 0
    duplicates = 0
    for qr in qr_codes:
        if batch_session.add_child(qr.strip()):
            added += 1
        else:
            duplicates += 1
    
    # Auto-process if batch size reached
    auto_processed = False
    if len(batch_session.pending_children) >= 10:
        result = batch_session.process_batch()
        auto_processed = True
    else:
        result = {'processed': 0, 'errors': 0, 'time_ms': 0}
    
    return jsonify({
        'success': True,
        'added': added,
        'duplicates': duplicates,
        'pending': len(batch_session.pending_children),
        'total_scanned': len(batch_session.scanned_children),
        'auto_processed': auto_processed,
        'batch_result': result
    })

@batch_scanner.route('/ultra_batch/process', methods=['POST'])
def process_batch():
    """Process all pending children in the batch"""
    session_id = session.get('batch_session_id')
    if not session_id or session_id not in SCANNING_SESSIONS:
        return jsonify({'success': False, 'message': 'No active session'}), 400
    
    batch_session = SCANNING_SESSIONS[session_id]
    result = batch_session.process_batch()
    
    return jsonify({
        'success': True,
        'result': result,
        'total_scanned': len(batch_session.scanned_children),
        'session_time': int(time.time() - batch_session.start_time)
    })

@batch_scanner.route('/ultra_batch/complete', methods=['POST'])
def complete_batch_session():
    """Complete the batch scanning session"""
    session_id = session.get('batch_session_id')
    if not session_id or session_id not in SCANNING_SESSIONS:
        return jsonify({'success': False, 'message': 'No active session'}), 400
    
    batch_session = SCANNING_SESSIONS[session_id]
    
    # Process any remaining pending children
    if batch_session.pending_children:
        final_result = batch_session.process_batch()
    else:
        final_result = {'processed': 0, 'errors': 0, 'time_ms': 0}
    
    # Calculate session statistics
    total_time = time.time() - batch_session.start_time
    total_scanned = len(batch_session.scanned_children)
    
    # Clean up session
    del SCANNING_SESSIONS[session_id]
    session.pop('batch_session_id', None)
    
    return jsonify({
        'success': True,
        'summary': {
            'parent_qr': batch_session.parent_qr,
            'total_scanned': total_scanned,
            'total_time_seconds': int(total_time),
            'average_per_bag': round(total_time / max(total_scanned, 1), 2),
            'errors': batch_session.errors[:5]  # First 5 errors
        },
        'final_batch': final_result
    })

@batch_scanner.route('/ultra_batch/scanner')
def ultra_batch_scanner_ui():
    """Ultra-fast batch scanner UI"""
    return render_template_string(BATCH_SCANNER_TEMPLATE)

# Ultra-fast batch scanner template
BATCH_SCANNER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Ultra-Fast Batch Scanner</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .scanner-container {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .status-bar {
            background: #e3f2fd;
            border-radius: 5px;
            padding: 15px;
            margin: 20px 0;
        }
        .scan-input {
            width: 100%;
            padding: 15px;
            font-size: 18px;
            border: 2px solid #ddd;
            border-radius: 5px;
            margin: 10px 0;
        }
        .scan-input:focus {
            border-color: #2196f3;
            outline: none;
        }
        .btn {
            width: 100%;
            padding: 15px;
            font-size: 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            margin: 5px 0;
        }
        .btn-primary {
            background: #2196f3;
            color: white;
        }
        .btn-success {
            background: #4caf50;
            color: white;
        }
        .btn-danger {
            background: #f44336;
            color: white;
        }
        .stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin: 20px 0;
        }
        .stat-box {
            background: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #2196f3;
        }
        .stat-label {
            font-size: 12px;
            color: #666;
        }
        .progress-bar {
            width: 100%;
            height: 30px;
            background: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4caf50, #8bc34a);
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        .scan-list {
            max-height: 200px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 10px;
            margin: 10px 0;
        }
        .scan-item {
            padding: 5px;
            border-bottom: 1px solid #eee;
        }
        .error-msg {
            color: #f44336;
            padding: 10px;
            background: #ffebee;
            border-radius: 5px;
            margin: 10px 0;
        }
        .success-msg {
            color: #4caf50;
            padding: 10px;
            background: #e8f5e9;
            border-radius: 5px;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="scanner-container">
        <h1>⚡ Ultra-Fast Batch Scanner</h1>
        
        <div id="parent-section">
            <h3>Step 1: Scan Parent Bag</h3>
            <input type="text" id="parent-input" class="scan-input" 
                   placeholder="Scan or enter parent bag QR (e.g., SB00001)" autofocus>
            <button onclick="startSession()" class="btn btn-primary">Start Batch Session</button>
        </div>
        
        <div id="child-section" style="display:none;">
            <div class="status-bar">
                <strong>Parent:</strong> <span id="parent-qr"></span>
                <div class="progress-bar">
                    <div id="progress-fill" class="progress-fill">0/30</div>
                </div>
            </div>
            
            <h3>Step 2: Rapid Scan Child Bags</h3>
            <input type="text" id="child-input" class="scan-input" 
                   placeholder="Scan child bags rapidly (auto-processes every 10)">
            
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-value" id="scanned-count">0</div>
                    <div class="stat-label">Scanned</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="pending-count">0</div>
                    <div class="stat-label">Pending</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="time-elapsed">0s</div>
                    <div class="stat-label">Time</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="scan-rate">0/min</div>
                    <div class="stat-label">Rate</div>
                </div>
            </div>
            
            <button onclick="processBatch()" class="btn btn-success">Process Pending Batch</button>
            <button onclick="completeSession()" class="btn btn-danger">Complete Session</button>
            
            <div id="recent-scans" class="scan-list" style="display:none;">
                <strong>Recent Scans:</strong>
                <div id="scan-items"></div>
            </div>
        </div>
        
        <div id="messages"></div>
    </div>
    
    <script>
        let sessionId = null;
        let startTime = null;
        let scannedCount = 0;
        let pendingCount = 0;
        let recentScans = [];
        
        // Auto-focus and handle Enter key
        document.getElementById('parent-input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                startSession();
            }
        });
        
        function startSession() {
            const parentQr = document.getElementById('parent-input').value.trim();
            if (!parentQr) {
                showError('Please scan or enter a parent bag QR code');
                return;
            }
            
            fetch('/ultra_batch/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({parent_qr: parentQr})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    sessionId = data.session_id;
                    startTime = Date.now();
                    document.getElementById('parent-qr').textContent = data.parent_qr;
                    document.getElementById('parent-section').style.display = 'none';
                    document.getElementById('child-section').style.display = 'block';
                    document.getElementById('child-input').focus();
                    
                    if (data.existing_count > 0) {
                        scannedCount = data.existing_count;
                        updateStats();
                        showSuccess(`Parent ${data.parent_qr} ready. ${data.existing_count} children already linked.`);
                    } else {
                        showSuccess(`Session started for parent ${data.parent_qr}`);
                    }
                    
                    // Start timer
                    setInterval(updateTimer, 1000);
                    
                    // Setup child scanner
                    setupChildScanner();
                } else {
                    showError(data.message);
                }
            });
        }
        
        function setupChildScanner() {
            const input = document.getElementById('child-input');
            
            // Handle rapid scanning
            input.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    const qr = input.value.trim();
                    if (qr) {
                        scanChild(qr);
                        input.value = '';
                    }
                }
            });
            
            // Handle paste for multiple QRs
            input.addEventListener('paste', function(e) {
                setTimeout(() => {
                    const text = input.value;
                    const qrs = text.split(/[\\n,;\\s]+/).filter(q => q.trim());
                    if (qrs.length > 1) {
                        scanMultiple(qrs);
                        input.value = '';
                    }
                }, 10);
            });
        }
        
        function scanChild(qr) {
            fetch('/ultra_batch/scan', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({qr_codes: [qr]})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    pendingCount = data.pending;
                    
                    if (data.auto_processed) {
                        scannedCount = data.total_scanned;
                        pendingCount = 0;
                        showSuccess(`Auto-processed batch: ${data.batch_result.processed} linked`);
                    }
                    
                    if (data.duplicates > 0) {
                        showError(`${qr} already scanned`);
                    } else {
                        recentScans.unshift(qr);
                        updateRecentScans();
                    }
                    
                    updateStats();
                }
            });
        }
        
        function scanMultiple(qrs) {
            fetch('/ultra_batch/scan', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({qr_codes: qrs})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    pendingCount = data.pending;
                    scannedCount = data.total_scanned;
                    showSuccess(`Added ${data.added} bags to batch`);
                    
                    if (data.auto_processed) {
                        showSuccess(`Auto-processed: ${data.batch_result.processed} linked`);
                    }
                    
                    updateStats();
                }
            });
        }
        
        function processBatch() {
            fetch('/ultra_batch/process', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    scannedCount = data.total_scanned;
                    pendingCount = 0;
                    showSuccess(`Batch processed: ${data.result.processed} bags linked in ${data.result.time_ms}ms`);
                    updateStats();
                }
            });
        }
        
        function completeSession() {
            if (!confirm('Complete scanning session?')) return;
            
            fetch('/ultra_batch/complete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    const summary = data.summary;
                    showSuccess(`
                        Session Complete!
                        Parent: ${summary.parent_qr}
                        Total Scanned: ${summary.total_scanned} bags
                        Time: ${summary.total_time_seconds} seconds
                        Average: ${summary.average_per_bag}s per bag
                    `);
                    
                    setTimeout(() => {
                        window.location.href = '/dashboard';
                    }, 3000);
                }
            });
        }
        
        function updateStats() {
            document.getElementById('scanned-count').textContent = scannedCount;
            document.getElementById('pending-count').textContent = pendingCount;
            
            // Update progress bar
            const progress = Math.min((scannedCount / 30) * 100, 100);
            document.getElementById('progress-fill').style.width = progress + '%';
            document.getElementById('progress-fill').textContent = scannedCount + '/30';
        }
        
        function updateTimer() {
            if (!startTime) return;
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            document.getElementById('time-elapsed').textContent = elapsed + 's';
            
            // Calculate scan rate
            if (elapsed > 0 && scannedCount > 0) {
                const rate = Math.round((scannedCount / elapsed) * 60);
                document.getElementById('scan-rate').textContent = rate + '/min';
            }
        }
        
        function updateRecentScans() {
            if (recentScans.length > 0) {
                document.getElementById('recent-scans').style.display = 'block';
                const html = recentScans.slice(0, 10).map(qr => 
                    '<div class="scan-item">' + qr + '</div>'
                ).join('');
                document.getElementById('scan-items').innerHTML = html;
            }
        }
        
        function showError(msg) {
            showMessage(msg, 'error');
        }
        
        function showSuccess(msg) {
            showMessage(msg, 'success');
        }
        
        function showMessage(msg, type) {
            const div = document.createElement('div');
            div.className = type === 'error' ? 'error-msg' : 'success-msg';
            div.textContent = msg;
            document.getElementById('messages').appendChild(div);
            setTimeout(() => div.remove(), 5000);
        }
    </script>
</body>
</html>
"""

def register_batch_scanner(app):
    """Register the batch scanner blueprint with the Flask app"""
    app.register_blueprint(batch_scanner)
    logger.info("Ultra-fast batch scanner registered")
    return batch_scanner
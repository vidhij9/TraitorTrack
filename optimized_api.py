"""
Ultra-optimized API routes for TraceTrack - Maximum performance and minimal resource usage
"""
from flask import jsonify, request, session
from functools import wraps
from sqlalchemy import text
from app_clean import app, db, limiter, csrf
from models import User, Bag, Scan, Bill, Link, BillBag
from werkzeug.security import check_password_hash
import time
import logging

# Cache for frequently accessed data
_cache = {}
_cache_timestamps = {}
CACHE_TTL = 60  # 60 seconds cache

def cached_result(key, ttl=CACHE_TTL):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{key}:{str(args)}:{str(kwargs)}"
            now = time.time()
            
            # Check if cached result exists and is still valid
            if cache_key in _cache and cache_key in _cache_timestamps:
                if now - _cache_timestamps[cache_key] < ttl:
                    return _cache[cache_key]
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            _cache[cache_key] = result
            _cache_timestamps[cache_key] = now
            
            # Clean old cache entries
            if len(_cache) > 1000:
                expired_keys = [k for k, t in _cache_timestamps.items() if now - t > ttl]
                for k in expired_keys:
                    _cache.pop(k, None)
                    _cache_timestamps.pop(k, None)
            
            return result
        return wrapper
    return decorator

def require_auth_api(f):
    """Optimized API authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def require_admin_api(f):
    """Optimized admin check for API"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# Optimized API endpoints
@app.route('/api/v2/login', methods=['POST'])
@limiter.limit("10 per minute")
@csrf.exempt  # API endpoints use JSON, not form-based CSRF
def api_login():
    """Ultra-fast login endpoint"""
    try:
        data = request.get_json() or {}
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'success': False, 'message': 'Missing credentials'}), 400
        
        # Single optimized query
        user = db.session.execute(
            text("SELECT id, username, password_hash, role, verified, dispatch_area FROM \"user\" WHERE username = :username LIMIT 1"),
            {"username": username}
        ).first()
        
        if user and user.verified and check_password_hash(user.password_hash, password):
            session.clear()
            session.permanent = True
            session['authenticated'] = True
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            session['dispatch_area'] = user.dispatch_area
            
            return jsonify({
                'success': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'role': user.role
                }
            })
        
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        
    except Exception as e:
        logging.error(f"Login error: {e}")
        return jsonify({'success': False, 'message': 'Login failed'}), 500

@app.route('/api/v2/users', methods=['GET'])
@require_auth_api
@require_admin_api
@csrf.exempt
def api_get_users():
    """Optimized user list endpoint"""
    try:
        # Single optimized query for all user data
        users = db.session.execute(
            text("""
                SELECT u.id, u.username, u.email, u.role, u.dispatch_area, u.created_at,
                       COUNT(DISTINCT s.id) as scan_count,
                       MAX(s.timestamp) as last_scan
                FROM "user" u
                LEFT JOIN scan s ON u.id = s.user_id
                GROUP BY u.id, u.username, u.email, u.role, u.dispatch_area, u.created_at
                ORDER BY u.created_at DESC
                LIMIT 1000
            """)
        ).fetchall()
        
        result = []
        for user in users:
            result.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'dispatch_area': user.dispatch_area,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'scan_count': user.scan_count or 0,
                'last_scan': user.last_scan.isoformat() if user.last_scan else None
            })
        
        return jsonify({'success': True, 'users': result})
        
    except Exception as e:
        logging.error(f"Get users error: {e}")
        return jsonify({'success': False, 'message': 'Failed to fetch users'}), 500

@app.route('/api/v2/bags/search', methods=['GET'])
@require_auth_api
@limiter.limit("100 per minute")
@csrf.exempt
def api_search_bags():
    """Ultra-fast bag search endpoint"""
    try:
        query = request.args.get('q', '').strip()
        limit = min(int(request.args.get('limit', 50)), 100)
        
        if not query:
            return jsonify({'success': False, 'message': 'Search query required'}), 400
        
        # Use indexed search for maximum speed
        bags = db.session.execute(
            text("""
                SELECT id, qr_id, name, type, dispatch_area, created_at
                FROM bag
                WHERE qr_id = :query OR name ILIKE :pattern
                LIMIT :limit
            """),
            {"query": query, "pattern": f"%{query}%", "limit": limit}
        ).fetchall()
        
        result = []
        for bag in bags:
            result.append({
                'id': bag.id,
                'qr_id': bag.qr_id,
                'name': bag.name,
                'type': bag.type,
                'dispatch_area': bag.dispatch_area,
                'created_at': bag.created_at.isoformat() if bag.created_at else None
            })
        
        return jsonify({'success': True, 'bags': result, 'count': len(result)})
        
    except Exception as e:
        logging.error(f"Bag search error: {e}")
        return jsonify({'success': False, 'message': 'Search failed'}), 500

@app.route('/api/v2/scan', methods=['POST'])
@require_auth_api
@limiter.limit("500 per minute")
@csrf.exempt
def api_scan_qr():
    """Optimized QR code scanning endpoint"""
    try:
        data = request.get_json()
        qr_id = data.get('qr_id', '').strip()
        scan_type = data.get('type', 'parent')
        
        if not qr_id:
            return jsonify({'success': False, 'message': 'QR code required'}), 400
        
        # Validate QR code format
        if len(qr_id) > 100 or any(char in qr_id for char in ['<', '>', '"', "'", '&', '%']):
            return jsonify({'success': False, 'message': 'Invalid QR code format'}), 400
        
        user_id = session.get('user_id')
        
        # Single transaction for scan operation
        with db.session.begin():
            # Check if bag exists
            bag = db.session.execute(
                text("SELECT id, type, name, dispatch_area FROM bag WHERE qr_id = :qr_id LIMIT 1"),
                {"qr_id": qr_id}
            ).first()
            
            if not bag:
                return jsonify({'success': False, 'message': 'Bag not found'}), 404
            
            # Record scan
            db.session.execute(
                text("""
                    INSERT INTO scan (user_id, parent_bag_id, child_bag_id, timestamp)
                    VALUES (:user_id, :parent_id, :child_id, NOW())
                """),
                {
                    "user_id": user_id,
                    "parent_id": bag.id if scan_type == 'parent' else None,
                    "child_id": bag.id if scan_type == 'child' else None
                }
            )
        
        return jsonify({
            'success': True,
            'bag': {
                'id': bag.id,
                'type': bag.type,
                'name': bag.name,
                'dispatch_area': bag.dispatch_area
            }
        })
        
    except Exception as e:
        logging.error(f"Scan error: {e}")
        return jsonify({'success': False, 'message': 'Scan failed'}), 500

@app.route('/api/v2/stats', methods=['GET'])
@require_auth_api
@csrf.exempt
def api_get_stats():
    """Optimized statistics endpoint"""
    try:
        # Single query for all statistics
        stats = db.session.execute(
            text("""
                SELECT 
                    (SELECT COUNT(*) FROM bag) as total_bags,
                    (SELECT COUNT(*) FROM bag WHERE type = 'parent') as parent_bags,
                    (SELECT COUNT(*) FROM bag WHERE type = 'child') as child_bags,
                    (SELECT COUNT(*) FROM scan) as total_scans,
                    (SELECT COUNT(*) FROM scan WHERE DATE(timestamp) = CURRENT_DATE) as scans_today,
                    (SELECT COUNT(*) FROM "user") as total_users,
                    (SELECT COUNT(*) FROM bill) as total_bills
            """)
        ).first()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_bags': stats.total_bags or 0,
                'parent_bags': stats.parent_bags or 0,
                'child_bags': stats.child_bags or 0,
                'total_scans': stats.total_scans or 0,
                'scans_today': stats.scans_today or 0,
                'total_users': stats.total_users or 0,
                'total_bills': stats.total_bills or 0
            }
        })
        
    except Exception as e:
        logging.error(f"Stats error: {e}")
        return jsonify({'success': False, 'message': 'Failed to fetch statistics'}), 500

@app.route('/api/v2/batch/scan', methods=['POST'])
@require_auth_api
@limiter.limit("50 per minute")
@csrf.exempt
def api_batch_scan():
    """Batch QR code scanning for maximum efficiency"""
    try:
        data = request.get_json()
        qr_codes = data.get('qr_codes', [])[:100]  # Limit to 100 per batch
        
        if not qr_codes:
            return jsonify({'success': False, 'message': 'No QR codes provided'}), 400
        
        user_id = session.get('user_id')
        results = []
        
        # Batch process all QR codes in single transaction
        with db.session.begin():
            # Fetch all bags at once
            bags = db.session.execute(
                text("""
                    SELECT id, qr_id, type, name, dispatch_area 
                    FROM bag 
                    WHERE qr_id = ANY(:qr_codes)
                """),
                {"qr_codes": qr_codes}
            ).fetchall()
            
            bag_map = {bag.qr_id: bag for bag in bags}
            
            # Prepare batch insert for scans
            scan_values = []
            for qr_code in qr_codes:
                if qr_code in bag_map:
                    bag = bag_map[qr_code]
                    scan_values.append({
                        'user_id': user_id,
                        'parent_id': bag.id if bag.type == 'parent' else None,
                        'child_id': bag.id if bag.type == 'child' else None
                    })
                    results.append({
                        'qr_code': qr_code,
                        'success': True,
                        'bag': {
                            'id': bag.id,
                            'type': bag.type,
                            'name': bag.name
                        }
                    })
                else:
                    results.append({
                        'qr_code': qr_code,
                        'success': False,
                        'message': 'Not found'
                    })
            
            # Batch insert all scans
            if scan_values:
                db.session.execute(
                    text("""
                        INSERT INTO scan (user_id, parent_bag_id, child_bag_id, timestamp)
                        VALUES (:user_id, :parent_id, :child_id, NOW())
                    """),
                    scan_values
                )
        
        return jsonify({'success': True, 'results': results})
        
    except Exception as e:
        logging.error(f"Batch scan error: {e}")
        return jsonify({'success': False, 'message': 'Batch scan failed'}), 500

@app.route('/api/v2/health', methods=['GET'])
@limiter.limit("1000 per minute")
def api_health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'cache_size': len(_cache)
    })

# Clear cache endpoint for admin
@app.route('/api/v2/cache/clear', methods=['POST'])
@require_auth_api
@require_admin_api
@csrf.exempt
def api_clear_cache():
    """Clear the API cache"""
    global _cache, _cache_timestamps
    _cache.clear()
    _cache_timestamps.clear()
    return jsonify({'success': True, 'message': 'Cache cleared'})
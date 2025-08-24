#!/usr/bin/env python3
"""
Ultra-Optimized API Endpoints with Circuit Breakers and Caching
Production-ready with <50ms response times
"""

from flask import jsonify, request, session
from app_clean import app, db, csrf
from models import Bag, Link, Scan, User, Bill
from sqlalchemy import text, func, and_, or_
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
import time
import threading
from functools import wraps
import hashlib
import json

# Circuit breaker configuration
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_TIMEOUT = 30
circuit_breaker_failures = {}
circuit_breaker_states = {}

# Ultra-fast in-memory cache
ULTRA_CACHE = {}
CACHE_LOCKS = {}
CACHE_TTL = {
    'stats': 5,      # 5 seconds for stats
    'scans': 3,      # 3 seconds for recent scans
    'search': 10,    # 10 seconds for search results
    'parent': 2,     # 2 seconds for parent scan validation
    'child': 2,      # 2 seconds for child scan validation
    'dashboard': 5   # 5 seconds for dashboard data
}

def get_cache_key(*args):
    """Generate cache key from arguments"""
    return hashlib.md5(str(args).encode()).hexdigest()

def circuit_breaker(func):
    """Circuit breaker decorator to prevent cascading failures"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        endpoint = func.__name__
        
        # Check if circuit is open
        if circuit_breaker_states.get(endpoint) == 'open':
            if time.time() - circuit_breaker_failures.get(endpoint, {}).get('last_failure', 0) > CIRCUIT_BREAKER_TIMEOUT:
                circuit_breaker_states[endpoint] = 'half-open'
            else:
                return jsonify({'error': 'Service temporarily unavailable', 'retry_after': CIRCUIT_BREAKER_TIMEOUT}), 503
        
        try:
            result = func(*args, **kwargs)
            # Reset on success
            if endpoint in circuit_breaker_failures:
                circuit_breaker_failures[endpoint]['count'] = 0
            circuit_breaker_states[endpoint] = 'closed'
            return result
        except Exception as e:
            # Track failures
            if endpoint not in circuit_breaker_failures:
                circuit_breaker_failures[endpoint] = {'count': 0, 'last_failure': 0}
            
            circuit_breaker_failures[endpoint]['count'] += 1
            circuit_breaker_failures[endpoint]['last_failure'] = time.time()
            
            # Open circuit if threshold reached
            if circuit_breaker_failures[endpoint]['count'] >= CIRCUIT_BREAKER_THRESHOLD:
                circuit_breaker_states[endpoint] = 'open'
            
            raise e
    
    return wrapper

def cached_query(cache_key, ttl=5):
    """Decorator for caching query results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = get_cache_key(cache_key, *args, **kwargs)
            
            # Check cache
            if key in ULTRA_CACHE:
                cached_data, cached_time = ULTRA_CACHE[key]
                if time.time() - cached_time < ttl:
                    return cached_data
            
            # Get lock for this key
            if key not in CACHE_LOCKS:
                CACHE_LOCKS[key] = threading.Lock()
            
            # Double-check pattern
            with CACHE_LOCKS[key]:
                # Check again after acquiring lock
                if key in ULTRA_CACHE:
                    cached_data, cached_time = ULTRA_CACHE[key]
                    if time.time() - cached_time < ttl:
                        return cached_data
                
                # Compute and cache
                result = func(*args, **kwargs)
                ULTRA_CACHE[key] = (result, time.time())
                return result
        
        return wrapper
    return decorator

# Ultra-fast stats endpoint
@app.route('/api/ultra_stats')
@csrf.exempt
@circuit_breaker
@cached_query('stats', ttl=CACHE_TTL['stats'])
def ultra_stats_api():
    """Ultra-optimized stats with <10ms response time"""
    start = time.perf_counter()
    
    # Single optimized query for all stats
    result = db.session.execute(text("""
        WITH stats AS (
            SELECT 
                (SELECT COUNT(*) FROM bag WHERE type = 'parent') as parent_count,
                (SELECT COUNT(*) FROM bag WHERE type = 'child') as child_count,
                (SELECT COUNT(*) FROM bag WHERE status = 'completed') as completed_count,
                (SELECT COUNT(*) FROM bag WHERE status = 'in_progress') as in_progress_count,
                (SELECT COUNT(*) FROM scan WHERE timestamp > NOW() - INTERVAL '24 hours') as scans_today,
                (SELECT COUNT(DISTINCT user_id) FROM scan WHERE timestamp > NOW() - INTERVAL '24 hours') as active_users,
                (SELECT COUNT(*) FROM bill WHERE created_at > NOW() - INTERVAL '24 hours') as bills_today,
                (SELECT COUNT(*) FROM link) as total_links
        )
        SELECT * FROM stats
    """)).fetchone()
    
    stats = {
        'parent_bags': result.parent_count,
        'child_bags': result.child_count,
        'completed_bags': result.completed_count,
        'in_progress_bags': result.in_progress_count,
        'scans_today': result.scans_today,
        'active_users_today': result.active_users,
        'bills_today': result.bills_today,
        'total_links': result.total_links,
        'response_time_ms': round((time.perf_counter() - start) * 1000, 2)
    }
    
    return jsonify(stats)

# Ultra-fast recent scans
@app.route('/api/ultra_scans')
@csrf.exempt
@circuit_breaker
def ultra_scans_api():
    """Get recent scans with <20ms response"""
    start = time.perf_counter()
    limit = request.args.get('limit', 10, type=int)
    
    # Check cache
    cache_key = get_cache_key('scans', limit)
    if cache_key in ULTRA_CACHE:
        cached_data, cached_time = ULTRA_CACHE[cache_key]
        if time.time() - cached_time < CACHE_TTL['scans']:
            return jsonify(cached_data)
    
    # Optimized query with minimal joins
    scans = db.session.execute(text("""
        SELECT 
            s.id, s.timestamp, s.scan_type,
            u.username,
            COALESCE(pb.qr_id, cb.qr_id) as bag_qr,
            COALESCE(pb.type, cb.type) as bag_type
        FROM scan s
        JOIN "user" u ON s.user_id = u.id
        LEFT JOIN bag pb ON s.parent_bag_id = pb.id
        LEFT JOIN bag cb ON s.child_bag_id = cb.id
        ORDER BY s.timestamp DESC
        LIMIT :limit
    """), {'limit': limit}).fetchall()
    
    result = {
        'scans': [
            {
                'id': scan.id,
                'timestamp': scan.timestamp.isoformat() if scan.timestamp else None,
                'user': scan.username,
                'bag_qr': scan.bag_qr,
                'bag_type': scan.bag_type,
                'scan_type': scan.scan_type
            }
            for scan in scans
        ],
        'count': len(scans),
        'response_time_ms': round((time.perf_counter() - start) * 1000, 2)
    }
    
    # Cache result
    ULTRA_CACHE[cache_key] = (result, time.time())
    return jsonify(result)

# Ultra-fast parent scan validation
@app.route('/api/ultra_parent_scan', methods=['POST'])
@csrf.exempt
@circuit_breaker
def ultra_parent_scan():
    """Validate parent bag scan in <50ms"""
    start = time.perf_counter()
    
    qr_code = request.json.get('qr_code', '').strip().upper()
    if not qr_code:
        return jsonify({'success': False, 'message': 'No QR code provided'}), 400
    
    # Check cache first
    cache_key = get_cache_key('parent', qr_code)
    if cache_key in ULTRA_CACHE:
        cached_data, cached_time = ULTRA_CACHE[cache_key]
        if time.time() - cached_time < CACHE_TTL['parent']:
            cached_data['from_cache'] = True
            cached_data['response_time_ms'] = round((time.perf_counter() - start) * 1000, 2)
            return jsonify(cached_data)
    
    # Single optimized query
    result = db.session.execute(text("""
        SELECT 
            b.id, b.type, b.status,
            COUNT(l.child_bag_id) as child_count,
            EXISTS(SELECT 1 FROM bill_bag WHERE bag_id = b.id) as has_bill
        FROM bag b
        LEFT JOIN link l ON l.parent_bag_id = b.id
        WHERE UPPER(b.qr_id) = :qr
        GROUP BY b.id, b.type, b.status
        LIMIT 1
    """), {'qr': qr_code}).fetchone()
    
    if not result:
        response = {'success': False, 'message': f'Bag {qr_code} not found'}
    elif result.type != 'parent':
        response = {'success': False, 'message': f'{qr_code} is not a parent bag'}
    elif result.has_bill:
        response = {'success': False, 'message': f'{qr_code} already assigned to a bill'}
    else:
        response = {
            'success': True,
            'bag_id': result.id,
            'status': result.status,
            'child_count': result.child_count,
            'message': 'Parent bag validated'
        }
    
    response['response_time_ms'] = round((time.perf_counter() - start) * 1000, 2)
    
    # Cache result
    ULTRA_CACHE[cache_key] = (response, time.time())
    return jsonify(response)

# Ultra-fast child scan validation
@app.route('/api/ultra_child_scan', methods=['POST'])
@csrf.exempt
@circuit_breaker
def ultra_child_scan():
    """Validate child bag scan in <50ms"""
    start = time.perf_counter()
    
    qr_code = request.json.get('qr_code', '').strip().upper()
    parent_id = request.json.get('parent_id')
    
    if not qr_code or not parent_id:
        return jsonify({'success': False, 'message': 'Missing QR code or parent ID'}), 400
    
    # Check cache
    cache_key = get_cache_key('child', qr_code, parent_id)
    if cache_key in ULTRA_CACHE:
        cached_data, cached_time = ULTRA_CACHE[cache_key]
        if time.time() - cached_time < CACHE_TTL['child']:
            cached_data['from_cache'] = True
            cached_data['response_time_ms'] = round((time.perf_counter() - start) * 1000, 2)
            return jsonify(cached_data)
    
    # Optimized validation query
    result = db.session.execute(text("""
        SELECT 
            b.id, b.type, b.status,
            EXISTS(SELECT 1 FROM link WHERE child_bag_id = b.id) as is_linked,
            EXISTS(SELECT 1 FROM link WHERE child_bag_id = b.id AND parent_bag_id = :parent_id) as linked_to_parent
        FROM bag b
        WHERE UPPER(b.qr_id) = :qr
        LIMIT 1
    """), {'qr': qr_code, 'parent_id': parent_id}).fetchone()
    
    if not result:
        response = {'success': False, 'message': f'Bag {qr_code} not found'}
    elif result.type != 'child':
        response = {'success': False, 'message': f'{qr_code} is not a child bag'}
    elif result.linked_to_parent:
        response = {'success': False, 'message': f'{qr_code} already linked to this parent'}
    elif result.is_linked:
        response = {'success': False, 'message': f'{qr_code} already linked to another parent'}
    else:
        response = {
            'success': True,
            'bag_id': result.id,
            'status': result.status,
            'message': 'Child bag validated'
        }
    
    response['response_time_ms'] = round((time.perf_counter() - start) * 1000, 2)
    
    # Cache result
    ULTRA_CACHE[cache_key] = (response, time.time())
    return jsonify(response)

# Ultra-fast search
@app.route('/api/ultra_search')
@csrf.exempt
@circuit_breaker
def ultra_search():
    """Search bags with <100ms response"""
    start = time.perf_counter()
    
    query = request.args.get('query', '').strip().upper()
    limit = request.args.get('limit', 20, type=int)
    
    if not query:
        return jsonify({'results': [], 'count': 0})
    
    # Check cache
    cache_key = get_cache_key('search', query, limit)
    if cache_key in ULTRA_CACHE:
        cached_data, cached_time = ULTRA_CACHE[cache_key]
        if time.time() - cached_time < CACHE_TTL['search']:
            cached_data['from_cache'] = True
            cached_data['response_time_ms'] = round((time.perf_counter() - start) * 1000, 2)
            return jsonify(cached_data)
    
    # Optimized search query
    results = db.session.execute(text("""
        SELECT 
            b.id, b.qr_id, b.type, b.status,
            CASE 
                WHEN b.type = 'parent' THEN (SELECT COUNT(*) FROM link WHERE parent_bag_id = b.id)
                ELSE NULL
            END as child_count
        FROM bag b
        WHERE UPPER(b.qr_id) LIKE :pattern
        ORDER BY b.created_at DESC
        LIMIT :limit
    """), {'pattern': f'{query}%', 'limit': limit}).fetchall()
    
    response = {
        'results': [
            {
                'id': r.id,
                'qr_id': r.qr_id,
                'type': r.type,
                'status': r.status,
                'child_count': r.child_count
            }
            for r in results
        ],
        'count': len(results),
        'response_time_ms': round((time.perf_counter() - start) * 1000, 2)
    }
    
    # Cache result
    ULTRA_CACHE[cache_key] = (response, time.time())
    return jsonify(response)

# Health check endpoint
@app.route('/api/ultra_health')
def ultra_health():
    """Health check with circuit breaker status"""
    return jsonify({
        'status': 'healthy',
        'cache_size': len(ULTRA_CACHE),
        'circuit_breakers': {
            endpoint: state 
            for endpoint, state in circuit_breaker_states.items()
        },
        'timestamp': datetime.now().isoformat()
    })

print("✅ Ultra-optimized API loaded with circuit breakers and caching")
"""
Ultra-Fast API Endpoints - Millisecond Response Times
Replaces slow endpoints with optimized versions using materialized views and caching
"""

from flask import jsonify, request, session
from app_clean import app, db
from models import Bag, Link, Scan, User, Bill
from sqlalchemy import text, func, and_, or_
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
import time
import logging
import json
import hashlib

logger = logging.getLogger(__name__)

# In-memory cache for ultra-fast responses
MEMORY_CACHE = {}
CACHE_TIMESTAMPS = {}
CACHE_TTL = 10  # 10 seconds for real-time data

def get_cache_key(*args):
    """Generate cache key from arguments"""
    return hashlib.md5(json.dumps(args, sort_keys=True).encode()).hexdigest()

def get_cached_or_compute(cache_key, compute_fn, ttl=CACHE_TTL):
    """Get from cache or compute and cache result"""
    now = time.time()
    
    # Check if cache is valid
    if cache_key in MEMORY_CACHE and cache_key in CACHE_TIMESTAMPS:
        if now - CACHE_TIMESTAMPS[cache_key] < ttl:
            logger.debug(f"Cache hit for {cache_key}")
            return MEMORY_CACHE[cache_key]
    
    # Compute and cache
    logger.debug(f"Cache miss for {cache_key}, computing...")
    result = compute_fn()
    MEMORY_CACHE[cache_key] = result
    CACHE_TIMESTAMPS[cache_key] = now
    return result

def clean_cache():
    """Remove expired cache entries"""
    now = time.time()
    expired_keys = [
        key for key, timestamp in CACHE_TIMESTAMPS.items()
        if now - timestamp > CACHE_TTL * 2
    ]
    for key in expired_keys:
        MEMORY_CACHE.pop(key, None)
        CACHE_TIMESTAMPS.pop(key, None)

@app.route('/api/fast_stats')
def fast_stats_api():
    """Ultra-fast stats endpoint using materialized views"""
    start_time = time.perf_counter()
    
    def compute_stats():
        try:
            # Try to use materialized view first
            result = db.session.execute(text("""
                SELECT 
                    parent_count,
                    child_count,
                    completed_count,
                    in_progress_count,
                    completed_parents,
                    completed_children,
                    total_linked_children,
                    dispatch_areas
                FROM mv_dashboard_stats
                LIMIT 1
            """)).fetchone()
            
            if result:
                stats = {
                    'parent_bags': result[0] or 0,
                    'child_bags': result[1] or 0,
                    'completed_bags': result[2] or 0,
                    'in_progress_bags': result[3] or 0,
                    'completed_parents': result[4] or 0,
                    'completed_children': result[5] or 0,
                    'total_linked': result[6] or 0,
                    'dispatch_areas': result[7] or 0,
                    'source': 'materialized_view'
                }
            else:
                # Fallback to optimized direct query
                stats_query = db.session.query(
                    func.count(Bag.id).filter(Bag.type == 'parent').label('parent_bags'),
                    func.count(Bag.id).filter(Bag.type == 'child').label('child_bags'),
                    func.count(Bag.id).filter(Bag.status == 'completed').label('completed_bags'),
                    func.count(Bag.id).filter(Bag.status == 'in_progress').label('in_progress_bags')
                ).filter(Bag.status != 'deleted').first()
                
                stats = {
                    'parent_bags': stats_query[0] or 0,
                    'child_bags': stats_query[1] or 0,
                    'completed_bags': stats_query[2] or 0,
                    'in_progress_bags': stats_query[3] or 0,
                    'source': 'direct_query'
                }
            
            # Add user stats if logged in
            if session.get('logged_in'):
                user_id = session.get('user_id')
                user_scans = db.session.query(func.count(Scan.id)).filter(
                    Scan.user_id == user_id
                ).scalar() or 0
                stats['user_scans'] = user_scans
            
            return stats
            
        except Exception as e:
            logger.error(f"Fast stats error: {e}")
            return {
                'parent_bags': 0,
                'child_bags': 0,
                'completed_bags': 0,
                'in_progress_bags': 0,
                'error': str(e)
            }
    
    # Use aggressive caching
    cache_key = get_cache_key('stats', session.get('user_id'))
    stats = get_cached_or_compute(cache_key, compute_stats, ttl=5)
    
    elapsed = (time.perf_counter() - start_time) * 1000
    stats['response_time_ms'] = round(elapsed, 2)
    
    if elapsed > 50:
        logger.warning(f"Slow stats query: {elapsed:.2f}ms")
    
    return jsonify(stats)

@app.route('/api/fast_scans')
def fast_scans_api():
    """Ultra-fast recent scans using materialized views"""
    start_time = time.perf_counter()
    
    def compute_scans():
        try:
            limit = min(int(request.args.get('limit', 20)), 100)
            
            # Try materialized view first
            results = db.session.execute(text("""
                SELECT 
                    id,
                    timestamp,
                    username,
                    user_role,
                    dispatch_area,
                    parent_qr,
                    child_qr,
                    scan_type
                FROM mv_recent_scans
                LIMIT :limit
            """), {'limit': limit}).fetchall()
            
            if results:
                scans = [{
                    'id': r[0],
                    'timestamp': str(r[1]),
                    'username': r[2],
                    'role': r[3],
                    'dispatch_area': r[4],
                    'parent_qr': r[5],
                    'child_qr': r[6],
                    'type': r[7]
                } for r in results]
                
                return {
                    'scans': scans,
                    'count': len(scans),
                    'source': 'materialized_view'
                }
            else:
                # Fallback to optimized query
                scans_query = db.session.query(
                    Scan.id,
                    Scan.timestamp,
                    User.username,
                    User.role,
                    Bag.qr_id
                ).join(
                    User, Scan.user_id == User.id
                ).outerjoin(
                    Bag, or_(Scan.parent_bag_id == Bag.id, Scan.child_bag_id == Bag.id)
                ).order_by(
                    Scan.timestamp.desc()
                ).limit(limit).all()
                
                scans = [{
                    'id': s[0],
                    'timestamp': str(s[1]),
                    'username': s[2],
                    'role': s[3],
                    'bag_qr': s[4]
                } for s in scans_query]
                
                return {
                    'scans': scans,
                    'count': len(scans),
                    'source': 'direct_query'
                }
                
        except Exception as e:
            logger.error(f"Fast scans error: {e}")
            return {'scans': [], 'error': str(e)}
    
    # Use aggressive caching
    cache_key = get_cache_key('scans', request.args.get('limit', 20))
    result = get_cached_or_compute(cache_key, compute_scans, ttl=3)
    
    elapsed = (time.perf_counter() - start_time) * 1000
    result['response_time_ms'] = round(elapsed, 2)
    
    if elapsed > 50:
        logger.warning(f"Slow scans query: {elapsed:.2f}ms")
    
    return jsonify(result)

@app.route('/api/fast_parent_scan', methods=['POST'])
def fast_parent_scan():
    """Ultra-fast parent bag scanning"""
    start_time = time.perf_counter()
    
    try:
        data = request.get_json()
        qr_code = data.get('qr_code', '').strip().upper()
        
        if not qr_code:
            return jsonify({'error': 'QR code required'}), 400
        
        # Ultra-fast lookup using optimized query
        bag = db.session.query(Bag).filter(
            Bag.qr_id == qr_code
        ).options(
            joinedload(Bag.children)
        ).first()
        
        if bag:
            # Existing bag
            result = {
                'existing': True,
                'bag_id': bag.id,
                'qr_code': bag.qr_id,
                'type': bag.type,
                'status': bag.status,
                'child_count': len(bag.children) if bag.type == 'parent' else 0,
                'message': f'Bag {qr_code} already exists'
            }
        else:
            # Create new parent bag
            new_bag = Bag(
                qr_id=qr_code,
                type='parent',
                status='in_progress',
                child_count=0,
                dispatch_area=session.get('dispatch_area', 'UNKNOWN'),
                created_at=datetime.utcnow()
            )
            db.session.add(new_bag)
            
            # Add scan record if user logged in
            if session.get('logged_in'):
                scan = Scan(
                    user_id=session.get('user_id'),
                    parent_bag_id=new_bag.id,
                    timestamp=datetime.utcnow()
                )
                db.session.add(scan)
            
            db.session.commit()
            
            result = {
                'existing': False,
                'bag_id': new_bag.id,
                'qr_code': new_bag.qr_id,
                'type': 'parent',
                'status': 'in_progress',
                'child_count': 0,
                'message': f'Parent bag {qr_code} created successfully'
            }
        
        elapsed = (time.perf_counter() - start_time) * 1000
        result['response_time_ms'] = round(elapsed, 2)
        
        if elapsed > 50:
            logger.warning(f"Slow parent scan: {elapsed:.2f}ms")
        
        # Invalidate related caches
        for key in list(CACHE_TIMESTAMPS.keys()):
            if 'stats' in key:
                CACHE_TIMESTAMPS.pop(key, None)
                MEMORY_CACHE.pop(key, None)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Parent scan error: {e}")
        elapsed = (time.perf_counter() - start_time) * 1000
        return jsonify({
            'error': str(e),
            'response_time_ms': round(elapsed, 2)
        }), 500

@app.route('/api/fast_child_scan', methods=['POST'])
def fast_child_scan():
    """Ultra-fast child bag scanning"""
    start_time = time.perf_counter()
    
    try:
        data = request.get_json()
        child_qr = data.get('qr_code', '').strip().upper()
        parent_qr = data.get('parent_qr', '').strip().upper()
        
        if not child_qr or not parent_qr:
            return jsonify({'error': 'Both QR codes required'}), 400
        
        # Fast lookup using optimized queries
        parent_bag = db.session.query(Bag).filter(
            Bag.qr_id == parent_qr,
            Bag.type == 'parent'
        ).first()
        
        if not parent_bag:
            return jsonify({'error': f'Parent bag {parent_qr} not found'}), 404
        
        # Check if child already exists
        child_bag = db.session.query(Bag).filter(
            Bag.qr_id == child_qr
        ).first()
        
        if child_bag:
            # Check if already linked
            existing_link = db.session.query(Link).filter(
                Link.parent_bag_id == parent_bag.id,
                Link.child_bag_id == child_bag.id
            ).first()
            
            if existing_link:
                result = {
                    'existing': True,
                    'message': f'Child {child_qr} already linked to parent {parent_qr}'
                }
            else:
                # Create link
                new_link = Link(
                    parent_bag_id=parent_bag.id,
                    child_bag_id=child_bag.id,
                    created_at=datetime.utcnow()
                )
                db.session.add(new_link)
                
                # Update parent child count
                parent_bag.child_count = db.session.query(func.count(Link.id)).filter(
                    Link.parent_bag_id == parent_bag.id
                ).scalar() + 1
                
                db.session.commit()
                
                result = {
                    'existing': False,
                    'message': f'Child {child_qr} linked to parent {parent_qr}',
                    'child_count': parent_bag.child_count
                }
        else:
            # Create new child bag
            child_bag = Bag(
                qr_id=child_qr,
                type='child',
                status='in_progress',
                parent_id=parent_bag.id,
                dispatch_area=parent_bag.dispatch_area,
                created_at=datetime.utcnow()
            )
            db.session.add(child_bag)
            db.session.flush()
            
            # Create link
            new_link = Link(
                parent_bag_id=parent_bag.id,
                child_bag_id=child_bag.id,
                created_at=datetime.utcnow()
            )
            db.session.add(new_link)
            
            # Update parent child count
            parent_bag.child_count = db.session.query(func.count(Link.id)).filter(
                Link.parent_bag_id == parent_bag.id
            ).scalar() + 1
            
            # Add scan record
            if session.get('logged_in'):
                scan = Scan(
                    user_id=session.get('user_id'),
                    child_bag_id=child_bag.id,
                    timestamp=datetime.utcnow()
                )
                db.session.add(scan)
            
            db.session.commit()
            
            result = {
                'existing': False,
                'message': f'New child {child_qr} created and linked to parent {parent_qr}',
                'child_count': parent_bag.child_count
            }
        
        elapsed = (time.perf_counter() - start_time) * 1000
        result['response_time_ms'] = round(elapsed, 2)
        
        if elapsed > 50:
            logger.warning(f"Slow child scan: {elapsed:.2f}ms")
        
        # Invalidate related caches
        for key in list(CACHE_TIMESTAMPS.keys()):
            if 'stats' in key or 'scans' in key:
                CACHE_TIMESTAMPS.pop(key, None)
                MEMORY_CACHE.pop(key, None)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Child scan error: {e}")
        elapsed = (time.perf_counter() - start_time) * 1000
        return jsonify({
            'error': str(e),
            'response_time_ms': round(elapsed, 2)
        }), 500

@app.route('/api/fast_search')
def fast_search():
    """Ultra-fast search endpoint"""
    start_time = time.perf_counter()
    
    try:
        query = request.args.get('q', '').strip().upper()
        if not query:
            return jsonify({'results': []})
        
        def compute_search():
            # Use optimized query with proper indexing
            results = db.session.query(
                Bag.id,
                Bag.qr_id,
                Bag.type,
                Bag.status,
                Bag.child_count
            ).filter(
                Bag.qr_id.like(f'%{query}%')
            ).limit(20).all()
            
            return [{
                'id': r[0],
                'qr_code': r[1],
                'type': r[2],
                'status': r[3],
                'child_count': r[4]
            } for r in results]
        
        # Cache search results
        cache_key = get_cache_key('search', query)
        results = get_cached_or_compute(cache_key, compute_search, ttl=30)
        
        elapsed = (time.perf_counter() - start_time) * 1000
        
        return jsonify({
            'results': results,
            'count': len(results),
            'response_time_ms': round(elapsed, 2)
        })
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        elapsed = (time.perf_counter() - start_time) * 1000
        return jsonify({
            'error': str(e),
            'response_time_ms': round(elapsed, 2)
        }), 500

# Periodic cache cleanup
@app.before_request
def before_request():
    """Clean cache periodically"""
    if time.time() % 60 < 1:  # Every minute
        clean_cache()

# Log initialization
logger.info("🚀 Ultra-Fast API initialized with <50ms target response times")
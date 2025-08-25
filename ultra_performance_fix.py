#!/usr/bin/env python3
"""
Ultra Performance Fix - Implement aggressive caching and query optimization
Targets: <100ms response time for all endpoints
"""

import redis
import json
import hashlib
import time
from functools import wraps
from flask import g, request
import logging

logger = logging.getLogger(__name__)

# Redis configuration for ultra-fast caching
redis_pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    db=0,
    max_connections=100,
    socket_connect_timeout=2,
    socket_timeout=2,
    socket_keepalive=True,
    socket_keepalive_options={
        1: 1,  # TCP_KEEPIDLE
        2: 1,  # TCP_KEEPINTVL
        3: 3,  # TCP_KEEPCNT
    }
)

try:
    redis_client = redis.Redis(connection_pool=redis_pool)
    redis_client.ping()
    REDIS_AVAILABLE = True
    logger.info("✅ Redis connected for ultra-fast caching")
except:
    REDIS_AVAILABLE = False
    logger.warning("⚠️ Redis not available - using in-memory cache")
    # Fallback to in-memory cache
    MEMORY_CACHE = {}

def ultra_cache(ttl=60):
    """Ultra-fast caching decorator with millisecond precision"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"ultra:{func.__name__}:{hashlib.md5(str(args).encode() + str(kwargs).encode()).hexdigest()}"
            
            # Try cache first
            if REDIS_AVAILABLE:
                try:
                    cached = redis_client.get(cache_key)
                    if cached:
                        return json.loads(cached)
                except:
                    pass
            else:
                # Use in-memory cache
                if cache_key in MEMORY_CACHE:
                    cached_time, cached_data = MEMORY_CACHE[cache_key]
                    if time.time() - cached_time < ttl:
                        return cached_data
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            if REDIS_AVAILABLE:
                try:
                    redis_client.setex(cache_key, ttl, json.dumps(result))
                except:
                    pass
            else:
                MEMORY_CACHE[cache_key] = (time.time(), result)
                # Clean old entries
                if len(MEMORY_CACHE) > 1000:
                    oldest = sorted(MEMORY_CACHE.items(), key=lambda x: x[1][0])[:100]
                    for k, _ in oldest:
                        del MEMORY_CACHE[k]
            
            return result
        return wrapper
    return decorator

def optimize_stats_endpoint(app, db):
    """Optimize the /api/stats endpoint for <50ms response"""
    
    @ultra_cache(ttl=30)  # Cache for 30 seconds
    def get_cached_stats():
        """Get dashboard stats with aggressive caching"""
        from sqlalchemy import text
        
        # Use raw SQL for maximum speed
        query = text("""
            SELECT 
                (SELECT COUNT(*) FROM scan WHERE timestamp > CURRENT_DATE - INTERVAL '7 days') as recent_scans,
                (SELECT COUNT(*) FROM bag WHERE type = 'parent') as parent_count,
                (SELECT COUNT(*) FROM bag WHERE type = 'child') as child_count,
                (SELECT COUNT(*) FROM bill) as bill_count,
                (SELECT COUNT(DISTINCT user_id) FROM scan WHERE timestamp > CURRENT_DATE - INTERVAL '1 day') as active_users
        """)
        
        result = db.session.execute(query).first()
        
        return {
            'recent_scans': result[0] or 0,
            'parent_count': result[1] or 0,
            'child_count': result[2] or 0,
            'bill_count': result[3] or 0,
            'active_users': result[4] or 0,
            'cache_timestamp': time.time()
        }
    
    # Replace the slow endpoint
    @app.route('/api/ultra_stats')
    def ultra_stats():
        """Ultra-fast stats endpoint"""
        start_time = time.time()
        stats = get_cached_stats()
        elapsed = (time.time() - start_time) * 1000
        stats['response_time_ms'] = elapsed
        return stats

def optimize_scans_endpoint(app, db):
    """Optimize the /api/scans endpoint for <50ms response"""
    
    @ultra_cache(ttl=10)  # Cache for 10 seconds
    def get_recent_scans(limit=10):
        """Get recent scans with caching"""
        from sqlalchemy import text
        
        query = text("""
            SELECT 
                s.id,
                s.timestamp,
                u.username,
                pb.qr_id as parent_qr,
                cb.qr_id as child_qr
            FROM scan s
            LEFT JOIN "user" u ON s.user_id = u.id
            LEFT JOIN bag pb ON s.parent_bag_id = pb.id
            LEFT JOIN bag cb ON s.child_bag_id = cb.id
            ORDER BY s.timestamp DESC
            LIMIT :limit
        """)
        
        results = db.session.execute(query, {"limit": limit}).fetchall()
        
        scans = []
        for row in results:
            scans.append({
                'id': row[0],
                'timestamp': row[1].isoformat() if row[1] else None,
                'username': row[2],
                'parent_qr': row[3],
                'child_qr': row[4]
            })
        
        return scans
    
    @app.route('/api/ultra_scans')
    def ultra_scans():
        """Ultra-fast recent scans endpoint"""
        start_time = time.time()
        limit = request.args.get('limit', 10, type=int)
        scans = get_recent_scans(limit)
        elapsed = (time.time() - start_time) * 1000
        return {
            'scans': scans,
            'response_time_ms': elapsed
        }

def optimize_child_scan(app, db):
    """Optimize child scan processing for <100ms response"""
    
    @app.route('/process_child_ultra', methods=['POST'])
    def process_child_ultra():
        """Ultra-fast child scan processing"""
        start_time = time.time()
        
        # Get data
        qr_code = request.form.get('qr_id', '').strip()
        parent_qr = request.form.get('parent_qr', '').strip()
        
        if not qr_code or not parent_qr:
            return {'success': False, 'message': 'Missing QR codes'}, 400
        
        # Use raw SQL for speed
        from sqlalchemy import text
        
        try:
            # Check parent exists
            parent_check = text("SELECT id FROM bag WHERE qr_id = :qr AND type = 'parent' LIMIT 1")
            parent = db.session.execute(parent_check, {"qr": parent_qr}).first()
            
            if not parent:
                return {'success': False, 'message': 'Parent bag not found'}, 404
            
            parent_id = parent[0]
            
            # Check if child exists
            child_check = text("SELECT id FROM bag WHERE qr_id = :qr LIMIT 1")
            child = db.session.execute(child_check, {"qr": qr_code}).first()
            
            if child:
                child_id = child[0]
            else:
                # Create child bag
                create_child = text("""
                    INSERT INTO bag (qr_id, type, created_at, updated_at)
                    VALUES (:qr, 'child', NOW(), NOW())
                    RETURNING id
                """)
                child_result = db.session.execute(create_child, {"qr": qr_code})
                child_id = child_result.first()[0]
            
            # Create link
            create_link = text("""
                INSERT INTO link (parent_bag_id, child_bag_id, created_at)
                VALUES (:parent_id, :child_id, NOW())
                ON CONFLICT DO NOTHING
            """)
            db.session.execute(create_link, {"parent_id": parent_id, "child_id": child_id})
            
            # Create scan record
            user_id = g.get('user_id', 1)  # Get from session
            create_scan = text("""
                INSERT INTO scan (user_id, parent_bag_id, child_bag_id, timestamp)
                VALUES (:user_id, :parent_id, :child_id, NOW())
            """)
            db.session.execute(create_scan, {
                "user_id": user_id,
                "parent_id": parent_id,
                "child_id": child_id
            })
            
            db.session.commit()
            
            elapsed = (time.time() - start_time) * 1000
            
            return {
                'success': True,
                'message': f'Child {qr_code} linked to parent {parent_qr}',
                'response_time_ms': elapsed
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ultra scan error: {e}")
            return {'success': False, 'message': 'Processing error'}, 500

def apply_ultra_optimizations(app, db):
    """Apply all ultra-performance optimizations"""
    
    logger.info("Applying ultra-performance optimizations...")
    
    # Optimize endpoints
    optimize_stats_endpoint(app, db)
    optimize_scans_endpoint(app, db)
    optimize_child_scan(app, db)
    
    # Add connection pool warming
    @app.before_first_request
    def warm_connection_pool():
        """Warm up database connection pool"""
        from sqlalchemy import text
        for _ in range(10):
            try:
                db.session.execute(text("SELECT 1"))
            except:
                pass
    
    # Add request optimization
    @app.before_request
    def optimize_request():
        """Optimize each request"""
        g.request_start = time.time()
    
    @app.after_request
    def log_slow_requests(response):
        """Log slow requests"""
        if hasattr(g, 'request_start'):
            elapsed = (time.time() - g.request_start) * 1000
            if elapsed > 100:
                logger.warning(f"Slow request: {request.path} took {elapsed:.0f}ms")
        return response
    
    logger.info("✅ Ultra-performance optimizations applied")
    
    return app

# Export for use in main app
__all__ = ['apply_ultra_optimizations', 'ultra_cache']
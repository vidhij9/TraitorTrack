"""
Optimized Routes with Redis Caching - Target: <100ms response times
"""

from flask import Blueprint, jsonify, request, g
from sqlalchemy import text
from redis_cache_manager import cache, cache_manager, invalidate_cache
import time
import logging

logger = logging.getLogger(__name__)

optimized_bp = Blueprint('optimized', __name__)

@optimized_bp.route('/api/cached/stats')
@cache(ttl=30, prefix="stats")
def cached_stats():
    """Ultra-fast cached dashboard stats"""
    start = time.time()
    
    from app_clean import db
    
    # Optimized single query for all stats
    query = text("""
        WITH stats AS (
            SELECT 
                (SELECT COUNT(*) FROM scan WHERE timestamp > NOW() - INTERVAL '7 days') as recent_scans,
                (SELECT COUNT(*) FROM bag WHERE type = 'parent') as parent_bags,
                (SELECT COUNT(*) FROM bag WHERE type = 'child') as child_bags,
                (SELECT COUNT(*) FROM bill WHERE created_at > NOW() - INTERVAL '30 days') as recent_bills,
                (SELECT COUNT(DISTINCT user_id) FROM scan WHERE timestamp > NOW() - INTERVAL '24 hours') as active_users,
                (SELECT COUNT(*) FROM "user" WHERE is_active = true) as total_users,
                (SELECT COUNT(*) FROM link) as total_links,
                (SELECT COUNT(*) FROM scan WHERE timestamp > NOW() - INTERVAL '1 hour') as hourly_scans
        )
        SELECT * FROM stats
    """)
    
    result = db.session.execute(query).first()
    
    stats = {
        'recent_scans': result[0] or 0,
        'parent_bags': result[1] or 0,
        'child_bags': result[2] or 0,
        'recent_bills': result[3] or 0,
        'active_users': result[4] or 0,
        'total_users': result[5] or 0,
        'total_links': result[6] or 0,
        'hourly_scans': result[7] or 0,
        'response_time_ms': (time.time() - start) * 1000,
        'cached': False
    }
    
    return jsonify(stats)

@optimized_bp.route('/api/cached/recent_scans')
@cache(ttl=10, prefix="scans")
def cached_recent_scans():
    """Cached recent scans with pagination"""
    start = time.time()
    limit = request.args.get('limit', 10, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    from app_clean import db
    
    # Optimized query with minimal joins
    query = text("""
        SELECT 
            s.id,
            s.timestamp,
            u.username,
            pb.qr_id as parent_qr,
            cb.qr_id as child_qr,
            pb.type as parent_type,
            cb.type as child_type
        FROM scan s
        LEFT JOIN "user" u ON s.user_id = u.id
        LEFT JOIN bag pb ON s.parent_bag_id = pb.id
        LEFT JOIN bag cb ON s.child_bag_id = cb.id
        ORDER BY s.timestamp DESC
        LIMIT :limit OFFSET :offset
    """)
    
    results = db.session.execute(query, {
        'limit': min(limit, 100),
        'offset': offset
    }).fetchall()
    
    scans = []
    for row in results:
        scans.append({
            'id': row[0],
            'timestamp': row[1].isoformat() if row[1] else None,
            'username': row[2] or 'Unknown',
            'parent_qr': row[3],
            'child_qr': row[4],
            'parent_type': row[5],
            'child_type': row[6]
        })
    
    return jsonify({
        'scans': scans,
        'count': len(scans),
        'response_time_ms': (time.time() - start) * 1000,
        'cached': False
    })

@optimized_bp.route('/api/cached/bags')
@cache(ttl=60, prefix="bags")
def cached_bags():
    """Cached bag listing with filtering"""
    start = time.time()
    bag_type = request.args.get('type', None)
    limit = request.args.get('limit', 100, type=int)
    
    from app_clean import db
    
    if bag_type:
        query = text("""
            SELECT id, qr_id, type, created_at, updated_at
            FROM bag
            WHERE type = :bag_type
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        params = {'bag_type': bag_type, 'limit': min(limit, 1000)}
    else:
        query = text("""
            SELECT id, qr_id, type, created_at, updated_at
            FROM bag
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        params = {'limit': min(limit, 1000)}
    
    results = db.session.execute(query, params).fetchall()
    
    bags = []
    for row in results:
        bags.append({
            'id': row[0],
            'qr_id': row[1],
            'type': row[2],
            'created_at': row[3].isoformat() if row[3] else None,
            'updated_at': row[4].isoformat() if row[4] else None
        })
    
    return jsonify({
        'bags': bags,
        'count': len(bags),
        'response_time_ms': (time.time() - start) * 1000,
        'cached': False
    })

@optimized_bp.route('/api/cached/search')
@cache(ttl=30, prefix="search")
def cached_search():
    """Cached search with full-text capabilities"""
    start = time.time()
    query_str = request.args.get('q', '')
    search_type = request.args.get('type', 'all')
    
    if not query_str:
        return jsonify({'results': [], 'error': 'Query required'}), 400
    
    from app_clean import db
    
    results_data = {'bags': [], 'users': [], 'bills': []}
    
    # Search bags
    if search_type in ['all', 'bags']:
        bag_query = text("""
            SELECT id, qr_id, type
            FROM bag
            WHERE qr_id ILIKE :pattern
            LIMIT 20
        """)
        bags = db.session.execute(bag_query, {
            'pattern': f'%{query_str}%'
        }).fetchall()
        
        results_data['bags'] = [
            {'id': b[0], 'qr_id': b[1], 'type': b[2]} 
            for b in bags
        ]
    
    # Search users
    if search_type in ['all', 'users']:
        user_query = text("""
            SELECT id, username, email, role
            FROM "user"
            WHERE username ILIKE :pattern OR email ILIKE :pattern
            LIMIT 10
        """)
        users = db.session.execute(user_query, {
            'pattern': f'%{query_str}%'
        }).fetchall()
        
        results_data['users'] = [
            {'id': u[0], 'username': u[1], 'email': u[2], 'role': u[3]} 
            for u in users
        ]
    
    return jsonify({
        'results': results_data,
        'query': query_str,
        'response_time_ms': (time.time() - start) * 1000,
        'cached': False
    })

@optimized_bp.route('/api/cache/stats')
def cache_stats():
    """Get cache performance statistics"""
    stats = cache_manager.get_stats()
    return jsonify(stats)

@optimized_bp.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear cache (admin only)"""
    pattern = request.json.get('pattern', '*') if request.json else '*'
    deleted = invalidate_cache(pattern)
    return jsonify({
        'success': True,
        'deleted_keys': deleted,
        'pattern': pattern
    })

@optimized_bp.route('/api/health/redis')
def redis_health():
    """Check Redis health"""
    try:
        if cache_manager.redis_client:
            cache_manager.redis_client.ping()
            info = cache_manager.redis_client.info()
            return jsonify({
                'status': 'healthy',
                'connected': True,
                'memory_used': info.get('used_memory_human', 'N/A'),
                'connected_clients': info.get('connected_clients', 0),
                'cache_stats': cache_manager.get_stats()
            })
        else:
            return jsonify({
                'status': 'degraded',
                'connected': False,
                'message': 'Using in-memory cache fallback',
                'cache_stats': cache_manager.get_stats()
            })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

def register_optimized_routes(app):
    """Register optimized routes with the Flask app"""
    app.register_blueprint(optimized_bp)
    logger.info("✅ Optimized routes with Redis caching registered")
    return app
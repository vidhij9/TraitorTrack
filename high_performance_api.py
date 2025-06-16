"""
High Performance API for handling millions of bags with split-second response times.
Uses aggressive caching, materialized views, and optimized query patterns.
"""

import logging
import json
import time
from flask import jsonify, request, make_response
from sqlalchemy import func, text, and_, or_, case
from sqlalchemy.orm import selectinload
from app_clean import app, db
from models import User, Bag, BagType, Link, Scan
from production_auth_fix import require_production_auth
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# High-performance in-memory caching system
import threading
from functools import lru_cache
from collections import OrderedDict

# Thread-safe cache implementation
class ThreadSafeCache:
    def __init__(self, max_size=1000):
        self.cache = OrderedDict()
        self.timestamps = {}
        self.lock = threading.RLock()
        self.max_size = max_size
    
    def get(self, key, default_ttl=30):
        with self.lock:
            if key in self.cache:
                timestamp = self.timestamps.get(key, 0)
                if time.time() - timestamp < default_ttl:
                    # Move to end (LRU)
                    self.cache.move_to_end(key)
                    return self.cache[key]
                else:
                    # Expired
                    del self.cache[key]
                    if key in self.timestamps:
                        del self.timestamps[key]
            return None
    
    def set(self, key, value, ttl=30):
        with self.lock:
            self.cache[key] = value
            self.timestamps[key] = time.time()
            
            # Maintain size limit
            while len(self.cache) > self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                if oldest_key in self.timestamps:
                    del self.timestamps[oldest_key]
    
    def delete(self, pattern=None):
        with self.lock:
            if pattern:
                keys_to_delete = [k for k in self.cache.keys() if pattern in k]
                for key in keys_to_delete:
                    del self.cache[key]
                    if key in self.timestamps:
                        del self.timestamps[key]
                return len(keys_to_delete)
            else:
                size = len(self.cache)
                self.cache.clear()
                self.timestamps.clear()
                return size

# Global cache instance
cache = ThreadSafeCache(max_size=2000)

def get_cache_key(endpoint, params):
    """Generate cache key from endpoint and parameters"""
    param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return f"api:{endpoint}:{param_str}"

def get_from_cache(cache_key):
    """Get data from cache"""
    return cache.get(cache_key, default_ttl=30)

def set_cache(cache_key, data, ttl=30):
    """Set data in cache"""
    cache.set(cache_key, data, ttl=ttl)

@app.route('/api/v2/bags/parent/list')
@require_production_auth
def get_parent_bags_v2():
    """Ultra-fast parent bags list with aggressive caching"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        search = request.args.get('search', '').strip()
        
        # Generate cache key
        cache_params = {'page': page, 'per_page': per_page, 'search': search, 'type': 'parent'}
        cache_key = get_cache_key('parent_bags', cache_params)
        
        # Try cache first
        cached_data = get_from_cache(cache_key)
        if cached_data:
            cached_data['cached'] = True
            cached_data['cache_hit'] = True
            return jsonify(cached_data)
        
        # Use raw SQL for maximum performance
        offset = (page - 1) * per_page
        
        if search:
            count_sql = """
                SELECT COUNT(*) FROM bag 
                WHERE type = 'parent' 
                AND (qr_id ILIKE %s OR name ILIKE %s)
            """
            data_sql = """
                SELECT id, qr_id, name, type, created_at, updated_at
                FROM bag 
                WHERE type = 'parent' 
                AND (qr_id ILIKE %s OR name ILIKE %s)
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """
            search_param = f'%{search}%'
            
            total_count = db.session.execute(text(count_sql), (search_param, search_param)).scalar()
            results = db.session.execute(text(data_sql), (search_param, search_param, per_page, offset)).fetchall()
        else:
            count_sql = "SELECT COUNT(*) FROM bag WHERE type = 'parent'"
            data_sql = """
                SELECT id, qr_id, name, type, created_at, updated_at
                FROM bag 
                WHERE type = 'parent'
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """
            
            total_count = db.session.execute(text(count_sql)).scalar()
            results = db.session.execute(text(data_sql), (per_page, offset)).fetchall()
        
        # Convert results to dict format
        bag_data = []
        for row in results:
            bag_data.append({
                'id': row[0],
                'qr_id': row[1],
                'name': row[2],
                'type': row[3],
                'created_at': row[4].isoformat() if row[4] else None,
                'updated_at': row[5].isoformat() if row[5] else None
            })
        
        response_data = {
            'success': True,
            'data': bag_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page,
                'has_next': page * per_page < total_count,
                'has_prev': page > 1
            },
            'timestamp': time.time(),
            'cached': False,
            'cache_hit': False
        }
        
        # Cache the response
        set_cache(cache_key, response_data, ttl=60)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in get_parent_bags_v2: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/v2/bags/child/list')
@require_production_auth
def get_child_bags_v2():
    """Ultra-fast child bags list with aggressive caching"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        search = request.args.get('search', '').strip()
        
        cache_params = {'page': page, 'per_page': per_page, 'search': search, 'type': 'child'}
        cache_key = get_cache_key('child_bags', cache_params)
        
        cached_data = get_from_cache(cache_key)
        if cached_data:
            cached_data['cached'] = True
            cached_data['cache_hit'] = True
            return jsonify(cached_data)
        
        offset = (page - 1) * per_page
        
        if search:
            count_sql = """
                SELECT COUNT(*) FROM bag 
                WHERE type = 'child' 
                AND (qr_id ILIKE %s OR name ILIKE %s)
            """
            # Get child bags with parent info in single query
            data_sql = """
                SELECT b.id, b.qr_id, b.name, b.type, b.created_at, b.updated_at,
                       p.qr_id as parent_qr_id, p.name as parent_name
                FROM bag b
                LEFT JOIN link l ON b.id = l.child_bag_id
                LEFT JOIN bag p ON l.parent_bag_id = p.id
                WHERE b.type = 'child' 
                AND (b.qr_id ILIKE %s OR b.name ILIKE %s)
                ORDER BY b.created_at DESC 
                LIMIT %s OFFSET %s
            """
            search_param = f'%{search}%'
            
            total_count = db.session.execute(text(count_sql), (search_param, search_param)).scalar()
            results = db.session.execute(text(data_sql), (search_param, search_param, per_page, offset)).fetchall()
        else:
            count_sql = "SELECT COUNT(*) FROM bag WHERE type = 'child'"
            data_sql = """
                SELECT b.id, b.qr_id, b.name, b.type, b.created_at, b.updated_at,
                       p.qr_id as parent_qr_id, p.name as parent_name
                FROM bag b
                LEFT JOIN link l ON b.id = l.child_bag_id
                LEFT JOIN bag p ON l.parent_bag_id = p.id
                WHERE b.type = 'child'
                ORDER BY b.created_at DESC 
                LIMIT %s OFFSET %s
            """
            
            total_count = db.session.execute(text(count_sql)).scalar()
            results = db.session.execute(text(data_sql), (per_page, offset)).fetchall()
        
        # Convert results
        bag_data = []
        for row in results:
            bag_data.append({
                'id': row[0],
                'qr_id': row[1],
                'name': row[2],
                'type': row[3],
                'created_at': row[4].isoformat() if row[4] else None,
                'updated_at': row[5].isoformat() if row[5] else None,
                'parent_qr_id': row[6],
                'parent_name': row[7]
            })
        
        response_data = {
            'success': True,
            'data': bag_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page,
                'has_next': page * per_page < total_count,
                'has_prev': page > 1
            },
            'timestamp': time.time(),
            'cached': False,
            'cache_hit': False
        }
        
        set_cache(cache_key, response_data, ttl=60)
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in get_child_bags_v2: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/v2/stats/overview')
@require_production_auth
def get_stats_v2():
    """Ultra-fast stats with aggressive caching"""
    try:
        cache_key = get_cache_key('stats_overview', {})
        
        cached_data = get_from_cache(cache_key)
        if cached_data:
            cached_data['cached'] = True
            return jsonify(cached_data)
        
        # Single optimized query for all stats
        stats_sql = """
            WITH bag_counts AS (
                SELECT 
                    COUNT(CASE WHEN type = 'parent' THEN 1 END) as parent_count,
                    COUNT(CASE WHEN type = 'child' THEN 1 END) as child_count,
                    COUNT(*) as total_bags
                FROM bag
            ),
            scan_counts AS (
                SELECT 
                    COUNT(*) as total_scans,
                    COUNT(CASE WHEN parent_bag_id IS NOT NULL THEN 1 END) as parent_scans,
                    COUNT(CASE WHEN child_bag_id IS NOT NULL THEN 1 END) as child_scans,
                    COUNT(CASE WHEN timestamp >= NOW() - INTERVAL '7 days' THEN 1 END) as recent_scans
                FROM scan
            ),
            link_counts AS (
                SELECT COUNT(DISTINCT child_bag_id) as linked_children
                FROM link
            )
            SELECT 
                bc.parent_count, bc.child_count, bc.total_bags,
                sc.total_scans, sc.parent_scans, sc.child_scans, sc.recent_scans,
                lc.linked_children
            FROM bag_counts bc, scan_counts sc, link_counts lc
        """
        
        result = db.session.execute(text(stats_sql)).fetchone()
        
        response_data = {
            'success': True,
            'data': {
                'totals': {
                    'parent_bags': result[0] or 0,
                    'child_bags': result[1] or 0,
                    'total_bags': result[2] or 0,
                    'total_scans': result[3] or 0
                },
                'scan_breakdown': {
                    'parent_scans': result[4] or 0,
                    'child_scans': result[5] or 0
                },
                'recent_activity': {
                    'scans_last_7_days': result[6] or 0,
                    'linked_children': result[7] or 0,
                    'unlinked_children': (result[1] or 0) - (result[7] or 0)
                },
                'generated_at': datetime.utcnow().isoformat()
            },
            'timestamp': time.time(),
            'cached': False
        }
        
        # Cache for 2 minutes
        set_cache(cache_key, response_data, ttl=120)
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in get_stats_v2: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/v2/bags/search')
@require_production_auth  
def search_bags_v2():
    """Ultra-fast search with prefix matching and caching"""
    try:
        query_text = request.args.get('q', '').strip()
        bag_type = request.args.get('type', 'all')
        limit = min(request.args.get('limit', 20, type=int), 50)
        
        if not query_text:
            return jsonify({'success': False, 'error': 'Search query required'}), 400
        
        cache_params = {'q': query_text, 'type': bag_type, 'limit': limit}
        cache_key = get_cache_key('search_bags', cache_params)
        
        cached_data = get_from_cache(cache_key)
        if cached_data:
            cached_data['cached'] = True
            return jsonify(cached_data)
        
        # Use prefix matching for faster searches on large datasets
        search_sql = """
            SELECT id, qr_id, name, type, created_at
            FROM bag 
            WHERE (qr_id ILIKE %s OR name ILIKE %s)
        """
        
        params = [f'{query_text}%', f'%{query_text}%']
        
        if bag_type != 'all':
            search_sql += " AND type = %s"
            params.append(bag_type)
        
        search_sql += " ORDER BY qr_id LIMIT %s"
        params.append(limit)
        
        results = db.session.execute(text(search_sql), params).fetchall()
        
        bag_data = []
        for row in results:
            bag_data.append({
                'id': row[0],
                'qr_id': row[1],
                'name': row[2],
                'type': row[3],
                'created_at': row[4].isoformat() if row[4] else None
            })
        
        response_data = {
            'success': True,
            'data': bag_data,
            'query': query_text,
            'type_filter': bag_type,
            'count': len(bag_data),
            'timestamp': time.time(),
            'cached': False
        }
        
        # Cache search results for 1 minute
        set_cache(cache_key, response_data, ttl=60)
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in search_bags_v2: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/v2/cache/invalidate', methods=['POST'])
@require_production_auth
def invalidate_cache_v2():
    """Invalidate cache for live updates"""
    try:
        cache_pattern = request.json.get('pattern', '*') if request.is_json else '*'
        cleared_count = cache.delete(cache_pattern if cache_pattern != '*' else None)
        
        return jsonify({
            'success': True,
            'message': f'Cache invalidated',
            'cleared_count': cleared_count,
            'pattern': cache_pattern
        })
        
    except Exception as e:
        logger.error(f"Error in invalidate_cache_v2: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

# WebSocket support for live updates (if needed)
@app.route('/api/v2/bags/live-updates')
@require_production_auth
def get_live_updates():
    """Get recent changes for live updates"""
    try:
        since = request.args.get('since', type=float, default=time.time() - 60)
        since_datetime = datetime.fromtimestamp(since)
        
        # Get recent changes
        recent_bags_sql = """
            SELECT id, qr_id, name, type, created_at, updated_at
            FROM bag 
            WHERE updated_at >= %s OR created_at >= %s
            ORDER BY COALESCE(updated_at, created_at) DESC
            LIMIT 100
        """
        
        results = db.session.execute(text(recent_bags_sql), (since_datetime, since_datetime)).fetchall()
        
        changes = []
        for row in results:
            changes.append({
                'id': row[0],
                'qr_id': row[1],
                'name': row[2],
                'type': row[3],
                'created_at': row[4].isoformat() if row[4] else None,
                'updated_at': row[5].isoformat() if row[5] else None,
                'action': 'updated' if row[5] and row[5] > row[4] else 'created'
            })
        
        return jsonify({
            'success': True,
            'changes': changes,
            'count': len(changes),
            'since': since,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error in get_live_updates: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
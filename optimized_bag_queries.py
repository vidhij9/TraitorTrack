"""
Ultra-fast bag management query optimizations
Performance-focused database queries for the bags page
"""

import time
from typing import Dict, Any, Optional, Tuple
from sqlalchemy import text, and_, or_, func, desc
from sqlalchemy.orm import joinedload
from app_clean import db
from models import Bag, Link, BillBag, BagType
from cache_manager import QueryCache
import logging

logger = logging.getLogger(__name__)

class OptimizedBagQueries:
    """Ultra-optimized bag queries for lightning-fast page loads"""
    
    @staticmethod
    @QueryCache.cached_filtered_bags(max_age=15)
    def get_filtered_bags_with_stats(
        page: int = 1,
        per_page: int = 20,
        bag_type: str = 'all',
        search_query: str = '',
        date_from: str = '',
        date_to: str = '',
        linked_status: str = 'all',
        bill_status: str = 'all',
        dispatch_area: Optional[str] = None
    ) -> Tuple[Any, Dict[str, Any], int]:
        """
        Ultra-optimized single query that gets filtered bags AND stats in one database round trip
        Returns: (paginated_bags, stats_dict, total_filtered_count)
        """
        start_time = time.time()
        
        # Build the comprehensive CTE (Common Table Expression) query
        base_conditions = []
        params = {}
        
        # Dispatch area filter
        if dispatch_area:
            base_conditions.append("b.dispatch_area = :dispatch_area")
            params['dispatch_area'] = dispatch_area
        
        # Type filter
        if bag_type != 'all':
            base_conditions.append("b.type = :bag_type")
            params['bag_type'] = bag_type
        
        # Search filter
        if search_query:
            base_conditions.append("(UPPER(b.qr_id) LIKE UPPER(:search) OR UPPER(b.name) LIKE UPPER(:search))")
            params['search'] = f'%{search_query}%'
        
        # Date filters
        if date_from:
            base_conditions.append("DATE(b.created_at) >= :date_from")
            params['date_from'] = date_from
        
        if date_to:
            base_conditions.append("DATE(b.created_at) <= :date_to")
            params['date_to'] = date_to
        
        # Linked status filter - optimized with EXISTS clauses
        if linked_status == 'linked':
            base_conditions.append("""
                (
                    (b.type = 'parent' AND EXISTS (SELECT 1 FROM link l WHERE l.parent_bag_id = b.id))
                    OR 
                    (b.type = 'child' AND EXISTS (SELECT 1 FROM link l WHERE l.child_bag_id = b.id))
                )
            """)
        elif linked_status == 'unlinked':
            base_conditions.append("""
                (
                    (b.type = 'parent' AND NOT EXISTS (SELECT 1 FROM link l WHERE l.parent_bag_id = b.id))
                    OR 
                    (b.type = 'child' AND NOT EXISTS (SELECT 1 FROM link l WHERE l.child_bag_id = b.id))
                )
            """)
        
        # Bill status filter - optimized with EXISTS
        if bill_status == 'billed':
            base_conditions.append("b.type = 'parent' AND EXISTS (SELECT 1 FROM bill_bag bb WHERE bb.bag_id = b.id)")
        elif bill_status == 'unbilled':
            base_conditions.append("b.type = 'parent' AND NOT EXISTS (SELECT 1 FROM bill_bag bb WHERE bb.bag_id = b.id)")
        
        where_clause = "WHERE " + " AND ".join(base_conditions) if base_conditions else ""
        
        # Ultra-optimized single query with pagination and stats
        optimized_query = text(f"""
            WITH filtered_bags AS (
                SELECT b.*, 
                       ROW_NUMBER() OVER (ORDER BY b.created_at DESC) as row_num,
                       COUNT(*) OVER() as total_filtered,
                       -- Add link counts for each bag
                       CASE 
                           WHEN b.type = 'parent' THEN (SELECT COUNT(*) FROM link l WHERE l.parent_bag_id = b.id)
                           ELSE 0
                       END as linked_children_count,
                       CASE 
                           WHEN b.type = 'child' THEN (SELECT parent_bag_id FROM link l WHERE l.child_bag_id = b.id LIMIT 1)
                           ELSE NULL
                       END as linked_parent_id,
                       -- Get bill info
                       CASE 
                           WHEN b.type = 'parent' THEN (SELECT bb.bill_id FROM bill_bag bb WHERE bb.bag_id = b.id LIMIT 1)
                           ELSE NULL
                       END as bill_id
                FROM bag b
                {where_clause}
            ),
            stats_data AS (
                SELECT 
                    COUNT(*) as total_bags,
                    COUNT(CASE WHEN type = 'parent' THEN 1 END) as parent_bags,
                    COUNT(CASE WHEN type = 'child' THEN 1 END) as child_bags,
                    (SELECT COUNT(DISTINCT parent_bag_id) FROM link) as linked_parent_count,
                    (SELECT COUNT(DISTINCT child_bag_id) FROM link) as linked_child_count
                FROM bag 
                {where_clause.replace('filtered_bags', 'bag') if dispatch_area else ''}
            )
            SELECT 
                fb.id, fb.qr_id, fb.type, fb.name, fb.dispatch_area, 
                fb.created_at, fb.updated_at, fb.child_count, fb.parent_id,
                fb.total_filtered, fb.linked_children_count, fb.linked_parent_id, fb.bill_id,
                sd.total_bags, sd.parent_bags, sd.child_bags, 
                sd.linked_parent_count, sd.linked_child_count
            FROM filtered_bags fb
            CROSS JOIN stats_data sd
            WHERE fb.row_num BETWEEN :offset + 1 AND :offset + :limit
            ORDER BY fb.created_at DESC
        """)
        
        offset = (page - 1) * per_page
        params.update({
            'offset': offset,
            'limit': per_page
        })
        
        try:
            result = db.session.execute(optimized_query, params).fetchall()
            
            if not result:
                # No results case
                empty_stats = {
                    'total_bags': 0,
                    'parent_bags': 0,
                    'child_bags': 0,
                    'linked_bags': 0,
                    'unlinked_bags': 0,
                    'filtered_count': 0
                }
                return [], empty_stats, 0
            
            # Extract bags and stats from result
            bags_data = []
            stats = None
            total_filtered = 0
            
            for row in result:
                if stats is None:
                    # Extract stats from first row
                    total_filtered = row.total_filtered
                    linked_bags = row.linked_parent_count + row.linked_child_count
                    unlinked_bags = row.total_bags - linked_bags
                    
                    stats = {
                        'total_bags': row.total_bags,
                        'parent_bags': row.parent_bags,
                        'child_bags': row.child_bags,
                        'linked_bags': linked_bags,
                        'unlinked_bags': unlinked_bags,
                        'filtered_count': total_filtered
                    }
                
                # Extract bag data
                bag_dict = {
                    'id': row.id,
                    'qr_id': row.qr_id,
                    'type': row.type,
                    'name': row.name,
                    'dispatch_area': row.dispatch_area,
                    'created_at': row.created_at,
                    'updated_at': row.updated_at,
                    'child_count': row.child_count,
                    'parent_id': row.parent_id,
                    'linked_children_count': row.linked_children_count,
                    'linked_parent_id': row.linked_parent_id,
                    'bill_id': row.bill_id
                }
                bags_data.append(bag_dict)
            
            query_time = (time.time() - start_time) * 1000
            logger.info(f"Optimized bag query completed in {query_time:.2f}ms for {len(bags_data)} results")
            
            return bags_data, stats, total_filtered
            
        except Exception as e:
            logger.error(f"Optimized bag query failed: {str(e)}")
            raise
    
    @staticmethod
    def create_pagination_object(bags_data, page, per_page, total_count):
        """Create a pagination-like object from raw data"""
        class MockPagination:
            def __init__(self, items, page, per_page, total):
                self.items = items
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = (total + per_page - 1) // per_page
                self.has_prev = page > 1
                self.has_next = page < self.pages
                self.prev_num = page - 1 if self.has_prev else None
                self.next_num = page + 1 if self.has_next else None
        
        return MockPagination(bags_data, page, per_page, total_count)

class CachedBagStats:
    """Ultra-fast cached statistics for dashboard"""
    _cache = {}
    _cache_timeout = 30  # 30 seconds cache
    _last_update = 0
    
    @classmethod
    def get_stats(cls, force_refresh=False):
        """Get cached stats or refresh if needed"""
        current_time = time.time()
        
        if force_refresh or (current_time - cls._last_update) > cls._cache_timeout:
            cls._refresh_cache()
            cls._last_update = current_time
        
        return cls._cache.copy()
    
    @classmethod
    def _refresh_cache(cls):
        """Refresh statistics cache with optimized query"""
        try:
            stats_query = text("""
                SELECT 
                    COUNT(*) as total_bags,
                    COUNT(CASE WHEN type = 'parent' THEN 1 END) as parent_bags,
                    COUNT(CASE WHEN type = 'child' THEN 1 END) as child_bags,
                    (SELECT COUNT(DISTINCT parent_bag_id) FROM link) as linked_parent_count,
                    (SELECT COUNT(DISTINCT child_bag_id) FROM link) as linked_child_count
                FROM bag
            """)
            
            result = db.session.execute(stats_query).fetchone()
            
            if result:
                linked_bags = result.linked_parent_count + result.linked_child_count
                unlinked_bags = result.total_bags - linked_bags
                
                cls._cache = {
                    'total_bags': result.total_bags,
                    'parent_bags': result.parent_bags,
                    'child_bags': result.child_bags,
                    'linked_bags': linked_bags,
                    'unlinked_bags': unlinked_bags
                }
            else:
                cls._cache = {
                    'total_bags': 0,
                    'parent_bags': 0,
                    'child_bags': 0,
                    'linked_bags': 0,
                    'unlinked_bags': 0
                }
                
        except Exception as e:
            logger.error(f"Stats cache refresh failed: {str(e)}")
            cls._cache = {
                'total_bags': 0,
                'parent_bags': 0,
                'child_bags': 0,
                'linked_bags': 0,
                'unlinked_bags': 0
            }
"""
High-Performance Query Optimizer for TraitorTrack
Optimizes critical scanner and linking operations for sub-50ms response times
"""
from flask import session
from sqlalchemy import text
from functools import lru_cache
import time
import logging

logger = logging.getLogger(__name__)

class QueryOptimizer:
    """Optimized database operations for maximum performance"""
    
    def __init__(self, db):
        self.db = db
        # In-memory cache for frequently accessed bags (session-scoped)
        self._bag_cache = {}
        self._cache_ttl = 60  # 60 second cache TTL
        self._cache_timestamps = {}
    
    def get_bag_by_qr(self, qr_id, bag_type=None):
        """
        Ultra-fast bag lookup - direct query (cache disabled to fix DetachedInstanceError)
        Target: <10ms with proper indexes
        """
        from models import Bag
        
        # Direct database query - cache disabled temporarily
        # TODO: Re-implement with ID-based caching to avoid DetachedInstanceError
        if bag_type:
            bag = Bag.query.filter_by(qr_id=qr_id, type=bag_type).first()
        else:
            bag = Bag.query.filter_by(qr_id=qr_id).first()
        
        return bag
    
    def get_child_count_fast(self, parent_bag_id):
        """
        Lightning-fast child count using raw SQL
        Target: <5ms
        """
        result = self.db.session.execute(
            text("SELECT COUNT(*) FROM link WHERE parent_bag_id = :parent_id"),
            {"parent_id": parent_bag_id}
        ).scalar()
        return result or 0
    
    def check_link_exists_fast(self, parent_bag_id, child_bag_id):
        """
        Fast link existence check using raw SQL
        Target: <5ms
        """
        result = self.db.session.execute(
            text("""
                SELECT 1 FROM link 
                WHERE parent_bag_id = :parent_id AND child_bag_id = :child_id 
                LIMIT 1
            """),
            {"parent_id": parent_bag_id, "child_id": child_bag_id}
        ).scalar()
        return result is not None
    
    def check_circular_relationship(self, parent_bag_id, child_bag_id, max_depth=50):
        """
        Check if creating a link would create a circular relationship
        Returns: (is_circular, message)
        
        Validates:
        1. Direct circular: A -> B -> A
        2. Indirect circular: A -> B -> C -> A
        3. Self-linking: A -> A
        
        Uses recursive CTE for efficient cycle detection
        Target: <10ms
        """
        # Check self-linking
        if parent_bag_id == child_bag_id:
            return True, "Cannot link a bag to itself"
        
        # Use recursive CTE to check if child_bag_id is an ancestor of parent_bag_id
        # If it is, creating the link would form a cycle
        query = text("""
            WITH RECURSIVE ancestors AS (
                -- Start from the parent bag we want to link TO
                SELECT parent_bag_id, child_bag_id, 1 AS depth
                FROM link
                WHERE child_bag_id = :parent_bag_id
                
                UNION ALL
                
                -- Recursively find ancestors
                SELECT l.parent_bag_id, l.child_bag_id, a.depth + 1
                FROM link l
                INNER JOIN ancestors a ON l.child_bag_id = a.parent_bag_id
                WHERE a.depth < :max_depth
            )
            SELECT 1 FROM ancestors 
            WHERE parent_bag_id = :child_bag_id
            LIMIT 1
        """)
        
        result = self.db.session.execute(
            query,
            {
                "parent_bag_id": parent_bag_id,
                "child_bag_id": child_bag_id,
                "max_depth": max_depth
            }
        ).scalar()
        
        if result:
            return True, "This link would create a circular relationship (parent-child cycle)"
        
        return False, ""
    
    def create_link_fast(self, parent_bag_id, child_bag_id, user_id):
        """
        Ultra-fast link creation using raw SQL with circular relationship validation
        Target: <25ms total (includes circular check)
        Returns: (success, message)
        """
        try:
            # Check if link already exists (fast)
            if self.check_link_exists_fast(parent_bag_id, child_bag_id):
                return False, "Link already exists"
            
            # CRITICAL: Check for circular relationships before creating link
            is_circular, circular_message = self.check_circular_relationship(parent_bag_id, child_bag_id)
            if is_circular:
                return False, circular_message
            
            # Create link using raw SQL
            self.db.session.execute(
                text("""
                    INSERT INTO link (parent_bag_id, child_bag_id, created_at)
                    VALUES (:parent_id, :child_id, NOW())
                """),
                {"parent_id": parent_bag_id, "child_id": child_bag_id}
            )
            
            # Update parent bag child_count (if column exists)
            self.db.session.execute(
                text("""
                    UPDATE bag 
                    SET child_count = (
                        SELECT COUNT(*) FROM link WHERE parent_bag_id = :parent_id
                    )
                    WHERE id = :parent_id
                """),
                {"parent_id": parent_bag_id}
            )
            
            return True, "Link created successfully"
        except Exception as e:
            logger.error(f"Failed to create link: parent_bag_id={parent_bag_id}, child_bag_id={child_bag_id}, error={str(e)}", exc_info=True)
            return False, str(e)
    
    def create_scan_fast(self, user_id, parent_bag_id=None, child_bag_id=None):
        """
        Fast scan record creation using raw SQL
        Target: <10ms
        """
        try:
            self.db.session.execute(
                text("""
                    INSERT INTO scan (user_id, parent_bag_id, child_bag_id, timestamp)
                    VALUES (:user_id, :parent_id, :child_id, NOW())
                """),
                {
                    "user_id": user_id,
                    "parent_id": parent_bag_id,
                    "child_id": child_bag_id
                }
            )
            return True
        except Exception as e:
            logger.error(f"Failed to create scan: user_id={user_id}, parent_bag_id={parent_bag_id}, child_bag_id={child_bag_id}", exc_info=True)
            return False
    
    def link_bag_to_bill_fast(self, bill_id, bag_id):
        """
        Ultra-fast bill-bag linking using raw SQL
        Target: <15ms
        Returns: (success, message)
        """
        try:
            # Check if link already exists
            exists = self.db.session.execute(
                text("""
                    SELECT 1 FROM bill_bag 
                    WHERE bill_id = :bill_id AND bag_id = :bag_id 
                    LIMIT 1
                """),
                {"bill_id": bill_id, "bag_id": bag_id}
            ).scalar()
            
            if exists:
                return False, "Bag already linked to this bill"
            
            # Create link
            self.db.session.execute(
                text("""
                    INSERT INTO bill_bag (bill_id, bag_id, created_at)
                    VALUES (:bill_id, :bag_id, NOW())
                """),
                {"bill_id": bill_id, "bag_id": bag_id}
            )
            
            # Update bill statistics in one query
            self.db.session.execute(
                text("""
                    UPDATE bill SET
                        parent_bag_count = (
                            SELECT COUNT(*) FROM bill_bag WHERE bill_id = :bill_id
                        ),
                        total_weight_kg = (
                            SELECT COALESCE(SUM(b.weight_kg), 0)
                            FROM bill_bag bb
                            JOIN bag b ON bb.bag_id = b.id
                            WHERE bb.bill_id = :bill_id
                        )
                    WHERE id = :bill_id
                """),
                {"bill_id": bill_id}
            )
            
            return True, "Bag linked to bill successfully"
        except Exception as e:
            logger.error(f"Failed to link bag to bill: bill_id={bill_id}, bag_id={bag_id}, error={str(e)}", exc_info=True)
            return False, str(e)
    
    def batch_link_bags_to_bill(self, bill_id, bag_ids):
        """
        Batch link multiple bags to a bill
        Target: <50ms for 10 bags
        """
        if not bag_ids:
            return True, "No bags to link"
        
        try:
            # Build values string for bulk insert
            values = []
            params = {"bill_id": bill_id}
            for i, bag_id in enumerate(bag_ids):
                values.append(f"(:bill_id, :bag_id_{i}, NOW())")
                params[f"bag_id_{i}"] = bag_id
            
            values_str = ", ".join(values)
            
            # Bulk insert with ON CONFLICT DO NOTHING
            self.db.session.execute(
                text(f"""
                    INSERT INTO bill_bag (bill_id, bag_id, created_at)
                    VALUES {values_str}
                    ON CONFLICT (bill_id, bag_id) DO NOTHING
                """),
                params
            )
            
            # Update bill statistics
            self.db.session.execute(
                text("""
                    UPDATE bill SET
                        parent_bag_count = (
                            SELECT COUNT(*) FROM bill_bag WHERE bill_id = :bill_id
                        ),
                        total_weight_kg = (
                            SELECT COALESCE(SUM(b.weight_kg), 0)
                            FROM bill_bag bb
                            JOIN bag b ON bb.bag_id = b.id
                            WHERE bb.bill_id = :bill_id
                        )
                    WHERE id = :bill_id
                """),
                {"bill_id": bill_id}
            )
            
            return True, f"Successfully linked {len(bag_ids)} bags to bill"
        except Exception as e:
            logger.error(f"Failed to batch link bags to bill: bill_id={bill_id}, bag_count={len(bag_ids)}, error={str(e)}", exc_info=True)
            return False, str(e)
    
    def invalidate_cache(self, qr_id=None):
        """Invalidate cache for a specific bag or all bags"""
        if qr_id:
            cache_key = f"bag:{qr_id}"
            self._bag_cache.pop(cache_key, None)
            self._cache_timestamps.pop(cache_key, None)
        else:
            self._bag_cache.clear()
            self._cache_timestamps.clear()
    
    def clear_old_cache(self):
        """Clear expired cache entries"""
        now = time.time()
        expired_keys = [
            key for key, timestamp in self._cache_timestamps.items()
            if now - timestamp > self._cache_ttl
        ]
        for key in expired_keys:
            self._bag_cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
    
    def create_bag_optimized(self, qr_id, bag_type, user_id, dispatch_area=None, name=None, weight_kg=None):
        """
        Optimized bag creation using raw SQL
        Target: <20ms
        Returns: Bag object or None
        """
        from models import Bag
        try:
            # Use raw SQL for faster insert
            result = self.db.session.execute(
                text("""
                    INSERT INTO bag (qr_id, type, user_id, dispatch_area, name, weight_kg, created_at)
                    VALUES (:qr_id, :type, :user_id, :dispatch_area, :name, :weight_kg, NOW())
                    RETURNING id
                """),
                {
                    "qr_id": qr_id,
                    "type": bag_type,
                    "user_id": user_id,
                    "dispatch_area": dispatch_area,
                    "name": name,
                    "weight_kg": weight_kg
                }
            )
            bag_id = result.scalar()
            
            # Return the created bag object
            bag = Bag.query.get(bag_id)
            
            # Update cache
            cache_key = f"bag:{qr_id}"
            self._bag_cache[cache_key] = bag
            self._cache_timestamps[cache_key] = time.time()
            
            return bag
        except Exception as e:
            logger.error(f"Failed to create bag: qr_id={qr_id}, type={bag_type}, user_id={user_id}, error={str(e)}", exc_info=True)
            return None
    
    def create_scan_optimized(self, user_id, parent_bag_id=None, child_bag_id=None):
        """
        Optimized scan creation (alias for create_scan_fast for compatibility)
        Target: <10ms
        Returns: True/False
        """
        return self.create_scan_fast(user_id, parent_bag_id, child_bag_id)
    
    def create_link_optimized(self, parent_bag_id, child_bag_id):
        """
        Optimized link creation using raw SQL with circular relationship validation
        Target: <25ms (includes circular check)
        Returns: (link_object, created_boolean)
        Raises: ValueError if circular relationship detected
        """
        from models import Link
        try:
            # Check if link already exists
            if self.check_link_exists_fast(parent_bag_id, child_bag_id):
                # Return existing link
                link = Link.query.filter_by(
                    parent_bag_id=parent_bag_id, 
                    child_bag_id=child_bag_id
                ).first()
                return link, False
            
            # CRITICAL: Check for circular relationships before creating link
            is_circular, circular_message = self.check_circular_relationship(parent_bag_id, child_bag_id)
            if is_circular:
                raise ValueError(circular_message)
            
            # Create link using raw SQL
            result = self.db.session.execute(
                text("""
                    INSERT INTO link (parent_bag_id, child_bag_id, created_at)
                    VALUES (:parent_id, :child_id, NOW())
                    RETURNING id
                """),
                {"parent_id": parent_bag_id, "child_id": child_bag_id}
            )
            link_id = result.scalar()
            
            # Get the created link object
            link = Link.query.get(link_id)
            return link, True
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Failed to create link optimized: parent_bag_id={parent_bag_id}, child_bag_id={child_bag_id}, error={str(e)}", exc_info=True)
            return None, False
    
    def bulk_commit(self):
        """
        Commit pending database changes
        Returns: True on success, False on failure
        """
        try:
            self.db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to commit database transaction", exc_info=True)
            self.db.session.rollback()
            return False

# Create singleton instance
query_optimizer = None

def init_query_optimizer(db):
    """Initialize the global query optimizer"""
    global query_optimizer
    query_optimizer = QueryOptimizer(db)
    return query_optimizer

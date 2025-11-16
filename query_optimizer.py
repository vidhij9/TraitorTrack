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
        # ID-only cache to avoid DetachedInstanceError + leverage SQLAlchemy identity map
        self._bag_id_cache = {}    # Maps qr_id -> bag_id for minimal memory footprint
        self._cache_ttl = 30  # 30 second cache TTL for aggressive caching
        self._cache_timestamps = {}
        self._cache_hits = 0
        self._cache_misses = 0
    
    def get_bag_by_qr(self, qr_id, bag_type=None):
        """
        Ultra-fast bag lookup with optimized ID-only caching (no DetachedInstanceError)
        Target: <1ms (cached), <10ms (uncached with indexes)
        
        Strategy: Cache only bag_id, then use SQLAlchemy's identity map for free object reuse
        """
        from models import Bag
        
        # Clean expired cache entries periodically
        now = time.time()
        cache_key = f"{qr_id}:{bag_type}" if bag_type else qr_id
        
        # Check cache for bag_id first
        if cache_key in self._bag_id_cache:
            cached_timestamp = self._cache_timestamps.get(cache_key, 0)
            if now - cached_timestamp < self._cache_ttl:
                # Cache hit - use session.get for identity map reuse (no extra query if already loaded)
                self._cache_hits += 1
                bag_id = self._bag_id_cache[cache_key]
                bag = Bag.query.get(bag_id)  # Uses SQLAlchemy identity map if available
                return bag
            else:
                # Cache expired - remove
                del self._bag_id_cache[cache_key]
                del self._cache_timestamps[cache_key]
        
        # Cache miss - query database using raw SQL for speed
        self._cache_misses += 1
        if bag_type:
            result = self.db.session.execute(
                text("SELECT id FROM bag WHERE qr_id = :qr_id AND type = :bag_type LIMIT 1"),
                {"qr_id": qr_id, "bag_type": bag_type}
            ).scalar()
        else:
            result = self.db.session.execute(
                text("SELECT id FROM bag WHERE qr_id = :qr_id LIMIT 1"),
                {"qr_id": qr_id}
            ).scalar()
        
        if result:
            bag_id = result
            # Cache only the ID (minimal memory footprint)
            self._bag_id_cache[cache_key] = bag_id
            self._cache_timestamps[cache_key] = now
            
            # Enforce cache size limit (prevent memory bloat)
            if len(self._bag_id_cache) > 5000:
                self._evict_oldest_cache_entries()
            
            # Get full object (will be in identity map for subsequent gets in same request)
            bag = Bag.query.get(bag_id)
            return bag
        
        return None
    
    def _evict_oldest_cache_entries(self):
        """Evict oldest 20% of cache entries to prevent memory bloat"""
        if not self._cache_timestamps:
            return
        
        # Sort by timestamp and remove oldest 20%
        sorted_keys = sorted(self._cache_timestamps.items(), key=lambda x: x[1])
        num_to_evict = len(sorted_keys) // 5  # Remove 20%
        
        for cache_key, _ in sorted_keys[:num_to_evict]:
            self._bag_id_cache.pop(cache_key, None)
            self._cache_timestamps.pop(cache_key, None)
    
    def invalidate_bag_cache(self, qr_id=None, bag_id=None):
        """
        Invalidate cache for a specific bag by QR ID or bag ID
        Call this after any bag mutation (create, update, delete, link, unlink)
        
        Args:
            qr_id: QR code of the bag to invalidate
            bag_id: Database ID of the bag to invalidate
        """
        if qr_id:
            # Remove all cache entries for this QR (with and without type specifier)
            keys_to_remove = [k for k in self._bag_id_cache.keys() if k.startswith(qr_id)]
            for key in keys_to_remove:
                self._bag_id_cache.pop(key, None)
                self._cache_timestamps.pop(key, None)
        
        if bag_id:
            # Find and remove cache entries by bag_id
            keys_to_remove = [k for k, v in self._bag_id_cache.items() if v == bag_id]
            for key in keys_to_remove:
                self._bag_id_cache.pop(key, None)
                self._cache_timestamps.pop(key, None)
    
    def invalidate_all_cache(self):
        """
        Clear all cached data
        Call this after bulk operations or when cache coherence is critical
        """
        self._bag_id_cache.clear()
        self._cache_timestamps.clear()
        logger.debug("All query optimizer caches cleared")
    
    def get_cache_stats(self):
        """Get cache performance statistics"""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hits': self._cache_hits,
            'misses': self._cache_misses,
            'hit_rate': f"{hit_rate:.1f}%",
            'cached_entries': len(self._bag_id_cache),
            'ttl_seconds': self._cache_ttl
        }
    
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
        Ultra-fast link creation with ATOMIC 30-child limit enforcement
        Target: <25ms total (includes all validation checks)
        Returns: (success, message)
        
        Uses SELECT ... FOR UPDATE to prevent race conditions in concurrent scans
        """
        try:
            # VALIDATION 1: Check if link already exists (fast)
            if self.check_link_exists_fast(parent_bag_id, child_bag_id):
                return False, "Link already exists"
            
            # VALIDATION 2: Verify parent and child bag types (before locking)
            parent_type_result = self.db.session.execute(
                text("SELECT type FROM bag WHERE id = :bag_id"),
                {"bag_id": parent_bag_id}
            ).scalar()
            
            child_type_result = self.db.session.execute(
                text("SELECT type FROM bag WHERE id = :bag_id"),
                {"bag_id": child_bag_id}
            ).scalar()
            
            if parent_type_result != 'parent':
                return False, f"Invalid parent bag: bag type is '{parent_type_result}', must be 'parent'"
            
            if child_type_result != 'child':
                return False, f"Invalid child bag: bag type is '{child_type_result}', must be 'child'"
            
            # ATOMIC OPERATION: Lock parent bag row to prevent concurrent modifications
            # This prevents race conditions where multiple concurrent scans could exceed 30 children
            # Lock parent bag row using SELECT ... FOR UPDATE
            self.db.session.execute(
                text("""
                    SELECT id FROM bag 
                    WHERE id = :parent_id 
                    FOR UPDATE
                """),
                {"parent_id": parent_bag_id}
            )
            
            # Now that parent is locked, count children (safe from concurrent modifications)
            current_count = self.get_child_count_fast(parent_bag_id)
            
            # Quick circular relationship check (self-linking and direct parent already child)
            is_circular_quick = self.db.session.execute(
                text("""
                    SELECT CASE 
                        WHEN :parent_id = :child_id THEN 1
                        WHEN EXISTS (
                            SELECT 1 FROM link 
                            WHERE parent_bag_id = :child_id AND child_bag_id = :parent_id
                        ) THEN 1
                        ELSE 0
                    END as is_circular
                """),
                {"parent_id": parent_bag_id, "child_id": child_bag_id}
            ).scalar()
            
            is_circular = is_circular_quick == 1
            
            # VALIDATION 3: Enforce 30-child maximum limit (ATOMIC - checked under lock)
            if current_count >= 30:
                return False, f"Parent bag has reached maximum capacity (30/30 children). Cannot add more children."
            
            # VALIDATION 4: Quick circular check
            if is_circular:
                # Full circular check for deep cycles
                is_circular_full, circular_message = self.check_circular_relationship(parent_bag_id, child_bag_id)
                if is_circular_full:
                    return False, circular_message
            
            # Create link using raw SQL (still under transaction lock)
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
    
    def invalidate_cache(self, qr_id=None, bag_type=None):
        """Invalidate cache for a specific bag or all bags"""
        if qr_id:
            # Invalidate both type-specific and generic cache keys
            cache_keys = [qr_id]
            if bag_type:
                cache_keys.append(f"{qr_id}:{bag_type}")
            
            for cache_key in cache_keys:
                self._bag_id_cache.pop(cache_key, None)
                self._cache_timestamps.pop(cache_key, None)
        else:
            # Clear all caches
            self._bag_id_cache.clear()
            self._cache_timestamps.clear()
    
    def clear_old_cache(self):
        """Clear expired cache entries"""
        now = time.time()
        expired_keys = [
            key for key, timestamp in self._cache_timestamps.items()
            if now - timestamp > self._cache_ttl
        ]
        for key in expired_keys:
            self._bag_id_cache.pop(key, None)
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
            
            # Update cache with bag ID only (minimal memory)
            if bag:
                cache_key = qr_id
                self._bag_id_cache[cache_key] = bag.id
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

def init_query_optimizer(db, redis_client=None):
    """
    Initialize the global query optimizer with optional Redis support
    
    Args:
        db: SQLAlchemy database instance
        redis_client: Optional Redis client for distributed caching (None = in-memory only)
    """
    global query_optimizer
    query_optimizer = QueryOptimizer(db)
    # TODO: Migrate bag_id_cache to Redis when redis_client is provided
    # For now, keep using in-memory cache (works in development, acceptable in production since bag lookups are fast)
    return query_optimizer

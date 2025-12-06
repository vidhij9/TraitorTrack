"""
High-Performance Query Optimizer for TraitorTrack
Optimizes critical scanner and linking operations for sub-50ms response times
"""
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

class QueryOptimizer:
    """Optimized database operations for maximum performance"""
    
    def __init__(self, db):
        self.db = db
    
    def get_bag_by_qr(self, qr_id, bag_type=None):
        """
        Fast bag lookup using optimized SQL query with indexes
        Target: <10ms with proper indexing
        """
        from models import Bag
        from sqlalchemy import func
        
        if bag_type:
            bag = Bag.query.filter(
                func.upper(Bag.qr_id) == func.upper(qr_id),
                Bag.type == bag_type
            ).first()
        else:
            bag = Bag.query.filter(
                func.upper(Bag.qr_id) == func.upper(qr_id)
            ).first()
        
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
        """Invalidate cache for a specific bag or all bags (legacy method for compatibility)"""
        # Cache invalidation calls removed
        pass
    
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
    
    def ultra_fast_bill_parent_scan(self, bill_id, qr_code, user_id):
        """
        Ultra-optimized bill parent bag scanning in a SINGLE database transaction.
        
        Consolidates 8-10 ORM queries into ONE atomic transaction:
        1. Acquires advisory lock for bill
        2. Validates bill exists and has capacity
        3. Finds parent bag using indexed lower(qr_id) lookup
        4. Checks for existing links (same bill, other bills)
        5. Creates BillBag link and Scan record
        6. Updates bill counters atomically
        
        Target: <50ms P95 response time
        
        Args:
            bill_id: Integer bill ID
            qr_code: Parent bag QR code (will be normalized to uppercase)
            user_id: ID of user performing the scan
            
        Returns:
            dict with keys:
            - success: bool
            - error_type: str (for error responses)
            - message: str
            - bag_id, child_count, linked_count, expected_count, etc. (for success)
        """
        qr_code = qr_code.strip().upper()
        
        try:
            # Single transaction with advisory lock
            result = self.db.session.execute(
                text("""
                    WITH
                    -- Step 1: Acquire advisory lock for this bill (prevents concurrent modifications)
                    lock_acquired AS (
                        SELECT pg_advisory_xact_lock(100000 + :bill_id) AS locked
                    ),
                    -- Step 2: Get bill info with capacity check
                    bill_info AS (
                        SELECT 
                            id,
                            bill_id,
                            status,
                            COALESCE(parent_bag_count, 1) AS parent_bag_count,
                            COALESCE(linked_parent_count, 0) AS linked_parent_count,
                            COALESCE(total_weight_kg, 0) AS total_weight_kg,
                            COALESCE(expected_weight_kg, 0) AS expected_weight_kg,
                            COALESCE(total_child_bags, 0) AS total_child_bags
                        FROM bill
                        WHERE id = :bill_id
                        FOR UPDATE
                    ),
                    -- Step 3: Find parent bag using indexed lower() lookup
                    parent_bag_info AS (
                        SELECT 
                            b.id,
                            b.qr_id,
                            b.type,
                            b.child_count,
                            COALESCE((SELECT COUNT(*) FROM link WHERE parent_bag_id = b.id), 0) AS actual_child_count
                        FROM bag b
                        WHERE lower(b.qr_id) = lower(:qr_code)
                        FOR UPDATE
                    ),
                    -- Step 4: Check if already linked to THIS bill
                    existing_same_bill AS (
                        SELECT bb.id, bb.bill_id, bb.bag_id
                        FROM bill_bag bb
                        JOIN parent_bag_info p ON bb.bag_id = p.id
                        WHERE bb.bill_id = :bill_id
                    ),
                    -- Step 5: Check if linked to OTHER bill
                    existing_other_bill AS (
                        SELECT bb.id, bb.bill_id, b.bill_id AS other_bill_id
                        FROM bill_bag bb
                        JOIN parent_bag_info p ON bb.bag_id = p.id
                        JOIN bill b ON bb.bill_id = b.id
                        WHERE bb.bill_id != :bill_id
                    )
                    -- Return validation results
                    SELECT 
                        (SELECT id FROM bill_info) AS bill_pk,
                        (SELECT bill_id FROM bill_info) AS bill_code,
                        (SELECT status FROM bill_info) AS bill_status,
                        (SELECT parent_bag_count FROM bill_info) AS capacity,
                        (SELECT linked_parent_count FROM bill_info) AS linked_count,
                        (SELECT total_weight_kg FROM bill_info) AS current_weight,
                        (SELECT expected_weight_kg FROM bill_info) AS expected_weight,
                        (SELECT total_child_bags FROM bill_info) AS child_bags_total,
                        (SELECT id FROM parent_bag_info) AS bag_id,
                        (SELECT qr_id FROM parent_bag_info) AS bag_qr,
                        (SELECT type FROM parent_bag_info) AS bag_type,
                        (SELECT actual_child_count FROM parent_bag_info) AS child_count,
                        (SELECT id FROM existing_same_bill) IS NOT NULL AS already_linked_same,
                        (SELECT other_bill_id FROM existing_other_bill) AS linked_to_other_bill
                """),
                {
                    "bill_id": int(bill_id),
                    "qr_code": qr_code
                }
            ).fetchone()
            
            if not result:
                return {
                    "success": False,
                    "error_type": "query_failed",
                    "message": "Database query failed. Please try again."
                }
            
            # Unpack results
            (bill_pk, bill_code, bill_status, capacity, linked_count, 
             current_weight, expected_weight, child_bags_total,
             bag_id, bag_qr, bag_type, child_count,
             already_linked_same, linked_to_other_bill) = result
            
            # Validation checks
            if not bill_pk:
                return {
                    "success": False,
                    "error_type": "bill_not_found",
                    "message": f"Bill #{bill_id} not found. Please refresh the page."
                }
            
            if not bag_id:
                return {
                    "success": False,
                    "error_type": "bag_not_found",
                    "message": f"Bag {qr_code} not registered in system. Please scan a registered parent bag."
                }
            
            if bag_type != 'parent':
                return {
                    "success": False,
                    "error_type": "wrong_bag_type",
                    "message": f"{qr_code} is registered as a {bag_type} bag, not a parent bag."
                }
            
            if already_linked_same:
                return {
                    "success": False,
                    "error_type": "already_linked_same_bill",
                    "message": f"{qr_code} already linked to this bill (contains {child_count} children)."
                }
            
            if linked_to_other_bill:
                return {
                    "success": False,
                    "error_type": "already_linked_other_bill",
                    "message": f"{qr_code} already linked to Bill #{linked_to_other_bill}. Cannot link to multiple bills."
                }
            
            # Check capacity
            if linked_count >= capacity:
                return {
                    "success": False,
                    "error_type": "capacity_reached",
                    "is_at_capacity": True,
                    "message": f"Bill capacity reached ({linked_count}/{capacity} parent bags). Cannot add more bags."
                }
            
            # All validations passed - create the link and update counters atomically
            # Calculate weight delta based on bag type (SB = 30kg expected, Mxxx-xx = 15kg expected)
            if qr_code.startswith('SB'):
                expected_weight_delta = 30.0
            elif qr_code.startswith('M') and '-' in qr_code:
                expected_weight_delta = 15.0
            else:
                expected_weight_delta = 30.0  # Default
            
            # Insert BillBag, Scan, and update Bill in one atomic operation
            self.db.session.execute(
                text("""
                    -- Insert bill-bag link
                    INSERT INTO bill_bag (bill_id, bag_id, created_at)
                    VALUES (:bill_id, :bag_id, NOW());
                    
                    -- Insert scan record
                    INSERT INTO scan (parent_bag_id, user_id, timestamp)
                    VALUES (:bag_id, :user_id, NOW());
                    
                    -- Update bag child_count and weight
                    UPDATE bag 
                    SET child_count = :child_count, 
                        weight_kg = :child_count,
                        status = CASE WHEN :child_count >= 30 THEN 'completed' ELSE 'in_progress' END
                    WHERE id = :bag_id;
                    
                    -- Update bill counters atomically
                    UPDATE bill 
                    SET linked_parent_count = COALESCE(linked_parent_count, 0) + 1,
                        total_weight_kg = COALESCE(total_weight_kg, 0) + :child_count,
                        expected_weight_kg = COALESCE(expected_weight_kg, 0) + :expected_delta,
                        total_child_bags = COALESCE(total_child_bags, 0) + :child_count,
                        status = CASE WHEN status = 'new' THEN 'processing' ELSE status END
                    WHERE id = :bill_id;
                """),
                {
                    "bill_id": int(bill_pk),
                    "bag_id": int(bag_id),
                    "user_id": int(user_id),
                    "child_count": int(child_count or 0),
                    "expected_delta": expected_weight_delta
                }
            )
            
            self.db.session.commit()
            
            # Calculate new values
            new_linked_count = linked_count + 1
            new_total_weight = current_weight + (child_count or 0)
            new_expected_weight = expected_weight + expected_weight_delta
            is_at_capacity = new_linked_count >= capacity
            
            capacity_message = " Bill is now at capacity!" if is_at_capacity else ""
            
            return {
                "success": True,
                "error_type": "success",
                "message": f"{bag_qr} linked successfully! Contains {child_count} children ({new_linked_count}/{capacity} bags total){capacity_message}",
                "bag_qr": bag_qr,
                "bag_id": bag_id,
                "child_count": child_count or 0,
                "linked_count": new_linked_count,
                "expected_count": capacity,
                "actual_weight": new_total_weight,
                "expected_weight": new_expected_weight,
                "is_at_capacity": is_at_capacity,
                "remaining_capacity": max(0, capacity - new_linked_count),
                "bill_status": "processing" if bill_status == "new" else bill_status
            }
            
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"Ultra fast bill parent scan failed: bill_id={bill_id}, qr={qr_code}, error={str(e)}", exc_info=True)
            return {
                "success": False,
                "error_type": "server_error",
                "message": f"Error processing scan: {str(e)}"
            }

# Create singleton instance
query_optimizer = None

def init_query_optimizer(db):
    """
    Initialize the global query optimizer
    
    Args:
        db: SQLAlchemy database instance
    """
    global query_optimizer
    query_optimizer = QueryOptimizer(db)
    return query_optimizer

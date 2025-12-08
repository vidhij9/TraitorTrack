-- OPTIMIZED STATISTICS TABLE FOR 1.8M+ BAGS
-- This table maintains real-time counts without expensive COUNT(*) queries
-- Updated via triggers for instant dashboard performance
-- IDEMPOTENT: Safe to run multiple times

CREATE TABLE IF NOT EXISTS statistics_cache (
    id INTEGER PRIMARY KEY DEFAULT 1,
    total_bags INTEGER DEFAULT 0,
    parent_bags INTEGER DEFAULT 0,
    child_bags INTEGER DEFAULT 0,
    total_scans INTEGER DEFAULT 0,
    total_bills INTEGER DEFAULT 0,
    total_users INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT single_row CHECK (id = 1)
);

-- Insert initial row
INSERT INTO statistics_cache (id) VALUES (1)
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- BAG TRIGGERS (INSERT, UPDATE, DELETE)
-- ============================================================================

-- TRIGGER: Update statistics when bags are inserted
CREATE OR REPLACE FUNCTION update_stats_on_bag_insert()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE statistics_cache SET
        total_bags = total_bags + 1,
        parent_bags = parent_bags + CASE WHEN NEW.type = 'parent' THEN 1 ELSE 0 END,
        child_bags = child_bags + CASE WHEN NEW.type = 'child' THEN 1 ELSE 0 END,
        last_updated = CURRENT_TIMESTAMP
    WHERE id = 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS bag_insert_trigger ON bag;
CREATE TRIGGER bag_insert_trigger
AFTER INSERT ON bag
FOR EACH ROW
EXECUTE FUNCTION update_stats_on_bag_insert();

-- TRIGGER: Update statistics when bag type is changed (UPDATE)
CREATE OR REPLACE FUNCTION update_stats_on_bag_update()
RETURNS TRIGGER AS $$
BEGIN
    -- If type changed, adjust both old and new type counts
    IF OLD.type != NEW.type THEN
        UPDATE statistics_cache SET
            parent_bags = parent_bags 
                - CASE WHEN OLD.type = 'parent' THEN 1 ELSE 0 END
                + CASE WHEN NEW.type = 'parent' THEN 1 ELSE 0 END,
            child_bags = child_bags 
                - CASE WHEN OLD.type = 'child' THEN 1 ELSE 0 END
                + CASE WHEN NEW.type = 'child' THEN 1 ELSE 0 END,
            last_updated = CURRENT_TIMESTAMP
        WHERE id = 1;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS bag_update_trigger ON bag;
CREATE TRIGGER bag_update_trigger
AFTER UPDATE ON bag
FOR EACH ROW
EXECUTE FUNCTION update_stats_on_bag_update();

-- TRIGGER: Update statistics when bags are deleted
CREATE OR REPLACE FUNCTION update_stats_on_bag_delete()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE statistics_cache SET
        total_bags = GREATEST(0, total_bags - 1),
        parent_bags = GREATEST(0, parent_bags - CASE WHEN OLD.type = 'parent' THEN 1 ELSE 0 END),
        child_bags = GREATEST(0, child_bags - CASE WHEN OLD.type = 'child' THEN 1 ELSE 0 END),
        last_updated = CURRENT_TIMESTAMP
    WHERE id = 1;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS bag_delete_trigger ON bag;
CREATE TRIGGER bag_delete_trigger
AFTER DELETE ON bag
FOR EACH ROW
EXECUTE FUNCTION update_stats_on_bag_delete();

-- ============================================================================
-- SCAN TRIGGERS (INSERT, DELETE)
-- ============================================================================

-- TRIGGER: Update statistics when scans are inserted
CREATE OR REPLACE FUNCTION update_stats_on_scan_insert()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE statistics_cache SET
        total_scans = total_scans + 1,
        last_updated = CURRENT_TIMESTAMP
    WHERE id = 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS scan_insert_trigger ON scan;
CREATE TRIGGER scan_insert_trigger
AFTER INSERT ON scan
FOR EACH ROW
EXECUTE FUNCTION update_stats_on_scan_insert();

-- TRIGGER: Update statistics when scans are deleted
CREATE OR REPLACE FUNCTION update_stats_on_scan_delete()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE statistics_cache SET
        total_scans = GREATEST(0, total_scans - 1),
        last_updated = CURRENT_TIMESTAMP
    WHERE id = 1;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS scan_delete_trigger ON scan;
CREATE TRIGGER scan_delete_trigger
AFTER DELETE ON scan
FOR EACH ROW
EXECUTE FUNCTION update_stats_on_scan_delete();

-- ============================================================================
-- BILL TRIGGERS (INSERT, DELETE)
-- ============================================================================

-- TRIGGER: Update statistics when bills are inserted
CREATE OR REPLACE FUNCTION update_stats_on_bill_insert()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE statistics_cache SET
        total_bills = total_bills + 1,
        last_updated = CURRENT_TIMESTAMP
    WHERE id = 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS bill_insert_trigger ON bill;
CREATE TRIGGER bill_insert_trigger
AFTER INSERT ON bill
FOR EACH ROW
EXECUTE FUNCTION update_stats_on_bill_insert();

-- TRIGGER: Update statistics when bills are deleted
CREATE OR REPLACE FUNCTION update_stats_on_bill_delete()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE statistics_cache SET
        total_bills = GREATEST(0, total_bills - 1),
        last_updated = CURRENT_TIMESTAMP
    WHERE id = 1;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS bill_delete_trigger ON bill;
CREATE TRIGGER bill_delete_trigger
AFTER DELETE ON bill
FOR EACH ROW
EXECUTE FUNCTION update_stats_on_bill_delete();

-- ============================================================================
-- USER TRIGGERS (INSERT, DELETE)
-- ============================================================================

-- TRIGGER: Update statistics when users are inserted
CREATE OR REPLACE FUNCTION update_stats_on_user_insert()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE statistics_cache SET
        total_users = total_users + 1,
        last_updated = CURRENT_TIMESTAMP
    WHERE id = 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS user_insert_trigger ON "user";
CREATE TRIGGER user_insert_trigger
AFTER INSERT ON "user"
FOR EACH ROW
EXECUTE FUNCTION update_stats_on_user_insert();

-- TRIGGER: Update statistics when users are deleted
CREATE OR REPLACE FUNCTION update_stats_on_user_delete()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE statistics_cache SET
        total_users = GREATEST(0, total_users - 1),
        last_updated = CURRENT_TIMESTAMP
    WHERE id = 1;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS user_delete_trigger ON "user";
CREATE TRIGGER user_delete_trigger
AFTER DELETE ON "user"
FOR EACH ROW
EXECUTE FUNCTION update_stats_on_user_delete();

-- ============================================================================
-- INITIALIZE STATISTICS FROM EXISTING DATA
-- This ensures accurate counts even when running on existing database
-- ============================================================================

UPDATE statistics_cache SET
    total_bags = (SELECT COUNT(*) FROM bag),
    parent_bags = (SELECT COUNT(*) FROM bag WHERE type = 'parent'),
    child_bags = (SELECT COUNT(*) FROM bag WHERE type = 'child'),
    total_scans = (SELECT COUNT(*) FROM scan),
    total_bills = (SELECT COUNT(*) FROM bill),
    total_users = (SELECT COUNT(*) FROM "user"),
    last_updated = CURRENT_TIMESTAMP
WHERE id = 1;

-- FIX STATISTICS CACHE: Add missing triggers for UPDATE and DELETE operations

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

-- Refresh all counts to ensure accuracy after adding missing triggers
UPDATE statistics_cache SET
    total_bags = (SELECT COUNT(*) FROM bag),
    parent_bags = (SELECT COUNT(*) FROM bag WHERE type = 'parent'),
    child_bags = (SELECT COUNT(*) FROM bag WHERE type = 'child'),
    total_scans = (SELECT COUNT(*) FROM scan),
    total_bills = (SELECT COUNT(*) FROM bill),
    total_users = (SELECT COUNT(*) FROM "user"),
    last_updated = CURRENT_TIMESTAMP
WHERE id = 1;

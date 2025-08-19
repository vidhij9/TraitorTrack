-- Update Existing Bags with Their Owners
-- This script links existing bags to the users who scanned them
-- Run this on production AFTER the migration script

BEGIN;

-- Update parent bags with the user who scanned them
-- Uses the most recent scan for each parent bag
UPDATE bag b
SET user_id = (
    SELECT s.user_id 
    FROM scan s 
    WHERE s.parent_bag_id = b.id 
    AND s.user_id IS NOT NULL
    ORDER BY s.timestamp DESC 
    LIMIT 1
)
WHERE b.type = 'parent' 
AND b.user_id IS NULL
AND EXISTS (
    SELECT 1 FROM scan s 
    WHERE s.parent_bag_id = b.id 
    AND s.user_id IS NOT NULL
);

-- Count of parent bags updated
SELECT COUNT(*) as parent_bags_updated 
FROM bag 
WHERE type = 'parent' AND user_id IS NOT NULL;

-- Update child bags with the user who scanned them
-- Uses the most recent scan for each child bag
UPDATE bag b
SET user_id = (
    SELECT s.user_id 
    FROM scan s 
    WHERE s.child_bag_id = b.id 
    AND s.user_id IS NOT NULL
    ORDER BY s.timestamp DESC 
    LIMIT 1
)
WHERE b.type = 'child' 
AND b.user_id IS NULL
AND EXISTS (
    SELECT 1 FROM scan s 
    WHERE s.child_bag_id = b.id 
    AND s.user_id IS NOT NULL
);

-- Count of child bags updated
SELECT COUNT(*) as child_bags_updated 
FROM bag 
WHERE type = 'child' AND user_id IS NOT NULL;

-- Summary of updates
SELECT 
    type,
    COUNT(*) as total_bags,
    COUNT(user_id) as bags_with_owner,
    COUNT(*) - COUNT(user_id) as bags_without_owner,
    ROUND(COUNT(user_id)::numeric / COUNT(*)::numeric * 100, 2) as percent_with_owner
FROM bag
GROUP BY type
ORDER BY type;

-- Detailed check: Show a sample of updated bags
SELECT 
    b.id,
    b.qr_id,
    b.type,
    b.name,
    u.username as owner,
    b.created_at
FROM bag b
LEFT JOIN "user" u ON b.user_id = u.id
WHERE b.user_id IS NOT NULL
ORDER BY b.updated_at DESC
LIMIT 10;

COMMIT;

-- Note: Bags without scan history will remain without owners
-- These will get owners when they're scanned next time with the new code
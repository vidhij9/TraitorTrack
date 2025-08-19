-- Quick Check: Current State of Bag Ownership
-- Run this BEFORE and AFTER the update to see the difference

-- Summary of bags with and without owners
SELECT 
    type as bag_type,
    COUNT(*) as total_bags,
    COUNT(user_id) as bags_with_owner,
    COUNT(*) - COUNT(user_id) as bags_without_owner
FROM bag
GROUP BY type
ORDER BY type;

-- Check if scan history exists to update bags
SELECT 
    'Parent bags with scan history' as category,
    COUNT(DISTINCT b.id) as count
FROM bag b
INNER JOIN scan s ON s.parent_bag_id = b.id
WHERE b.type = 'parent' AND b.user_id IS NULL AND s.user_id IS NOT NULL

UNION ALL

SELECT 
    'Child bags with scan history' as category,
    COUNT(DISTINCT b.id) as count
FROM bag b
INNER JOIN scan s ON s.child_bag_id = b.id
WHERE b.type = 'child' AND b.user_id IS NULL AND s.user_id IS NOT NULL

UNION ALL

SELECT 
    'Bags that will remain without owner' as category,
    COUNT(*) as count
FROM bag b
WHERE b.user_id IS NULL
AND NOT EXISTS (
    SELECT 1 FROM scan s 
    WHERE (s.parent_bag_id = b.id OR s.child_bag_id = b.id) 
    AND s.user_id IS NOT NULL
);
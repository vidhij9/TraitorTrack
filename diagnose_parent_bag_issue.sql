-- Diagnose Why Parent Bags Weren't Updated
-- This helps understand the issue with parent bag ownership

-- 1. Check if parent bags have scan records
SELECT 
    'Parent bags in scan table (as parent_bag_id)' as check_type,
    COUNT(DISTINCT s.parent_bag_id) as count
FROM scan s
WHERE s.parent_bag_id IS NOT NULL
  AND s.user_id IS NOT NULL

UNION ALL

SELECT 
    'Parent bags in scan table (as child_bag_id)' as check_type,
    COUNT(DISTINCT s.child_bag_id) as count
FROM scan s
INNER JOIN bag b ON b.id = s.child_bag_id
WHERE b.type = 'parent'
  AND s.user_id IS NOT NULL

UNION ALL

-- 2. Check parent-child relationships
SELECT 
    'Parent bags with linked children' as check_type,
    COUNT(DISTINCT l.parent_bag_id) as count
FROM link l

UNION ALL

SELECT 
    'Parent bags with children that have owners' as check_type,
    COUNT(DISTINCT l.parent_bag_id) as count
FROM link l
INNER JOIN bag c ON c.id = l.child_bag_id
WHERE c.user_id IS NOT NULL;

-- 3. Detailed look at a few parent bags without owners
SELECT 
    p.id as parent_id,
    p.qr_id as parent_qr,
    p.created_at as parent_created,
    COUNT(DISTINCT l.child_bag_id) as total_children,
    COUNT(DISTINCT CASE WHEN c.user_id IS NOT NULL THEN c.id END) as children_with_owner,
    COUNT(DISTINCT s.id) as scan_records
FROM bag p
LEFT JOIN link l ON p.id = l.parent_bag_id
LEFT JOIN bag c ON c.id = l.child_bag_id
LEFT JOIN scan s ON s.parent_bag_id = p.id
WHERE p.type = 'parent' AND p.user_id IS NULL
GROUP BY p.id, p.qr_id, p.created_at
ORDER BY p.id
LIMIT 10;
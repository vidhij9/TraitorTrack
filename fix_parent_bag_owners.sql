-- Fix Parent Bag Owners Based on Their Children
-- This finds parent bags without owners and assigns them the owner of their child bags

BEGIN;

-- First, let's see what we're about to update
SELECT 
    p.id as parent_id,
    p.qr_id as parent_qr,
    p.name as parent_name,
    COUNT(DISTINCT c.id) as child_count,
    COUNT(DISTINCT c.user_id) as unique_owners,
    MIN(u.username) as owner_username,
    MIN(c.user_id) as owner_id
FROM bag p
INNER JOIN link l ON p.id = l.parent_bag_id
INNER JOIN bag c ON c.id = l.child_bag_id
LEFT JOIN "user" u ON c.user_id = u.id
WHERE p.user_id IS NULL  -- Parent has no owner
  AND c.user_id IS NOT NULL  -- Child has an owner
GROUP BY p.id, p.qr_id, p.name
ORDER BY p.id;

-- Update parent bags with the owner from their children
-- (using the most common owner if children have different owners)
UPDATE bag p
SET user_id = (
    SELECT c.user_id
    FROM link l
    INNER JOIN bag c ON c.id = l.child_bag_id
    WHERE l.parent_bag_id = p.id
      AND c.user_id IS NOT NULL
    GROUP BY c.user_id
    ORDER BY COUNT(*) DESC  -- Most common owner if multiple
    LIMIT 1
)
WHERE p.type = 'parent'
  AND p.user_id IS NULL
  AND EXISTS (
    SELECT 1 
    FROM link l
    INNER JOIN bag c ON c.id = l.child_bag_id
    WHERE l.parent_bag_id = p.id
      AND c.user_id IS NOT NULL
  );

-- Show how many parent bags were updated
SELECT 
    'Parent bags updated' as status,
    COUNT(*) as count
FROM bag 
WHERE type = 'parent' 
  AND user_id IS NOT NULL;

-- Check if any parent bags still don't have owners
SELECT 
    'Parent bags still without owners' as status,
    COUNT(*) as count
FROM bag 
WHERE type = 'parent' 
  AND user_id IS NULL;

-- List any remaining parent bags without owners (shouldn't be any if logic is correct)
SELECT 
    p.id,
    p.qr_id,
    p.name,
    COUNT(l.child_bag_id) as linked_children,
    'No children with owners' as reason
FROM bag p
LEFT JOIN link l ON p.id = l.parent_bag_id
WHERE p.type = 'parent' 
  AND p.user_id IS NULL
GROUP BY p.id, p.qr_id, p.name
ORDER BY p.id;

COMMIT;
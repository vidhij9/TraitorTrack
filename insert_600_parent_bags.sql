-- SQL to insert 600 parent bags (M444-00001 to M444-00600)
-- Run this in pgAdmin after cleanup

INSERT INTO bag (qr_id, type, name, child_count, status, weight_kg, created_at, updated_at)
SELECT 
    'M444-' || LPAD(n::text, 5, '0') as qr_id,
    'parent' as type,
    'Parent Bag ' || n as name,
    0 as child_count,
    'pending' as status,
    0.0 as weight_kg,
    NOW() as created_at,
    NOW() as updated_at
FROM generate_series(1, 600) as n;

-- Verify the insert
SELECT COUNT(*) as total_parent_bags FROM bag WHERE qr_id LIKE 'M444-%';

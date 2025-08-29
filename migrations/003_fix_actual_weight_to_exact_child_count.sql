-- Migration: fix actual weight to exact child count
-- Date: 2025-08-29
-- Description: fix actual weight to exact child count

-- Update all bills to have correct actual weight based on exact child count
UPDATE bill 
SET total_weight_kg = (
    SELECT COALESCE(SUM(
        (SELECT COUNT(*) FROM link WHERE parent_bag_id = b.id)
    ), 0)
    FROM bill_bag bb
    JOIN bag b ON bb.bag_id = b.id
    WHERE bb.bill_id = bill.id
)
WHERE bill.id IS NOT NULL;

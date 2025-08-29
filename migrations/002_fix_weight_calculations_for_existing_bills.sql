-- Migration: Fix weight calculations for existing bills
-- Date: 2025-08-29
-- Description: Corrects actual and expected weight calculations for all existing bills

-- Update expected weight = parent_bags * 30kg for all bills
UPDATE bill b
SET expected_weight_kg = (
    SELECT COALESCE(COUNT(*) * 30.0, 0.0)
    FROM bill_bag bb
    WHERE bb.bill_id = b.id
);

-- Update actual weight calculation for existing bills
-- Each parent with 30+ children = 30kg, otherwise child count
UPDATE bill b
SET total_weight_kg = (
    SELECT COALESCE(SUM(
        CASE 
            WHEN (SELECT COUNT(*) FROM link WHERE parent_bag_id = bag.id) >= 30 THEN 30
            ELSE (SELECT COUNT(*) FROM link WHERE parent_bag_id = bag.id)
        END
    ), 0.0)
    FROM bill_bag bb
    JOIN bag ON bag.id = bb.bag_id
    WHERE bb.bill_id = b.id
);

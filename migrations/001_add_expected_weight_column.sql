-- Migration: Add expected_weight_kg column to bill table
-- Date: 2025-08-29
-- Description: Adds expected weight tracking (30kg per parent bag for billing)

-- Add expected_weight_kg column if it doesn't exist
ALTER TABLE bill 
ADD COLUMN IF NOT EXISTS expected_weight_kg FLOAT DEFAULT 0.0;

-- Update existing bills with correct expected weight (30kg per parent bag)
UPDATE bill b
SET expected_weight_kg = (
    SELECT COALESCE(COUNT(*) * 30.0, 0.0)
    FROM bill_bag bb
    WHERE bb.bill_id = b.id
)
WHERE expected_weight_kg = 0 OR expected_weight_kg IS NULL;

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
-- Production Database Migration Script
-- This adds the expected_weight_kg column to the bill table
-- Run this in the production database pane

-- Step 1: Add the expected_weight_kg column to the bill table
ALTER TABLE bill 
ADD COLUMN IF NOT EXISTS expected_weight_kg FLOAT DEFAULT 0.0;

-- Step 2: Update existing bills with correct expected weight (30kg per parent bag)
UPDATE bill b
SET expected_weight_kg = (
    SELECT COUNT(*) * 30.0
    FROM bill_bag bb
    WHERE bb.bill_id = b.id
)
WHERE expected_weight_kg = 0 OR expected_weight_kg IS NULL;

-- Step 3: Update actual weight calculation for existing bills
-- Each parent with 30+ children = 30kg, otherwise child count
UPDATE bill b
SET total_weight_kg = (
    SELECT COALESCE(SUM(
        CASE 
            WHEN (SELECT COUNT(*) FROM link WHERE parent_bag_id = bag.id) >= 30 THEN 30
            ELSE (SELECT COUNT(*) FROM link WHERE parent_bag_id = bag.id)
        END
    ), 0)
    FROM bill_bag bb
    JOIN bag ON bag.id = bb.bag_id
    WHERE bb.bill_id = b.id
);

-- Verification query - run this to check the migration worked
SELECT 
    'Migration Complete' as status,
    COUNT(*) as total_bills,
    COUNT(CASE WHEN expected_weight_kg IS NOT NULL THEN 1 END) as bills_with_expected_weight
FROM bill;
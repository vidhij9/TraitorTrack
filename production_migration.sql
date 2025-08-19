-- Production Database Migration Script
-- Run this on the production AWS database BEFORE deploying the new code
-- Created: August 19, 2025
-- Purpose: Add bag ownership tracking feature

-- IMPORTANT: Backup your production database before running this migration!

BEGIN;

-- 1. Add user_id column to bag table (nullable to preserve existing data)
ALTER TABLE bag 
ADD COLUMN IF NOT EXISTS user_id INTEGER 
REFERENCES "user"(id) ON DELETE SET NULL;

-- 2. Add index for user_id on bag table for performance
CREATE INDEX IF NOT EXISTS idx_bag_user_id ON bag(user_id);

-- 3. Add composite index for user's bags by type
CREATE INDEX IF NOT EXISTS idx_bag_user_type ON bag(user_id, type);

-- 4. Make user_id nullable in scan table (if not already)
-- This preserves audit history when users are deleted
ALTER TABLE scan 
ALTER COLUMN user_id DROP NOT NULL;

-- 5. Make user_id nullable in promotionrequest table (if exists)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'promotionrequest') THEN
        ALTER TABLE promotionrequest 
        ALTER COLUMN user_id DROP NOT NULL;
    END IF;
END $$;

-- Verify the changes
SELECT 'Migration completed successfully' AS status;

-- Check the new columns
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'bag' AND column_name = 'user_id';

COMMIT;

-- To rollback if needed:
-- BEGIN;
-- ALTER TABLE bag DROP COLUMN IF EXISTS user_id;
-- DROP INDEX IF EXISTS idx_bag_user_id;
-- DROP INDEX IF EXISTS idx_bag_user_type;
-- COMMIT;
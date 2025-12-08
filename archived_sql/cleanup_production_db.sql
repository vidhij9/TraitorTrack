-- Production Database Cleanup Script
-- =================================
-- This script cleans the production database, keeping only the superadmin user.
-- 
-- WARNING: This is a DESTRUCTIVE operation. Run with caution!
-- Make sure you have a backup before proceeding.
--
-- How to use:
-- 1. Go to the Replit Database panel for your production database
-- 2. Open the SQL console/query tool
-- 3. Copy and paste this script
-- 4. Review the commands
-- 5. Execute

-- Step 1: Find superadmin user ID (don't delete this one)
-- First, let's verify the superadmin exists
SELECT id, username, email, role FROM "user" WHERE username = 'superadmin';

-- Step 2: Delete all scans (they reference bags and users)
DELETE FROM scan;

-- Step 3: Delete all bill_bag links (they reference bags and bills)
DELETE FROM bill_bag;

-- Step 4: Delete all links (parent-child bag relationships)
DELETE FROM link;

-- Step 5: Delete all bags
DELETE FROM bag;

-- Step 6: Delete all bills
DELETE FROM bill;

-- Step 7: Delete all notifications
DELETE FROM notification;

-- Step 8: Delete all audit logs
DELETE FROM audit_log;

-- Step 9: Delete all promotion requests
DELETE FROM promotion_request;

-- Step 10: Delete all users EXCEPT superadmin
DELETE FROM "user" WHERE username != 'superadmin';

-- Step 11: Verify cleanup
SELECT 'Users remaining:' as info, COUNT(*) as count FROM "user";
SELECT 'Bags remaining:' as info, COUNT(*) as count FROM bag;
SELECT 'Bills remaining:' as info, COUNT(*) as count FROM bill;
SELECT 'Scans remaining:' as info, COUNT(*) as count FROM scan;
SELECT 'Links remaining:' as info, COUNT(*) as count FROM link;

-- Step 12: Reset sequences (optional - uncomment if needed)
-- This resets auto-increment IDs to start fresh
-- ALTER SEQUENCE user_id_seq RESTART WITH 2;
-- ALTER SEQUENCE bag_id_seq RESTART WITH 1;
-- ALTER SEQUENCE bill_id_seq RESTART WITH 1;
-- ALTER SEQUENCE scan_id_seq RESTART WITH 1;
-- ALTER SEQUENCE link_id_seq RESTART WITH 1;

-- Done! Your production database now only has the superadmin user.

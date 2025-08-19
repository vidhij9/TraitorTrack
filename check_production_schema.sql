-- Check Production Database Schema Script
-- Run this on production to see what needs to be migrated

-- Check if bag table has user_id column
SELECT 
    'bag.user_id' as feature,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'bag' AND column_name = 'user_id'
        ) THEN '✓ EXISTS'
        ELSE '✗ MISSING - NEEDS MIGRATION'
    END as status;

-- Check if bag table has required indexes
SELECT 
    'idx_bag_user_id index' as feature,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE tablename = 'bag' AND indexname = 'idx_bag_user_id'
        ) THEN '✓ EXISTS'
        ELSE '✗ MISSING - NEEDS MIGRATION'
    END as status;

-- Check if scan.user_id is nullable (for preserving audit history)
SELECT 
    'scan.user_id nullable' as feature,
    CASE 
        WHEN is_nullable = 'YES' THEN '✓ CORRECT'
        WHEN is_nullable = 'NO' THEN '✗ NEEDS UPDATE - Should be nullable'
        ELSE '✗ Column not found'
    END as status
FROM information_schema.columns 
WHERE table_name = 'scan' AND column_name = 'user_id'
UNION ALL
SELECT 
    'scan.user_id nullable' as feature,
    '✗ Column not found' as status
WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'scan' AND column_name = 'user_id'
);

-- Summary
SELECT 
    '=== MIGRATION NEEDED ===' as summary,
    'Run production_migration.sql if any items show ✗' as action;
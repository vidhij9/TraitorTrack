-- List of 57 Bags Without Owners
-- These are bags that have never been scanned (no scan history)

SELECT 
    id,
    qr_id,
    type,
    name,
    created_at,
    updated_at,
    CASE 
        WHEN created_at < NOW() - INTERVAL '30 days' THEN 'Old (30+ days)'
        WHEN created_at < NOW() - INTERVAL '7 days' THEN 'Recent (7-30 days)' 
        ELSE 'New (< 7 days)'
    END as age_category
FROM bag 
WHERE user_id IS NULL
ORDER BY type, created_at DESC;

-- Summary by type and age
SELECT 
    type,
    CASE 
        WHEN created_at < NOW() - INTERVAL '30 days' THEN 'Old (30+ days)'
        WHEN created_at < NOW() - INTERVAL '7 days' THEN 'Recent (7-30 days)' 
        ELSE 'New (< 7 days)'
    END as age_category,
    COUNT(*) as count
FROM bag 
WHERE user_id IS NULL
GROUP BY type, age_category
ORDER BY type, age_category;
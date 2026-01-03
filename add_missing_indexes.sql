-- Missing indexes for production database
-- Run this against PRODUCTION_DATABASE_URL to fix slow query issues

-- ============================================
-- BILL TABLE - Missing indexes
-- ============================================
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_created ON bill (created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_keyset_pagination ON bill (created_at, id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_linked_count ON bill (linked_parent_count);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_status_created ON bill (status, created_at);

-- ============================================
-- BILL_BAG TABLE - Missing indexes
-- ============================================
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_bag_bag_id ON bill_bag (bag_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_bag_bill_id ON bill_bag (bill_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_billbag_bag_only ON bill_bag (bag_id);

-- ============================================
-- LINK TABLE - Missing indexes (CRITICAL for bill viewing)
-- ============================================
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_child_id ON link (child_bag_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_parent_id ON link (parent_bag_id);

-- ============================================
-- NOTIFICATION TABLE - Check if missing
-- ============================================
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notification_user_read ON notification (user_id, is_read);

-- Verify indexes were created
SELECT 
    t.relname as table_name,
    COUNT(DISTINCT i.relname) as index_count
FROM 
    pg_class t,
    pg_class i,
    pg_index ix
WHERE 
    t.oid = ix.indrelid
    AND i.oid = ix.indexrelid
    AND t.relkind = 'r'
    AND t.relname IN ('bill', 'bill_bag', 'link', 'notification')
GROUP BY t.relname
ORDER BY t.relname;

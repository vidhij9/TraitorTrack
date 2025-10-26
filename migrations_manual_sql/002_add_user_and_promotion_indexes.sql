-- Migration: Add performance indexes to user and promotionrequest tables
-- Date: 2025-10-26
-- Description: Adds critical database indexes to optimize authentication, user queries, and admin dashboards
--              Fixes performance bottleneck for 100+ concurrent users on login and role-based queries

-- ==============================================================================
-- USER TABLE INDEXES
-- ==============================================================================
-- These indexes optimize authentication hot path and admin dashboards

-- Login and authentication queries (username/email lookups)
-- Note: Unique indexes already exist from constraints, but explicit indexes improve query planning
CREATE INDEX IF NOT EXISTS idx_user_username ON "user"(username);
CREATE INDEX IF NOT EXISTS idx_user_email ON "user"(email);

-- Role-based access control (RBAC) queries
CREATE INDEX IF NOT EXISTS idx_user_role ON "user"(role);
COMMENT ON INDEX idx_user_role IS 'Optimizes role filtering for admin/biller/dispatcher queries';

-- User activity dashboards and analytics
CREATE INDEX IF NOT EXISTS idx_user_created_at ON "user"(created_at);
COMMENT ON INDEX idx_user_created_at IS 'Optimizes user registration analytics and activity dashboards';

-- Password reset functionality
CREATE INDEX IF NOT EXISTS idx_user_password_reset_token ON "user"(password_reset_token);
COMMENT ON INDEX idx_user_password_reset_token IS 'Fast lookup for password reset token validation';

-- Account lockout security checks
CREATE INDEX IF NOT EXISTS idx_user_locked_until ON "user"(locked_until);
COMMENT ON INDEX idx_user_locked_until IS 'Optimizes account lockout validation during login';

-- Two-factor authentication filtering
CREATE INDEX IF NOT EXISTS idx_user_two_fa_enabled ON "user"(two_fa_enabled);
COMMENT ON INDEX idx_user_two_fa_enabled IS 'Optimizes queries filtering users with 2FA enabled/disabled';

-- Composite indexes for complex queries
CREATE INDEX IF NOT EXISTS idx_user_role_created ON "user"(role, created_at);
COMMENT ON INDEX idx_user_role_created IS 'Optimizes admin dashboard: new users by role over time';

CREATE INDEX IF NOT EXISTS idx_user_role_dispatch_area ON "user"(role, dispatch_area);
COMMENT ON INDEX idx_user_role_dispatch_area IS 'Optimizes dispatcher area-based filtering queries';

-- ==============================================================================
-- PROMOTIONREQUEST TABLE INDEXES
-- ==============================================================================
-- These indexes optimize admin promotion management dashboards

-- User's promotion request history
CREATE INDEX IF NOT EXISTS idx_promotion_user_id ON promotionrequest(user_id);
COMMENT ON INDEX idx_promotion_user_id IS 'Fast lookup of promotion requests by user';

-- Status filtering (pending/approved/rejected)
CREATE INDEX IF NOT EXISTS idx_promotion_status ON promotionrequest(status);
COMMENT ON INDEX idx_promotion_status IS 'Optimizes filtering promotion requests by status';

-- Time-based sorting and analytics
CREATE INDEX IF NOT EXISTS idx_promotion_requested_at ON promotionrequest(requested_at);
COMMENT ON INDEX idx_promotion_requested_at IS 'Optimizes date-based sorting and analytics';

-- Admin processing tracking
CREATE INDEX IF NOT EXISTS idx_promotion_admin_id ON promotionrequest(admin_id);
COMMENT ON INDEX idx_promotion_admin_id IS 'Track promotion requests processed by specific admin';

-- Composite index for admin dashboard (most common query)
CREATE INDEX IF NOT EXISTS idx_promotion_status_requested ON promotionrequest(status, requested_at);
COMMENT ON INDEX idx_promotion_status_requested IS 'Optimizes admin dashboard: pending requests sorted by date';

-- ==============================================================================
-- VERIFICATION AND STATISTICS
-- ==============================================================================

-- Display index creation summary
DO $$
DECLARE
    user_index_count INTEGER;
    promotion_index_count INTEGER;
BEGIN
    -- Count user table indexes
    SELECT COUNT(*) INTO user_index_count
    FROM pg_indexes
    WHERE tablename = 'user'
    AND indexname NOT LIKE '%pkey%';
    
    -- Count promotionrequest table indexes
    SELECT COUNT(*) INTO promotion_index_count
    FROM pg_indexes
    WHERE tablename = 'promotionrequest'
    AND indexname NOT LIKE '%pkey%';
    
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'MIGRATION 002: Database Indexes Created Successfully';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'User table: % indexes (optimizes authentication & user queries)', user_index_count;
    RAISE NOTICE 'PromotionRequest table: % indexes (optimizes admin dashboards)', promotion_index_count;
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Expected Performance Improvements:';
    RAISE NOTICE '- Login queries: 10x-100x faster (sequential scan -> index scan)';
    RAISE NOTICE '- Admin dashboards: 5x-20x faster (full table scan -> index scan)';
    RAISE NOTICE '- Password reset: Instant token lookup vs linear scan';
    RAISE NOTICE '- 2FA queries: Efficient filtering by enabled status';
    RAISE NOTICE '============================================================';
END $$;

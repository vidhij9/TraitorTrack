-- Migration: Add before/after state columns to audit_log table
-- Purpose: Enable comprehensive audit trails with state snapshots
-- Created: 2025-10-25
-- Safe: Adds nullable columns, backward compatible

-- Add before_state column for storing entity state before change
ALTER TABLE audit_log 
ADD COLUMN IF NOT EXISTS before_state TEXT NULL;

-- Add after_state column for storing entity state after change
ALTER TABLE audit_log 
ADD COLUMN IF NOT EXISTS after_state TEXT NULL;

-- Add request_id column for correlating audit logs with request tracking
ALTER TABLE audit_log 
ADD COLUMN IF NOT EXISTS request_id VARCHAR(36) NULL;

-- Add index for request_id lookups
CREATE INDEX IF NOT EXISTS idx_audit_request_id ON audit_log(request_id);

-- Verify columns were added
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'audit_log' AND column_name = 'before_state'
    ) THEN
        RAISE EXCEPTION 'Migration failed: before_state column not added';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'audit_log' AND column_name = 'after_state'
    ) THEN
        RAISE EXCEPTION 'Migration failed: after_state column not added';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'audit_log' AND column_name = 'request_id'
    ) THEN
        RAISE EXCEPTION 'Migration failed: request_id column not added';
    END IF;
    
    RAISE NOTICE 'Migration successful: audit_log enhanced with before/after state tracking';
END $$;

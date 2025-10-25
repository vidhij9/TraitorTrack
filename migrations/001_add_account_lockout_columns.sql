-- Migration: Add account lockout columns to user table
-- Date: 2025-10-25
-- Description: Adds failed login tracking and account lockout functionality

-- Add failed login attempts counter
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0;

-- Add lock expiration timestamp
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP;

-- Add last failed login timestamp for tracking
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS last_failed_login TIMESTAMP;

-- Add comments for documentation
COMMENT ON COLUMN "user".failed_login_attempts IS 'Counter for failed login attempts (resets to 0 on successful login)';
COMMENT ON COLUMN "user".locked_until IS 'Account locked until this timestamp (NULL if not locked)';
COMMENT ON COLUMN "user".last_failed_login IS 'Timestamp of the most recent failed login attempt';

-- Update existing users to have default values
UPDATE "user" SET failed_login_attempts = 0 WHERE failed_login_attempts IS NULL;
UPDATE "user" SET locked_until = NULL WHERE locked_until IS NOT NULL AND locked_until < NOW();

-- Create index for faster lockout checks
CREATE INDEX IF NOT EXISTS idx_user_locked_until ON "user"(locked_until) WHERE locked_until IS NOT NULL;

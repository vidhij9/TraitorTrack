# Database Migrations

This directory contains SQL migration scripts for TraceTrack database schema changes.

## Migration Files

### 001_add_account_lockout_columns.sql
**Date**: 2025-10-25  
**Description**: Adds account lockout functionality to prevent brute-force attacks

**Changes**:
- Adds `failed_login_attempts` column (tracks failed login count)
- Adds `locked_until` column (account lock expiration timestamp)
- Adds `last_failed_login` column (timestamp of last failed attempt)
- Creates index on `locked_until` for performance
- Sets default values for existing users

## How to Apply Migrations

### Development Environment (Replit)
Migrations are applied automatically when you add columns via `execute_sql_tool` or run migration scripts.

### Production Environment

#### Manual Application:
```bash
# Connect to production database
psql $PRODUCTION_DATABASE_URL

# Run migration
\i migrations/001_add_account_lockout_columns.sql

# Verify changes
\d "user"
```

#### Using psql from command line:
```bash
psql $PRODUCTION_DATABASE_URL -f migrations/001_add_account_lockout_columns.sql
```

#### Verify Migration:
```sql
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'user' 
AND column_name IN ('failed_login_attempts', 'locked_until', 'last_failed_login');
```

## Migration Safety

All migrations use `IF NOT EXISTS` clauses to be idempotent - they can be run multiple times safely without errors.

## Future Migrations

When adding new migrations:
1. Name them sequentially: `002_description.sql`, `003_description.sql`, etc.
2. Use `IF NOT EXISTS` / `IF EXISTS` clauses for idempotency
3. Include rollback instructions in comments
4. Test in development before applying to production
5. Update this README with migration details

## Rollback Instructions

### 001_add_account_lockout_columns.sql
To rollback this migration (not recommended after data exists):
```sql
-- WARNING: This will lose all lockout data
DROP INDEX IF EXISTS idx_user_locked_until;
ALTER TABLE "user" DROP COLUMN IF EXISTS failed_login_attempts;
ALTER TABLE "user" DROP COLUMN IF EXISTS locked_until;
ALTER TABLE "user" DROP COLUMN IF EXISTS last_failed_login;
```

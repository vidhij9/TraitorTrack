# Production Database Migration Fix

## Problem
Your production login is failing because the database is missing security-related columns that were added through migrations but haven't been applied to production yet.

## Missing Columns in Production
The following columns are missing from the `user` table in production:
- `failed_login_attempts` - Account lockout protection
- `locked_until` - Account lockout timing
- `last_failed_login` - Last failed login tracking
- `password_reset_token` - Password reset functionality
- `password_reset_token_expires` - Password reset expiration
- `totp_secret` - Two-factor authentication
- `two_fa_enabled` - Two-factor authentication flag

## Solution: Apply Pending Migrations

### Step 1: Verify Current Production Migration Status
First, check which migrations are currently applied in production:

```bash
flask db current
```

### Step 2: Apply All Pending Migrations
Run this command to apply all pending migrations to the production database:

```bash
flask db upgrade
```

This will apply the following migrations in order:
1. `c25e20b7535f` - Initial migration with all existing models
2. `bc112eaa12f2` - Add case insensitive unique constraint to QR ID
3. `9516c0528a3c` - Add password reset fields to User model
4. `6830e8e892ce` - Add two-factor authentication fields to User model
5. `a1b2c3d4e5f6` - Add account lockout fields to User model
6. `986e81b92e8e` - Add destination and vehicle_number to Bill model

### Step 3: Verify Migration Success
After running the upgrade, verify all columns are now present:

```bash
flask db current
```

The output should show: `986e81b92e8e (head)`

### Alternative: Manual SQL Commands (If Flask-Migrate Fails)

If for any reason Flask-Migrate doesn't work in production, you can run these SQL commands directly:

```sql
-- Add account lockout fields
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS last_failed_login TIMESTAMP;

-- Add password reset fields
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS password_reset_token VARCHAR(100);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS password_reset_token_expires TIMESTAMP;

-- Add two-factor authentication fields  
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(32);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS two_fa_enabled BOOLEAN DEFAULT FALSE;
```

### Important Notes
1. **Backup First**: Always backup your production database before running migrations
2. **Test First**: These migrations have been tested in the development environment and work correctly
3. **No Data Loss**: These migrations only ADD columns with safe defaults - no existing data will be affected
4. **Immediate Fix**: Once applied, the login functionality will work immediately

## Quick Fix Command
Run this single command in your production environment:

```bash
flask db upgrade
```

That's it! Your login should work immediately after this command completes.
# AWS Production Database Fix Guide

## Problem Summary
Your production database is missing 7 columns in the `user` table that are required for login and security features:

1. **Account Lockout Protection**
   - `failed_login_attempts` - Tracks failed login attempts
   - `locked_until` - Account lockout expiry timestamp
   - `last_failed_login` - Last failed login timestamp

2. **Password Reset Functionality**
   - `password_reset_token` - Token for password reset
   - `password_reset_token_expires` - Token expiration

3. **Two-Factor Authentication**
   - `totp_secret` - TOTP secret for 2FA
   - `two_fa_enabled` - 2FA enabled flag

## Quick Fix (Recommended)

### Option 1: Run SQL Directly on AWS RDS

Connect to your AWS RDS PostgreSQL database and run these commands:

```sql
-- Add account lockout fields
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS last_failed_login TIMESTAMP WITHOUT TIME ZONE;

-- Add password reset fields
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS password_reset_token VARCHAR(100);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS password_reset_token_expires TIMESTAMP WITHOUT TIME ZONE;

-- Add two-factor authentication fields
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(32);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS two_fa_enabled BOOLEAN DEFAULT FALSE;
```

### How to Execute on AWS RDS

#### Method 1: Using psql Command Line

```bash
# Connect to your AWS RDS database
psql "postgresql://YOUR_USERNAME:YOUR_PASSWORD@YOUR_RDS_ENDPOINT:5432/YOUR_DATABASE_NAME"

# Then paste the SQL commands above
```

#### Method 2: Using AWS RDS Query Editor (if enabled)

1. Go to AWS RDS Console
2. Select your database instance
3. Click "Query Editor" in the left sidebar
4. Connect with your database credentials
5. Paste and execute the SQL commands

#### Method 3: Using pgAdmin or DBeaver

1. Open pgAdmin or DBeaver
2. Create a new connection to your AWS RDS instance
3. Open a new SQL query window
4. Paste and execute the SQL commands

### Verification

After running the commands, verify all columns were created:

```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'user'
  AND column_name IN (
    'failed_login_attempts',
    'locked_until',
    'last_failed_login',
    'password_reset_token',
    'password_reset_token_expires',
    'totp_secret',
    'two_fa_enabled'
  )
ORDER BY column_name;
```

Expected output should show all 7 columns.

## Alternative: Using Flask-Migrate (If Replit Database)

If you're using Replit's built-in PostgreSQL database instead of AWS:

1. Open the Database pane in Replit
2. Select "Production database"
3. Click the SQL runner
4. Paste and run the SQL commands from Option 1

## Safety Notes

✅ **SAFE Operations:**
- All these commands use `IF NOT EXISTS` or `ADD COLUMN IF NOT EXISTS`
- If columns already exist, commands will be skipped (no errors)
- All columns have safe defaults (0, FALSE, or NULL)
- No existing data will be modified or lost

✅ **No Downtime Required:**
- These are additive operations only
- Your application can stay running
- Login will work immediately after execution

✅ **Rollback (if needed):**
If you need to remove these columns later:

```sql
-- ONLY USE IF YOU NEED TO ROLLBACK
ALTER TABLE "user" DROP COLUMN IF EXISTS failed_login_attempts;
ALTER TABLE "user" DROP COLUMN IF EXISTS locked_until;
ALTER TABLE "user" DROP COLUMN IF EXISTS last_failed_login;
ALTER TABLE "user" DROP COLUMN IF EXISTS password_reset_token;
ALTER TABLE "user" DROP COLUMN IF EXISTS password_reset_token_expires;
ALTER TABLE "user" DROP COLUMN IF EXISTS totp_secret;
ALTER TABLE "user" DROP COLUMN IF EXISTS two_fa_enabled;
```

## Post-Fix Testing

After applying the fix, test the login functionality:

1. Navigate to your production website
2. Try logging in with a valid user account
3. Login should work without any errors

If you still see errors, check:
- Did all SQL commands execute successfully?
- Run the verification query to confirm all columns exist
- Check application logs for any other issues

## What Changed in Development

In your development environment, I've already:
- ✅ Removed `destination` and `vehicle_number` from Bill table
- ✅ Updated all templates and routes accordingly
- ✅ Tested bill creation - works perfectly
- ✅ Database migrations are clean and up-to-date

Your production database just needs the 7 User table columns added, and everything will work!
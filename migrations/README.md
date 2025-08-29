# Database Migrations System

This migration system automatically runs on every deployment to ensure production and development databases stay in sync.

## How It Works

1. **Automatic Execution**: Migrations run automatically when the application starts
2. **Track Execution**: Each migration is recorded in `schema_migrations` table
3. **No Duplicates**: Already executed migrations are skipped
4. **Sequential Order**: Migrations run in alphabetical order (001_, 002_, etc.)

## Creating New Migrations

### Using the Helper Script
```bash
python migrations/create_migration.py "add user profile table"
```

### Manual Creation
Create a new file following the naming pattern: `XXX_description.sql`

Example: `002_add_user_profiles.sql`

```sql
-- Migration: Add user profiles table
-- Date: 2025-08-29
-- Description: Adds user profile information storage

-- Create the table
CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    bio TEXT,
    avatar_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Update existing data if needed
UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE profile_id IS NULL;
```

## Migration Best Practices

### Safe Operations
- Use `IF NOT EXISTS` for CREATE statements
- Use `ADD COLUMN IF NOT EXISTS` for new columns
- Handle data migration carefully
- Always test on development first

### Example Safe Migration
```sql
-- ✅ SAFE: Add column with default value
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;

-- ✅ SAFE: Create index if not exists
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ✅ SAFE: Update with WHERE clause
UPDATE users SET email_verified = TRUE WHERE created_at < '2025-01-01';
```

### Avoid Unsafe Operations
```sql
-- ❌ UNSAFE: Dropping columns (data loss)
ALTER TABLE users DROP COLUMN old_column;

-- ❌ UNSAFE: Changing column types (potential data loss)
ALTER TABLE users ALTER COLUMN id TYPE UUID;

-- ❌ UNSAFE: Dropping tables
DROP TABLE old_table;
```

## Current Migrations

1. `001_add_expected_weight_column.sql` - Adds expected weight tracking to bills

## Deployment Process

1. **Development**: Create and test migration locally
2. **Push Code**: Migration files are included in deployment
3. **Automatic Execution**: Migration runs on production startup
4. **Verification**: Check logs for successful execution

## Troubleshooting

### Migration Failed
Check the application logs for detailed error messages:
```
❌ Migration failed: 002_example.sql - [error details]
```

### Manual Recovery
If needed, you can manually mark a migration as executed:
```sql
INSERT INTO schema_migrations (migration_name, executed_at, success)
VALUES ('002_example.sql', CURRENT_TIMESTAMP, TRUE);
```

### Check Migration Status
```sql
SELECT * FROM schema_migrations ORDER BY executed_at;
```

## Benefits

- **No Manual Steps**: Migrations run automatically on deployment
- **Consistent Databases**: Development and production stay in sync
- **Safe Deployments**: Failed migrations prevent application startup
- **Audit Trail**: Complete history of schema changes
- **Team Collaboration**: Everyone gets the same schema changes
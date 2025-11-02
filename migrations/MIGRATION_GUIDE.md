# Database Migration Guide

TraitorTrack uses **Flask-Migrate** (built on Alembic) for database schema management. This provides version control for your database, automatic migration generation, and safe schema evolution.

## Quick Start

### Fresh Database Setup (First Time)

For a brand new database deployment:

```bash
# 1. Initialize database schema from migrations
flask db upgrade

# 2. Start the application
# Admin user will be created automatically with password from ADMIN_PASSWORD env var
# If ADMIN_PASSWORD is not set, a random password will be generated and displayed
```

### Making Schema Changes (Existing Database)

1. **Make Changes**: Modify models in `models.py`
   ```python
   # Example: Add a new field to models.py
   class User(db.Model):
       # ... existing fields ...
       last_login = db.Column(db.DateTime)  # New field
   ```

2. **Generate Migration**: Automatically detect changes
   ```bash
   flask db migrate -m "Add last_login to User model"
   # Or: python manage.py migrate -m "Add last_login to User model"
   ```

3. **Apply Migration**: Update database schema
   ```bash
   flask db upgrade
   # Or: python manage.py upgrade
   ```

## Common Commands

```bash
# Initialize migrations (first time only, already done)
flask db init

# Create a new migration after model changes
flask db migrate -m "Description of changes"

# Apply all pending migrations
flask db upgrade

# Rollback last migration
flask db downgrade

# Show current migration version
flask db current

# Show migration history
flask db history

# Show SQL that will be executed (don't apply)
flask db upgrade --sql
```

## Migration Workflow

### Development Environment

1. **Make Changes**: Modify models in `models.py`
2. **Generate Migration**: `flask db migrate -m "description"`
3. **Review Migration**: Check the generated file in `migrations/versions/`
4. **Test Migration**: `flask db upgrade` (apply to dev database)
5. **Verify Changes**: Test your application
6. **Commit**: Add migration file to git

### Production Deployment

1. **Backup Database**: Always backup before migrations
   ```bash
   pg_dump $PRODUCTION_DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Review Migration**: Inspect the migration file carefully
   ```bash
   cat migrations/versions/[migration_file].py
   ```

3. **Test on Staging**: Apply to staging environment first
   ```bash
   FLASK_APP=app.py PRODUCTION_DATABASE_URL=$STAGING_DB flask db upgrade
   ```

4. **Apply to Production**: Only after staging verification
   ```bash
   FLASK_APP=app.py PRODUCTION_DATABASE_URL=$PRODUCTION_DB flask db upgrade
   ```

5. **Monitor**: Watch application logs for errors

## Migration Best Practices

### ✅ DO

- **Review generated migrations**: Alembic isn't perfect, always review
- **Test migrations**: Apply to dev/staging before production
- **Make small changes**: One logical change per migration
- **Backup before production**: Always backup production database
- **Use descriptive messages**: `flask db migrate -m "Clear description"`
- **Commit migrations**: Add to version control immediately
- **Add default values**: For new required columns on existing data
- **Use batch operations**: For large table alterations

### ❌ DON'T

- **Don't skip migrations**: Apply all migrations in order
- **Don't edit applied migrations**: Create new ones instead
- **Don't delete migration files**: They're needed for downgrades
- **Don't assume Alembic is perfect**: Always review generated code
- **Don't apply untested migrations**: Test in dev/staging first
- **Don't forget indexes**: Alembic may not detect all index changes

## Advanced Usage

### Creating Empty Migration

For custom SQL or data migrations:
```bash
flask db revision -m "Custom data migration"
```

Then edit the generated file to add custom SQL.

### Rollback to Specific Version

```bash
# Rollback to specific migration
flask db downgrade [migration_id]

# Rollback all migrations
flask db downgrade base
```

### Branching and Merging

If you have multiple migration branches:
```bash
# Show branches
flask db branches

# Merge branches
flask db merge -m "Merge migration branches"
```

### Custom SQL in Migrations

```python
def upgrade():
    # Regular Alembic operations
    op.add_column('user', sa.Column('new_field', sa.String(50)))
    
    # Custom SQL
    op.execute('''
        UPDATE user 
        SET new_field = 'default_value' 
        WHERE new_field IS NULL
    ''')

def downgrade():
    op.drop_column('user', 'new_field')
```

## Troubleshooting

### Migration Not Detecting Changes

**Problem**: `flask db migrate` says "No changes detected"

**Solutions**:
1. Ensure models are imported in `app.py`
2. Check model changes are actually different
3. Try `flask db revision` to create empty migration
4. Review `env.py` to ensure all models are loaded

### Migration Conflicts

**Problem**: Multiple developers created migrations

**Solutions**:
1. Use `flask db branches` to see branches
2. Use `flask db merge` to combine migrations
3. Coordinate with team on migration creation

### Failed Migration

**Problem**: Migration fails during upgrade

**Solutions**:
1. Check error message carefully
2. Review migration file for issues
3. Fix migration file and try again
4. If needed, `flask db downgrade` and fix
5. For production: restore from backup if needed

### Alembic Version Mismatch

**Problem**: Database version doesn't match migration files

**Solutions**:
```bash
# Stamp database to specific version without running migration
flask db stamp [migration_id]

# Stamp to latest
flask db stamp head
```

## Migration File Structure

```python
"""Migration description

Revision ID: abc123def456
Revises: xyz789abc012
Create Date: 2025-10-25 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'abc123def456'
down_revision = 'xyz789abc012'
branch_labels = None
depends_on = None

def upgrade():
    # Operations to apply migration
    op.add_column('table_name', 
        sa.Column('column_name', sa.String(length=50), nullable=True)
    )

def downgrade():
    # Operations to rollback migration
    op.drop_column('table_name', 'column_name')
```

## Integration with CI/CD

### Pre-Deployment Checks

```bash
# Check if migrations are needed
flask db check

# Show pending migrations
flask db current
flask db heads

# Dry-run migration (show SQL without applying)
flask db upgrade --sql
```

### Automated Deployment

```bash
#!/bin/bash
# deploy.sh

# Backup database
pg_dump $PRODUCTION_DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Apply migrations
FLASK_APP=app.py flask db upgrade

# Restart application
# ... restart commands ...
```

## Manual SQL Migrations (Legacy)

The `migrations_manual_sql/` directory contains manually-written SQL migrations from before Alembic was set up. These have already been applied to the development database:

- `001_add_account_lockout_columns.sql` - Account lockout fields

**Note**: New migrations should use Alembic (above). Manual SQL migrations are preserved for reference only.

## Emergency Procedures

### Rollback Failed Migration

```bash
# 1. Check current state
flask db current

# 2. Rollback one version
flask db downgrade -1

# 3. Verify application works
# Test your application

# 4. Fix migration file
# Edit migrations/versions/[file].py

# 5. Re-apply
flask db upgrade
```

### Database Out of Sync

If database and migration files are out of sync:

```bash
# 1. Check what Alembic thinks is current
flask db current

# 2. Check actual database schema
psql $DATABASE_URL -c "\d user"  # Example table

# 3. Options:
# a) Stamp to current state (if you know it's correct)
flask db stamp head

# b) Or generate migration from scratch
# - Backup current migrations/
# - Delete migrations/versions/*.py
# - Run: flask db migrate -m "Regenerate from current state"
```

## Resources

- [Flask-Migrate Documentation](https://flask-migrate.readthedocs.io/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)

## Support

For migration issues:
1. Check this guide first
2. Review Alembic/Flask-Migrate documentation
3. Check application logs for specific errors
4. Review migration file generated by Alembic
5. Test in development environment before production

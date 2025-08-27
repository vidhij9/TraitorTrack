# 🗄️ RDS Data Migration Guide

This guide explains how to migrate your existing RDS PostgreSQL data to work with the updated TraceTrack schema while preserving all your existing data.

## 📋 Overview

The migration process will:
1. **Backup** your existing data
2. **Analyze** your current schema
3. **Create** new schema structure
4. **Migrate** data with field mapping
5. **Preserve** all relationships and data integrity

## 🔄 Schema Changes

### New Schema Structure

| Table | Purpose | Key Changes |
|-------|---------|-------------|
| `user` | User accounts | Enhanced role system, dispatch areas |
| `bag` | Bag tracking | Unified parent/child model, weight tracking |
| `link` | Parent-child relationships | Dedicated linking table |
| `bill` | Bill management | Enhanced bill tracking with weights |
| `bill_bag` | Bill-bag associations | Many-to-many relationship |
| `scan` | Scan history | Simplified scan tracking |
| `promotionrequest` | Admin requests | User promotion workflow |
| `audit_log` | System audit trail | Complete action logging |

### Field Mapping

The migration script automatically maps old field names to new ones:

#### User Table Mapping
```sql
-- Old fields → New fields
username/name → username
email → email
password_hash/password → password_hash
role → role
area → dispatch_area
verified → verified
```

#### Bag Table Mapping
```sql
-- Old fields → New fields
qr_id/qr_code/id → qr_id
type → type
name/bag_name → name
child_count/children_count → child_count
parent_id/parent_bag_id → parent_id
user_id/owner_id → user_id
dispatch_area/area → dispatch_area
status → status
weight_kg/weight → weight_kg
```

#### Scan Table Mapping
```sql
-- Old fields → New fields
timestamp/created_at → timestamp
parent_bag_id/parent_id → parent_bag_id
child_bag_id/child_id → child_bag_id
user_id/scanner_id → user_id
```

## 🚀 Migration Options

### Option 1: Automatic Migration (Recommended)

The deployment script will automatically run migration if `AWS_DATABASE_URL` is set:

```bash
# Set your RDS database URL
export AWS_DATABASE_URL="postgresql://user:pass@your-rds-endpoint:5432/dbname"

# Run deployment (includes migration)
./deploy.sh
```

### Option 2: Manual Migration

Run migration separately:

```bash
# Set database URL
export AWS_DATABASE_URL="postgresql://user:pass@your-rds-endpoint:5432/dbname"

# Run migration
python migrate_rds_simple.py
```

### Option 3: Advanced Migration

For complex schema differences:

```bash
# Use the comprehensive migration script
python migrate_existing_rds_data.py \
  --source-db-url "postgresql://user:pass@your-rds-endpoint:5432/dbname" \
  --backup-file "my_backup.json"
```

## 📊 Migration Process

### Step 1: Backup Creation
- Creates timestamped backup file
- Exports all existing data to JSON
- Preserves data integrity

### Step 2: Schema Analysis
- Detects existing table structure
- Identifies field differences
- Maps old fields to new schema

### Step 3: Schema Creation
- Creates new tables with `IF NOT EXISTS`
- Adds performance indexes
- Maintains referential integrity

### Step 4: Data Migration
- Migrates users with role mapping
- Migrates bags with type classification
- Migrates scans with relationship preservation
- Migrates bills with enhanced tracking
- Migrates links with parent-child relationships

### Step 5: Verification
- Validates data integrity
- Checks foreign key relationships
- Confirms all data preserved

## 🔧 Configuration

### Environment Variables

```bash
# Required for migration
AWS_DATABASE_URL="postgresql://user:pass@your-rds-endpoint:5432/dbname"

# Optional
DATABASE_URL="postgresql://user:pass@your-rds-endpoint:5432/dbname"
```

### Database Permissions

Your database user needs:
- `CREATE TABLE` permissions
- `INSERT` permissions
- `SELECT` permissions
- `CREATE INDEX` permissions

## 📁 Backup Files

Migration creates backup files:
- **Location**: Current directory
- **Format**: JSON with timestamp
- **Example**: `rds_backup_20250125_143022.json`

### Backup Structure
```json
{
  "user": [
    {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "role": "admin"
    }
  ],
  "bag": [
    {
      "id": 1,
      "qr_id": "PARENT001",
      "type": "parent",
      "name": "Parent Bag 1"
    }
  ],
  "scan": [
    {
      "id": 1,
      "timestamp": "2025-01-25T14:30:22",
      "parent_bag_id": 1,
      "user_id": 1
    }
  ]
}
```

## ⚠️ Important Notes

### Data Preservation
- **All existing data is preserved**
- **No data loss during migration**
- **Backup created before any changes**
- **Rollback possible using backup file**

### Schema Compatibility
- **Handles missing fields gracefully**
- **Maps common field name variations**
- **Creates default values for missing data**
- **Maintains data relationships**

### Performance
- **Uses transactions for data integrity**
- **Creates indexes for performance**
- **Handles large datasets efficiently**
- **Minimal downtime during migration**

## 🚨 Troubleshooting

### Common Issues

1. **Connection Failed**
   ```bash
   # Check database URL format
   export AWS_DATABASE_URL="postgresql://user:pass@host:port/dbname"
   ```

2. **Permission Denied**
   ```sql
   -- Grant necessary permissions
   GRANT CREATE, INSERT, SELECT ON DATABASE dbname TO username;
   ```

3. **Field Mapping Issues**
   ```bash
   # Check backup file for field names
   cat rds_backup_*.json | grep -A 5 "field_name"
   ```

4. **Migration Failed**
   ```bash
   # Check logs for specific errors
   python migrate_rds_simple.py 2>&1 | tee migration.log
   ```

### Recovery Options

1. **Restore from Backup**
   ```bash
   # Use backup file to restore data
   python restore_from_backup.py --backup-file rds_backup_*.json
   ```

2. **Manual Rollback**
   ```sql
   -- Drop new tables and recreate old ones
   DROP TABLE IF EXISTS new_table_name;
   -- Restore from backup
   ```

## ✅ Verification

After migration, verify:

1. **Data Counts**
   ```sql
   SELECT COUNT(*) FROM "user";
   SELECT COUNT(*) FROM bag;
   SELECT COUNT(*) FROM scan;
   ```

2. **Relationships**
   ```sql
   SELECT COUNT(*) FROM link WHERE parent_bag_id IS NOT NULL;
   SELECT COUNT(*) FROM bill_bag WHERE bill_id IS NOT NULL;
   ```

3. **Application Access**
   - Test login with existing users
   - Verify bag relationships
   - Check scan history
   - Test bill functionality

## 🎯 Post-Migration

### What's New
- **Enhanced user roles** (admin, biller, dispatcher)
- **Improved bag tracking** with weight calculations
- **Better bill management** with detailed tracking
- **Audit logging** for all system actions
- **Performance optimizations** with indexes

### What's Preserved
- **All user accounts** and passwords
- **All bag data** and relationships
- **All scan history** and timestamps
- **All bill information** and associations
- **All existing functionality**

## 📞 Support

If you encounter issues:
1. Check the backup file for data verification
2. Review migration logs for specific errors
3. Verify database permissions and connectivity
4. Test with a small dataset first

The migration is designed to be safe and reversible, with comprehensive backup and logging throughout the process.
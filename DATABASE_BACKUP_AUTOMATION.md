# TraitorTrack Database Backup Automation

**Version:** 1.0.0  
**Last Updated:** November 2025  
**System:** TraitorTrack Warehouse Bag Tracking System

---

## Table of Contents

1. [Overview](#overview)
2. [Automated Backup Strategies](#automated-backup-strategies)
3. [PostgreSQL Backup Tools](#postgresql-backup-tools)
4. [Backup Scheduling](#backup-scheduling)
5. [Cloud Backup Solutions](#cloud-backup-solutions)
6. [Backup Retention Policies](#backup-retention-policies)
7. [Backup Verification and Testing](#backup-verification-and-testing)
8. [Restore Procedures](#restore-procedures)
9. [Monitoring Backup Health](#monitoring-backup-health)
10. [Cost Optimization](#cost-optimization)

---

## Overview

### Importance of Database Backups

TraitorTrack's PostgreSQL database contains critical business data:

- **1.8M+ bags** with parent-child relationships
- **Bill records** with financial data
- **User accounts** and authentication data
- **Audit logs** for compliance and security
- **Scan history** for operational tracking

**Risk of Data Loss:**
- Hardware failure
- Human error (accidental deletion)
- Software bugs
- Security breaches (ransomware)
- Natural disasters

**Business Impact Without Backups:**
- Complete loss of operational data
- Unable to resume business operations
- Regulatory compliance violations
- Customer trust damage
- Financial losses: $50,000-500,000+

### Backup Strategy Summary

| Backup Type | Frequency | Retention | Storage | RPO | Use Case |
|-------------|-----------|-----------|---------|-----|----------|
| **Full** | Daily | 30 days | S3 Standard | 24 hours | Complete restore |
| **Incremental** | Every 6 hours | 7 days | S3 Standard | 6 hours | Point-in-time recovery |
| **Continuous (WAL)** | Real-time | 7 days | S3 Standard | 5 minutes | Minimal data loss |
| **Weekly Full** | Weekly | 90 days | S3 IA | 7 days | Long-term archive |
| **Monthly Archive** | Monthly | 1 year | S3 Glacier | 30 days | Compliance/audit |

**Total Storage Estimate:**
- Database size: ~50GB
- Daily backups (30 days): ~1.5TB
- Weekly backups (12 weeks): ~600GB
- Monthly backups (12 months): ~600GB
- **Total:** ~2.7TB

**Estimated Monthly Cost:** $60-80 (see [Cost Optimization](#cost-optimization))

---

## Automated Backup Strategies

### 1. Full Backup Strategy

**Definition:** Complete copy of entire database

**Advantages:**
- ✅ Simplest to restore
- ✅ Self-contained (no dependencies)
- ✅ Fastest recovery time
- ✅ Easy to verify

**Disadvantages:**
- ❌ Largest storage requirement
- ❌ Slowest backup time
- ❌ Higher network bandwidth usage

**Recommended Schedule:** Daily at 3:00 AM (low-traffic period)

**Implementation:**

```bash
#!/bin/bash
# /opt/scripts/backup_full_daily.sh

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/daily"
DB_NAME="traitortrack"
S3_BUCKET="s3://traitortrack-backups"
RETENTION_DAYS=30

# Logging
LOG_FILE="/var/log/traitortrack/backups/backup_full_${BACKUP_DATE}.log"
mkdir -p $(dirname $LOG_FILE)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

log "=== Starting Full Backup ==="
log "Database: $DB_NAME"
log "Timestamp: $BACKUP_DATE"

# Create local backup directory
mkdir -p $BACKUP_DIR

# Perform backup with compression
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_full_${BACKUP_DATE}.sql.gz"
log "Creating backup: $BACKUP_FILE"

START_TIME=$(date +%s)

pg_dump $PRODUCTION_DATABASE_URL \
    --clean --if-exists --create \
    --verbose \
    --no-owner --no-privileges \
    2>&1 | tee -a $LOG_FILE | gzip > $BACKUP_FILE

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
BACKUP_SIZE=$(du -h $BACKUP_FILE | cut -f1)

log "Backup completed in ${DURATION}s, size: $BACKUP_SIZE"

# Verify backup integrity
log "Verifying backup integrity..."
if gunzip -t $BACKUP_FILE 2>&1 | tee -a $LOG_FILE; then
    log "✓ Backup integrity verified"
else
    log "✗ Backup integrity check FAILED"
    exit 1
fi

# Upload to S3
log "Uploading to S3..."
aws s3 cp $BACKUP_FILE "${S3_BUCKET}/daily/" \
    --storage-class STANDARD \
    --metadata "backup-type=full,timestamp=$BACKUP_DATE,duration=$DURATION,size=$BACKUP_SIZE" \
    2>&1 | tee -a $LOG_FILE

if [ $? -eq 0 ]; then
    log "✓ Uploaded to S3 successfully"
else
    log "✗ S3 upload FAILED"
    exit 1
fi

# Clean up old local backups
log "Cleaning up local backups older than $RETENTION_DAYS days..."
find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
DELETED_COUNT=$(find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS | wc -l)
log "Deleted $DELETED_COUNT old backups"

# Clean up old S3 backups
log "Cleaning up S3 backups older than $RETENTION_DAYS days..."
CUTOFF_DATE=$(date -d "$RETENTION_DAYS days ago" +%Y%m%d)
aws s3 ls ${S3_BUCKET}/daily/ | while read -r line; do
    FILE_DATE=$(echo $line | awk '{print $4}' | grep -oP '\d{8}')
    if [ "$FILE_DATE" -lt "$CUTOFF_DATE" ]; then
        FILE_NAME=$(echo $line | awk '{print $4}')
        log "Deleting old backup: $FILE_NAME"
        aws s3 rm "${S3_BUCKET}/daily/$FILE_NAME"
    fi
done

# Send notification
log "Sending backup notification..."
/opt/scripts/notify_backup_success.sh \
    --type "full" \
    --size "$BACKUP_SIZE" \
    --duration "$DURATION" \
    --timestamp "$BACKUP_DATE"

log "=== Backup Complete ==="
log "Summary: $BACKUP_FILE ($BACKUP_SIZE) in ${DURATION}s"

exit 0
```

### 2. Incremental Backup Strategy

**Definition:** Backup only changes since last full backup

**Advantages:**
- ✅ Faster backup time (5-10 minutes vs 30-60 minutes)
- ✅ Less storage space
- ✅ Lower network usage
- ✅ Can run more frequently

**Disadvantages:**
- ❌ Slower restore (need full + all incrementals)
- ❌ More complex restore procedure
- ❌ Dependency on previous backups

**Recommended Schedule:** Every 6 hours

**Implementation with pg_basebackup:**

```bash
#!/bin/bash
# /opt/scripts/backup_incremental.sh

set -e

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/incremental"
S3_BUCKET="s3://traitortrack-backups"

# Check if full backup exists today
LATEST_FULL=$(aws s3 ls ${S3_BUCKET}/daily/ | grep $(date +%Y%m%d) | tail -n1 | awk '{print $4}')

if [ -z "$LATEST_FULL" ]; then
    echo "No full backup found for today, creating one first..."
    /opt/scripts/backup_full_daily.sh
fi

# Create incremental backup using WAL archiving
# This requires WAL archiving to be enabled (see Continuous Backup section)

mkdir -p $BACKUP_DIR

# Archive current WAL files
pg_receivewal -D ${BACKUP_DIR}/wal_${BACKUP_DATE} \
    --synchronous \
    --compress=9 \
    --dbname=$PRODUCTION_DATABASE_URL \
    --slot incremental_backup \
    --verbose

# Upload to S3
tar -czf ${BACKUP_DIR}/incremental_${BACKUP_DATE}.tar.gz \
    ${BACKUP_DIR}/wal_${BACKUP_DATE}

aws s3 cp ${BACKUP_DIR}/incremental_${BACKUP_DATE}.tar.gz \
    ${S3_BUCKET}/incremental/ \
    --storage-class STANDARD

# Cleanup
rm -rf ${BACKUP_DIR}/wal_${BACKUP_DATE}
rm ${BACKUP_DIR}/incremental_${BACKUP_DATE}.tar.gz

echo "✓ Incremental backup complete: incremental_${BACKUP_DATE}.tar.gz"
```

### 3. Continuous Backup (WAL Archiving)

**Definition:** Real-time streaming of Write-Ahead Logs (WAL)

**Advantages:**
- ✅ Minimal data loss (RPO: ~5 minutes)
- ✅ Point-in-time recovery (PITR)
- ✅ Continuous protection
- ✅ No backup window required

**Disadvantages:**
- ❌ More complex setup
- ❌ Requires more storage
- ❌ Needs monitoring

**Recommended:** Always enable for production

**Setup WAL Archiving:**

**For AWS RDS (Automatic):**

```bash
# Enable automated backups (includes WAL archiving)
aws rds modify-db-instance \
    --db-instance-identifier traitortrack-primary \
    --backup-retention-period 7 \
    --apply-immediately

# Verify settings
aws rds describe-db-instances \
    --db-instance-identifier traitortrack-primary \
    --query 'DBInstances[0].[BackupRetentionPeriod,PreferredBackupWindow]'
```

**For Self-Managed PostgreSQL:**

**postgresql.conf:**

```conf
# Enable WAL archiving
wal_level = replica
archive_mode = on
archive_command = '/opt/scripts/archive_wal.sh %p %f'
archive_timeout = 300  # Archive every 5 minutes
max_wal_size = 4GB
min_wal_size = 1GB
```

**Archive Script (/opt/scripts/archive_wal.sh):**

```bash
#!/bin/bash
# Archive WAL file to S3

WAL_PATH=$1
WAL_FILE=$2
S3_BUCKET="s3://traitortrack-backups/wal"

# Compress and upload
gzip -c $WAL_PATH | aws s3 cp - ${S3_BUCKET}/${WAL_FILE}.gz \
    --metadata "archive-time=$(date -u +%Y%m%dT%H%M%SZ)"

# Verify upload
if [ $? -eq 0 ]; then
    exit 0
else
    echo "WAL archive failed: $WAL_FILE" >> /var/log/postgresql/archive_errors.log
    exit 1
fi
```

**Restart PostgreSQL:**

```bash
sudo systemctl restart postgresql
```

**Verify WAL Archiving:**

```sql
-- Check WAL archiving status
SELECT name, setting FROM pg_settings WHERE name LIKE 'archive%';

-- Force WAL switch to test archiving
SELECT pg_switch_wal();

-- Check archive status
SELECT archived_count, failed_count 
FROM pg_stat_archiver;
```

---

## PostgreSQL Backup Tools

### 1. pg_dump (Logical Backup)

**Best For:** Development, testing, smaller databases

**Advantages:**
- ✅ Human-readable SQL format
- ✅ Selective backup (specific tables/schemas)
- ✅ Cross-version compatible
- ✅ Easy to inspect and modify

**Disadvantages:**
- ❌ Slower for large databases
- ❌ No point-in-time recovery
- ❌ Locks tables during dump

**Basic Usage:**

```bash
# Full database dump
pg_dump $PRODUCTION_DATABASE_URL \
    --clean --if-exists \
    --file=traitortrack_backup.sql

# Compressed dump
pg_dump $PRODUCTION_DATABASE_URL \
    --clean --if-exists \
    --format=custom \
    --compress=9 \
    --file=traitortrack_backup.dump

# Specific tables only
pg_dump $PRODUCTION_DATABASE_URL \
    --table=bag --table=bill \
    --file=critical_tables_backup.sql

# Exclude audit logs (for smaller backup)
pg_dump $PRODUCTION_DATABASE_URL \
    --exclude-table=audit_log \
    --file=traitortrack_without_audit.sql
```

**Parallel Dump (Faster for Large Databases):**

```bash
# Use 4 parallel jobs
pg_dump $PRODUCTION_DATABASE_URL \
    --format=directory \
    --jobs=4 \
    --file=traitortrack_backup_dir

# Restore from parallel dump
pg_restore --dbname=$PRODUCTION_DATABASE_URL \
    --jobs=4 \
    --verbose \
    traitortrack_backup_dir
```

### 2. pg_basebackup (Physical Backup)

**Best For:** Production, large databases, PITR

**Advantages:**
- ✅ Faster than pg_dump for large databases
- ✅ Supports point-in-time recovery
- ✅ Binary copy (exact replica)
- ✅ Can be used for replication

**Disadvantages:**
- ❌ Version-specific (PostgreSQL version must match)
- ❌ Backup entire cluster (not selective)
- ❌ Larger backup size

**Basic Usage:**

```bash
# Create base backup
pg_basebackup -h db-host -U postgres \
    --pgdata=/backups/base \
    --format=tar \
    --gzip \
    --compress=9 \
    --checkpoint=fast \
    --progress \
    --verbose

# Backup with WAL files included
pg_basebackup -h db-host -U postgres \
    --pgdata=/backups/base \
    --format=tar \
    --wal-method=fetch \
    --gzip \
    --compress=9 \
    --progress
```

**Advanced: Backup to S3 Directly:**

```bash
# Stream backup directly to S3
pg_basebackup -h db-host -U postgres \
    --format=tar \
    --gzip \
    --compress=9 \
    --wal-method=stream \
    --progress \
    | aws s3 cp - s3://traitortrack-backups/base/backup_$(date +%Y%m%d).tar.gz
```

### 3. pg_dumpall (Cluster-Wide Backup)

**Best For:** Backing up all databases and global objects

**Usage:**

```bash
# Backup all databases and roles
pg_dumpall -h db-host -U postgres \
    --clean --if-exists \
    | gzip > cluster_backup.sql.gz

# Backup only global objects (roles, tablespaces)
pg_dumpall -h db-host -U postgres \
    --globals-only \
    > globals_backup.sql
```

### 4. Barman (Backup and Recovery Manager)

**Best For:** Enterprise production environments

**Features:**
- Full and incremental backups
- Point-in-time recovery
- Retention policies
- Compression and encryption
- Remote backup

**Installation:**

```bash
# Install Barman
sudo apt-get install barman

# Configure Barman server
sudo -u barman vim /etc/barman.d/traitortrack.conf
```

**Configuration (/etc/barman.d/traitortrack.conf):**

```ini
[traitortrack]
description = "TraitorTrack Production Database"
ssh_command = ssh postgres@db-server
conninfo = host=db-server user=barman dbname=traitortrack
backup_method = rsync
reuse_backup = link
backup_options = concurrent_backup
archiver = on
compression = gzip
```

**Usage:**

```bash
# Perform backup
barman backup traitortrack

# List backups
barman list-backup traitortrack

# Restore to specific time
barman recover traitortrack latest /var/lib/postgresql/14/main \
    --target-time "2025-11-25 10:30:00"
```

---

## Backup Scheduling

### Cron-Based Scheduling

**Edit crontab:**

```bash
sudo crontab -e
```

**Backup Schedule:**

```cron
# TraitorTrack Database Backup Schedule

# Daily full backup at 3:00 AM
0 3 * * * /opt/scripts/backup_full_daily.sh >> /var/log/traitortrack/backups/cron.log 2>&1

# Incremental backups every 6 hours
0 */6 * * * /opt/scripts/backup_incremental.sh >> /var/log/traitortrack/backups/cron.log 2>&1

# Weekly full backup with extended retention (Sundays at 2:00 AM)
0 2 * * 0 /opt/scripts/backup_weekly.sh >> /var/log/traitortrack/backups/cron.log 2>&1

# Monthly archive (1st of month at 1:00 AM)
0 1 1 * * /opt/scripts/backup_monthly_archive.sh >> /var/log/traitortrack/backups/cron.log 2>&1

# Backup verification (daily at 5:00 AM)
0 5 * * * /opt/scripts/verify_latest_backup.sh >> /var/log/traitortrack/backups/cron.log 2>&1

# Cleanup old logs (weekly)
0 0 * * 0 find /var/log/traitortrack/backups -name "*.log" -mtime +30 -delete
```

### Systemd Timer (Modern Alternative to Cron)

**Create service file (/etc/systemd/system/traitortrack-backup.service):**

```ini
[Unit]
Description=TraitorTrack Database Backup
After=network.target postgresql.service

[Service]
Type=oneshot
User=postgres
ExecStart=/opt/scripts/backup_full_daily.sh
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Create timer file (/etc/systemd/system/traitortrack-backup.timer):**

```ini
[Unit]
Description=TraitorTrack Daily Backup Timer
Requires=traitortrack-backup.service

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 03:00:00
Persistent=true
AccuracySec=5min

[Install]
WantedBy=timers.target
```

**Enable and start timer:**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable timer (start on boot)
sudo systemctl enable traitortrack-backup.timer

# Start timer now
sudo systemctl start traitortrack-backup.timer

# Check timer status
sudo systemctl list-timers traitortrack-backup.timer

# View logs
sudo journalctl -u traitortrack-backup.service -f
```

---

## Cloud Backup Solutions

### 1. AWS RDS Automated Backups

**Features:**
- ✅ Fully managed by AWS
- ✅ Point-in-time recovery
- ✅ No maintenance required
- ✅ Automatic retention management

**Configuration:**

```bash
# Enable automated backups
aws rds modify-db-instance \
    --db-instance-identifier traitortrack-primary \
    --backup-retention-period 7 \
    --preferred-backup-window "03:00-04:00" \
    --apply-immediately

# Enable backup copy to another region (DR)
aws rds create-db-instance-read-replica \
    --db-instance-identifier traitortrack-backup-replica \
    --source-db-instance-identifier traitortrack-primary \
    --source-region us-east-1 \
    --region us-west-2
```

**Restore from RDS Backup:**

```bash
# List available restore points
aws rds describe-db-instance-automated-backups \
    --db-instance-identifier traitortrack-primary

# Restore to point in time
aws rds restore-db-instance-to-point-in-time \
    --source-db-instance-identifier traitortrack-primary \
    --target-db-instance-identifier traitortrack-restored \
    --restore-time 2025-11-25T10:30:00Z
```

**Cost:**
- Included with RDS instance cost
- Storage cost: ~$0.095/GB-month
- For 50GB database: ~$4.75/month

### 2. Neon Backups (Replit Integrated)

**Features:**
- ✅ Built-in to Replit PostgreSQL
- ✅ Point-in-time recovery (PITR)
- ✅ Automatic retention
- ✅ One-click restore in Replit UI

**Configuration:**

Neon automatically backs up your database:
- **Frequency:** Continuous (WAL-based)
- **Retention:** 7 days (free tier), 30 days (paid)
- **Storage:** Managed by Neon

**Restore from Neon:**

1. Open Replit Database tab
2. Click "Backups"
3. Select restore point
4. Click "Restore to new database" or "Restore in place"

**Cost:**
- Free tier: 7-day retention, 0.5GB storage
- Pro tier: 30-day retention, 10GB storage ($8/month)

### 3. S3 Backup Storage

**Backup Storage Strategy:**

```
s3://traitortrack-backups/
├── daily/          # Daily full backups (30-day retention)
├── weekly/         # Weekly backups (90-day retention)
├── monthly/        # Monthly archives (1-year retention)
├── wal/            # Continuous WAL files (7-day retention)
└── incremental/    # Incremental backups (7-day retention)
```

**Create S3 Bucket:**

```bash
# Create bucket with versioning
aws s3api create-bucket \
    --bucket traitortrack-backups \
    --region us-east-1

aws s3api put-bucket-versioning \
    --bucket traitortrack-backups \
    --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
    --bucket traitortrack-backups \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            }
        }]
    }'

# Set lifecycle policies
aws s3api put-bucket-lifecycle-configuration \
    --bucket traitortrack-backups \
    --lifecycle-configuration file://lifecycle.json
```

**Lifecycle Policy (lifecycle.json):**

```json
{
  "Rules": [
    {
      "Id": "Daily backups - 30 day retention",
      "Status": "Enabled",
      "Filter": {"Prefix": "daily/"},
      "Expiration": {"Days": 30},
      "Transitions": [
        {
          "Days": 7,
          "StorageClass": "STANDARD_IA"
        }
      ]
    },
    {
      "Id": "Weekly backups - 90 day retention",
      "Status": "Enabled",
      "Filter": {"Prefix": "weekly/"},
      "Expiration": {"Days": 90},
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "GLACIER"
        }
      ]
    },
    {
      "Id": "Monthly archives - 1 year retention",
      "Status": "Enabled",
      "Filter": {"Prefix": "monthly/"},
      "Expiration": {"Days": 365},
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "DEEP_ARCHIVE"
        }
      ]
    }
  ]
}
```

---

## Backup Retention Policies

### Retention Strategy

**Grandfather-Father-Son (GFS) Strategy:**

```
┌──────────────────────────────────────────────────┐
│                   Retention Timeline             │
├──────────────────────────────────────────────────┤
│ Daily (Son):    Last 30 days                     │
│ Weekly (Father): Last 12 weeks (3 months)        │
│ Monthly (Grandfather): Last 12 months (1 year)   │
└──────────────────────────────────────────────────┘
```

**Retention Configuration:**

| Backup Type | Frequency | Keep | Storage Class | Cost/GB |
|-------------|-----------|------|---------------|---------|
| Daily | Every day | 30 days | S3 Standard → IA after 7 days | $0.023 |
| Weekly | Sunday | 12 weeks | S3 Standard → Glacier after 30 days | $0.004 |
| Monthly | 1st of month | 12 months | S3 Glacier Deep Archive | $0.00099 |
| Continuous (WAL) | Real-time | 7 days | S3 Standard | $0.023 |

**Script to Enforce Retention:**

```bash
#!/bin/bash
# /opt/scripts/enforce_retention.sh

S3_BUCKET="s3://traitortrack-backups"

# Daily backups - delete older than 30 days
aws s3 ls ${S3_BUCKET}/daily/ | while read -r line; do
    CREATE_DATE=$(echo $line | awk '{print $1}')
    FILE_NAME=$(echo $line | awk '{print $4}')
    FILE_AGE=$(( ($(date +%s) - $(date -d "$CREATE_DATE" +%s)) / 86400 ))
    
    if [ $FILE_AGE -gt 30 ]; then
        echo "Deleting daily backup: $FILE_NAME (age: $FILE_AGE days)"
        aws s3 rm "${S3_BUCKET}/daily/$FILE_NAME"
    fi
done

# Weekly backups - delete older than 90 days
aws s3 ls ${S3_BUCKET}/weekly/ | while read -r line; do
    CREATE_DATE=$(echo $line | awk '{print $1}')
    FILE_NAME=$(echo $line | awk '{print $4}')
    FILE_AGE=$(( ($(date +%s) - $(date -d "$CREATE_DATE" +%s)) / 86400 ))
    
    if [ $FILE_AGE -gt 90 ]; then
        echo "Deleting weekly backup: $FILE_NAME (age: $FILE_AGE days)"
        aws s3 rm "${S3_BUCKET}/weekly/$FILE_NAME"
    fi
done

# Monthly backups - delete older than 365 days
aws s3 ls ${S3_BUCKET}/monthly/ | while read -r line; do
    CREATE_DATE=$(echo $line | awk '{print $1}')
    FILE_NAME=$(echo $line | awk '{print $4}')
    FILE_AGE=$(( ($(date +%s) - $(date -d "$CREATE_DATE" +%s)) / 86400 ))
    
    if [ $FILE_AGE -gt 365 ]; then
        echo "Deleting monthly archive: $FILE_NAME (age: $FILE_AGE days)"
        aws s3 rm "${S3_BUCKET}/monthly/$FILE_NAME"
    fi
done

echo "✓ Retention policy enforced"
```

---

## Backup Verification and Testing

### Automated Verification Script

```bash
#!/bin/bash
# /opt/scripts/verify_latest_backup.sh

set -e

S3_BUCKET="s3://traitortrack-backups"
TEST_DB="traitortrack_test_restore"
LOG_FILE="/var/log/traitortrack/backups/verify_$(date +%Y%m%d).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

log "=== Starting Backup Verification ==="

# Get latest backup
LATEST_BACKUP=$(aws s3 ls ${S3_BUCKET}/daily/ | sort | tail -n1 | awk '{print $4}')

if [ -z "$LATEST_BACKUP" ]; then
    log "✗ ERROR: No backup found in S3"
    exit 1
fi

log "Latest backup: $LATEST_BACKUP"

# Download backup
log "Downloading backup..."
aws s3 cp "${S3_BUCKET}/daily/${LATEST_BACKUP}" /tmp/

# Verify file integrity
log "Verifying file integrity..."
if gunzip -t /tmp/$LATEST_BACKUP; then
    log "✓ File integrity OK"
else
    log "✗ File corrupted"
    exit 1
fi

# Create test database
log "Creating test database..."
psql postgres://user:pass@host:5432/postgres -c "DROP DATABASE IF EXISTS $TEST_DB;"
psql postgres://user:pass@host:5432/postgres -c "CREATE DATABASE $TEST_DB;"

# Restore to test database
log "Restoring to test database..."
START_TIME=$(date +%s)
gunzip -c /tmp/$LATEST_BACKUP | psql postgres://user:pass@host:5432/$TEST_DB 2>&1 | tee -a $LOG_FILE
END_TIME=$(date +%s)
RESTORE_DURATION=$((END_TIME - START_TIME))

log "Restore completed in ${RESTORE_DURATION}s"

# Verify data integrity
log "Verifying data integrity..."

# Check record counts
RECORD_COUNTS=$(psql postgres://user:pass@host:5432/$TEST_DB -t -c "
    SELECT 
        'bags: ' || COUNT(*) FROM bag
    UNION ALL
    SELECT 'bills: ' || COUNT(*) FROM bill
    UNION ALL
    SELECT 'users: ' || COUNT(*) FROM \"user\"
    UNION ALL
    SELECT 'scans: ' || COUNT(*) FROM scan;
" | tr '\n' ', ')

log "Record counts: $RECORD_COUNTS"

# Check for data consistency
CONSISTENCY_CHECK=$(psql postgres://user:pass@host:5432/$TEST_DB -t -c "
    SELECT COUNT(*) 
    FROM bag b 
    LEFT JOIN link l ON b.id = l.child_id 
    WHERE b.type = 'child' AND l.id IS NULL;
")

if [ "$CONSISTENCY_CHECK" -gt 0 ]; then
    log "⚠ WARNING: Found $CONSISTENCY_CHECK orphaned child bags"
else
    log "✓ Data consistency OK"
fi

# Check schema integrity
SCHEMA_CHECK=$(psql postgres://user:pass@host:5432/$TEST_DB -t -c "
    SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';
")

log "Tables found: $SCHEMA_CHECK"

if [ "$SCHEMA_CHECK" -lt 10 ]; then
    log "✗ ERROR: Missing tables"
    exit 1
fi

# Cleanup
log "Cleaning up..."
psql postgres://user:pass@host:5432/postgres -c "DROP DATABASE $TEST_DB;"
rm /tmp/$LATEST_BACKUP

log "=== Verification Complete ==="
log "Status: ✓ SUCCESS"
log "Backup: $LATEST_BACKUP"
log "Restore time: ${RESTORE_DURATION}s"

# Send notification
/opt/scripts/notify_backup_verified.sh \
    --backup "$LATEST_BACKUP" \
    --duration "$RESTORE_DURATION" \
    --records "$RECORD_COUNTS"

exit 0
```

**Schedule Daily:**

```cron
# Verify backup daily at 5:00 AM
0 5 * * * /opt/scripts/verify_latest_backup.sh
```

### Manual Testing Checklist

**Quarterly Full Restore Test:**

- [ ] Select backup from previous quarter
- [ ] Create new test database instance
- [ ] Restore full backup
- [ ] Verify all tables present
- [ ] Check record counts match expected values
- [ ] Test application connectivity
- [ ] Perform sample queries
- [ ] Check foreign key constraints
- [ ] Verify indexes exist
- [ ] Test user authentication
- [ ] Document restore time
- [ ] Clean up test environment

---

## Restore Procedures

### Full Restore from pg_dump

```bash
#!/bin/bash
# restore_full_backup.sh

# Confirm restore operation
read -p "⚠️  This will OVERWRITE the database. Type 'RESTORE' to confirm: " CONFIRM
if [ "$CONFIRM" != "RESTORE" ]; then
    echo "Restore cancelled"
    exit 1
fi

BACKUP_FILE=$1
DB_URL=$PRODUCTION_DATABASE_URL

# Stop application to prevent writes
sudo systemctl stop traitortrack

# Terminate existing connections
psql $DB_URL -c "
    SELECT pg_terminate_backend(pid) 
    FROM pg_stat_activity 
    WHERE datname = 'traitortrack' AND pid <> pg_backend_pid();
"

# Drop and recreate database
psql postgres://user:pass@host:5432/postgres -c "DROP DATABASE traitortrack;"
psql postgres://user:pass@host:5432/postgres -c "CREATE DATABASE traitortrack;"

# Restore backup
gunzip -c $BACKUP_FILE | psql $DB_URL

# Verify restore
psql $DB_URL -c "SELECT COUNT(*) FROM bag;"

# Restart application
sudo systemctl start traitortrack

echo "✓ Restore complete"
```

### Point-in-Time Recovery (PITR) from WAL

```bash
#!/bin/bash
# pitr_restore.sh

TARGET_TIME="2025-11-25 10:30:00"
BASE_BACKUP="/backups/base/backup_20251125.tar.gz"
WAL_ARCHIVE="s3://traitortrack-backups/wal/"

# Extract base backup
mkdir -p /var/lib/postgresql/14/pitr_restore
tar -xzf $BASE_BACKUP -C /var/lib/postgresql/14/pitr_restore

# Create recovery configuration
cat > /var/lib/postgresql/14/pitr_restore/recovery.conf <<EOF
restore_command = 'aws s3 cp ${WAL_ARCHIVE}%f.gz - | gunzip > %p'
recovery_target_time = '$TARGET_TIME'
recovery_target_action = 'promote'
EOF

# Start PostgreSQL in recovery mode
sudo -u postgres /usr/lib/postgresql/14/bin/postgres \
    -D /var/lib/postgresql/14/pitr_restore

# Wait for recovery to complete (monitor logs)
tail -f /var/lib/postgresql/14/pitr_restore/log/postgresql-*.log

# Once promoted, update connection string and restart app
export PRODUCTION_DATABASE_URL="postgresql://user:pass@localhost:5432/traitortrack"
sudo systemctl restart traitortrack
```

---

## Monitoring Backup Health

### Backup Success Monitoring

```python
# /opt/scripts/monitor_backups.py
import boto3
from datetime import datetime, timedelta
import sys

def check_backup_health():
    s3 = boto3.client('s3')
    bucket = 'traitortrack-backups'
    
    # Check daily backups
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    # List objects from yesterday
    prefix = f'daily/'
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    
    if 'Contents' not in response:
        print("❌ No daily backups found")
        sys.exit(1)
    
    # Check if backup from yesterday exists
    yesterday_backups = [
        obj for obj in response['Contents']
        if yesterday.strftime('%Y%m%d') in obj['Key']
    ]
    
    if not yesterday_backups:
        print(f"❌ No backup found for {yesterday}")
        sys.exit(1)
    
    # Check backup size
    latest_backup = max(yesterday_backups, key=lambda x: x['LastModified'])
    backup_size_gb = latest_backup['Size'] / (1024**3)
    
    # Expected size: ~50GB compressed
    if backup_size_gb < 10:
        print(f"⚠️  Backup size unusually small: {backup_size_gb:.2f} GB")
        sys.exit(1)
    
    print(f"✓ Backup health OK")
    print(f"  Latest: {latest_backup['Key']}")
    print(f"  Size: {backup_size_gb:.2f} GB")
    print(f"  Time: {latest_backup['LastModified']}")
    
    return 0

if __name__ == '__main__':
    sys.exit(check_backup_health())
```

### CloudWatch Alarms

```bash
# Alert if no backup in last 25 hours
aws cloudwatch put-metric-alarm \
    --alarm-name traitortrack-backup-missing \
    --alarm-description "No database backup in last 25 hours" \
    --metric-name BackupAge \
    --namespace TraitorTrack \
    --statistic Maximum \
    --period 3600 \
    --threshold 25 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 1 \
    --alarm-actions arn:aws:sns:us-east-1:123456789:backup-alerts
```

---

## Cost Optimization

### Storage Cost Breakdown

**Monthly Cost Estimate (50GB database):**

| Storage Type | Usage | Storage Class | Cost/GB | Monthly Cost |
|--------------|-------|---------------|---------|--------------|
| Daily backups (30 days) | 1.5TB | Standard → IA | $0.023 → $0.0125 | $28.13 |
| Weekly backups (12 weeks) | 600GB | Glacier | $0.004 | $2.40 |
| Monthly backups (12 months) | 600GB | Deep Archive | $0.00099 | $0.59 |
| WAL archives (7 days) | 350GB | Standard | $0.023 | $8.05 |
| **Total** | **~3TB** | | | **~$39.17/month** |

**Cost Optimization Strategies:**

### 1. Compress Backups

```bash
# Use maximum compression
pg_dump $DATABASE_URL | gzip -9 > backup.sql.gz

# Compression ratio: ~80% reduction
# 50GB → 10GB = $30/month savings
```

### 2. Transition to Cheaper Storage Classes

```bash
# Move old backups to Glacier after 7 days
aws s3api put-object-lifecycle-configuration \
    --bucket traitortrack-backups \
    --lifecycle-configuration file://lifecycle.json
```

### 3. Deduplicate Incremental Backups

```bash
# Use incremental backups instead of full backups
# Storage savings: ~70%
```

### 4. Optimize Retention Policies

| Adjustment | Savings |
|------------|---------|
| Daily backups: 30 → 7 days | -$21.50/month |
| WAL archives: 7 → 3 days | -$4.60/month |
| Total potential savings | -$26.10/month |

**Recommended minimal retention:**
- Daily: 7 days (sufficient for most scenarios)
- Weekly: 4 weeks
- Monthly: 6 months
- **New Monthly Cost:** ~$13/month

---

## Summary

TraitorTrack's database backup automation ensures data protection and business continuity:

**Backup Strategy:**
- ✅ Daily full backups (RPO: 24 hours)
- ✅ Continuous WAL archiving (RPO: 5 minutes)
- ✅ Automated retention management
- ✅ Regular verification testing

**Tools Used:**
- pg_dump for logical backups
- WAL archiving for continuous backup
- AWS S3 for backup storage
- Automated scripts for backup/restore

**Cost:** ~$13-40/month (depending on retention policy)

**Next Steps:**

1. Set up S3 bucket with lifecycle policies
2. Configure daily backup scripts
3. Enable WAL archiving
4. Test restore procedures
5. Schedule verification tests

**See Also:**

- [DISASTER_RECOVERY_PROCEDURES.md](DISASTER_RECOVERY_PROCEDURES.md) - DR planning and testing
- [DATABASE_READ_REPLICA_GUIDE.md](DATABASE_READ_REPLICA_GUIDE.md) - Read replica setup
- [OPERATIONAL_RUNBOOK.md](OPERATIONAL_RUNBOOK.md) - Database maintenance

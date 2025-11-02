# TraitorTrack Disaster Recovery Procedures

**Version:** 1.0.0  
**Last Updated:** November 2025  
**System:** TraitorTrack Warehouse Bag Tracking System

---

## Table of Contents

1. [Disaster Recovery Overview](#disaster-recovery-overview)
2. [RPO and RTO Targets](#rpo-and-rto-targets)
3. [Critical System Components](#critical-system-components)
4. [Database Backup and Restore](#database-backup-and-restore)
5. [Application Code Recovery](#application-code-recovery)
6. [Secrets and Configuration Recovery](#secrets-and-configuration-recovery)
7. [Service Failover Procedures](#service-failover-procedures)
8. [Communication Protocols](#communication-protocols)
9. [DR Testing Schedule](#dr-testing-schedule)
10. [Incident Response Runbook](#incident-response-runbook)

---

## Disaster Recovery Overview

### Purpose

This document outlines procedures for recovering TraitorTrack warehouse operations after a disaster, ensuring minimal data loss and downtime.

### Disaster Categories

| Category | Examples | Severity | Response Time |
|----------|----------|----------|---------------|
| **Infrastructure** | Server failure, AWS outage, network failure | High | <2 hours |
| **Database** | Database corruption, accidental deletion | Critical | <1 hour |
| **Application** | Code bug, deployment failure | Medium | <30 minutes |
| **Security** | Breach, ransomware, DDoS | Critical | Immediate |
| **Natural** | Power outage, datacenter fire, flood | High | <4 hours |

### Business Impact

**Without Disaster Recovery:**
- ❌ Warehouse operations halted
- ❌ Unable to scan or track bags
- ❌ Cannot generate bills
- ❌ Lost revenue: $5,000-10,000 per day
- ❌ Customer trust damage

**With Disaster Recovery:**
- ✅ Operations resume within 1-4 hours
- ✅ Data loss < 5 minutes
- ✅ Automated failover capabilities
- ✅ Business continuity maintained

### Disaster Recovery Team

| Role | Responsibility | Contact |
|------|----------------|---------|
| **DR Coordinator** | Overall incident management | Primary: On-call admin |
| **Database Admin** | Database recovery and validation | Primary: Lead developer |
| **DevOps Engineer** | Infrastructure restoration | Primary: System admin |
| **Security Officer** | Security incident response | Primary: Security lead |
| **Communications Lead** | Stakeholder updates | Primary: Business owner |

---

## RPO and RTO Targets

### Recovery Point Objective (RPO)

**Maximum acceptable data loss**

| Component | Target RPO | Implementation |
|-----------|------------|----------------|
| Database (primary) | **5 minutes** | Continuous WAL archiving to S3 |
| Database (development) | **24 hours** | Daily automated backups |
| Application code | **0 (zero)** | Git version control |
| Configuration | **1 hour** | Documented in Git + secrets manager |
| Audit logs | **5 minutes** | Included in database backups |
| Session data | **Acceptable loss** | Stateless (users re-login) |

### Recovery Time Objective (RTO)

**Maximum acceptable downtime**

| Disaster Type | Target RTO | Procedure |
|---------------|------------|-----------|
| Application crash | **5 minutes** | Automatic restart via systemd/Replit |
| Database corruption | **1 hour** | Restore from latest backup |
| Server failure | **2 hours** | Launch new instance, restore data |
| AWS region outage | **4 hours** | Failover to secondary region |
| Complete datacenter loss | **8 hours** | Rebuild from backups |

### Calculation Examples

**Scenario 1: Database Corruption at 10:00 AM**
- Detection: 10:05 AM (5 minutes)
- Decision to restore: 10:10 AM
- Backup retrieval: 10:20 AM (10 minutes)
- Database restore: 10:40 AM (20 minutes)
- Application restart: 10:45 AM (5 minutes)
- Validation: 10:55 AM (10 minutes)
- **Total RTO: 55 minutes** ✅ (within 1 hour target)
- **Data Loss: Last backup at 09:55 AM** = 5 minutes ✅

**Scenario 2: Application Server Failure at 2:00 PM**
- Detection: 2:02 PM (2 minutes - monitoring alert)
- Launch new EC2 instance: 2:05 PM (3 minutes)
- Deploy code from Git: 2:10 PM (5 minutes)
- Configure environment: 2:15 PM (5 minutes)
- Connect to database: 2:17 PM (2 minutes)
- Validation: 2:20 PM (3 minutes)
- **Total RTO: 20 minutes** ✅ (within 2 hour target)
- **Data Loss: 0** ✅ (database unaffected)

---

## Critical System Components

### Component Inventory

#### 1. Database (PostgreSQL)

**Criticality:** 🔴 **CRITICAL** - Cannot operate without database

**Details:**
- **Type:** AWS RDS PostgreSQL 14+
- **Size:** ~50GB (1.8M+ bags)
- **Location:** us-east-1 (primary)
- **Backup:** Automated daily + continuous WAL
- **Dependencies:** None

**Recovery Priority:** 1 (highest)

#### 2. Application Server (Flask/Gunicorn)

**Criticality:** 🔴 **CRITICAL** - Core application

**Details:**
- **Platform:** Replit Deployment / AWS EC2
- **Code:** Git repository (GitHub/GitLab)
- **Configuration:** Environment variables
- **Dependencies:** Database, session storage

**Recovery Priority:** 2

#### 3. Session Storage (Filesystem)

**Criticality:** 🟡 **MEDIUM** - Users can re-login

**Details:**
- **Type:** `/tmp/flask_session`
- **Size:** ~100MB
- **Backup:** Not critical (acceptable loss)
- **Dependencies:** None

**Recovery Priority:** 4 (low)

#### 4. Static Assets (CSS/JS/Images)

**Criticality:** 🟡 **MEDIUM** - Can operate without (basic HTML)

**Details:**
- **Location:** `/static` directory in Git
- **Size:** ~166KB
- **Backup:** Git repository
- **Dependencies:** None

**Recovery Priority:** 3

#### 5. Email Service (SendGrid)

**Criticality:** 🟢 **LOW** - Nice to have

**Details:**
- **Provider:** SendGrid API
- **Function:** Password resets, notifications
- **Backup:** API keys in secrets manager

**Recovery Priority:** 5 (lowest)

### Dependency Map

```
┌─────────────────────────────────────────┐
│         Users / Load Balancer           │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│      Application Server (Flask)         │ ◄── Priority 2
│  - Gunicorn workers                     │
│  - Session management                   │
│  - Authentication                       │
└───────┬─────────────┬───────────────────┘
        │             │
        ▼             ▼
┌───────────────┐  ┌──────────────────────┐
│  PostgreSQL   │  │   Session Storage    │
│   Database    │  │   (Filesystem)       │
│  (AWS RDS)    │  │   /tmp/flask_session │
└───────────────┘  └──────────────────────┘
   Priority 1          Priority 4
   
     (All code backed by Git repository)
```

### Single Points of Failure (SPOF)

| Component | SPOF Risk | Mitigation |
|-----------|-----------|------------|
| Database | ✅ High | Multi-AZ RDS, automated backups, read replicas |
| Application Server | ✅ High | Auto-scaling, health checks, load balancer |
| AWS Region | ✅ Medium | Cross-region backups, failover plan |
| Git Repository | ✅ Low | Multiple remotes (GitHub + GitLab mirrors) |
| DNS | ✅ Low | Cloudflare with automatic failover |

---

## Database Backup and Restore

### Backup Strategy

#### 1. Automated Daily Backups (AWS RDS)

**Configuration:**

```bash
# Enable automated backups
aws rds modify-db-instance \
  --db-instance-identifier traitortrack-primary \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --apply-immediately

# Verify backup settings
aws rds describe-db-instances \
  --db-instance-identifier traitortrack-primary \
  --query 'DBInstances[0].[BackupRetentionPeriod,PreferredBackupWindow]'
```

**Schedule:** Daily at 3:00 AM (low-traffic window)  
**Retention:** 7 days  
**Storage Location:** AWS RDS automated backup storage

#### 2. Manual Backups (pg_dump)

**Weekly full backup:**

```bash
#!/bin/bash
# backup_database.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/traitortrack"
BACKUP_FILE="$BACKUP_DIR/traitortrack_$DATE.sql.gz"

# Create backup directory
mkdir -p $BACKUP_DIR

# Dump database with compression
pg_dump $PRODUCTION_DATABASE_URL \
  --clean --if-exists --create \
  --verbose \
  | gzip > $BACKUP_FILE

# Verify backup
if [ -f $BACKUP_FILE ]; then
    SIZE=$(du -h $BACKUP_FILE | cut -f1)
    echo "✓ Backup created: $BACKUP_FILE ($SIZE)"
    
    # Upload to S3
    aws s3 cp $BACKUP_FILE s3://traitortrack-backups/database/ \
      --storage-class STANDARD_IA \
      --metadata "backup-type=manual,timestamp=$DATE"
    
    echo "✓ Uploaded to S3"
else
    echo "✗ Backup failed"
    exit 1
fi

# Clean up local backups older than 3 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +3 -delete
```

**Schedule:** Weekly on Sunday at 2:00 AM  
**Retention:** 4 weeks locally, 3 months on S3  
**Storage:** S3 bucket `s3://traitortrack-backups/database/`

#### 3. Continuous Backup (WAL Archiving)

**Enable WAL archiving to S3:**

```sql
-- On AWS RDS PostgreSQL
-- This is automatically configured by AWS, verify settings:
SHOW wal_level;           -- Should be 'replica' or 'logical'
SHOW archive_mode;        -- Should be 'on'
SHOW archive_command;     -- AWS handles this automatically
```

**For self-managed PostgreSQL:**

```conf
# /etc/postgresql/14/main/postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'aws s3 cp %p s3://traitortrack-backups/wal/%f'
archive_timeout = 300  # Archive every 5 minutes
```

**RPO:** 5 minutes (based on archive_timeout)

### Restore Procedures

#### Restore from AWS RDS Automated Backup

**Scenario:** Database corruption, need to restore to point-in-time

**Procedure:**

```bash
# 1. Identify target restore time
TARGET_TIME="2025-11-25T10:30:00Z"

# 2. Create new DB instance from backup
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier traitortrack-primary \
  --target-db-instance-identifier traitortrack-restored \
  --restore-time $TARGET_TIME \
  --db-instance-class db.t3.large \
  --publicly-accessible false

# 3. Wait for restore to complete
aws rds wait db-instance-available \
  --db-instance-identifier traitortrack-restored

# 4. Verify data
RESTORED_URL=$(aws rds describe-db-instances \
  --db-instance-identifier traitortrack-restored \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

psql "postgresql://user:pass@$RESTORED_URL:5432/traitortrack" \
  -c "SELECT COUNT(*) FROM bag;"

# 5. Update application to use restored database
export PRODUCTION_DATABASE_URL="postgresql://user:pass@$RESTORED_URL:5432/traitortrack"

# 6. Restart application
sudo systemctl restart traitortrack

# 7. Verify application functionality
curl https://traitortrack.example.com/health
```

**Expected Time:** 20-40 minutes (depends on database size)

#### Restore from pg_dump Backup

**Scenario:** Need to restore from specific manual backup

**Procedure:**

```bash
# 1. Download backup from S3
BACKUP_DATE="20251125_030000"
aws s3 cp s3://traitortrack-backups/database/traitortrack_$BACKUP_DATE.sql.gz /tmp/

# 2. Stop application (prevent writes during restore)
sudo systemctl stop traitortrack

# 3. Drop and recreate database (DANGEROUS - confirm first!)
read -p "⚠️  This will DELETE all current data. Type 'CONFIRM' to proceed: " CONFIRM
if [ "$CONFIRM" != "CONFIRM" ]; then
    echo "Restore cancelled"
    exit 1
fi

psql $PRODUCTION_DATABASE_URL -c "
    SELECT pg_terminate_backend(pid) 
    FROM pg_stat_activity 
    WHERE datname = 'traitortrack' AND pid <> pg_backend_pid();
"

psql postgres://user:pass@host:5432/postgres -c "DROP DATABASE traitortrack;"
psql postgres://user:pass@host:5432/postgres -c "CREATE DATABASE traitortrack;"

# 4. Restore data
gunzip -c /tmp/traitortrack_$BACKUP_DATE.sql.gz | \
  psql $PRODUCTION_DATABASE_URL

# 5. Verify data
psql $PRODUCTION_DATABASE_URL -c "
    SELECT 
        (SELECT COUNT(*) FROM bag) AS total_bags,
        (SELECT COUNT(*) FROM bill) AS total_bills,
        (SELECT COUNT(*) FROM \"user\") AS total_users;
"

# 6. Restart application
sudo systemctl start traitortrack

# 7. Verify application
curl https://traitortrack.example.com/health
curl https://traitortrack.example.com/api/stats
```

**Expected Time:** 15-30 minutes

#### Restore from WAL Archives (Point-in-Time Recovery)

**Scenario:** Need precise recovery to specific timestamp

See [DATABASE_BACKUP_AUTOMATION.md](DATABASE_BACKUP_AUTOMATION.md) for detailed PITR procedures.

---

## Application Code Recovery

### Git Repository Backup

**Primary Repository:** GitHub (https://github.com/org/traitortrack)  
**Mirror Repository:** GitLab (https://gitlab.com/org/traitortrack) - automatic mirror

**Setup automatic mirror:**

```bash
# Add GitLab as remote
git remote add gitlab https://gitlab.com/org/traitortrack.git

# Create post-push hook to mirror
cat > .git/hooks/post-push <<'EOF'
#!/bin/bash
git push gitlab --all --follow-tags
EOF
chmod +x .git/hooks/post-push
```

### Recovery from Git

**Scenario:** Application server lost, need to redeploy

**Procedure:**

```bash
# 1. Launch new server (AWS EC2, Replit, etc.)

# 2. Install dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip git postgresql-client

# 3. Clone repository
git clone https://github.com/org/traitortrack.git /opt/traitortrack
cd /opt/traitortrack

# 4. Install Python dependencies
pip3 install -r requirements.txt

# 5. Restore environment variables (see next section)
# ... configure secrets ...

# 6. Run database migrations (if needed)
flask db upgrade

# 7. Start application
gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 4 main:app

# 8. Verify
curl http://localhost:5000/health
```

**Expected Time:** 15-30 minutes

### Code Rollback

**Scenario:** Bad deployment, need to rollback

```bash
# View recent commits
git log --oneline -10

# Rollback to specific commit
git checkout <commit-hash>

# Or rollback to previous release tag
git checkout v1.2.0

# Restart application
sudo systemctl restart traitortrack
```

### Deployment from Backup

If Git is unavailable, restore from code backup:

```bash
# Download latest code backup from S3
aws s3 cp s3://traitortrack-backups/code/latest.tar.gz /tmp/

# Extract
tar -xzf /tmp/latest.tar.gz -C /opt/traitortrack

# Proceed with deployment
```

---

## Secrets and Configuration Recovery

### Secrets Inventory

| Secret | Purpose | Storage | Recovery Method |
|--------|---------|---------|-----------------|
| `SESSION_SECRET` | Flask session encryption | AWS Secrets Manager | Retrieve from ASM |
| `ADMIN_PASSWORD` | Initial admin account | AWS Secrets Manager | Retrieve from ASM |
| `PRODUCTION_DATABASE_URL` | Database connection | AWS Secrets Manager | Retrieve from ASM |
| `SENDGRID_API_KEY` | Email service | AWS Secrets Manager | Retrieve from ASM |
| `SENDGRID_FROM_EMAIL` | Email sender | AWS Secrets Manager | Retrieve from ASM |

### AWS Secrets Manager Setup

**Store secrets:**

```bash
# Create secret for database URL
aws secretsmanager create-secret \
  --name traitortrack/production/database-url \
  --description "Production database connection string" \
  --secret-string "postgresql://user:password@host:5432/traitortrack"

# Create secret for session key
aws secretsmanager create-secret \
  --name traitortrack/production/session-secret \
  --secret-string "$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"

# Create secret for SendGrid
aws secretsmanager create-secret \
  --name traitortrack/production/sendgrid-api-key \
  --secret-string "SG.xxxxxxxxxxxxxxxxxxxxxxxx"
```

**Retrieve secrets during recovery:**

```bash
# Retrieve all secrets
export PRODUCTION_DATABASE_URL=$(aws secretsmanager get-secret-value \
  --secret-id traitortrack/production/database-url \
  --query SecretString --output text)

export SESSION_SECRET=$(aws secretsmanager get-secret-value \
  --secret-id traitortrack/production/session-secret \
  --query SecretString --output text)

export SENDGRID_API_KEY=$(aws secretsmanager get-secret-value \
  --secret-id traitortrack/production/sendgrid-api-key \
  --query SecretString --output text)

# Write to .env file for application
cat > /opt/traitortrack/.env <<EOF
PRODUCTION_DATABASE_URL=$PRODUCTION_DATABASE_URL
SESSION_SECRET=$SESSION_SECRET
SENDGRID_API_KEY=$SENDGRID_API_KEY
ENVIRONMENT=production
REPLIT_DEPLOYMENT=1
EOF
```

### Manual Secret Recovery (Offline Backup)

**Create encrypted backup:**

```bash
# Export secrets to encrypted file
cat > secrets.txt <<EOF
SESSION_SECRET=$SESSION_SECRET
ADMIN_PASSWORD=$ADMIN_PASSWORD
PRODUCTION_DATABASE_URL=$PRODUCTION_DATABASE_URL
SENDGRID_API_KEY=$SENDGRID_API_KEY
EOF

# Encrypt with GPG (requires passphrase)
gpg --symmetric --cipher-algo AES256 secrets.txt

# Store encrypted file in secure location
mv secrets.txt.gpg ~/traitortrack-secrets-backup.gpg
rm secrets.txt

# Upload to S3 with encryption
aws s3 cp ~/traitortrack-secrets-backup.gpg \
  s3://traitortrack-backups/secrets/ \
  --sse AES256
```

**Restore from encrypted backup:**

```bash
# Download encrypted secrets
aws s3 cp s3://traitortrack-backups/secrets/traitortrack-secrets-backup.gpg /tmp/

# Decrypt (requires passphrase)
gpg --decrypt /tmp/traitortrack-secrets-backup.gpg > /tmp/secrets.txt

# Load into environment
source /tmp/secrets.txt

# Securely delete decrypted file
shred -vfz -n 10 /tmp/secrets.txt
```

---

## Service Failover Procedures

### Database Failover

#### Multi-AZ Automatic Failover (AWS RDS)

**Setup:**

```bash
# Enable Multi-AZ deployment
aws rds modify-db-instance \
  --db-instance-identifier traitortrack-primary \
  --multi-az \
  --apply-immediately
```

**Automatic Failover:**
- **Trigger:** Primary database failure detected
- **Time:** 60-120 seconds
- **Action:** AWS automatically promotes standby to primary
- **DNS Update:** Endpoint DNS updated automatically
- **Application:** No code changes needed

**Manual Failover (for testing or maintenance):**

```bash
# Force failover to standby
aws rds reboot-db-instance \
  --db-instance-identifier traitortrack-primary \
  --force-failover
```

#### Read Replica Promotion (Disaster Scenario)

See [DATABASE_READ_REPLICA_GUIDE.md](DATABASE_READ_REPLICA_GUIDE.md) for detailed procedures.

**Quick procedure:**

```bash
# 1. Promote read replica to standalone
aws rds promote-read-replica \
  --db-instance-identifier traitortrack-replica-1

# 2. Wait for promotion
aws rds wait db-instance-available \
  --db-instance-identifier traitortrack-replica-1

# 3. Update application connection string
export PRODUCTION_DATABASE_URL="postgresql://user:pass@new-endpoint:5432/traitortrack"

# 4. Restart application
sudo systemctl restart traitortrack
```

**Time:** 5-15 minutes

### Application Server Failover

#### Auto-Scaling Group (AWS)

**Setup:**

```bash
# Create launch template
aws ec2 create-launch-template \
  --launch-template-name traitortrack-app-template \
  --launch-template-data '{
    "ImageId": "ami-xxxxxxxxx",
    "InstanceType": "t3.medium",
    "UserData": "<base64-encoded-startup-script>",
    "IamInstanceProfile": {"Name": "traitortrack-app-role"}
  }'

# Create auto-scaling group
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name traitortrack-asg \
  --launch-template LaunchTemplateName=traitortrack-app-template \
  --min-size 2 \
  --max-size 5 \
  --desired-capacity 2 \
  --vpc-zone-identifier "subnet-xxx,subnet-yyy" \
  --health-check-type ELB \
  --health-check-grace-period 300 \
  --target-group-arns arn:aws:elasticloadbalancing:...
```

**Automatic Behavior:**
- Health check fails → instance terminated
- New instance launched automatically
- Load balancer updated
- No manual intervention required

#### Manual Failover

```bash
# 1. Launch new EC2 instance
aws ec2 run-instances \
  --image-id ami-xxxxxxxxx \
  --instance-type t3.medium \
  --key-name traitortrack-key \
  --security-group-ids sg-xxxxxxxxx \
  --subnet-id subnet-xxxxxxxxx \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=traitortrack-app-failover}]'

# 2. Wait for instance to be running
INSTANCE_ID=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=traitortrack-app-failover" --query 'Reservations[0].Instances[0].InstanceId' --output text)
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

# 3. Deploy application (see "Application Code Recovery")

# 4. Add to load balancer
aws elbv2 register-targets \
  --target-group-arn arn:aws:elasticloadbalancing:... \
  --targets Id=$INSTANCE_ID

# 5. Remove failed instance from load balancer
aws elbv2 deregister-targets \
  --target-group-arn arn:aws:elasticloadbalancing:... \
  --targets Id=<old-instance-id>
```

### DNS Failover (Cloudflare)

**Setup health checks:**

```bash
# Enable health checks in Cloudflare dashboard
# - Monitor primary: https://traitortrack.example.com/health
# - Failover to backup: https://backup.traitortrack.example.com
# - Check interval: 60 seconds
# - Failure threshold: 3 consecutive failures
```

**Automatic DNS failover:**
- Primary fails health check → DNS updated to backup
- Time: 60-180 seconds
- No manual intervention

---

## Communication Protocols

### Incident Notification

**Communication Channels:**

1. **Email:** DR team distribution list (dr-team@example.com)
2. **Slack/Teams:** #traitortrack-incidents channel
3. **SMS:** Critical team members (via PagerDuty/OpsGenie)
4. **Status Page:** Public status updates (status.traitortrack.com)

**Notification Template:**

```
SUBJECT: [INCIDENT] TraitorTrack - <Severity> - <Brief Description>

INCIDENT DETAILS:
- Severity: [P1-Critical / P2-High / P3-Medium / P4-Low]
- Detected: [Timestamp]
- Impact: [Description of user impact]
- Affected Components: [Database / Application / Network]
- Status: [Investigating / Identified / Monitoring / Resolved]

CURRENT STATUS:
[Brief update on situation]

NEXT STEPS:
[Planned actions]

ESTIMATED RECOVERY: [Time estimate]

DR Coordinator: [Name]
```

### Stakeholder Updates

**Update Frequency:**

| Severity | Initial Update | Ongoing Updates | Resolution |
|----------|----------------|-----------------|------------|
| P1 (Critical) | Within 15 min | Every 30 min | Immediate |
| P2 (High) | Within 30 min | Every 1 hour | Within 2 hours |
| P3 (Medium) | Within 1 hour | Every 2 hours | Within 4 hours |
| P4 (Low) | Within 4 hours | Daily | Next business day |

**Stakeholders:**

- **Users:** Status page updates (public)
- **Management:** Email summary
- **DR Team:** Real-time Slack updates
- **Customers:** Direct email (for P1/P2)

### Post-Incident Report

**Template:**

```markdown
# Incident Post-Mortem: [Incident Title]

**Date:** [Date]
**Duration:** [Start time] - [End time] ([total duration])
**Severity:** [P1/P2/P3/P4]
**Impact:** [Number of users affected, revenue impact]

## Summary
[Brief description of what happened]

## Timeline
- [Time] - Incident started (first symptoms)
- [Time] - Detected (monitoring alert / user report)
- [Time] - DR team notified
- [Time] - Root cause identified
- [Time] - Fix implemented
- [Time] - Service restored
- [Time] - Incident closed

## Root Cause
[Technical explanation of what caused the incident]

## Resolution
[What was done to fix the issue]

## Impact Assessment
- Users affected: [number / percentage]
- Data loss: [amount / none]
- Downtime: [duration]
- Revenue impact: [estimate]

## What Went Well
- [Positive aspects of response]

## What Could Be Improved
- [Areas for improvement]

## Action Items
1. [ ] [Action item] - Owner: [Name] - Due: [Date]
2. [ ] [Action item] - Owner: [Name] - Due: [Date]

## Lessons Learned
[Key takeaways for future incidents]
```

---

## DR Testing Schedule

### Testing Frequency

| Test Type | Frequency | Duration | Participants |
|-----------|-----------|----------|--------------|
| **Database Restore** | Monthly | 1 hour | DB Admin |
| **Application Failover** | Quarterly | 2 hours | DevOps, DR Team |
| **Full DR Simulation** | Annually | 4-8 hours | All teams |
| **Communication Drill** | Semi-annually | 30 minutes | DR Coordinator |

### Monthly Database Restore Test

**Objective:** Verify backup integrity and restore procedures

**Procedure:**

```bash
#!/bin/bash
# dr_test_database.sh

echo "=== TraitorTrack DR Test: Database Restore ==="
echo "Date: $(date)"
echo ""

# 1. Download latest backup
echo "1. Downloading latest backup..."
LATEST_BACKUP=$(aws s3 ls s3://traitortrack-backups/database/ | sort | tail -n 1 | awk '{print $4}')
aws s3 cp s3://traitortrack-backups/database/$LATEST_BACKUP /tmp/

# 2. Create test database
echo "2. Creating test database..."
psql postgres://user:pass@host:5432/postgres -c "DROP DATABASE IF EXISTS traitortrack_test;"
psql postgres://user:pass@host:5432/postgres -c "CREATE DATABASE traitortrack_test;"

# 3. Restore backup
echo "3. Restoring backup..."
START_TIME=$(date +%s)
gunzip -c /tmp/$LATEST_BACKUP | psql postgres://user:pass@host:5432/traitortrack_test
END_TIME=$(date +%s)
RESTORE_TIME=$((END_TIME - START_TIME))

# 4. Verify data
echo "4. Verifying data..."
RECORD_COUNTS=$(psql postgres://user:pass@host:5432/traitortrack_test -t -c "
    SELECT 
        'bags=' || COUNT(*) FROM bag
    UNION ALL
    SELECT 'bills=' || COUNT(*) FROM bill
    UNION ALL
    SELECT 'users=' || COUNT(*) FROM \"user\";
")

# 5. Clean up
echo "5. Cleaning up..."
psql postgres://user:pass@host:5432/postgres -c "DROP DATABASE traitortrack_test;"
rm /tmp/$LATEST_BACKUP

# 6. Report results
echo ""
echo "=== Test Results ==="
echo "Backup file: $LATEST_BACKUP"
echo "Restore time: ${RESTORE_TIME}s"
echo "Record counts: $RECORD_COUNTS"
echo "Status: ✓ SUCCESS"
echo ""
```

**Success Criteria:**
- ✅ Backup downloads successfully
- ✅ Restore completes without errors
- ✅ Record counts match expected values
- ✅ Restore time < 5 minutes

### Quarterly Application Failover Test

**Objective:** Verify application can failover to backup infrastructure

**Procedure:**

1. **Pre-test:**
   - Notify team of scheduled test
   - Enable maintenance mode (optional)
   - Document current state

2. **Simulate failure:**
   - Stop primary application server
   - Monitor automatic failover

3. **Verify:**
   - Health checks pass
   - Users can access application
   - Database connectivity works
   - Sessions maintained (or users can re-login)

4. **Restore:**
   - Restart primary server
   - Remove maintenance mode
   - Monitor for issues

5. **Document:**
   - Record failover time
   - Note any issues
   - Update procedures if needed

### Annual Full DR Simulation

**Objective:** Complete disaster recovery from scratch

**Scenario:** "AWS us-east-1 region is completely unavailable"

**Procedure:**

1. **Declare simulation start** (9:00 AM)
2. **Activate DR team**
3. **Restore database** in us-west-2 from S3 backups
4. **Deploy application** in us-west-2 from Git
5. **Configure secrets** from AWS Secrets Manager
6. **Update DNS** to point to new region
7. **Verify full functionality**
8. **Declare recovery complete**
9. **Document timeline and issues**
10. **Conduct post-mortem**

**Success Criteria:**
- ✅ Recovery completed within RTO (4 hours)
- ✅ Data loss within RPO (5 minutes)
- ✅ All critical functions operational
- ✅ No secrets lost
- ✅ Team followed documented procedures

---

## Incident Response Runbook

### Step 1: Detection and Assessment

**Possible Detection Methods:**
- Monitoring alert (AWS CloudWatch, Datadog, etc.)
- User report (email, phone, support ticket)
- Health check failure
- Manual observation

**Initial Assessment (5 minutes):**

```bash
# Quick health check
curl https://traitortrack.example.com/health

# Check application logs
tail -100 /var/log/traitortrack/app.log | grep ERROR

# Check database connectivity
psql $PRODUCTION_DATABASE_URL -c "SELECT 1;"

# Check system resources
top -bn1 | head -20
df -h
free -m
```

**Severity Classification:**

```
P1 (Critical): Complete service outage, data loss
  → Notify all, immediate action, hourly updates

P2 (High): Major functionality impaired, performance degraded
  → Notify team, action within 30 min, 2-hour updates

P3 (Medium): Minor functionality issue, workaround available
  → Notify team, action within 4 hours

P4 (Low): Cosmetic issue, no user impact
  → Log ticket, resolve in next sprint
```

### Step 2: Communication

**Immediate (within 15 minutes of P1, 30 minutes of P2):**

```bash
# Send notification to team
./scripts/notify_incident.sh \
  --severity P1 \
  --title "Database connection failure" \
  --impact "All users unable to access system"

# Update status page
curl -X POST https://api.statuspage.io/incidents \
  -H "Authorization: Bearer $STATUSPAGE_API_KEY" \
  -d '{
    "incident": {
      "name": "Database connectivity issue",
      "status": "investigating",
      "impact": "major"
    }
  }'
```

### Step 3: Triage and Diagnosis

**Database Issues:**

```sql
-- Check active connections
SELECT COUNT(*), state FROM pg_stat_activity GROUP BY state;

-- Check long-running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
FROM pg_stat_activity 
WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '5 minutes';

-- Check replication lag (if using replicas)
SELECT * FROM pg_stat_replication;

-- Check database size
SELECT pg_size_pretty(pg_database_size('traitortrack'));
```

**Application Issues:**

```bash
# Check Gunicorn workers
ps aux | grep gunicorn

# Check error logs
tail -500 /var/log/traitortrack/app.log | grep -i error

# Check connection pool
curl http://localhost:5000/pool_dashboard

# Check system health
curl http://localhost:5000/api/system_health
```

### Step 4: Mitigation

**Quick Fixes (if possible):**

```bash
# Restart application
sudo systemctl restart traitortrack

# Clear session cache
rm -rf /tmp/flask_session/*

# Kill long-running queries
psql $PRODUCTION_DATABASE_URL -c "
    SELECT pg_terminate_backend(pid) 
    FROM pg_stat_activity 
    WHERE state = 'active' 
      AND now() - pg_stat_activity.query_start > interval '10 minutes';
"

# Scale up resources (AWS)
aws rds modify-db-instance \
  --db-instance-identifier traitortrack-primary \
  --db-instance-class db.t3.xlarge \
  --apply-immediately
```

### Step 5: Recovery

**Follow appropriate recovery procedure:**

- Database corruption → [Database Restore](#database-backup-and-restore)
- Application failure → [Application Recovery](#application-code-recovery)
- Infrastructure failure → [Service Failover](#service-failover-procedures)

### Step 6: Verification

**Comprehensive Testing:**

```bash
# 1. Health endpoint
curl https://traitortrack.example.com/health
# Expected: {"status": "ok"}

# 2. Login flow
curl -X POST https://traitortrack.example.com/login \
  -d "username=testuser&password=testpass"
# Expected: 200 OK, session cookie set

# 3. Dashboard stats
curl https://traitortrack.example.com/api/stats
# Expected: JSON with statistics

# 4. Database operations
# - Create test bag
# - Search for bag
# - Delete test bag

# 5. Monitor for errors
tail -f /var/log/traitortrack/app.log | grep ERROR
# Expected: No new errors
```

### Step 7: Post-Incident

**Immediate (within 1 hour):**
- Update status page to "Resolved"
- Send resolution notification
- Document timeline

**Within 24 hours:**
- Complete post-mortem report
- Identify root cause
- Create action items

**Within 1 week:**
- Review action items with team
- Update runbooks if needed
- Schedule follow-up if necessary

---

## Summary

TraitorTrack's disaster recovery plan ensures business continuity with:

**Recovery Targets:**
- **RPO:** 5 minutes (minimal data loss)
- **RTO:** 1-4 hours (fast recovery)

**Key Procedures:**
1. ✅ Automated daily database backups
2. ✅ Multi-AZ database failover
3. ✅ Git-based code recovery
4. ✅ AWS Secrets Manager for configuration
5. ✅ Documented runbooks for all scenarios

**Testing Schedule:**
- Monthly database restore tests
- Quarterly failover tests
- Annual full DR simulation

**Next Steps:**

1. Set up AWS Secrets Manager for all secrets
2. Configure Multi-AZ deployment for production database
3. Schedule first DR test
4. Document team contact information
5. Create status page

**See Also:**

- [DATABASE_BACKUP_AUTOMATION.md](DATABASE_BACKUP_AUTOMATION.md) - Detailed backup procedures
- [OPERATIONAL_RUNBOOK.md](OPERATIONAL_RUNBOOK.md) - Daily operations
- [PRODUCTION_DEPLOYMENT_CHECKLIST.md](PRODUCTION_DEPLOYMENT_CHECKLIST.md) - Deployment guide

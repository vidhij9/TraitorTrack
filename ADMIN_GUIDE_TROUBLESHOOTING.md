# TraitorTrack Admin Guide & Troubleshooting

**Version:** 1.0.0  
**Last Updated:** November 2025  
**Audience:** System Administrators

---

## Table of Contents

1. [Admin Dashboard Overview](#admin-dashboard-overview)
2. [User Management](#user-management)
3. [System Health Monitoring](#system-health-monitoring)
4. [Audit Log Review](#audit-log-review)
5. [Two-Factor Authentication Management](#two-factor-authentication-management)
6. [Performance Tuning](#performance-tuning)
7. [Database Maintenance](#database-maintenance)
8. [Security Best Practices](#security-best-practices)
9. [Advanced Troubleshooting](#advanced-troubleshooting)
10. [Common Issues & Solutions](#common-issues--solutions)

---

## Admin Dashboard Overview

### Access Requirements

- **Role**: Admin
- **Login**: `https://your-domain.com/login`
- **2FA**: Required for admin accounts (strongly recommended)

### Admin Navigation

**Additional Menu Items** (admins only):
- 👥 **User Management** - Create, edit, delete users
- 🔐 **Promotion Requests** - Review admin promotion requests
- 📊 **System Health** - Real-time system monitoring
- 🔍 **Audit Logs** - Security and change tracking
- 💾 **Pool Dashboard** - Database connection monitoring
- ⚙️ **Settings** - System configuration

### Admin Capabilities

**Full Access**:
- ✅ All dispatcher and biller functions
- ✅ User account management
- ✅ Role assignments
- ✅ Password resets
- ✅ System health monitoring
- ✅ Audit log review
- ✅ Database maintenance
- ✅ Security configuration
- ✅ Data deletion and cleanup

---

## User Management

### View All Users

1. Click "**User Management**"
2. View user list with:
   - Username
   - Email
   - Role (Admin/Biller/Dispatcher)
   - Dispatch area (if dispatcher)
   - Account status (Active/Locked)
   - Created date
   - Last login

**Filters**:
- Role: All, Admin, Biller, Dispatcher
- Status: All, Active, Locked
- Dispatch Area: All, Lucknow, Indore, etc.

### Create New User

1. Click "**User Management**" → "**Create User**"
2. Fill in details:
   - **Username**: Unique, 3-64 characters
   - **Email**: Valid email address (unique)
   - **Password**: Strong password (min 8 characters)
   - **Role**: Admin, Biller, or Dispatcher
   - **Dispatch Area**: Required for dispatchers only
3. Click "**Create User**"

**Password Requirements**:
- Minimum 8 characters
- At least one uppercase letter (recommended)
- At least one number (recommended)
- At least one special character (recommended)

**Security Best Practices**:
- ✅ Use complex passwords
- ✅ Enable 2FA for admin accounts immediately
- ✅ Verify email address
- ❌ Don't reuse passwords
- ❌ Don't share admin credentials

### Edit User

1. Go to "**User Management**"
2. Click on username
3. Click "**Edit User**"
4. Modify:
   - Email address
   - Role
   - Dispatch area
   - Account status
5. Click "**Save Changes**"

**Role Change Implications**:
- **Dispatcher → Biller**: Gains bill management and all-area access
- **Biller → Dispatcher**: Loses bill management, restricted to one area
- **→ Admin**: Gains full system access, requires 2FA
- **Admin → Any**: Loses admin access, 2FA remains enabled

**Audit Logging**: All role changes are logged with before/after snapshots.

### Reset User Password

**Method 1: Email Reset Link** (Preferred)

1. Go to "**User Management**" → Select user
2. Click "**Send Password Reset**"
3. User receives email with reset link (valid 1 hour)
4. User clicks link, sets new password

**Method 2: Set Temporary Password**

1. Select user → Click "**Set Temporary Password**"
2. Generate or enter temporary password
3. Click "**Set Password**"
4. **Important**: Communicate password securely to user
5. User should change password immediately after login

**Method 3: Database Reset** (Emergency)

```sql
-- Connect to database
psql $PRODUCTION_DATABASE_URL

-- Clear reset token (allows user to request new reset)
UPDATE "user" 
SET password_reset_token = NULL, 
    password_reset_token_expires = NULL 
WHERE username = 'locked_user';
```

### Unlock Account

**Automatic Lockout**: After 5 failed login attempts, account locks for 30 minutes.

**Manual Unlock**:

1. Go to "**User Management**" → Find locked user
2. Click "**Unlock Account**"
3. Confirm action

**Database Unlock** (if UI unavailable):

```sql
UPDATE "user" 
SET failed_login_attempts = 0, 
    locked_until = NULL, 
    last_failed_login = NULL 
WHERE username = 'locked_user';
```

**Audit Check** (investigate lockout):

```sql
SELECT timestamp, details, ip_address
FROM audit_log
WHERE action = 'login_failed'
  AND details->>'username' = 'locked_user'
ORDER BY timestamp DESC
LIMIT 10;
```

### Delete User

**Warning**: User deletion is permanent and removes:
- User account
- Scan history attribution (scans remain, user_id set to NULL)
- Created bags/bills attribution
- Audit log user reference (logs remain, anonymized)

**Procedure**:

1. Go to "**User Management**" → Select user
2. Click "**Delete User**"
3. **Confirm deletion** (type username to verify)
4. Optionally anonymize audit logs (GDPR compliance)

**GDPR-Compliant Deletion**:
- ✅ User record deleted
- ✅ Email anonymized in audit logs
- ✅ IP addresses anonymized
- ✅ Audit trail preserved (entity changes remain)
- ✅ Data integrity maintained (foreign keys set to NULL)

**Audit Log After Deletion**:

```sql
-- User deleted, but logs remain with NULL user_id
SELECT action, entity_type, entity_id, before_state
FROM audit_log
WHERE user_id IS NULL
  AND action = 'delete_user'
ORDER BY timestamp DESC;
```

### Manage Promotion Requests

**Workflow**: Non-admin users can request admin promotion

**Review Request**:

1. Click "**Promotion Requests**"
2. View pending requests with:
   - Requesting user
   - Reason provided
   - Request date
3. Click on request

**Approve Request**:

1. Review user history and reason
2. Click "**Approve**"
3. Add admin notes (optional)
4. User role upgraded to Admin
5. User notified (in-app notification)
6. Audit log created

**Reject Request**:

1. Click "**Reject**"
2. Add reason for rejection (required)
3. User notified with reason
4. Audit log created

**Security Considerations**:
- ⚠️ Admin promotion grants full system access
- ⚠️ Verify user identity and need
- ⚠️ Review user's audit history
- ⚠️ Require 2FA enablement after promotion

---

## System Health Monitoring

### System Health Dashboard

Access: "**System Health**" or `/api/system_health`

**Component Status**:

| Component | Healthy | Degraded | Unhealthy |
|-----------|---------|----------|-----------|
| Database | <100ms query, <80% pool | <500ms query, <95% pool | >500ms query or >95% pool |
| Cache | >60% hit rate | 30-60% hit rate | <30% hit rate |
| Session | Configured, secure | Configured, insecure | Not configured |
| Rate Limiter | Enabled | N/A | Disabled |
| Audit Logging | <200ms query | 200-500ms query | >500ms or unavailable |
| Email | Configured | Not configured | Error |

**Overall Status**:
- 🟢 **Healthy**: All systems operational
- 🟡 **Degraded**: Functional but suboptimal
- 🔴 **Unhealthy**: Critical system failure
- ⚪ **Unknown**: Status cannot be determined

**Sample Response**:

```json
{
  "status": "healthy",
  "message": "All systems operational",
  "timestamp": "2025-11-25T10:30:00",
  "service": "TraitorTrack",
  "version": "2.0",
  "components": {
    "database": {
      "status": "healthy",
      "connected": true,
      "query_time_ms": 5.2,
      "pool": {
        "size": 40,
        "checked_out": 15,
        "usage_percent": 37.5
      }
    },
    "cache": {
      "status": "healthy",
      "hit_rate": 72.5,
      "total_hits": 15234,
      "total_misses": 5123,
      "entries": 234
    }
  }
}
```

### Connection Pool Dashboard

Access: "**Pool Dashboard**" or `/pool_dashboard`

**Real-Time Metrics**:
- **Pool Usage**: Current % of max connections
- **Checked Out**: Active database connections
- **Available**: Free connections
- **Overflow**: Connections beyond base pool
- **Trend**: Usage trend (last 10 minutes)

**Alert Thresholds**:
- 🟢 **<70%**: Healthy
- 🟡 **70-85%**: Warning (monitor)
- 🟠 **85-95%**: Critical (investigate)
- 🔴 **>95%**: Danger (immediate action)

**Usage Trend**:
- ⬆️ **Increasing**: Usage growing over time
- ⬇️ **Decreasing**: Usage declining
- ➡️ **Stable**: Consistent usage

**Recommendations** (displayed on dashboard):
- Warning: "Monitor pool usage trends"
- Critical: "Review active queries for optimization"
- Danger: "Scale up database connection limits immediately"

**Export Data**: Download pool history as CSV

### Performance Metrics

**Dashboard Response Time**:

```bash
# Test from command line
time curl -I https://your-domain.com/dashboard

# Target: <50ms
```

**API Response Time**:

```bash
# Statistics API
time curl https://your-domain.com/api/stats

# Target: <200ms
```

**Database Query Performance**:

```sql
-- Enable query timing
\timing

-- Test common queries
SELECT count(*) FROM bag;
SELECT count(*) FROM bill;

-- Target: <100ms each
```

**Cache Hit Rate**:

Access: System Health → Cache Component

**Target**: >60% hit rate

**Improve cache performance**:
- Increase cache TTL (see [Performance Tuning](#performance-tuning))
- Verify caching enabled (`cache_utils.py`)
- Check cache entry count (low = cache not used)

---

## Audit Log Review

### Access Audit Logs

1. Click "**Audit Logs**" in admin menu
2. View recent events (last 100)

**Default View**:
- Timestamp
- User (who performed action)
- Action (what happened)
- Entity Type (bag, bill, user, etc.)
- Entity ID
- IP Address (anonymized if GDPR enabled)
- Details

### Filter Audit Logs

**Filters**:
- **User**: Filter by username
- **Action**: Specific action type
- **Entity Type**: Bag, Bill, User, etc.
- **Date Range**: Custom date/time range
- **IP Address**: Filter by IP (admins only)

**Common Filters**:

```
# Recent login failures
Action: login_failed
Date Range: Last 24 hours

# Role changes
Action: role_change
Date Range: Last 7 days

# Bag deletions
Action: delete_bag
Entity Type: bag
Date Range: Last 30 days

# User activity
User: <username>
Date Range: Last 24 hours
```

### Audit Log Actions

**Security Events**:
- `login_success` - Successful login
- `login_failed` - Failed login attempt
- `login_locked` - Account locked after failed attempts
- `logout` - User logout
- `password_change` - Password changed
- `password_reset_request` - Password reset requested
- `password_reset_complete` - Password reset completed
- `2fa_enabled` - 2FA enabled
- `2fa_disabled` - 2FA disabled
- `2fa_verify_success` - 2FA verification succeeded
- `2fa_verify_failed` - 2FA verification failed

**User Management**:
- `user_created` - New user account created
- `user_updated` - User account modified
- `user_deleted` - User account deleted
- `role_change` - User role changed
- `unlock_account` - Account manually unlocked

**Data Operations**:
- `create_bag` - Bag created
- `update_bag` - Bag modified
- `delete_bag` - Bag deleted
- `create_bill` - Bill created
- `update_bill` - Bill modified
- `delete_bill` - Bill deleted
- `link_created` - Parent-child link created
- `link_deleted` - Link removed

### View Change History

**Before/After Snapshots**: Enhanced audit logs include state before and after changes

**Example**: View role change details

```sql
-- Get role change with before/after
SELECT 
    timestamp,
    u.username as changed_user,
    before_state->>'role' as old_role,
    after_state->>'role' as new_role,
    before_state->>'dispatch_area' as old_area,
    after_state->>'dispatch_area' as new_area,
    details
FROM audit_log
LEFT JOIN "user" u ON audit_log.entity_id = u.id
WHERE action = 'role_change'
  AND entity_type = 'user'
ORDER BY timestamp DESC
LIMIT 10;
```

**Query Entity History**:

```sql
-- Get all changes to a specific user
SELECT 
    timestamp,
    action,
    before_state,
    after_state,
    details
FROM audit_log
WHERE entity_type = 'user'
  AND entity_id = 5  -- User ID
ORDER BY timestamp DESC;
```

### Investigate Security Incidents

**Scenario: Suspicious login attempts**

```sql
-- Failed logins from same IP
SELECT 
    ip_address,
    details->>'username' as username,
    count(*) as attempts,
    min(timestamp) as first_attempt,
    max(timestamp) as last_attempt
FROM audit_log
WHERE action = 'login_failed'
  AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY ip_address, details->>'username'
HAVING count(*) > 5
ORDER BY count DESC;
```

**Scenario: Data deletion investigation**

```sql
-- Who deleted what and when
SELECT 
    timestamp,
    u.username as deleted_by,
    entity_type,
    entity_id,
    before_state,
    details
FROM audit_log
LEFT JOIN "user" u ON audit_log.user_id = u.id
WHERE action LIKE 'delete_%'
ORDER BY timestamp DESC
LIMIT 50;
```

**Scenario: User activity timeline**

```sql
-- Complete activity history for a user
SELECT 
    timestamp,
    action,
    entity_type,
    ip_address,
    details
FROM audit_log
WHERE user_id = 5  -- User ID
ORDER BY timestamp DESC
LIMIT 100;
```

### Audit Log Retention

**Default Retention**:
- Audit logs: 90 days
- Snapshots: 30 days (then cleared to save space)
- Critical actions: Preserved indefinitely

**Manual Cleanup** (if needed):

```sql
-- Delete audit logs older than 90 days (non-critical)
DELETE FROM audit_log
WHERE timestamp < NOW() - INTERVAL '90 days'
  AND action NOT IN ('delete_user', 'delete_bag', 'delete_bill', 'role_change');

-- Clear snapshots older than 30 days (keep logs, remove snapshots)
UPDATE audit_log
SET before_state = NULL, after_state = NULL
WHERE timestamp < NOW() - INTERVAL '30 days';
```

**Automated Retention** (via `audit_retention.py`):

```python
from audit_retention import AuditRetentionPolicy

# Dry run (see what would be cleaned)
result = AuditRetentionPolicy.run_maintenance(dry_run=True)
print(f"Would delete: {result['logs_to_delete']} logs")

# Execute cleanup
result = AuditRetentionPolicy.run_maintenance(dry_run=False)
print(f"Deleted: {result['logs_deleted']} logs")
```

---

## Two-Factor Authentication Management

### Enable 2FA (Admin Accounts)

**Recommendation**: All admin accounts should have 2FA enabled.

**User Self-Enrollment**:

1. User logs in
2. Goes to Profile → "Enable Two-Factor Authentication"
3. Scans QR code with authenticator app (Google Authenticator, Authy, etc.)
4. Enters 6-digit verification code
5. 2FA enabled

**Admin Enforcement**:

```sql
-- Check admins without 2FA
SELECT username, email, two_fa_enabled
FROM "user"
WHERE role = 'admin'
  AND (two_fa_enabled = false OR two_fa_enabled IS NULL);
```

**Notify admins to enable 2FA** via in-app notifications or email.

### Disable 2FA

**User Self-Disable**:

1. User goes to Profile → "Disable Two-Factor Authentication"
2. Enters current password
3. Enters current 6-digit 2FA code
4. 2FA disabled

**Admin Emergency Disable** (if user locked out):

```sql
-- Disable 2FA for locked-out user
UPDATE "user"
SET two_fa_enabled = false,
    totp_secret = NULL
WHERE username = 'locked_user';
```

**Audit Log Entry**: 2FA disable is logged automatically.

### 2FA Lockout Recovery

**Scenario**: User lost authenticator app

**Recovery Process**:

1. Verify user identity (phone, email, in-person)
2. Admin disables 2FA via database:
   ```sql
   UPDATE "user"
   SET two_fa_enabled = false, totp_secret = NULL
   WHERE username = 'locked_user';
   ```
3. User logs in without 2FA
4. User re-enables 2FA with new QR code

**Security Best Practice**: Require identity verification before disabling 2FA.

### Monitor 2FA Usage

```sql
-- 2FA adoption rate
SELECT 
    role,
    count(*) as total_users,
    count(*) FILTER (WHERE two_fa_enabled = true) as with_2fa,
    round(100.0 * count(*) FILTER (WHERE two_fa_enabled = true) / count(*), 1) as adoption_rate
FROM "user"
GROUP BY role
ORDER BY role;

-- Recent 2FA failures (potential attacks)
SELECT 
    timestamp,
    details->>'username' as username,
    ip_address,
    count(*) OVER (PARTITION BY ip_address) as attempts_from_ip
FROM audit_log
WHERE action = '2fa_verify_failed'
  AND timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;
```

---

## Performance Tuning

### Connection Pool Optimization

**Current Configuration** (per worker):
- Pool size: 25
- Max overflow: 15
- Total per worker: 40 connections
- Workers: 2 (default)
- Total max: 80 connections

**Scaling Guidelines**:

```bash
# For 100 concurrent users
POOL_SIZE=25
POOL_MAX_OVERFLOW=15
# Workers: 2

# For 200 concurrent users
POOL_SIZE=30
POOL_MAX_OVERFLOW=20
# Workers: 4

# For 500 concurrent users
POOL_SIZE=40
POOL_MAX_OVERFLOW=30
# Workers: 4
```

**Update Configuration**:

1. Set environment variables:
   ```bash
   export POOL_SIZE=30
   export POOL_MAX_OVERFLOW=20
   ```

2. Restart application

3. Verify in Pool Dashboard

**PostgreSQL Limits**:

```sql
-- Check max_connections
SHOW max_connections;

-- Should be > (POOL_SIZE + POOL_MAX_OVERFLOW) × Workers × Servers
-- Example: (30 + 20) × 2 workers × 2 servers = 200
-- Set max_connections to 250 (with buffer)

-- Update max_connections (requires restart)
ALTER SYSTEM SET max_connections = 250;
```

### Cache Tuning

**Increase Cache TTL**:

```python
# In cache_utils.py
CACHE_TTL = 600  # 10 minutes (from 300)
```

**Selective Caching**:

```python
# Cache dashboard stats aggressively
@cached_global(ttl=600)  # 10 minutes
def get_dashboard_stats():
    ...

# Cache user-specific data with shorter TTL
@cached_user(ttl=120)  # 2 minutes
def get_user_scans(user_id):
    ...
```

**Cache Invalidation**:

```python
from cache_utils import invalidate_cache, invalidate_stats_cache

# Invalidate specific cache
invalidate_cache('dashboard_stats')

# Invalidate all stats caches
invalidate_stats_cache()
```

### Database Indexing

**Verify Indexes Exist**:

```sql
-- List all indexes
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- Expected: 50+ indexes
```

**Missing Indexes?** Re-apply migration:

```bash
psql $PRODUCTION_DATABASE_URL -f migrations_manual_sql/002_add_user_and_promotion_indexes.sql
```

**Custom Index Creation** (if needed):

```sql
-- Example: Index on bag dispatch_area + created_at
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_area_created
ON bag(dispatch_area, created_at DESC);
```

**Note**: Use `CONCURRENTLY` to avoid table locking on large tables.

### Query Optimization

**Identify Slow Queries**:

```sql
-- Enable pg_stat_statements extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Top 10 slowest queries
SELECT 
    calls,
    round(total_exec_time::numeric, 2) as total_time_ms,
    round(mean_exec_time::numeric, 2) as avg_time_ms,
    query
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

**Analyze Query Performance**:

```sql
-- Example: Slow bag lookup
EXPLAIN ANALYZE
SELECT * FROM bag
WHERE type = 'parent'
  AND dispatch_area = 'lucknow'
ORDER BY created_at DESC
LIMIT 100;

-- Check if index is used
-- Should see: "Index Scan using idx_bag_type_area_created"
```

### Gunicorn Workers

**Formula**: Workers = (2 × CPU cores) + 1

```bash
# For 2 CPU cores
gunicorn --workers 5 \
  --threads 4 \
  --bind 0.0.0.0:5000 \
  main:app

# For 4 CPU cores
gunicorn --workers 9 \
  --threads 4 \
  --bind 0.0.0.0:5000 \
  main:app
```

**Monitor Worker Performance**:

```bash
# Check worker processes
ps aux | grep gunicorn

# Worker memory usage
ps aux | grep gunicorn | awk '{sum+=$6} END {print "Total Memory:", sum/1024, "MB"}'
```

---

## Database Maintenance

### Routine Maintenance

**Weekly Tasks**:

```sql
-- Vacuum and analyze (reclaim space, update statistics)
VACUUM ANALYZE;

-- Check database size
SELECT pg_size_pretty(pg_database_size(current_database()));
```

**Monthly Tasks**:

```sql
-- Reindex database (rebuild indexes for performance)
REINDEX DATABASE traitortrack_production;

-- Check for bloat
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS index_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Database Backups

**Automated** (AWS RDS):
- Daily snapshots (7-day retention)
- Automatic backup window: 2:00-3:00 AM UTC

**Manual Backup**:

```bash
# Full database backup
pg_dump $PRODUCTION_DATABASE_URL \
  --format=custom \
  --file=traitortrack_backup_$(date +%Y%m%d).dump

# Verify backup
pg_restore --list traitortrack_backup_20251125.dump | head
```

**Backup Schedule**:
- Daily: Automated (AWS RDS)
- Weekly: Manual full backup (long-term storage)
- Pre-deployment: Manual backup before migrations

### Data Cleanup

**Old Session Files**:

```bash
# Delete sessions older than 2 days
find /tmp/flask_session -type f -mtime +2 -delete

# Automate with cron
0 2 * * * find /tmp/flask_session -type f -mtime +2 -delete
```

**Old Audit Logs**:

```python
# Use audit retention system
from audit_retention import AuditRetentionPolicy

# Run maintenance (deletes logs >90 days, clears snapshots >30 days)
result = AuditRetentionPolicy.run_maintenance(dry_run=False)
```

**Orphaned Data**:

```sql
-- Find bags without scans (never used)
SELECT count(*) FROM bag
WHERE id NOT IN (
    SELECT DISTINCT parent_bag_id FROM scan WHERE parent_bag_id IS NOT NULL
    UNION
    SELECT DISTINCT child_bag_id FROM scan WHERE child_bag_id IS NOT NULL
);

-- Delete if appropriate (CAREFUL!)
-- DELETE FROM bag WHERE <condition>;
```

### Database Migrations

**Apply New Migration**:

```bash
# Alembic migration
alembic upgrade head

# Or manual SQL migration
psql $PRODUCTION_DATABASE_URL -f migrations_manual_sql/new_migration.sql
```

**Rollback Migration**:

```bash
# Downgrade one revision
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade <revision_id>
```

**Check Migration Status**:

```sql
-- Current Alembic revision
SELECT version_num FROM alembic_version;
```

---

## Security Best Practices

### Environment Variables

**Critical Secrets**:
- ✅ `SESSION_SECRET` - Rotate quarterly
- ✅ `ADMIN_PASSWORD` - Strong password, rotate regularly
- ✅ `SENDGRID_API_KEY` - Secure, rotate if compromised
- ✅ `PRODUCTION_DATABASE_URL` - Contains DB password

**Security Checklist**:
- [ ] Secrets stored in secure secrets manager (not in code)
- [ ] Secrets rotated regularly
- [ ] Old secrets revoked after rotation
- [ ] Access to secrets manager restricted

### HTTPS/SSL

**Production Requirements**:
- [ ] HTTPS enforced (HTTP redirects to HTTPS)
- [ ] Valid SSL certificate
- [ ] `SESSION_COOKIE_SECURE=True`
- [ ] HSTS headers enabled

**Verify HTTPS**:

```bash
# Check redirect
curl -I http://your-domain.com
# Should see: Location: https://your-domain.com

# Check SSL certificate
curl -vI https://your-domain.com 2>&1 | grep -A 10 'SSL connection'
```

### Rate Limiting

**Current Limits**:
- Login: 10/minute per IP
- Register: 5/minute per IP
- Password Reset: 3/minute (request), 5/minute (reset)
- 2FA: 5/minute per endpoint

**Monitor Rate Limiting**:

```sql
-- Check rate limit violations (blocked requests)
SELECT 
    timestamp,
    ip_address,
    details->>'endpoint' as endpoint,
    count(*) as blocked_requests
FROM audit_log
WHERE action = 'rate_limit_exceeded'
  AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY timestamp, ip_address, details->>'endpoint'
ORDER BY count DESC;
```

**Adjust Limits** (if needed):

```python
# In routes.py
@limiter.limit("20/minute")  # Increased from 10
def login():
    ...
```

### Account Security

**Enforce Strong Passwords**:

```python
# In password_utils.py
def validate_password_complexity(password):
    if len(password) < 12:  # Increased from 8
        return False, "Password must be at least 12 characters"
    # Add more complexity rules
```

**Audit Account Security**:

```sql
-- Admins without 2FA
SELECT username, email, created_at
FROM "user"
WHERE role = 'admin'
  AND two_fa_enabled = false;

-- Accounts with failed login attempts
SELECT username, failed_login_attempts, last_failed_login
FROM "user"
WHERE failed_login_attempts > 0
ORDER BY failed_login_attempts DESC;

-- Locked accounts
SELECT username, locked_until
FROM "user"
WHERE locked_until > NOW();
```

### GDPR Compliance

**PII Anonymization**:

Enabled by default via `ANONYMIZE_AUDIT_LOGS=true`

**What's Anonymized**:
- Email addresses → `user***@***.com`
- IP addresses → `192.168.xxx.xxx`

**User Data Deletion**:

When deleting users, ensure:
- [ ] User account deleted
- [ ] Email anonymized in audit logs
- [ ] IP addresses anonymized
- [ ] Right to erasure fulfilled

**Export User Data** (GDPR request):

```sql
-- Export all user data
SELECT * FROM "user" WHERE id = 5;
SELECT * FROM bag WHERE user_id = 5;
SELECT * FROM scan WHERE user_id = 5;
SELECT * FROM audit_log WHERE user_id = 5;
```

---

## Advanced Troubleshooting

### Application Won't Start

**Check Environment Variables**:

```bash
# Required variables
echo $SESSION_SECRET
echo $PRODUCTION_DATABASE_URL

# If missing, set them
export SESSION_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(64))")
```

**Check Database Connection**:

```bash
psql $PRODUCTION_DATABASE_URL -c "SELECT 1;"
# Should return: 1
```

**Check Python Dependencies**:

```bash
pip list | grep Flask
pip list | grep SQLAlchemy

# Reinstall if needed
pip install -r requirements.txt
```

**Check Logs**:

```bash
tail -100 /var/log/traitortrack/app.log
# Look for startup errors
```

### Database Connection Errors

**Symptoms**:
- "Connection refused"
- "Too many connections"
- "SSL connection error"

**Diagnosis**:

```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- Check max_connections limit
SHOW max_connections;

-- If at limit, kill idle connections
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
  AND query_start < NOW() - INTERVAL '1 hour';
```

**Increase max_connections** (if needed):

```sql
ALTER SYSTEM SET max_connections = 200;
-- Requires PostgreSQL restart
```

### Slow Dashboard Performance

**Check Statistics Cache**:

```sql
-- Verify statistics_cache table exists
SELECT * FROM statistics_cache;

-- If empty or missing, rebuild cache
-- (Will be auto-populated by database triggers)
INSERT INTO statistics_cache (id, total_bags, total_bills, last_updated)
VALUES (1, 0, 0, NOW())
ON CONFLICT (id) DO NOTHING;
```

**Check Database Performance**:

```sql
-- Dashboard query performance
EXPLAIN ANALYZE
SELECT count(*) FROM bag;

EXPLAIN ANALYZE
SELECT count(*) FROM bill;
```

**Clear Cache** (force rebuild):

```python
from cache_utils import invalidate_stats_cache
invalidate_stats_cache()
```

### Memory Leaks

**Symptoms**:
- Application memory grows over time
- Out of memory errors
- Server swap usage high

**Diagnosis**:

```bash
# Monitor memory usage
watch -n 5 free -h

# Process memory
ps aux --sort=-%mem | head -10

# Gunicorn workers
ps aux | grep gunicorn | awk '{print $6, $11}'
```

**Solution**:

Gunicorn auto-restarts workers after `max_requests` (default: 1000)

```bash
# Force worker restart
kill -HUP $(pgrep -f "gunicorn.*main:app")

# Or restart application
sudo systemctl restart traitortrack
```

### Session Issues

**User Complaints**:
- "Logged out unexpectedly"
- "Session expired too soon"

**Check Session Configuration**:

```python
# In app.py
SESSION_TYPE='filesystem'
SESSION_FILE_DIR='/tmp/flask_session'
SESSION_PERMANENT=False
PERMANENT_SESSION_LIFETIME=3600  # 1 hour
```

**Check Session Files**:

```bash
# Session file count
ls -1 /tmp/flask_session | wc -l

# Recent sessions
ls -lt /tmp/flask_session | head -10

# Disk space
df -h /tmp
```

**Clear Stale Sessions**:

```bash
find /tmp/flask_session -type f -mtime +1 -delete
```

### Deployment Failures

**Rollback Procedure**:

1. **Revert code**:
   ```bash
   git checkout <previous_tag>
   ```

2. **Rollback database** (if migration failed):
   ```bash
   alembic downgrade -1
   ```

3. **Restart application**:
   ```bash
   sudo systemctl restart traitortrack
   ```

4. **Verify health**:
   ```bash
   curl https://your-domain.com/health
   ```

5. **Investigate failure** in logs

---

## Common Issues & Solutions

### Issue: Users Can't Login

**Possible Causes**:
1. Wrong username/password
2. Account locked (5 failed attempts)
3. 2FA code incorrect
4. Session configuration issue

**Solutions**:

```sql
-- Check account status
SELECT username, failed_login_attempts, locked_until, two_fa_enabled
FROM "user"
WHERE username = 'user123';

-- Unlock account if locked
UPDATE "user"
SET failed_login_attempts = 0, locked_until = NULL
WHERE username = 'user123';

-- Check recent login attempts
SELECT timestamp, action, details, ip_address
FROM audit_log
WHERE details->>'username' = 'user123'
  AND action LIKE 'login%'
ORDER BY timestamp DESC
LIMIT 10;
```

### Issue: Slow Query Performance

**Diagnosis**:

```sql
-- Find slow queries
SELECT pid, query_start, state, query
FROM pg_stat_activity
WHERE state != 'idle'
  AND query_start < NOW() - INTERVAL '5 seconds'
ORDER BY query_start;

-- Check if indexes are being used
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan < 100
ORDER BY idx_scan;
```

**Solutions**:
1. Verify indexes exist
2. Run `VACUUM ANALYZE`
3. Reindex database
4. Optimize query (use EXPLAIN ANALYZE)

### Issue: Connection Pool Exhaustion

**Symptoms**: "QueuePool limit exceeded"

**Immediate Fix**:

```sql
-- Kill long-running queries
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state != 'idle'
  AND query_start < NOW() - INTERVAL '1 minute';
```

**Long-term Fix**:
1. Increase pool size
2. Scale database
3. Optimize queries
4. Add read replicas (if available)

### Issue: Disk Space Full

**Check Usage**:

```bash
df -h
du -sh /*
du -sh /tmp/flask_session
```

**Clean Up**:

```bash
# Old session files
find /tmp/flask_session -type f -mtime +1 -delete

# Old logs
find /var/log -name "*.log.*" -mtime +30 -delete

# Database cleanup (see Audit Log Retention)
```

### Issue: Email Not Sending

**Check Configuration**:

```bash
echo $SENDGRID_API_KEY
# Should be set

# Test SendGrid API
curl -X POST https://api.sendgrid.com/v3/mail/send \
  -H "Authorization: Bearer $SENDGRID_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"personalizations":[{"to":[{"email":"test@example.com"}]}],"from":{"email":"noreply@yourdomain.com"},"subject":"Test","content":[{"type":"text/plain","value":"Test email"}]}'
```

**Check Logs**:

```bash
grep -i "email" /var/log/traitortrack/app.log | tail -20
```

**Verify Email Service**:
- SendGrid account active
- API key valid
- Sending domain verified
- Not in spam filters

---

## Related Documentation

- [Deployment Checklist](PRODUCTION_DEPLOYMENT_CHECKLIST.md) - Deployment procedures
- [Operational Runbook](OPERATIONAL_RUNBOOK.md) - Day-to-day operations
- [User Guide](USER_GUIDE_DISPATCHERS_BILLERS.md) - End-user documentation
- [Session Configuration](SESSION_CONFIGURATION.md) - Session details
- [Audit Logging Guide](AUDIT_LOGGING_GUIDE.md) - Audit system

---

## Support Escalation

| Issue Type | Contact | Response Time |
|------------|---------|---------------|
| Security Incident | Security Team | Immediate |
| Database Emergency | DBA Team | <15 minutes |
| Application Error | Dev Team | <1 hour |
| Performance Issue | Ops Team | <2 hours |
| User Support | Help Desk | <4 hours |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | November 2025 | Initial admin guide and troubleshooting documentation |

---

**Admin Responsibilities**:
- 🔒 Maintain system security
- 📊 Monitor system health
- 👥 Manage user accounts
- 🛠️ Perform routine maintenance
- 🚨 Respond to alerts
- 📝 Review audit logs
- 🔧 Optimize performance
- 💾 Ensure backups are working

**Stay vigilant, stay secure!** 🛡️

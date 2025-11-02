# TraitorTrack Operational Runbook

**Version:** 1.0.0  
**Last Updated:** November 2025  
**System:** TraitorTrack Warehouse Bag Tracking System

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Common Operational Tasks](#common-operational-tasks)
4. [Monitoring & Health Checks](#monitoring--health-checks)
5. [Troubleshooting Guide](#troubleshooting-guide)
6. [Alert Response Procedures](#alert-response-procedures)
7. [Backup & Recovery](#backup--recovery)
8. [Scaling Guidelines](#scaling-guidelines)
9. [Performance Monitoring](#performance-monitoring)
10. [Emergency Procedures](#emergency-procedures)

---

## System Overview

### Purpose

TraitorTrack is a high-performance warehouse bag tracking system designed to manage:
- **1.8M+ bags** with parent-child relationships
- **100+ concurrent users** (dispatchers, billers, administrators)
- Real-time scanning and bill generation
- Comprehensive audit trails and security features

### Key Capabilities

- ✅ Parent-child bag linking (1:30 ratio)
- ✅ Dynamic bill generation with weight calculations
- ✅ Role-based access control (admin, biller, dispatcher)
- ✅ 2FA for admin users
- ✅ Real-time dashboard with <50ms response
- ✅ Comprehensive audit logging with GDPR compliance
- ✅ Connection pool monitoring and alerts

### SLA Targets

| Metric | Target |
|--------|--------|
| Uptime | 99.5% |
| Dashboard Response | <50ms |
| API Response | <200ms |
| Database Query | <100ms |
| Concurrent Users | 100+ |

---

## Architecture

### Component Stack

```
[Users] → [Load Balancer] → [Gunicorn (2 workers)]
                                    ↓
                            [Flask Application]
                                    ↓
                     [PostgreSQL Database (AWS RDS)]
                                    ↓
                        [Filesystem Sessions (/tmp)]
```

### Technology Stack

- **Backend**: Flask 3.1+, Python 3.10+
- **Database**: PostgreSQL 12+ (AWS RDS)
- **WSGI Server**: Gunicorn with sync workers (2 workers, 4 threads each)
- **Session Storage**: Filesystem-based (`/tmp/flask_session`)
- **Caching**: In-memory caching with TTL
- **Security**: Flask-Login, Flask-WTF, Flask-Limiter

### Database Schema

**Core Tables** (10 total):
1. `user` - User accounts and authentication
2. `bag` - Parent and child bags
3. `link` - Parent-child bag relationships
4. `bill` - Bills with weight calculations
5. `bill_bag` - Bill-to-bag associations
6. `scan` - Scanning history
7. `audit_log` - Comprehensive audit trail
8. `promotionrequest` - Admin promotion requests
9. `notification` - In-app notifications
10. `alembic_version` - Migration tracking

**Performance**: 50+ optimized indexes across all tables

### Network Ports

- **Application**: 5000 (HTTP, internal)
- **PostgreSQL**: 5432 (internal only)
- **Load Balancer**: 443 (HTTPS, public)

---

## Common Operational Tasks

### Restart Application

```bash
# Replit deployment (automatic via Replit platform)
# Manual restart via Replit UI or CLI

# AWS/EC2 deployment
sudo systemctl restart traitortrack

# Docker deployment
docker-compose restart app
```

**When to restart:**
- After environment variable changes
- Application appears frozen
- Memory usage abnormally high
- After code deployment

**Expected downtime**: <10 seconds (zero-downtime if using multiple workers)

### Check Application Logs

```bash
# View recent logs
tail -f /var/log/traitortrack/app.log

# Search for errors
grep -i error /var/log/traitortrack/app.log | tail -50

# Filter by date
grep "2025-11-25" /var/log/traitortrack/app.log
```

**Key log patterns to monitor:**
- `ERROR` - Application errors
- `CRITICAL` - Critical failures
- `WARNING` - Potential issues
- `Pool usage` - Connection pool alerts

### Database Maintenance

#### Vacuum Database (Weekly)

```sql
-- Connect to database
psql $PRODUCTION_DATABASE_URL

-- Vacuum analyze (updates statistics, reclaims space)
VACUUM ANALYZE;

-- For specific table
VACUUM ANALYZE bag;
```

**Schedule**: Weekly, during low-traffic period (2-4 AM)

#### Reindex Database (Monthly)

```sql
-- Reindex all tables (improves query performance)
REINDEX DATABASE traitortrack_production;
```

**Schedule**: Monthly, during maintenance window

#### Check Database Size

```sql
-- Total database size
SELECT pg_size_pretty(pg_database_size('traitortrack_production'));

-- Table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Clear Old Session Files

```bash
# Remove sessions older than 2 days
find /tmp/flask_session -type f -mtime +2 -delete

# Check session count
ls -1 /tmp/flask_session | wc -l

# Check disk usage
du -sh /tmp/flask_session
```

**Schedule**: Daily via cron job

```bash
# Add to crontab
0 2 * * * find /tmp/flask_session -type f -mtime +2 -delete
```

### User Management

#### Create Admin User

```bash
python manage.py create_admin \
  --username newadmin \
  --email admin@example.com \
  --password <secure_password>
```

#### Reset User Password

```bash
# Via admin dashboard
# 1. Login as admin
# 2. Go to User Management
# 3. Click user → Reset Password
# 4. Send reset link via email (if configured)

# Via database (emergency only)
psql $PRODUCTION_DATABASE_URL -c "
UPDATE \"user\" 
SET password_reset_token = '<token>', 
    password_reset_token_expires = NOW() + INTERVAL '1 hour'
WHERE email = 'user@example.com';
"
```

#### Unlock Account

```bash
# Via database
psql $PRODUCTION_DATABASE_URL -c "
UPDATE \"user\" 
SET failed_login_attempts = 0, 
    locked_until = NULL 
WHERE username = 'locked_user';
"
```

### Audit Log Review

```sql
-- Recent security events (last 24 hours)
SELECT timestamp, username, action, entity_type, details
FROM audit_log
LEFT JOIN "user" ON audit_log.user_id = "user".id
WHERE timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC
LIMIT 100;

-- Failed login attempts
SELECT timestamp, details->>'username' as username, ip_address
FROM audit_log
WHERE action = 'login_failed'
  AND timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;

-- User deletions
SELECT timestamp, username, entity_id, before_state
FROM audit_log
LEFT JOIN "user" ON audit_log.user_id = "user".id
WHERE action = 'delete_user'
ORDER BY timestamp DESC;
```

---

## Monitoring & Health Checks

### Health Endpoints

#### Basic Health Check

```bash
# Check if application is responding
curl https://your-domain.com/health

# Expected response
{"status": "ok"}
```

**Purpose**: Load balancer health checks, uptime monitoring

#### System Health Check

```bash
# Comprehensive component health
curl https://your-domain.com/api/system_health \
  -H "Cookie: session=<admin_session>"

# Expected response (JSON)
{
  "status": "healthy",
  "message": "All systems operational",
  "timestamp": "2025-11-25T10:30:00",
  "components": {
    "database": {"status": "healthy", "query_time_ms": 5.2},
    "cache": {"status": "healthy", "hit_rate": 72.5},
    "session": {"status": "healthy"},
    "rate_limiter": {"status": "healthy"},
    "audit_logging": {"status": "healthy"}
  }
}
```

**Component Status**:
- `healthy` - Operating normally
- `degraded` - Functional but slow/suboptimal
- `unhealthy` - Critical failure

### Connection Pool Dashboard

```bash
# Access pool dashboard (admin only)
https://your-domain.com/pool_dashboard
```

**Metrics displayed**:
- Current pool usage (%)
- Checked out connections
- Available connections
- Overflow connections
- Usage trend (last 10 minutes)

**Alert thresholds**:
- 🟢 <70% - Healthy
- 🟡 70-85% - Warning
- 🟠 85-95% - Critical
- 🔴 >95% - Danger

### Key Metrics to Monitor

#### Application Metrics

```bash
# Dashboard performance
time curl https://your-domain.com/dashboard

# API performance
time curl https://your-domain.com/api/stats

# Cache hit rate
curl https://your-domain.com/api/system_health | jq '.components.cache.hit_rate'
```

**Targets**:
- Dashboard: <50ms
- API: <200ms
- Cache hit rate: >60%

#### Database Metrics

```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity;

-- Slow queries (>5 seconds)
SELECT pid, now() - query_start as duration, query 
FROM pg_stat_activity 
WHERE state = 'active' 
  AND now() - query_start > interval '5 seconds';

-- Database size growth
SELECT pg_size_pretty(pg_database_size(current_database()));

-- Table sizes
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

#### System Resources

```bash
# CPU usage
top -bn1 | grep "Cpu(s)"

# Memory usage
free -h

# Disk usage
df -h

# Disk I/O
iostat -x 1 5
```

---

## Troubleshooting Guide

### Connection Pool Exhaustion

**Symptoms**:
- Timeouts on database queries
- "QueuePool limit exceeded" errors
- Slow application response
- Pool dashboard shows >95% usage

**Diagnosis**:

```sql
-- Check active connections
SELECT count(*), state 
FROM pg_stat_activity 
GROUP BY state;

-- Long-running queries
SELECT pid, usename, query_start, state, query 
FROM pg_stat_activity 
WHERE state != 'idle' 
  AND query_start < NOW() - INTERVAL '30 seconds'
ORDER BY query_start;
```

**Resolution**:

1. **Immediate**: Kill long-running queries
```sql
-- Kill specific query
SELECT pg_terminate_backend(<pid>);

-- Kill all idle connections (CAUTION)
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
  AND query_start < NOW() - INTERVAL '1 hour';
```

2. **Short-term**: Restart application
```bash
sudo systemctl restart traitortrack
```

3. **Long-term**: Scale connection pool
```bash
# Update environment variables
POOL_SIZE=30
POOL_MAX_OVERFLOW=20

# Restart application
```

### Slow Query Performance

**Symptoms**:
- Dashboard loads slowly (>200ms)
- API timeouts
- Database CPU at 100%

**Diagnosis**:

```sql
-- Enable query timing
\timing

-- Test slow queries
EXPLAIN ANALYZE SELECT * FROM bag WHERE type = 'parent';

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan < 100
ORDER BY idx_scan;
```

**Resolution**:

1. **Verify indexes exist**:
```sql
-- Check for missing indexes
SELECT tablename, indexname 
FROM pg_indexes 
WHERE schemaname = 'public'
  AND tablename IN ('user', 'bag', 'link', 'bill', 'scan', 'audit_log');
```

2. **Recreate indexes** (if missing):
```bash
psql $PRODUCTION_DATABASE_URL -f migrations_manual_sql/002_add_user_and_promotion_indexes.sql
```

3. **Update statistics**:
```sql
ANALYZE bag;
ANALYZE link;
```

### Session Issues

**Symptoms**:
- Users logged out unexpectedly
- "Session expired" errors
- Unable to login

**Diagnosis**:

```bash
# Check session directory
ls -lah /tmp/flask_session

# Check disk space
df -h /tmp

# Check session file permissions
stat /tmp/flask_session
```

**Resolution**:

1. **Clear old sessions**:
```bash
find /tmp/flask_session -type f -mtime +1 -delete
```

2. **Recreate session directory**:
```bash
rm -rf /tmp/flask_session
mkdir -p /tmp/flask_session
chmod 700 /tmp/flask_session
```

3. **Verify session configuration**:
```python
# In app.py
SESSION_TYPE='filesystem'
SESSION_FILE_DIR='/tmp/flask_session'
SESSION_PERMANENT=False
```

### High Memory Usage

**Symptoms**:
- Application memory usage >80%
- Out of memory errors
- System swap usage high

**Diagnosis**:

```bash
# Check process memory
ps aux | grep gunicorn | head -5

# Memory by process
top -o %MEM

# Application metrics
free -h
```

**Resolution**:

1. **Restart application workers**:
```bash
# Gunicorn auto-restarts workers after max_requests
# Default: 1000 requests per worker

# Force restart
sudo systemctl restart traitortrack
```

2. **Reduce cache size** (if using Redis):
```bash
# Clear cache
redis-cli FLUSHALL
```

3. **Scale vertically**: Increase server memory

### Rate Limit Errors

**Symptoms**:
- "Too many requests" errors (429)
- Legitimate users blocked

**Diagnosis**:

```bash
# Check recent failed requests in audit log
psql $PRODUCTION_DATABASE_URL -c "
SELECT ip_address, count(*) 
FROM audit_log 
WHERE action = 'login_failed' 
  AND timestamp > NOW() - INTERVAL '10 minutes'
GROUP BY ip_address 
ORDER BY count DESC;
"
```

**Resolution**:

1. **Whitelist IP** (if legitimate traffic):
```python
# In app.py, add to rate limiter exemption
@limiter.request_filter
def ip_whitelist():
    return request.remote_addr in ['1.2.3.4', '5.6.7.8']
```

2. **Increase rate limits** (temporary):
```python
# Edit routes.py
@limiter.limit("20/minute")  # Increased from 10/minute
def login():
    ...
```

3. **Block malicious IP** (permanent):
```bash
# At firewall/load balancer level
# (varies by deployment platform)
```

---

## Alert Response Procedures

### Connection Pool Alerts

#### WARNING Alert (70-85% usage)

**Action**: Monitor, no immediate action required

1. Check pool dashboard trends
2. Review active connections
3. Schedule scaling review if sustained

#### CRITICAL Alert (85-95% usage)

**Action**: Investigate within 15 minutes

1. **Check pool dashboard**:
   ```
   https://your-domain.com/pool_dashboard
   ```

2. **Identify long-running queries**:
   ```sql
   SELECT pid, query_start, state, query 
   FROM pg_stat_activity 
   WHERE state != 'idle'
   ORDER BY query_start;
   ```

3. **Review application logs** for errors

4. **Prepare to scale** if trend continues

#### DANGER Alert (>95% usage)

**Action**: IMMEDIATE response required

1. **Kill long-running queries** (if any):
   ```sql
   SELECT pg_terminate_backend(<pid>);
   ```

2. **Restart application** (releases connections):
   ```bash
   sudo systemctl restart traitortrack
   ```

3. **Increase pool size** (if sustained):
   ```bash
   # Update environment
   POOL_SIZE=30
   POOL_MAX_OVERFLOW=20
   ```

4. **Scale database** if needed (AWS RDS)

### Error Spike Alerts

**Threshold**: >10 errors/minute

**Action**:

1. **Check error logs**:
   ```bash
   tail -100 /var/log/traitortrack/app.log | grep ERROR
   ```

2. **Identify error pattern**:
   - Database connection errors → Check database health
   - Import errors → Check dependencies
   - Runtime errors → Check code deployment

3. **Rollback deployment** if recent code change

4. **Notify development team** with error details

### Failed Login Spike

**Threshold**: >20 failed logins/minute

**Action**: Potential brute force attack

1. **Check audit logs**:
   ```sql
   SELECT ip_address, count(*) as attempts
   FROM audit_log
   WHERE action = 'login_failed'
     AND timestamp > NOW() - INTERVAL '10 minutes'
   GROUP BY ip_address
   ORDER BY attempts DESC;
   ```

2. **Block malicious IPs** at firewall level

3. **Verify rate limiting** is active:
   ```bash
   curl -I https://your-domain.com/login
   # Should see: X-RateLimit-Limit, X-RateLimit-Remaining headers
   ```

4. **Notify security team**

### Database Disk Space Alert

**Threshold**: >80% disk usage

**Action**:

1. **Check disk usage**:
   ```sql
   SELECT pg_size_pretty(pg_database_size(current_database()));
   ```

2. **Identify large tables**:
   ```sql
   SELECT 
       tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
   FROM pg_tables
   WHERE schemaname = 'public'
   ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
   ```

3. **Clean up options**:
   - Vacuum old data: `VACUUM FULL;`
   - Archive old audit logs (>90 days)
   - Clear old sessions
   - Scale disk (AWS RDS)

---

## Backup & Recovery

### Backup Strategy

**Automated Backups** (AWS RDS):
- **Frequency**: Daily
- **Retention**: 7 days
- **Window**: 2:00-3:00 AM UTC
- **Type**: Automated snapshots

**Manual Backups**:
- Before major deployments
- Before database migrations
- Monthly full backups (long-term storage)

### Create Manual Backup

```bash
# PostgreSQL dump (logical backup)
pg_dump $PRODUCTION_DATABASE_URL \
  --format=custom \
  --file=traitortrack_$(date +%Y%m%d_%H%M%S).dump

# Or plain SQL format
pg_dump $PRODUCTION_DATABASE_URL \
  --file=traitortrack_$(date +%Y%m%d_%H%M%S).sql
```

### Restore from Backup

```bash
# Restore custom format dump
pg_restore --dbname=traitortrack_production \
  --clean --if-exists \
  traitortrack_20251125_120000.dump

# Restore SQL format
psql traitortrack_production < traitortrack_20251125_120000.sql
```

**Recovery Time Objective (RTO)**: <1 hour  
**Recovery Point Objective (RPO)**: <24 hours

### Disaster Recovery Procedure

1. **Assess damage**: Determine scope of data loss
2. **Identify restore point**: Select appropriate backup
3. **Stop application**: Prevent further writes
4. **Restore database**: Use pg_restore
5. **Verify data**: Run smoke tests
6. **Restart application**: Resume operations
7. **Monitor**: Watch for errors
8. **Post-mortem**: Document incident

---

## Scaling Guidelines

### Horizontal Scaling (Multiple Servers)

**Prerequisites**:
- Migrate to Redis sessions (see [SESSION_CONFIGURATION.md](SESSION_CONFIGURATION.md))
- Configure load balancer with sticky sessions (if using filesystem sessions)

**Steps**:

1. **Deploy additional app servers**
2. **Update load balancer** to distribute traffic
3. **Verify session persistence** across servers
4. **Monitor connection pool** usage per server

**Connection pool formula**:
```
Total DB connections = (POOL_SIZE + POOL_MAX_OVERFLOW) × Number of Workers × Number of Servers

Example: (25 + 15) × 2 workers × 2 servers = 160 connections
Ensure: PostgreSQL max_connections > 160
```

### Vertical Scaling (Larger Servers)

**When to scale**:
- CPU usage sustained >80%
- Memory usage sustained >85%
- Connection pool sustained >70%

**Application server sizing**:
- **Small**: 2 CPU, 4GB RAM - Up to 50 users
- **Medium**: 4 CPU, 8GB RAM - Up to 100 users
- **Large**: 8 CPU, 16GB RAM - Up to 200 users

**Database sizing** (AWS RDS):
- **db.t3.medium**: 2 vCPU, 4GB - Up to 100 users
- **db.t3.large**: 2 vCPU, 8GB - Up to 200 users
- **db.m5.large**: 2 vCPU, 8GB - Up to 500 users

### Performance Tuning

#### Database Connection Pool

```bash
# Increase pool size (per worker)
export POOL_SIZE=30
export POOL_MAX_OVERFLOW=20

# Restart application
```

#### Gunicorn Workers

```bash
# Increase workers (formula: 2 × CPU cores)
gunicorn --workers 4 \
  --threads 4 \
  --bind 0.0.0.0:5000 \
  main:app
```

#### Cache TTL

```python
# Increase cache lifetime for stable data
# In cache_utils.py
CACHE_TTL = 600  # 10 minutes (from 5 minutes)
```

---

## Performance Monitoring

### Dashboard Metrics

Access at: `https://your-domain.com/dashboard`

**Key metrics**:
- Total bags (parent + child)
- Total bills
- Recent scans (last 24 hours)
- Active users

**Expected performance**: <50ms response time

### API Metrics

```bash
# Statistics API
curl https://your-domain.com/api/stats

# System health API
curl https://your-domain.com/api/system_health
```

**Expected performance**: <200ms response time

### Query Performance

```sql
-- Enable query timing
\timing

-- Test common queries
SELECT count(*) FROM bag;
SELECT count(*) FROM link;
SELECT count(*) FROM bill;

-- Check index usage
SELECT 
    schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

**Target**: >90% of queries use indexes

### Cache Performance

```bash
# Get cache statistics
curl https://your-domain.com/api/system_health | jq '.components.cache'

# Expected output
{
  "status": "healthy",
  "hit_rate": 72.5,
  "total_hits": 15234,
  "total_misses": 5123,
  "entries": 234
}
```

**Target hit rate**: >60%

---

## Emergency Procedures

### Total System Outage

1. **Verify outage**:
   ```bash
   curl https://your-domain.com/health
   ```

2. **Check database**:
   ```bash
   psql $PRODUCTION_DATABASE_URL -c "SELECT 1;"
   ```

3. **Check application**:
   ```bash
   sudo systemctl status traitortrack
   ```

4. **Restart application**:
   ```bash
   sudo systemctl restart traitortrack
   ```

5. **Verify recovery**:
   ```bash
   curl https://your-domain.com/health
   ```

6. **Monitor logs**:
   ```bash
   tail -f /var/log/traitortrack/app.log
   ```

### Database Failure

1. **Check database status** (AWS RDS):
   - Go to AWS RDS Console
   - Check instance status
   - Review CloudWatch metrics

2. **Restore from backup** (if needed):
   - Select point-in-time restore
   - Update connection string
   - Restart application

3. **Verify data integrity**:
   ```sql
   SELECT count(*) FROM bag;
   SELECT count(*) FROM bill;
   ```

### Security Incident

1. **Identify threat**:
   ```sql
   -- Check recent audit logs
   SELECT * FROM audit_log 
   WHERE timestamp > NOW() - INTERVAL '1 hour'
   ORDER BY timestamp DESC;
   ```

2. **Block malicious access**:
   - Update firewall rules
   - Disable compromised accounts
   - Reset passwords if needed

3. **Notify security team**

4. **Document incident**

---

## Related Documentation

- [Deployment Checklist](PRODUCTION_DEPLOYMENT_CHECKLIST.md) - Deployment procedures
- [Admin Guide](ADMIN_GUIDE_TROUBLESHOOTING.md) - Admin-specific operations
- [User Guide](USER_GUIDE_DISPATCHERS_BILLERS.md) - End-user documentation
- [Session Configuration](SESSION_CONFIGURATION.md) - Session management details

---

## Escalation Contacts

| Role | Contact | Responsibility |
|------|---------|----------------|
| On-Call Engineer | [Contact] | First responder |
| Database Admin | [Contact] | Database issues |
| Security Team | [Contact] | Security incidents |
| Development Lead | [Contact] | Code/architecture issues |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | November 2025 | Initial operational runbook |

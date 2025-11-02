# TraitorTrack Production Deployment Checklist

**Version:** 1.0.0  
**Last Updated:** November 2025  
**System:** TraitorTrack Warehouse Bag Tracking System

---

## Table of Contents

1. [Pre-Deployment Verification](#pre-deployment-verification)
2. [Environment Configuration](#environment-configuration)
3. [Database Setup](#database-setup)
4. [Security Hardening](#security-hardening)
5. [Performance Optimization](#performance-optimization)
6. [Monitoring Setup](#monitoring-setup)
7. [Post-Deployment Verification](#post-deployment-verification)
8. [Rollback Procedures](#rollback-procedures)
9. [Go-Live Checklist](#go-live-checklist)

---

## Pre-Deployment Verification

### System Requirements

- [ ] **PostgreSQL**: Version 12+ installed and accessible
- [ ] **Python**: Version 3.10+ installed
- [ ] **Gunicorn**: WSGI server configured
- [ ] **Disk Space**: Minimum 20GB available (for 1.8M+ bags)
- [ ] **Memory**: Minimum 4GB RAM (8GB recommended for 100+ concurrent users)
- [ ] **CPU**: 2+ cores recommended

### Code Review

- [ ] All code merged to production branch
- [ ] No debug/development code in production
- [ ] All tests passing (run `pytest tests/`)
- [ ] No hardcoded secrets or credentials
- [ ] `SQLALCHEMY_ECHO` set to `False` in production
- [ ] Error pages tested (401, 403, 404, 500)

### Dependencies

- [ ] All Python dependencies installed (`pip install -r requirements.txt`)
- [ ] Dependency versions locked in `requirements.txt`
- [ ] No security vulnerabilities in dependencies (`pip audit`)

---

## Environment Configuration

### Required Environment Variables

All environment variables should be set via your deployment platform (Replit Secrets, AWS Systems Manager, etc.).

#### Critical Security Variables

```bash
# Session Security (REQUIRED)
SESSION_SECRET=<generate_with: python -c "import secrets; print(secrets.token_urlsafe(64))">

# Admin Account (REQUIRED for first login)
ADMIN_PASSWORD=<strong_password_here>
```

- [ ] `SESSION_SECRET` - Set to cryptographically secure random string (64+ characters)
- [ ] `ADMIN_PASSWORD` - Set to strong password for initial admin account

#### Database Configuration

```bash
# Production Database
PRODUCTION_DATABASE_URL=postgresql://user:password@host:5432/database_name

# Development Database (optional, for Replit workspace only)
DATABASE_URL=postgresql://user:password@host:5432/dev_database
```

- [ ] `PRODUCTION_DATABASE_URL` - AWS RDS or production PostgreSQL connection string
- [ ] `DATABASE_URL` - Development database (Replit workspace only)

#### Email Service (Optional but Recommended)

```bash
# SendGrid Configuration
SENDGRID_API_KEY=<your_sendgrid_api_key>
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
SENDGRID_ADMIN_EMAIL=admin@yourdomain.com
```

- [ ] `SENDGRID_API_KEY` - For password resets and notifications
- [ ] `SENDGRID_FROM_EMAIL` - Sender email address
- [ ] `SENDGRID_ADMIN_EMAIL` - Admin alert recipient

#### Optional Configuration

```bash
# Environment Detection
ENVIRONMENT=production
REPLIT_DEPLOYMENT=1

# File Upload Limits
MAX_FILE_UPLOAD_SIZE=16777216  # 16MB in bytes

# Connection Pool Tuning (per worker)
POOL_SIZE=25
POOL_MAX_OVERFLOW=15

# Connection Pool Monitoring
POOL_WARNING_THRESHOLD=0.70   # 70%
POOL_CRITICAL_THRESHOLD=0.85  # 85%
POOL_DANGER_THRESHOLD=0.95    # 95%
POOL_CHECK_INTERVAL=30        # seconds
POOL_ALERT_COOLDOWN=300       # 5 minutes
POOL_EMAIL_ALERTS=true

# Audit Log Anonymization (GDPR Compliance)
ANONYMIZE_AUDIT_LOGS=true
```

- [ ] `ENVIRONMENT` - Set to `production`
- [ ] `REPLIT_DEPLOYMENT` - Set to `1` for production deployments
- [ ] `MAX_FILE_UPLOAD_SIZE` - File upload limit (bytes)
- [ ] Pool monitoring thresholds configured
- [ ] GDPR anonymization enabled

### Verify Environment Variables

Run this command to verify all required variables are set:

```bash
python -c "
import os
required = ['SESSION_SECRET', 'ADMIN_PASSWORD']
missing = [v for v in required if not os.getenv(v)]
if missing:
    print(f'❌ Missing: {missing}')
    exit(1)
else:
    print('✅ All required environment variables set')
"
```

---

## Database Setup

### Database Creation

For AWS RDS or external PostgreSQL:

```bash
# Connect to PostgreSQL
psql -h <your-db-host> -U postgres

# Create database
CREATE DATABASE traitortrack_production;

# Create user (if needed)
CREATE USER traitortrack WITH PASSWORD '<secure_password>';
GRANT ALL PRIVILEGES ON DATABASE traitortrack_production TO traitortrack;
```

- [ ] Production database created
- [ ] Database user created with strong password
- [ ] Database accessible from application servers

### Database Migrations

Apply all migrations in order:

#### 1. Manual SQL Migrations

```bash
# Account lockout columns
psql $PRODUCTION_DATABASE_URL -f migrations_manual_sql/001_add_account_lockout_columns.sql

# Performance indexes (50+ indexes)
psql $PRODUCTION_DATABASE_URL -f migrations_manual_sql/002_add_user_and_promotion_indexes.sql
```

- [ ] Account lockout migration applied
- [ ] Performance indexes created (verify 50+ indexes exist)

#### 2. Alembic Migrations

```bash
# Initialize tables (if first deployment)
flask db upgrade head

# Or use Alembic directly
alembic upgrade head
```

- [ ] All Alembic migrations applied
- [ ] Migration history recorded (`alembic_version` table exists)

#### 3. Audit Log Enhancements

```bash
# Enhanced audit logging with before/after snapshots
psql $PRODUCTION_DATABASE_URL -f migrations/002_add_audit_before_after_columns.sql
```

- [ ] Audit log enhancements applied
- [ ] `before_state` and `after_state` columns exist

### Verify Database Schema

```bash
# Verify all tables exist
psql $PRODUCTION_DATABASE_URL -c "\dt"

# Expected tables:
# - user
# - bag
# - link
# - bill
# - bill_bag
# - scan
# - audit_log
# - promotionrequest
# - notification
# - alembic_version
```

- [ ] All 10 tables exist
- [ ] Indexes verified (run `\di` to list indexes)

### Initial Data Seeding

```bash
# Create initial admin user (if needed)
python manage.py create_admin --username admin --email admin@yourdomain.com
```

- [ ] Initial admin user created
- [ ] Admin can login successfully

---

## Security Hardening

### Application Security

- [ ] **HTTPS Enforcement**: Verify `SESSION_COOKIE_SECURE=True` in production
- [ ] **CSRF Protection**: Enabled via Flask-WTF (verify `WTF_CSRF_ENABLED=True`)
- [ ] **Security Headers**: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection
- [ ] **Password Hashing**: Scrypt algorithm (automatic via werkzeug)
- [ ] **Rate Limiting**: Configured for all auth endpoints
  - Login: 10/min
  - Register: 5/min
  - Password Reset: 3/min (forgot), 5/min (reset)
  - 2FA: 5/min (all endpoints)

### Database Security

```sql
-- Verify database user permissions (should NOT have superuser)
SELECT rolname, rolsuper FROM pg_roles WHERE rolname = 'traitortrack';

-- Enable SSL connections (AWS RDS default)
SHOW ssl;
```

- [ ] Database user is NOT superuser
- [ ] SSL connections enabled
- [ ] Database firewall rules configured (only allow app servers)

### Session Security

- [ ] Session files stored securely (`/tmp/flask_session` with proper permissions)
- [ ] Session cleanup cron job configured:

```bash
# Add to crontab
0 2 * * * find /tmp/flask_session -type f -mtime +2 -delete
```

- [ ] Non-permanent sessions (auto-logout on browser close)
- [ ] Session timeout: 1 hour absolute, 30 minutes inactivity

### Account Security

- [ ] Account lockout enabled (5 failed attempts → 30 min lockout)
- [ ] Password complexity enforced
- [ ] 2FA available for admin users
- [ ] Password reset tokens expire after 1 hour

### Audit & Compliance

- [ ] Audit logging enabled for all security events
- [ ] GDPR-compliant PII anonymization enabled (`ANONYMIZE_AUDIT_LOGS=true`)
- [ ] IP addresses anonymized in audit logs
- [ ] Email addresses anonymized in audit logs

---

## Performance Optimization

### Database Performance

- [ ] **Connection Pool**: Configured for 100+ concurrent users
  - Pool size: 25 per worker
  - Max overflow: 15 per worker
  - Total: 80 connections (2 workers × 40)
- [ ] **Indexes**: All 50+ performance indexes created
- [ ] **Query Optimizer**: `query_optimizer.py` enabled
- [ ] **Statistics Cache**: Database triggers created for dashboard stats

Verify statistics cache:

```sql
-- Check statistics_cache table exists
SELECT * FROM statistics_cache LIMIT 1;
```

- [ ] Statistics cache table exists and populated

### Application Performance

- [ ] **Caching**: In-memory caching enabled (`cache_utils.py`)
- [ ] **Cache TTL**: Configured (default: 300 seconds)
- [ ] **API Pagination**: 200-row limits with 10k offset cap
- [ ] **Request Logging**: Optimized (skips health checks, minimal API logging)

### Gunicorn Configuration

Verify `Procfile` or startup command:

```bash
# Recommended production config
gunicorn --bind 0.0.0.0:5000 \
  --workers 2 \
  --worker-class sync \
  --threads 4 \
  --timeout 120 \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --reuse-port \
  main:app
```

- [ ] Workers: 2-4 (formula: 2 × CPU cores)
- [ ] Threads: 4 per worker
- [ ] Timeout: 120 seconds
- [ ] Max requests: 1000 (auto-restart workers)

---

## Monitoring Setup

### Health Endpoints

- [ ] **Basic health**: `GET /health` - Returns 200 if app is running
- [ ] **System health**: `GET /api/system_health` - Comprehensive component status
- [ ] **Pool dashboard**: `/pool_dashboard` - Real-time connection pool metrics (admin only)

Test health endpoints:

```bash
# Basic health check
curl https://your-domain.com/health

# System health (requires authentication)
curl -u admin:password https://your-domain.com/api/system_health
```

### Connection Pool Monitoring

- [ ] Pool monitor started automatically (see `pool_monitor.py`)
- [ ] Alert thresholds configured:
  - Warning: 70%
  - Critical: 85%
  - Danger: 95%
- [ ] Email alerts configured (optional)
- [ ] Pool dashboard accessible to admins

### Application Logs

- [ ] Log level set to `INFO` (not `DEBUG`) in production
- [ ] Logs accessible via deployment platform
- [ ] Log rotation configured (if using file-based logging)

### Metrics to Monitor

#### Database Metrics

```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity;

-- Long-running queries (>5 seconds)
SELECT pid, now() - query_start as duration, query 
FROM pg_stat_activity 
WHERE state = 'active' AND now() - query_start > interval '5 seconds';

-- Database size
SELECT pg_size_pretty(pg_database_size('traitortrack_production'));
```

- [ ] Database connection monitoring configured
- [ ] Slow query logging enabled
- [ ] Database size alerts configured

#### Application Metrics

- [ ] Dashboard response time (<50ms target)
- [ ] API response time (<200ms target)
- [ ] Error rate monitoring
- [ ] Cache hit rate (>60% target)

---

## Post-Deployment Verification

### Smoke Tests

#### 1. Health Checks

```bash
# Test basic health
curl https://your-domain.com/health
# Expected: HTTP 200, {"status": "ok"}

# Test system health
curl -X GET https://your-domain.com/api/system_health \
  -H "Cookie: session=<admin_session>"
# Expected: HTTP 200, comprehensive health status
```

- [ ] Basic health check passes
- [ ] System health check passes
- [ ] All components report "healthy" status

#### 2. Authentication

- [ ] Admin login successful
- [ ] User registration works
- [ ] Password reset email sent (if configured)
- [ ] Account lockout works after 5 failed attempts
- [ ] Session timeout works (1 hour)

#### 3. Core Functionality

- [ ] Dashboard loads (<50ms)
- [ ] Create parent bag
- [ ] Scan child bag
- [ ] Link child to parent
- [ ] Create bill
- [ ] Link parent bag to bill
- [ ] View bill with correct weight calculations
- [ ] Search functionality works

#### 4. Admin Functions

- [ ] User management page accessible
- [ ] Admin can promote users
- [ ] Admin can reset user passwords
- [ ] Audit log viewable
- [ ] Pool dashboard accessible
- [ ] System health dashboard works

#### 5. Performance Tests

```bash
# Test dashboard performance
time curl https://your-domain.com/dashboard

# Test API endpoint performance
time curl https://your-domain.com/api/stats
```

- [ ] Dashboard response time <50ms
- [ ] API response time <200ms
- [ ] No database connection pool warnings

### Load Testing (Optional)

```bash
# Run locust load test (if available)
locust -f locustfile.py --host=https://your-domain.com

# Test with 50 concurrent users for 5 minutes
```

- [ ] System handles 50+ concurrent users
- [ ] No connection pool exhaustion
- [ ] Response times remain acceptable under load

---

## Rollback Procedures

### Quick Rollback (Application Only)

If deployment fails but database is intact:

```bash
# Revert to previous deployment
git checkout <previous_tag>

# Restart application
# (varies by deployment platform)
```

- [ ] Previous deployment tag documented
- [ ] Rollback process tested in staging

### Database Rollback

If database migration fails:

```bash
# Downgrade Alembic migrations
alembic downgrade -1

# Or downgrade to specific version
alembic downgrade <revision_id>
```

- [ ] Database backup exists BEFORE migration
- [ ] Rollback SQL scripts prepared (if needed)

### Full Rollback Checklist

- [ ] Stop application
- [ ] Restore database from backup (if needed)
- [ ] Revert application code
- [ ] Verify environment variables
- [ ] Restart application
- [ ] Run smoke tests
- [ ] Monitor for errors

### Backup Restoration

```bash
# Restore PostgreSQL backup
pg_restore --dbname=traitortrack_production \
  --clean --if-exists \
  /path/to/backup.dump

# Or for SQL format
psql traitortrack_production < /path/to/backup.sql
```

- [ ] Backup restoration procedure tested
- [ ] Recovery Time Objective (RTO) documented
- [ ] Recovery Point Objective (RPO) documented

---

## Go-Live Checklist

### Pre-Launch (T-24 hours)

- [ ] All checklist items above completed
- [ ] Staging environment tested successfully
- [ ] Database backup completed
- [ ] Rollback plan documented and tested
- [ ] Support team briefed
- [ ] Monitoring dashboards configured
- [ ] On-call schedule established

### Launch Window (T-0)

- [ ] Deploy application to production
- [ ] Run database migrations
- [ ] Verify health endpoints
- [ ] Run smoke tests
- [ ] Monitor error rates
- [ ] Monitor connection pool usage
- [ ] Monitor system resources (CPU, memory, disk)

### Post-Launch (T+1 hour)

- [ ] All smoke tests passing
- [ ] No critical errors in logs
- [ ] Connection pool healthy (<70% usage)
- [ ] Dashboard performance acceptable
- [ ] User logins successful
- [ ] Audit logging working

### Post-Launch (T+24 hours)

- [ ] Monitor application metrics
- [ ] Review audit logs for anomalies
- [ ] Check database performance
- [ ] Verify backup jobs running
- [ ] Review user feedback
- [ ] Document any issues encountered

---

## Related Documentation

- [Operational Runbook](OPERATIONAL_RUNBOOK.md) - Day-to-day operations
- [Admin Guide](ADMIN_GUIDE_TROUBLESHOOTING.md) - Admin tasks and troubleshooting
- [Session Configuration](SESSION_CONFIGURATION.md) - Session management details
- [Audit Logging Guide](AUDIT_LOGGING_GUIDE.md) - Audit system documentation
- [Features Documentation](FEATURES.md) - Feature status and capabilities

---

## Support Contacts

- **Development Team**: [Contact Information]
- **Database Admin**: [Contact Information]
- **Security Team**: [Contact Information]
- **On-Call Support**: [Contact Information]

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | November 2025 | Initial production deployment checklist |

---

**Note**: This checklist should be reviewed and updated after each deployment to reflect lessons learned and process improvements.

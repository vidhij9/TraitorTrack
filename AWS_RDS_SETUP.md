# AWS RDS PostgreSQL Setup for TraceTrack Production

## Overview
This guide explains how to set up AWS RDS PostgreSQL as the production database for your TraceTrack deployment on Replit, while keeping the development environment separate.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│  Development (Replit Workspace)             │
│  ├─ DATABASE_URL → Replit PostgreSQL        │
│  ├─ For testing & development               │
│  └─ Data: Test bags, test users             │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│  Production (Replit Deployment)             │
│  ├─ DATABASE_URL → AWS RDS PostgreSQL       │
│  ├─ For live operations                     │
│  └─ Data: Real bags, real users, real bills │
└─────────────────────────────────────────────┘
```

---

## Step-by-Step AWS RDS Setup

### Step 1: Create RDS Instance

1. **Sign in to AWS Console** → Navigate to RDS

2. **Create Database**:
   - Click "Create database"
   - Choose **PostgreSQL**
   - PostgreSQL Version: **14.x** or higher (recommended)

3. **Templates**:
   - For testing: **Free tier** (db.t3.micro)
   - For production: **Production** (db.t3.medium or higher)

4. **Settings**:
   ```
   DB instance identifier: tracetrack-production
   Master username: tracetrack_admin
   Master password: <generate-secure-password>
   ```

5. **Instance Configuration**:
   - Instance class: 
     - Testing: db.t3.micro (1 vCPU, 1 GB RAM)
     - Light production: db.t3.small (2 vCPU, 2 GB RAM)
     - Production: db.t3.medium+ (2 vCPU, 4 GB RAM)

6. **Storage**:
   - Storage type: General Purpose SSD (gp3)
   - Allocated storage: 20 GB (will auto-scale if needed)
   - Enable storage autoscaling
   - Maximum storage threshold: 100 GB

7. **Connectivity**:
   - VPC: Default (or your custom VPC)
   - Public access: **Yes** (for Replit to connect)
   - VPC security group: Create new or select existing
   - Availability Zone: No preference

8. **Database authentication**:
   - Password authentication (recommended for simplicity)
   - Or IAM database authentication (more secure)

9. **Additional Configuration**:
   - Initial database name: `tracetrack_production`
   - Backup retention: 7 days (recommended)
   - Enable automated backups
   - Backup window: Choose off-peak hours
   - Maintenance window: Choose off-peak hours

10. **Click "Create database"** (takes 5-10 minutes)

### Step 2: Configure Security Group

1. **Go to RDS** → Select your instance → **Connectivity & security** tab

2. **Click on the VPC security group**

3. **Edit inbound rules**:
   - Type: PostgreSQL
   - Protocol: TCP
   - Port: 5432
   - Source: **Custom** → `0.0.0.0/0` (allows all IPs - use with strong password)
   - OR: Specific Replit IPs if known
   - Description: "TraceTrack Replit access"

4. **Save rules**

**Security Note**: Opening to 0.0.0.0/0 is acceptable if:
- ✅ You use a strong master password
- ✅ RDS is not accessible without credentials
- ✅ You enable SSL/TLS connections
- ❌ Never commit credentials to code

### Step 3: Get Connection Details

1. **Go to RDS** → Select your instance

2. **Copy Endpoint** (from Connectivity & security):
   ```
   Example: tracetrack-production.abc123.us-east-1.rds.amazonaws.com
   ```

3. **Note Port**: Usually `5432`

4. **Build CONNECTION_URL**:
   ```
   postgresql://[username]:[password]@[endpoint]:[port]/[database]
   
   Example:
   postgresql://tracetrack_admin:YourSecureP@ss123@tracetrack-production.abc123.us-east-1.rds.amazonaws.com:5432/tracetrack_production
   ```

### Step 4: Test Connection Locally

Before deploying, test the connection:

```bash
# Method 1: Using psql (if installed)
psql "postgresql://username:password@endpoint:5432/database"

# Method 2: Using Python verification script
DATABASE_URL="postgresql://username:password@endpoint:5432/database" python verify_db_connection.py
```

Expected output:
```
✅ Connection successful!
   Database: tracetrack_production
   User: tracetrack_admin
   Size: 8192 kB
   PostgreSQL: PostgreSQL 14.x on x86_64-pc-linux-gnu
   Tables: 0

⚠️  WARNING: No tables found. Database needs initialization.
   The app will create tables automatically on first run.
```

### Step 5: Configure Replit Deployment

1. **In Replit**, open your TraceTrack project

2. **Go to Deployments**:
   - Click the "Deploy" button
   - Or use existing deployment

3. **Configure Environment Variables**:
   - Click on deployment settings/secrets
   - Add or update `DATABASE_URL`:
     ```
     DATABASE_URL=postgresql://tracetrack_admin:YourSecureP@ss123@tracetrack-production.abc123.us-east-1.rds.amazonaws.com:5432/tracetrack_production
     ```

4. **Keep Development Separate**:
   - In your workspace, go to Secrets (🔒 icon)
   - Verify `DATABASE_URL` points to Replit database (don't change it)
   - This keeps dev and prod data completely separate

### Step 6: Deploy and Initialize

1. **Deploy your application** on Replit

2. **First deployment** will automatically:
   - Create all database tables
   - Set up statistics_cache with triggers
   - Create indexes for performance
   - Initialize admin user

3. **Monitor deployment logs** for:
   ```
   Database initialized successfully
   Query optimizer initialized for high-performance operations
   ```

4. **Verify production database**:
   - Login to deployed app
   - Check dashboard loads
   - Create a test bag
   - Verify system health metrics

---

## Database Maintenance

### Daily Monitoring

Check RDS CloudWatch metrics:
- **CPU Utilization**: Should stay <70%
- **Free Storage**: Monitor growth
- **Database Connections**: Should be <80 (configured max)
- **Read/Write IOPS**: Monitor for bottlenecks

### Weekly Tasks

1. **Review Performance Insights**:
   - Identify slow queries
   - Check for connection pool issues
   - Monitor query patterns

2. **Check Backup Status**:
   - Verify automated backups are running
   - Test point-in-time recovery capability

### Monthly Tasks

1. **Review and Optimize**:
   - Run `VACUUM ANALYZE` for table optimization
   - Review indexes
   - Check for unused tables

2. **Security Audit**:
   - Review security group rules
   - Rotate master password if needed
   - Check for unauthorized access attempts

---

## Cost Optimization

### Current Configuration
- **db.t3.micro** (Free tier): ~$0/month for 12 months
- **db.t3.small**: ~$24/month
- **db.t3.medium**: ~$58/month
- **Storage**: ~$0.10/GB/month
- **Backup**: $0.095/GB/month

### Tips to Reduce Costs
1. Use **Reserved Instances** for 1-3 year commitments (up to 60% savings)
2. Right-size instance based on actual usage
3. Delete old manual snapshots
4. Use **RDS Proxy** to reduce connection overhead (for high traffic)
5. Consider **Aurora Serverless** for variable workloads

---

## Troubleshooting

### Connection Timeout
**Symptom**: App can't connect to RDS
**Solutions**:
- ✅ Verify security group allows port 5432
- ✅ Check RDS instance is "Available"
- ✅ Confirm endpoint URL is correct
- ✅ Test with `psql` or `verify_db_connection.py`

### Slow Queries
**Symptom**: Dashboard or lists load slowly
**Solutions**:
- ✅ Enable Performance Insights in RDS
- ✅ Check statistics_cache is updating
- ✅ Verify indexes are created
- ✅ Consider upgrading instance size

### Connection Pool Exhausted
**Symptom**: "Too many connections" errors
**Solutions**:
- ✅ Check RDS CloudWatch for connection count
- ✅ Increase `max_connections` in RDS parameter group
- ✅ Review app connection pool settings
- ✅ Consider using RDS Proxy

### High Costs
**Symptom**: Unexpected AWS charges
**Solutions**:
- ✅ Check instance type (downgrade if over-provisioned)
- ✅ Delete unused snapshots
- ✅ Review backup retention period
- ✅ Consider Reserved Instances

---

## Migration from Replit Database

If you have existing data in Replit database that needs to be migrated:

### Export from Replit Database
```bash
# In Replit workspace
pg_dump $DATABASE_URL > backup.sql
```

### Import to AWS RDS
```bash
# Point to AWS RDS
psql "postgresql://username:password@rds-endpoint:5432/database" < backup.sql
```

### Verify Migration
```bash
# Check table counts match
DATABASE_URL="rds-connection-string" python verify_db_connection.py
```

---

## Security Best Practices

1. **✅ Use Strong Passwords**:
   - Minimum 16 characters
   - Mix of uppercase, lowercase, numbers, symbols
   - Use password generator

2. **✅ Enable SSL/TLS**:
   - Download RDS CA certificate
   - Add to connection string: `?sslmode=require`

3. **✅ Rotate Credentials**:
   - Rotate master password every 90 days
   - Use AWS Secrets Manager for automatic rotation

4. **✅ Enable Encryption**:
   - Encryption at rest (enabled during creation)
   - Encryption in transit (SSL/TLS)

5. **✅ Monitor Access**:
   - Enable CloudTrail for API calls
   - Review CloudWatch logs
   - Set up alerts for suspicious activity

6. **✅ Regular Backups**:
   - Automated daily backups (enabled)
   - Test restore procedures monthly
   - Consider cross-region backup for DR

---

## Support Resources

- **AWS RDS Documentation**: https://docs.aws.amazon.com/rds/
- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **Replit Deployments**: Replit documentation
- **TraceTrack Docs**: See `DEPLOYMENT.md`

---

## Quick Reference

### Connection String Format
```
postgresql://[username]:[password]@[endpoint]:[port]/[database]
```

### Common psql Commands
```bash
# Connect
psql "postgresql://user:pass@host:5432/db"

# List databases
\l

# List tables
\dt

# Describe table
\d table_name

# Exit
\q
```

### Verification Commands
```bash
# Test connection
python verify_db_connection.py

# Check tables
psql -c "\dt" "connection-string"

# Check database size
psql -c "SELECT pg_size_pretty(pg_database_size(current_database()));" "connection-string"
```

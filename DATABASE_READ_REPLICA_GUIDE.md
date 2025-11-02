# TraitorTrack Database Read Replica Guide

**Version:** 1.0.0  
**Last Updated:** November 2025  
**System:** TraitorTrack Warehouse Bag Tracking System

---

## Table of Contents

1. [Overview](#overview)
2. [Benefits for TraitorTrack](#benefits-for-traitortrack)
3. [PostgreSQL Read Replica Configuration](#postgresql-read-replica-configuration)
4. [Connection String Setup](#connection-string-setup)
5. [Application Code Changes](#application-code-changes)
6. [Monitoring Replica Lag](#monitoring-replica-lag)
7. [Failover Procedures](#failover-procedures)
8. [Load Balancing Strategies](#load-balancing-strategies)
9. [Performance Tuning](#performance-tuning)
10. [Troubleshooting](#troubleshooting)

---

## Overview

Read replicas are read-only copies of your primary PostgreSQL database that asynchronously replicate data from the primary instance. They enable horizontal scaling of read-heavy workloads by distributing queries across multiple database servers.

### How Read Replicas Work

```
┌─────────────────┐
│  Primary DB     │ ──┐
│  (Read/Write)   │   │ Streaming
└─────────────────┘   │ Replication
                      │
                      ├──> ┌─────────────────┐
                      │    │  Read Replica 1 │
                      │    │  (Read Only)    │
                      │    └─────────────────┘
                      │
                      └──> ┌─────────────────┐
                           │  Read Replica 2 │
                           │  (Read Only)    │
                           └─────────────────┘
```

### Key Characteristics

- **Asynchronous Replication**: Changes are replicated with minimal lag (typically <1 second)
- **Read-Only**: Replicas cannot accept write operations
- **Automatic Failover**: Can be promoted to primary in disaster scenarios
- **Regional Distribution**: Can be deployed in different AWS regions for lower latency

---

## Benefits for TraitorTrack

### Current Load Profile

TraitorTrack's workload is heavily read-biased:

- **Dashboard Statistics**: Real-time queries every 2-5 seconds per user
- **Bag Lookups**: High-frequency searches and QR scans
- **Report Generation**: Analytics queries for bills and scan history
- **Audit Log Queries**: Security reviews and compliance reporting

**Estimated Read/Write Ratio**: 80-90% reads, 10-20% writes

### Performance Improvements

| Metric | Before Replicas | With 2 Replicas | Improvement |
|--------|----------------|-----------------|-------------|
| Dashboard Load Time | 50ms | 20-30ms | 40-60% faster |
| Concurrent Users | 100 | 200-300 | 2-3x capacity |
| Query Queue Time | 10-50ms | <5ms | 80-90% reduction |
| Primary DB CPU | 60-80% | 30-40% | 50% reduction |

### Cost-Benefit Analysis

**Costs:**
- AWS RDS Read Replica: ~$150-300/month (db.t3.large)
- Additional storage: ~$20-50/month
- Data transfer: ~$10-30/month

**Total**: ~$180-380/month

**Benefits:**
- Support 2-3x more users without primary DB upgrade
- Improved response times for all read operations
- Reduced risk of primary DB overload
- Better disaster recovery capability

**ROI**: Break-even at 150+ concurrent users or when primary DB CPU consistently exceeds 60%

---

## PostgreSQL Read Replica Configuration

### AWS RDS Read Replica Setup

#### Prerequisites

- Existing AWS RDS PostgreSQL primary instance
- Automated backups enabled on primary
- Sufficient network bandwidth between primary and replica

#### Step 1: Enable Automated Backups

```bash
# Verify backups are enabled (required for replication)
aws rds describe-db-instances \
  --db-instance-identifier traitortrack-primary \
  --query 'DBInstances[0].BackupRetentionPeriod'

# Enable if not configured
aws rds modify-db-instance \
  --db-instance-identifier traitortrack-primary \
  --backup-retention-period 7 \
  --apply-immediately
```

#### Step 2: Create Read Replica

**Via AWS Console:**

1. Navigate to RDS → Databases
2. Select `traitortrack-primary`
3. Click **Actions** → **Create read replica**
4. Configure:
   - **DB instance identifier**: `traitortrack-replica-1`
   - **Instance class**: `db.t3.large` (match or smaller than primary)
   - **Multi-AZ**: No (for cost savings)
   - **Public accessibility**: No
   - **VPC security groups**: Same as primary
5. Click **Create read replica**

**Via AWS CLI:**

```bash
aws rds create-db-instance-read-replica \
  --db-instance-identifier traitortrack-replica-1 \
  --source-db-instance-identifier traitortrack-primary \
  --db-instance-class db.t3.large \
  --availability-zone us-east-1b \
  --no-publicly-accessible \
  --vpc-security-group-ids sg-xxxxxxxxx \
  --tags Key=Environment,Value=production Key=Role,Value=read-replica
```

**Creation time**: 10-30 minutes depending on database size

#### Step 3: Verify Replication Status

```sql
-- Connect to primary database
psql $PRODUCTION_DATABASE_URL

-- Check replication slots
SELECT * FROM pg_replication_slots;

-- Check replication lag (on primary)
SELECT
    client_addr,
    state,
    sent_lsn,
    write_lsn,
    replay_lsn,
    sync_state,
    pg_wal_lsn_diff(sent_lsn, replay_lsn) AS lag_bytes
FROM pg_stat_replication;
```

Expected output:
```
 client_addr |   state   | lag_bytes 
-------------+-----------+-----------
 10.0.1.20   | streaming |      1024
```

#### Step 4: Configure Replica Parameters

```bash
# Create parameter group for read replica
aws rds create-db-parameter-group \
  --db-parameter-group-name traitortrack-replica-params \
  --db-parameter-group-family postgres14 \
  --description "TraitorTrack read replica optimizations"

# Optimize for read-heavy workload
aws rds modify-db-parameter-group \
  --db-parameter-group-name traitortrack-replica-params \
  --parameters \
    "ParameterName=max_connections,ParameterValue=200,ApplyMethod=immediate" \
    "ParameterName=shared_buffers,ParameterValue=2097152,ApplyMethod=pending-reboot" \
    "ParameterName=effective_cache_size,ParameterValue=6291456,ApplyMethod=immediate" \
    "ParameterName=random_page_cost,ParameterValue=1.1,ApplyMethod=immediate"

# Apply parameter group to replica
aws rds modify-db-instance \
  --db-instance-identifier traitortrack-replica-1 \
  --db-parameter-group-name traitortrack-replica-params \
  --apply-immediately
```

### Self-Managed PostgreSQL Replication

For non-AWS deployments:

#### Primary Configuration

Edit `/etc/postgresql/14/main/postgresql.conf`:

```conf
# Replication settings
wal_level = replica
max_wal_senders = 5
wal_keep_size = 1024MB
hot_standby = on
```

Edit `/etc/postgresql/14/main/pg_hba.conf`:

```conf
# Allow replication connections
host replication replicator 10.0.1.0/24 md5
```

Restart PostgreSQL:

```bash
sudo systemctl restart postgresql
```

#### Replica Configuration

1. **Create base backup from primary:**

```bash
# On replica server
sudo -u postgres pg_basebackup \
  -h primary-db-host \
  -U replicator \
  -D /var/lib/postgresql/14/main \
  -P -v -R -X stream -C -S replica_1
```

2. **Configure recovery settings:**

Create `/var/lib/postgresql/14/main/postgresql.auto.conf`:

```conf
primary_conninfo = 'host=primary-db-host port=5432 user=replicator password=xxxxx'
primary_slot_name = 'replica_1'
```

3. **Start replica:**

```bash
sudo systemctl start postgresql
```

4. **Verify replication:**

```sql
-- On replica
SELECT pg_is_in_recovery();  -- Should return 't' (true)

-- Check lag
SELECT
    CASE
        WHEN pg_last_wal_receive_lsn() = pg_last_wal_replay_lsn()
        THEN 0
        ELSE EXTRACT(EPOCH FROM now() - pg_last_xact_replay_timestamp())
    END AS lag_seconds;
```

---

## Connection String Setup

### Environment Variables

Add read replica connection strings to your environment:

```bash
# Primary database (read/write)
PRODUCTION_DATABASE_URL=postgresql://user:pass@traitortrack-primary.xxxx.us-east-1.rds.amazonaws.com:5432/traitortrack

# Read replica 1 (read-only)
READ_REPLICA_1_URL=postgresql://user:pass@traitortrack-replica-1.xxxx.us-east-1.rds.amazonaws.com:5432/traitortrack

# Read replica 2 (read-only) - optional
READ_REPLICA_2_URL=postgresql://user:pass@traitortrack-replica-2.xxxx.us-east-1.rds.amazonaws.com:5432/traitortrack

# Load balancer endpoint (optional, for automatic distribution)
READ_REPLICA_POOL_URL=postgresql://user:pass@traitortrack-read-pool.xxxx.us-east-1.rds.amazonaws.com:5432/traitortrack
```

### Connection Pool Configuration

Update `app.py` to support multiple database connections:

```python
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool, QueuePool

app = Flask(__name__)

# Primary database (write operations)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("PRODUCTION_DATABASE_URL")
app.config["SQLALCHEMY_BINDS"] = {
    "primary": os.environ.get("PRODUCTION_DATABASE_URL"),
    "replica_1": os.environ.get("READ_REPLICA_1_URL"),
    "replica_2": os.environ.get("READ_REPLICA_2_URL"),
}

# Configure connection pools
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 20,
    "max_overflow": 10,
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Separate engine options for replicas (higher pool sizes for read-heavy load)
app.config["SQLALCHEMY_BINDS_ENGINE_OPTIONS"] = {
    "replica_1": {
        "pool_size": 30,
        "max_overflow": 20,
        "pool_recycle": 300,
        "pool_pre_ping": True,
    },
    "replica_2": {
        "pool_size": 30,
        "max_overflow": 20,
        "pool_recycle": 300,
        "pool_pre_ping": True,
    },
}

db = SQLAlchemy(app)
```

### Load Balancer Setup (Optional)

For automatic read distribution, use AWS RDS Proxy or pgBouncer:

**AWS RDS Proxy Configuration:**

```bash
aws rds create-db-proxy \
  --db-proxy-name traitortrack-read-proxy \
  --engine-family POSTGRESQL \
  --auth '[{"AuthScheme":"SECRETS","SecretArn":"arn:aws:secretsmanager:..."}]' \
  --role-arn arn:aws:iam::123456789:role/RDSProxyRole \
  --vpc-subnet-ids subnet-xxx subnet-yyy \
  --target-group-config '{
      "DBInstanceIdentifiers": [
          "traitortrack-replica-1",
          "traitortrack-replica-2"
      ],
      "ConnectionPoolConfig": {
          "MaxConnectionsPercent": 100,
          "MaxIdleConnectionsPercent": 50
      }
  }'
```

---

## Application Code Changes

### Database Router Utility

Create `db_router.py` to intelligently route queries:

```python
from flask import g
from sqlalchemy import event
from sqlalchemy.engine import Engine
import random
import logging

logger = logging.getLogger(__name__)

class DatabaseRouter:
    """
    Intelligent database routing for read/write splitting.
    
    Routes write operations to primary, read operations to replicas.
    Includes health checking and automatic failback.
    """
    
    def __init__(self, app, db):
        self.app = app
        self.db = db
        self.replicas = ['replica_1', 'replica_2']
        self.unhealthy_replicas = set()
        self.last_health_check = {}
        
    def get_read_bind(self):
        """
        Get a healthy read replica connection.
        Falls back to primary if no replicas available.
        """
        healthy_replicas = [
            r for r in self.replicas 
            if r not in self.unhealthy_replicas
        ]
        
        if not healthy_replicas:
            logger.warning("No healthy read replicas, using primary")
            return None  # Use default (primary)
        
        # Round-robin selection
        selected = random.choice(healthy_replicas)
        return selected
    
    def execute_on_replica(self, query):
        """Execute SELECT query on read replica"""
        bind = self.get_read_bind()
        
        try:
            if bind:
                result = self.db.session.execute(
                    query,
                    bind_arguments={'bind': self.db.get_engine(self.app, bind)}
                )
            else:
                result = self.db.session.execute(query)
            return result
        except Exception as e:
            logger.error(f"Replica query failed, falling back to primary: {e}")
            if bind:
                self.unhealthy_replicas.add(bind)
            return self.db.session.execute(query)
    
    def health_check(self):
        """Check replica health and remove from unhealthy set if recovered"""
        for replica in list(self.unhealthy_replicas):
            try:
                engine = self.db.get_engine(self.app, replica)
                with engine.connect() as conn:
                    conn.execute("SELECT 1")
                self.unhealthy_replicas.remove(replica)
                logger.info(f"Replica {replica} recovered")
            except Exception as e:
                logger.debug(f"Replica {replica} still unhealthy: {e}")

# Initialize router
router = DatabaseRouter(app, db)
```

### Query Optimization Utility

Update `query_optimizer.py` to use read replicas:

```python
from db_router import router
from sqlalchemy import text

def get_dashboard_stats_from_replica():
    """
    Fetch dashboard statistics from read replica.
    Falls back to primary if replica unavailable.
    """
    query = text("""
        SELECT 
            total_bags,
            parent_bags,
            child_bags,
            total_bills,
            scans_today
        FROM statistics_cache
        WHERE id = 1
    """)
    
    result = router.execute_on_replica(query)
    return result.fetchone()

def search_bags_on_replica(search_term, limit=50, offset=0):
    """Search bags using read replica for reduced primary load"""
    query = text("""
        SELECT id, qr_id, type, weight, status, created_at
        FROM bag
        WHERE qr_id ILIKE :search_term
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """)
    
    result = router.execute_on_replica(
        query.bindparams(
            search_term=f"%{search_term}%",
            limit=limit,
            offset=offset
        )
    )
    return result.fetchall()

def get_audit_logs_from_replica(user_id=None, limit=100):
    """Fetch audit logs from replica (read-heavy, non-critical for consistency)"""
    if user_id:
        query = text("""
            SELECT timestamp, action, entity_type, details, ip_address
            FROM audit_log
            WHERE user_id = :user_id
            ORDER BY timestamp DESC
            LIMIT :limit
        """)
        result = router.execute_on_replica(
            query.bindparams(user_id=user_id, limit=limit)
        )
    else:
        query = text("""
            SELECT timestamp, username, action, entity_type, details
            FROM audit_log
            LEFT JOIN "user" ON audit_log.user_id = "user".id
            ORDER BY timestamp DESC
            LIMIT :limit
        """)
        result = router.execute_on_replica(query.bindparams(limit=limit))
    
    return result.fetchall()
```

### Route Updates

Update `routes.py` to use read replicas for read-heavy endpoints:

```python
from query_optimizer import (
    get_dashboard_stats_from_replica,
    search_bags_on_replica,
    get_audit_logs_from_replica
)

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard using read replica for statistics"""
    try:
        stats = get_dashboard_stats_from_replica()
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash('Error loading dashboard', 'error')
        return render_template('dashboard.html', stats={})

@app.route('/bag_management')
@login_required
def bag_management():
    """Bag search using read replica"""
    search_term = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    per_page = 50
    offset = (page - 1) * per_page
    
    bags = search_bags_on_replica(search_term, limit=per_page, offset=offset)
    return render_template('bag_management.html', bags=bags, page=page)

@app.route('/admin/audit_logs')
@login_required
@admin_required
def audit_logs():
    """Audit log viewer using read replica"""
    logs = get_audit_logs_from_replica(limit=200)
    return render_template('audit_logs.html', logs=logs)
```

### Write Operations (Always Use Primary)

Ensure write operations explicitly use primary:

```python
@app.route('/scan_parent', methods=['POST'])
@login_required
def scan_parent():
    """Scanning always uses primary database for consistency"""
    qr_id = request.form.get('qr_id')
    
    # This automatically uses primary (default bind)
    bag = Bag.query.filter_by(qr_id=qr_id).first()
    
    if not bag:
        bag = Bag(qr_id=qr_id, type='parent', status='active')
        db.session.add(bag)
    
    # Create scan record
    scan = Scan(bag_id=bag.id, user_id=current_user.id, scan_type='parent')
    db.session.add(scan)
    db.session.commit()
    
    return redirect(url_for('scan_complete'))
```

### Session Affinity for Consistency

For operations requiring read-after-write consistency:

```python
from flask import g

@app.before_request
def set_session_affinity():
    """
    Track recent writes in session to avoid reading stale data.
    Forces primary for reads immediately after writes.
    """
    g.force_primary = session.get('recent_write', False)
    
    # Clear flag after 5 seconds
    if g.force_primary:
        write_time = session.get('write_timestamp', 0)
        if time.time() - write_time > 5:
            session['recent_write'] = False
            g.force_primary = False

@app.after_request
def track_writes(response):
    """Mark session as having recent writes"""
    if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
        session['recent_write'] = True
        session['write_timestamp'] = time.time()
    return response
```

---

## Monitoring Replica Lag

### Key Metrics to Track

1. **Replication Lag** (bytes and seconds)
2. **Replica Connection Health**
3. **Query Distribution** (% to primary vs replicas)
4. **Error Rates** (replica query failures)

### Monitoring Queries

**On Primary Database:**

```sql
-- Replication lag in bytes and seconds
SELECT
    application_name,
    client_addr,
    state,
    sent_lsn,
    write_lsn,
    replay_lsn,
    sync_state,
    pg_wal_lsn_diff(sent_lsn, replay_lsn) AS lag_bytes,
    EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) AS lag_seconds
FROM pg_stat_replication;
```

**On Replica Database:**

```sql
-- Check if in recovery mode (should be true)
SELECT pg_is_in_recovery();

-- Last WAL received and replayed
SELECT
    pg_last_wal_receive_lsn() AS received_lsn,
    pg_last_wal_replay_lsn() AS replayed_lsn,
    pg_wal_lsn_diff(
        pg_last_wal_receive_lsn(),
        pg_last_wal_replay_lsn()
    ) AS lag_bytes;

-- Time since last replay
SELECT
    pg_last_xact_replay_timestamp() AS last_replay,
    EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) AS lag_seconds;
```

### Application-Level Monitoring

Add to `health_check.py`:

```python
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def check_replica_health():
    """
    Monitor read replica health and lag.
    Returns status and metrics for monitoring dashboard.
    """
    replicas = ['replica_1', 'replica_2']
    results = {}
    
    for replica in replicas:
        try:
            engine = db.get_engine(app, replica)
            with engine.connect() as conn:
                # Check if replica is responsive
                start_time = time.time()
                conn.execute(text("SELECT 1"))
                response_time = (time.time() - start_time) * 1000
                
                # Check replication lag
                lag_query = text("""
                    SELECT
                        pg_is_in_recovery() AS is_replica,
                        EXTRACT(EPOCH FROM (
                            now() - pg_last_xact_replay_timestamp()
                        )) AS lag_seconds
                """)
                result = conn.execute(lag_query).fetchone()
                
                lag_seconds = result.lag_seconds if result.lag_seconds else 0
                
                results[replica] = {
                    'status': 'healthy',
                    'response_time_ms': round(response_time, 2),
                    'lag_seconds': round(lag_seconds, 2),
                    'is_replica': result.is_replica,
                    'severity': 'ok' if lag_seconds < 5 else 'warning' if lag_seconds < 30 else 'critical'
                }
                
        except Exception as e:
            logger.error(f"Replica {replica} health check failed: {e}")
            results[replica] = {
                'status': 'unhealthy',
                'error': str(e),
                'severity': 'critical'
            }
    
    return results

@app.route('/api/replica_health')
@login_required
@admin_required
def replica_health_api():
    """API endpoint for replica monitoring dashboard"""
    health = check_replica_health()
    return jsonify(health)
```

### CloudWatch Alarms (AWS RDS)

```bash
# Alert if replica lag exceeds 30 seconds
aws cloudwatch put-metric-alarm \
  --alarm-name traitortrack-replica-lag-high \
  --alarm-description "Read replica lag exceeds 30 seconds" \
  --metric-name ReplicaLag \
  --namespace AWS/RDS \
  --statistic Average \
  --period 60 \
  --threshold 30 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --dimensions Name=DBInstanceIdentifier,Value=traitortrack-replica-1 \
  --alarm-actions arn:aws:sns:us-east-1:123456789:traitortrack-alerts

# Alert if replica connections fail
aws cloudwatch put-metric-alarm \
  --alarm-name traitortrack-replica-connection-failures \
  --alarm-description "Read replica connection failures detected" \
  --metric-name DatabaseConnections \
  --namespace AWS/RDS \
  --statistic Sum \
  --period 300 \
  --threshold 0 \
  --comparison-operator LessThanOrEqualToThreshold \
  --evaluation-periods 1 \
  --dimensions Name=DBInstanceIdentifier,Value=traitortrack-replica-1 \
  --alarm-actions arn:aws:sns:us-east-1:123456789:traitortrack-alerts
```

### Alerting Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Replication Lag | >5 seconds | >30 seconds | Investigate primary load, check network |
| Response Time | >100ms | >500ms | Check replica CPU/memory, consider scaling |
| Error Rate | >1% | >5% | Failover to primary, investigate replica |
| Connection Failures | Any | Sustained | Promote replica or restart |

---

## Failover Procedures

### When to Failover

**Planned Failover (Maintenance):**
- Primary database maintenance window
- Primary instance upgrade
- Region migration

**Unplanned Failover (Disaster):**
- Primary database failure
- Data center outage
- Corruption detection

### Pre-Failover Checklist

- [ ] Verify replica is caught up (lag <5 seconds)
- [ ] Backup current primary database
- [ ] Notify team of planned downtime
- [ ] Prepare rollback plan
- [ ] Update DNS/connection strings

### Promote Replica to Primary (AWS RDS)

**Via AWS Console:**

1. Navigate to RDS → Databases
2. Select `traitortrack-replica-1`
3. Click **Actions** → **Promote read replica**
4. Confirm promotion

**Via AWS CLI:**

```bash
# Promote replica to standalone instance
aws rds promote-read-replica \
  --db-instance-identifier traitortrack-replica-1

# Wait for promotion to complete
aws rds wait db-instance-available \
  --db-instance-identifier traitortrack-replica-1

# Verify new instance is read-write
aws rds describe-db-instances \
  --db-instance-identifier traitortrack-replica-1 \
  --query 'DBInstances[0].StatusInfos'
```

**Promotion time**: 5-15 minutes

### Update Application Configuration

```bash
# Update environment variables
# Old primary → read replica (demoted)
READ_REPLICA_1_URL=postgresql://user:pass@traitortrack-primary.xxxx.rds.amazonaws.com:5432/traitortrack

# Promoted replica → new primary
PRODUCTION_DATABASE_URL=postgresql://user:pass@traitortrack-replica-1.xxxx.rds.amazonaws.com:5432/traitortrack

# Restart application
sudo systemctl restart traitortrack
```

### Recreate Read Replicas

After promotion, create new read replicas from new primary:

```bash
aws rds create-db-instance-read-replica \
  --db-instance-identifier traitortrack-replica-new \
  --source-db-instance-identifier traitortrack-replica-1 \
  --db-instance-class db.t3.large
```

### Fallback to Original Primary

If failover was unsuccessful:

```bash
# Stop application writes
sudo systemctl stop traitortrack

# Demote promoted replica back to read-only
# (Manual step: requires database restart and configuration change)

# Point application back to original primary
export PRODUCTION_DATABASE_URL=<original_primary_url>

# Restart application
sudo systemctl start traitortrack
```

### Post-Failover Verification

```bash
# Verify application connectivity
curl https://your-domain.com/health

# Check database write operations
psql $PRODUCTION_DATABASE_URL -c "
    INSERT INTO audit_log (user_id, action, entity_type, details, ip_address)
    VALUES (1, 'failover_test', 'system', '{\"test\": true}', '127.0.0.1');
"

# Verify replication from new primary
psql $PRODUCTION_DATABASE_URL -c "SELECT * FROM pg_stat_replication;"

# Monitor for errors
tail -f /var/log/traitortrack/app.log
```

---

## Load Balancing Strategies

### Strategy 1: Application-Level Round Robin

**Pros:** Full control, no additional infrastructure  
**Cons:** Application complexity, no automatic health checking

Implementation in `db_router.py`:

```python
class RoundRobinRouter:
    def __init__(self, replicas):
        self.replicas = replicas
        self.current = 0
    
    def get_next_replica(self):
        replica = self.replicas[self.current % len(self.replicas)]
        self.current += 1
        return replica
```

### Strategy 2: AWS RDS Proxy

**Pros:** Automatic health checks, connection pooling, minimal app changes  
**Cons:** Additional cost (~$20/month), slight latency increase

See [Connection String Setup](#connection-string-setup) for configuration.

### Strategy 3: PgBouncer Load Balancer

**Pros:** Lightweight, efficient, cost-effective  
**Cons:** Requires separate server management

**PgBouncer Configuration** (`/etc/pgbouncer/pgbouncer.ini`):

```ini
[databases]
traitortrack = host=traitortrack-primary.rds.amazonaws.com port=5432 dbname=traitortrack
traitortrack-read = host=traitortrack-replica-1.rds.amazonaws.com,traitortrack-replica-2.rds.amazonaws.com port=5432 dbname=traitortrack

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 500
default_pool_size = 25
reserve_pool_size = 10
reserve_pool_timeout = 5
```

**Application connection:**

```bash
# Write operations
PRODUCTION_DATABASE_URL=postgresql://user:pass@pgbouncer-host:6432/traitortrack

# Read operations
READ_REPLICA_POOL_URL=postgresql://user:pass@pgbouncer-host:6432/traitortrack-read
```

### Strategy 4: HAProxy TCP Load Balancer

**Pros:** Advanced health checking, session persistence  
**Cons:** More complex setup, requires dedicated server

**HAProxy Configuration** (`/etc/haproxy/haproxy.cfg`):

```cfg
global
    log /dev/log local0
    maxconn 4096

defaults
    mode tcp
    timeout connect 10s
    timeout client 30s
    timeout server 30s

frontend postgres_read
    bind *:5433
    default_backend postgres_replicas

backend postgres_replicas
    balance roundrobin
    option pgsql-check user health_check
    server replica1 traitortrack-replica-1.rds.amazonaws.com:5432 check
    server replica2 traitortrack-replica-2.rds.amazonaws.com:5432 check backup
```

### Recommended Strategy for TraitorTrack

**Current Scale (100 users):** Application-level round robin  
**Target Scale (200-300 users):** AWS RDS Proxy or PgBouncer  
**Enterprise Scale (500+ users):** HAProxy with advanced health checks

---

## Performance Tuning

### Replica-Specific Optimizations

```sql
-- Increase shared buffers for read caching (requires restart)
ALTER SYSTEM SET shared_buffers = '4GB';

-- Optimize for read operations
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET random_page_cost = 1.1;  -- SSD optimization

-- Increase work memory for complex queries
ALTER SYSTEM SET work_mem = '64MB';

-- Parallel query execution
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
ALTER SYSTEM SET max_worker_processes = 8;

-- Reload configuration
SELECT pg_reload_conf();
```

### Query Optimization for Replicas

```sql
-- Add covering indexes for frequently accessed data
CREATE INDEX CONCURRENTLY idx_bag_qr_type_status_created 
ON bag(qr_id, type, status, created_at)
INCLUDE (weight);

-- Partial index for active bags only
CREATE INDEX CONCURRENTLY idx_active_bags 
ON bag(status, created_at)
WHERE status = 'active';

-- Index for audit log queries on replicas
CREATE INDEX CONCURRENTLY idx_audit_log_user_timestamp 
ON audit_log(user_id, timestamp DESC)
INCLUDE (action, entity_type);
```

### Connection Pool Tuning

```python
# Separate pool configurations for different workloads
app.config["SQLALCHEMY_BINDS_ENGINE_OPTIONS"] = {
    "replica_1": {
        "pool_size": 30,  # Higher for read-heavy load
        "max_overflow": 20,
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_timeout": 10,  # Faster timeout for replicas
        "echo_pool": False,
    },
}
```

### Caching Strategy

Leverage replicas for cache warming:

```python
from functools import lru_cache
import time

@lru_cache(maxsize=1000, ttl=60)
def get_cached_bag_from_replica(qr_id):
    """Cache bag lookups from replica for 60 seconds"""
    query = text("SELECT * FROM bag WHERE qr_id = :qr_id")
    result = router.execute_on_replica(query.bindparams(qr_id=qr_id))
    return result.fetchone()
```

### Monitoring Performance Gains

**Before/After Comparison:**

```sql
-- Track query distribution
SELECT
    datname,
    usename,
    application_name,
    COUNT(*) AS query_count,
    AVG(total_time) AS avg_query_time_ms
FROM pg_stat_statements
JOIN pg_database ON pg_stat_statements.dbid = pg_database.oid
WHERE datname = 'traitortrack'
GROUP BY datname, usename, application_name
ORDER BY avg_query_time_ms DESC;
```

---

## Troubleshooting

### Issue: High Replication Lag

**Symptoms:** Lag >30 seconds, stale data on reads

**Diagnosis:**

```sql
-- Check WAL sender statistics on primary
SELECT * FROM pg_stat_replication;

-- Check disk I/O on replica
SELECT * FROM pg_stat_bgwriter;
```

**Solutions:**

1. **Increase replica instance size** (more CPU/memory)
2. **Optimize slow queries** on primary (reduces WAL volume)
3. **Check network bandwidth** between primary and replica
4. **Temporarily stop analytics queries** on primary

### Issue: Replica Connection Failures

**Symptoms:** Application errors, fallback to primary

**Diagnosis:**

```bash
# Check replica connectivity
psql $READ_REPLICA_1_URL -c "SELECT 1"

# Check replica logs
aws rds download-db-log-file-portion \
  --db-instance-identifier traitortrack-replica-1 \
  --log-file-name error/postgresql.log.2025-11-25-10
```

**Solutions:**

1. **Verify security groups** allow application access
2. **Check connection limits** (max_connections on replica)
3. **Restart replica** if hung
4. **Promote replica** if corruption detected

### Issue: Inconsistent Read Results

**Symptoms:** Users see outdated data after writes

**Diagnosis:**

```python
# Check replication lag in application
def check_consistency():
    # Write to primary
    primary_result = db.session.execute(
        text("INSERT INTO test_table (value) VALUES ('test') RETURNING id")
    )
    db.session.commit()
    test_id = primary_result.fetchone()[0]
    
    # Read from replica immediately
    time.sleep(1)  # Wait for replication
    replica_result = router.execute_on_replica(
        text("SELECT value FROM test_table WHERE id = :id"),
        bind_params={'id': test_id}
    )
    
    return replica_result.fetchone() is not None
```

**Solutions:**

1. **Implement session affinity** (see [Application Code Changes](#application-code-changes))
2. **Use primary for critical reads** immediately after writes
3. **Add retry logic** with exponential backoff
4. **Increase replication lag tolerance** in application logic

---

## Summary

Read replicas provide significant performance improvements for TraitorTrack at production scale:

- **2-3x user capacity** without upgrading primary database
- **40-60% faster** dashboard and search queries
- **50% reduction** in primary database CPU usage
- **Improved disaster recovery** capability with automatic failover

**Next Steps:**

1. Create first read replica using AWS RDS Console
2. Implement `db_router.py` for intelligent query routing
3. Update read-heavy routes to use replicas
4. Monitor replica lag and performance metrics
5. Scale to 2-3 replicas as user load increases

**See Also:**

- [PRODUCTION_DEPLOYMENT_CHECKLIST.md](PRODUCTION_DEPLOYMENT_CHECKLIST.md) - Deployment procedures
- [OPERATIONAL_RUNBOOK.md](OPERATIONAL_RUNBOOK.md) - Daily operations guide
- [DATABASE_BACKUP_AUTOMATION.md](DATABASE_BACKUP_AUTOMATION.md) - Backup strategies
- [PERFORMANCE_BENCHMARKING_GUIDE.md](PERFORMANCE_BENCHMARKING_GUIDE.md) - Performance testing

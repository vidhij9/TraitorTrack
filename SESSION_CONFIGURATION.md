# Session Configuration Documentation

## Current Configuration: Filesystem-Based Sessions

TraceTrack currently uses **filesystem-based sessions** stored in `/tmp/flask_session` for optimal performance and stability under high concurrent load.

### Why Filesystem Sessions?

During load testing with 100+ concurrent users, we discovered that Redis-based sessions caused **port exhaustion** due to connection pool limits. Filesystem sessions eliminate this issue while providing excellent performance.

### Configuration Details

```python
SESSION_TYPE='filesystem'
SESSION_FILE_DIR='/tmp/flask_session'
SESSION_PERMANENT=False
SESSION_USE_SIGNER=True
SESSION_FILE_THRESHOLD=500  # Max 500 session files
```

### Limitations of Filesystem Sessions

#### 1. **Not Suitable for Multi-Server Deployments**
   - Sessions are stored locally on each server
   - Load balancers MUST use **sticky sessions** (session affinity)
   - Without sticky sessions, users will be logged out randomly

#### 2. **Session File Cleanup**
   - Old session files accumulate in `/tmp/flask_session`
   - **Recommended**: Set up a cron job to clean old sessions
   ```bash
   # Run daily to remove sessions older than 2 days
   0 2 * * * find /tmp/flask_session -type f -mtime +2 -delete
   ```

#### 3. **Disk Space Usage**
   - Each active session uses ~4KB disk space
   - 10,000 concurrent users = ~40MB disk space
   - Monitor `/tmp` disk usage in production

#### 4. **Performance Characteristics**
   - **Read/Write Speed**: Excellent (local filesystem)
   - **Scalability**: Limited to single-server or sticky-session deployments
   - **Reliability**: Good (survives application restarts)

---

## Migration Guide: Filesystem → Redis Sessions

When scaling to **multiple servers** or **cloud deployment**, migrate to Redis sessions.

### Prerequisites

1. **Redis Server**: 
   - Redis 6.0+ recommended
   - Configure `maxclients` appropriately (e.g., 10000)
   - Set `timeout 300` to prevent idle connection buildup

2. **Redis Connection Pool**:
   - Use `redis-py` with connection pooling
   - Configure pool size: `max_connections=50` per worker

### Step-by-Step Migration

#### 1. Install Dependencies

```bash
pip install redis flask-session[redis]
```

Update `requirements.txt`:
```
redis==4.5.1
flask-session==0.5.0
```

#### 2. Configure Redis Connection

Create `redis_config.py`:
```python
import os
import redis
from redis.connection import ConnectionPool

# Redis connection pool (CRITICAL for preventing port exhaustion)
redis_pool = ConnectionPool(
    host=os.environ.get('REDIS_HOST', 'localhost'),
    port=int(os.environ.get('REDIS_PORT', 6379)),
    password=os.environ.get('REDIS_PASSWORD'),
    db=0,
    max_connections=50,  # Per worker
    socket_keepalive=True,
    socket_connect_timeout=5,
    health_check_interval=30
)

redis_client = redis.Redis(connection_pool=redis_pool)
```

#### 3. Update `app.py` Configuration

Replace filesystem config with Redis:

```python
from redis_config import redis_client

app.config.update(
    SESSION_TYPE='redis',
    SESSION_REDIS=redis_client,
    SESSION_PERMANENT=False,
    SESSION_USE_SIGNER=True,
    SESSION_KEY_PREFIX='tracetrack:session:',
    SESSION_COOKIE_SECURE=is_production,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=3600  # 1 hour
)
```

#### 4. Set Environment Variables

```bash
# For development
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_PASSWORD=your_secure_password

# For production (Replit Secrets or cloud provider)
REDIS_HOST=your-redis-server.amazonaws.com
REDIS_PORT=6379
REDIS_PASSWORD=<use secrets manager>
```

#### 5. Test Redis Connection

```python
# Test Redis connectivity
try:
    redis_client.ping()
    logger.info("Redis connection successful")
except redis.ConnectionError as e:
    logger.error(f"Redis connection failed: {e}")
    raise
```

#### 6. Deploy and Monitor

1. **Deploy to staging** with Redis enabled
2. **Load test** with 100+ concurrent users
3. **Monitor Redis metrics**:
   - Connection count: `INFO clients`
   - Memory usage: `INFO memory`
   - Command stats: `INFO stats`

4. **Adjust pool size** if needed based on load

---

## Production Deployment Recommendations

### Option 1: Single-Server Deployment (Current)
- **Use**: Filesystem sessions ✅
- **Max Users**: 500-1000 concurrent
- **Setup**: Already configured
- **Notes**: Simple, fast, no external dependencies

### Option 2: Multi-Server with Load Balancer
- **Use**: Filesystem sessions with sticky sessions
- **Max Users**: 2000-5000 concurrent (2-4 servers)
- **Setup**: Configure load balancer for session affinity
- **Notes**: Still simple, but requires proper LB configuration

### Option 3: Cloud-Scale Deployment
- **Use**: Redis sessions
- **Max Users**: 10,000+ concurrent
- **Setup**: Follow migration guide above
- **Notes**: Most scalable, requires Redis infrastructure

---

## Monitoring and Troubleshooting

### Filesystem Sessions

**Check session count**:
```bash
ls -1 /tmp/flask_session | wc -l
```

**Check disk usage**:
```bash
du -sh /tmp/flask_session
```

**Clean old sessions manually**:
```bash
find /tmp/flask_session -type f -mtime +1 -delete
```

### Redis Sessions (After Migration)

**Monitor connections**:
```bash
redis-cli INFO clients
```

**Monitor session keys**:
```bash
redis-cli KEYS "tracetrack:session:*" | wc -l
```

**Monitor memory usage**:
```bash
redis-cli INFO memory | grep used_memory_human
```

---

## Summary

| Feature | Filesystem | Redis |
|---------|-----------|-------|
| Single-server | ✅ Excellent | ✅ Good |
| Multi-server | ⚠️ Sticky sessions required | ✅ Native support |
| Performance | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Complexity | ⭐ Very simple | ⭐⭐⭐ Moderate |
| External deps | None | Redis server |
| Max users | 1000 | 10,000+ |

**Current Status**: TraceTrack uses filesystem sessions optimized for 100+ concurrent users on single-server deployments.

**When to Migrate**: Switch to Redis when deploying to multiple servers or exceeding 1000 concurrent users.

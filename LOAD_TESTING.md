# Load Testing Guide - TraitorTrack

## Overview

This guide covers load testing, stress testing, and performance validation for the TraitorTrack warehouse system. The system must handle **100+ concurrent users** and manage **1.8M+ bags** efficiently.

---

## 🎯 Performance Targets

### Response Time Targets
- **API Endpoints (reads)**: < 100ms (P95)
- **API Endpoints (writes)**: < 500ms (P95)
- **Scan Operations**: < 200ms (P95)
- **Search Queries**: < 500ms (P95)
- **Dashboard Load**: < 1000ms (P95)

### Capacity Targets
- **Concurrent Users**: 100+ sustained
- **Requests/second**: 500+ sustained
- **Error Rate**: < 1% under normal load
- **Database Size**: 1.8M+ bags with no performance degradation

---

## 🚀 Quick Start

### Prerequisites

```bash
# Ensure Locust is installed
pip install locust

# Ensure server is running
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

### Run Load Tests

```bash
# Basic load test (100 users, 5 minutes)
make load-test

# Stress test (200 users, 10 minutes)
make stress-test

# Database scale test
make db-scale-test

# API performance test
make api-perf

# Interactive Web UI (recommended for exploration)
make load-test-ui
# Then visit: http://localhost:8089
```

---

## 📊 Test Types

### 1. Load Testing (`make load-test`)

**Purpose**: Validate system handles expected production load

**Configuration**:
- 100 concurrent users
- 10 users/second spawn rate
- 5 minute duration
- Realistic user mix: 60% dispatchers, 30% billers, 10% admins

**What it tests**:
- Normal warehouse operations
- Concurrent bag scanning
- Bill creation and management
- Dashboard statistics
- Search functionality

**Success criteria**:
- Error rate < 1%
- P95 response times within targets
- No crashes or timeouts

**Example output**:
```
Type     Name                            # reqs   # fails  Avg    Min    Max  Median  req/s
---------|-------------------------------|--------|--------|------|------|------|-------|-------
POST     Scan Parent Bag                  1250      12     156    45     982     150    4.2
GET      Dashboard                         800       3      89    32     456      85    2.7
POST     Create Bill                       450       1     243    87    1234     220    1.5
```

### 2. Stress Testing (`make stress-test`)

**Purpose**: Find system breaking points

**Configuration**:
- 200 concurrent users (2x expected load)
- 20 users/second spawn rate
- 10 minute duration
- Aggressive operations with minimal think time

**What it tests**:
- System stability under extreme load
- Race condition handling
- Database connection pooling
- Cache effectiveness
- Error recovery

**Success criteria**:
- System remains responsive
- Graceful degradation (no crashes)
- Error rate < 5% acceptable under stress
- Recovery after load reduction

### 3. Database Scale Testing (`make db-scale-test`)

**Purpose**: Validate database performance at scale (1.8M bags)

**What it tests**:
- Query performance with large datasets
- Index effectiveness
- Pagination efficiency
- JOIN performance
- Aggregation queries

**Tests performed**:
```python
✓ Count All Bags: 45ms
✓ Count Parent Bags (Indexed): 12ms
✓ Pagination: First Page (50 items): 8ms
✓ Pagination: Middle Page (offset 50k): 156ms
✓ Search: Exact QR Match (Indexed): 3ms
✓ Search: QR Pattern (LIKE): 89ms
✓ JOIN: Bags with Scan Counts: 234ms
✓ Dashboard: Aggregate Statistics: 67ms
```

**Success criteria**:
- All indexed queries < 100ms
- Pagination remains fast
- Search performs well with LIKE queries

### 4. API Performance Testing (`make api-perf`)

**Purpose**: Test critical API endpoints

**What it tests**:
- `/api/bags` - List and pagination
- `/api/bags/search` - Search performance
- `/api/bills` - Bill operations
- `/api/statistics` - Dashboard stats

**Success criteria**:
- P95 < 100ms for read endpoints
- Consistent performance under load

---

## 📈 Interpreting Results

### Understanding Locust Metrics

**Request Metrics**:
- **# reqs**: Total requests sent
- **# fails**: Failed requests (errors, timeouts)
- **Avg**: Average response time
- **P50/P95/P99**: Percentile response times
- **req/s**: Requests per second

**What to look for**:
```
✅ GOOD:
  - P95 < target response time
  - Error rate < 1%
  - Stable req/s throughout test

⚠️ WARNING:
  - P95 approaching targets
  - Error rate 1-5%
  - Gradual performance degradation

❌ BAD:
  - P95 significantly exceeds targets
  - Error rate > 5%
  - Crashes or connection timeouts
```

### Example: Good Performance
```
Type     Name                  # reqs   # fails  P95    req/s  errors
---------|---------------------|--------|--------|-------|------|-------
POST     Scan Bag               5000      5      187ms   16.7   0.1%
GET      Dashboard              3200      0       95ms   10.7   0.0%
✅ System performing well
```

### Example: Poor Performance
```
Type     Name                  # reqs   # fails  P95      req/s  errors
---------|---------------------|--------|--------|---------|------|-------
POST     Scan Bag               5000     250    1850ms    16.7   5.0%
GET      Dashboard              3200     180     987ms    10.7   5.6%
❌ Performance degraded - investigate database or caching
```

---

## 🔧 Troubleshooting

### High Response Times

**Symptoms**: P95 > 1000ms

**Possible causes**:
1. **Database queries** - Check slow query log
2. **Missing indexes** - Run EXPLAIN on slow queries
3. **Connection pool exhausted** - Increase pool size
4. **Cache not working** - Check Redis connection

**Solutions**:
```python
# Check database connection pool
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 20,        # Increase if needed
    "max_overflow": 40,     # Increase if needed
    "pool_recycle": 300,
}

# Verify indexes exist
python -c "from models import *; print(Bag.__table__.indexes)"
```

### High Error Rates

**Symptoms**: > 1% errors under normal load

**Possible causes**:
1. **Database timeout** - Queries taking too long
2. **Connection errors** - Too many connections
3. **Memory issues** - Server running out of memory
4. **Application errors** - Bugs in code

**Solutions**:
```bash
# Check server logs
tail -f /tmp/logs/start_application_*.log

# Monitor system resources
htop

# Check database connections
psql -c "SELECT count(*) FROM pg_stat_activity;"
```

### Cache Issues

**Symptoms**: Dashboard slow, statistics outdated

**Solutions**:
```python
# Test cache invalidation
from cache_utils import invalidate_stats_cache
invalidate_stats_cache()

# Check Redis (if using)
redis-cli ping
redis-cli info stats
```

---

## 🎯 Running Custom Tests

### Custom Load Test

Create `tests/load/custom_test.py`:

```python
from locust import HttpUser, task, between

class CustomUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login"""
        self.client.post("/login", data={
            "username": "admin",
            "password": "vidhi2029"
        })
    
    @task
    def my_workflow(self):
        """Custom workflow"""
        self.client.get("/dashboard")
        self.client.post("/scan", data={"qr_id": "SB12345"})
```

Run it:
```bash
locust -f tests/load/custom_test.py --host=http://localhost:5000
```

### Test Specific Scenario

```bash
# Test only dispatchers (heavy scanning)
locust -f tests/load/locustfile.py \
  --host=http://localhost:5000 \
  --headless \
  -u 100 \
  -r 10 \
  --only-summary \
  --class-picker DispatcherUser

# Test only API endpoints
locust -f tests/load/locustfile.py \
  --host=http://localhost:5000 \
  --headless \
  -u 50 \
  -r 10 \
  --tags api-perf
```

---

## 📋 Load Test Checklist

### Before Testing

- [ ] Server is running (`gunicorn` or `make run`)
- [ ] Database has sufficient data (use seed script for realistic data)
- [ ] Redis is running (if using Redis sessions)
- [ ] Monitor tools ready (htop, database GUI)
- [ ] Logs are accessible

### During Testing

- [ ] Monitor server CPU/memory with `htop`
- [ ] Watch database connection count
- [ ] Check error logs in real-time
- [ ] Note any performance degradation
- [ ] Record baseline metrics

### After Testing

- [ ] Review Locust statistics
- [ ] Check for errors in logs
- [ ] Analyze slow queries
- [ ] Document any issues found
- [ ] Compare against performance targets

---

## 🏆 Performance Optimization Tips

### Database Optimization

```sql
-- Check missing indexes
SELECT schemaname, tablename, indexname 
FROM pg_indexes 
WHERE schemaname = 'public';

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM bag WHERE qr_id = 'SB12345';

-- Check table size
SELECT pg_size_pretty(pg_total_relation_size('bag'));
```

### Application Optimization

1. **Enable caching**:
   - Use Redis for session storage
   - Cache dashboard statistics
   - Cache frequently accessed data

2. **Optimize queries**:
   - Use `joinedload` for eager loading
   - Avoid N+1 queries
   - Use pagination for large results

3. **Connection pooling**:
   ```python
   app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
       "pool_size": 20,
       "max_overflow": 40,
       "pool_pre_ping": True,
   }
   ```

4. **Async operations**:
   - Use Gunicorn with gevent workers
   - Process background tasks asynchronously

---

## 📚 Advanced Topics

### Distributed Load Testing

Run Locust in distributed mode for massive load:

```bash
# Master node
locust -f tests/load/locustfile.py --master --expect-workers=4

# Worker nodes (run on multiple machines)
locust -f tests/load/locustfile.py --worker --master-host=<master-ip>
```

### Continuous Performance Monitoring

Integrate load tests in CI/CD:

```yaml
# .github/workflows/load-test.yml
- name: Load Test
  run: |
    make load-test
    # Fail if P95 > 500ms
```

### Custom Metrics

Add custom metrics to Locust:

```python
from locust import events

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("Load test starting...")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats
    if stats.total.fail_ratio > 0.01:
        environment.process_exit_code = 1  # Fail CI/CD
```

---

## 🎓 Best Practices

1. **Start small**: Begin with 10 users, then scale up
2. **Ramp slowly**: Use gradual spawn rate to avoid startup spikes
3. **Monitor everything**: CPU, memory, database, network
4. **Test realistic scenarios**: Mimic actual warehouse workflows
5. **Test at different scales**: 10, 50, 100, 200 users
6. **Document baselines**: Record "good" performance for comparison
7. **Test regularly**: Run load tests before major releases
8. **Fix incrementally**: Address one bottleneck at a time

---

## 📞 Support

### Common Questions

**Q: How much load should I test with?**  
A: Start with 100 users (expected production load), then test up to 200 users (2x capacity) for safety margin.

**Q: How long should tests run?**  
A: 5-10 minutes for load tests, longer for stress tests. Soak tests can run hours/days.

**Q: What if I can't meet performance targets?**  
A: Optimize one bottleneck at a time: database queries → caching → connection pooling → code optimization.

**Q: Should I test against production?**  
A: ⚠️ **NEVER** test against production! Always use development or staging environment.

---

## ✅ Summary

**Quick Commands**:
```bash
make load-test        # 100 users, 5 min
make stress-test      # 200 users, 10 min
make db-scale-test    # Database performance
make load-test-ui     # Interactive testing
```

**Success Metrics**:
- ✅ 100+ concurrent users sustained
- ✅ P95 response times within targets
- ✅ Error rate < 1%
- ✅ No crashes under load
- ✅ Graceful degradation under stress

**Before Publishing**:
```bash
# Run complete test suite
make test

# Run load test
make load-test

# Verify results meet targets
# ✓ All tests passed
# ✓ Load test successful
# → Ready for production!
```

---

*Last updated: November 21, 2025*

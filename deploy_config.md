# TraceTrack Deployment Configuration

## Optimized Configuration for 20+ Concurrent Users

### Current Test Results

#### Single Worker Performance (Default)
- **Success Rate:** 27.5% with 25 users
- **Average Response Time:** 6,585 ms
- **Requests/Second:** 3.4
- **Verdict:** ❌ Cannot handle 20+ concurrent users

#### Multi-Worker Configuration (Recommended)
- **Workers:** 4
- **Threads per Worker:** 2
- **Total Handlers:** 8 concurrent requests
- **Expected Performance:** 
  - Can handle 20-25 concurrent users
  - Response times < 1 second under normal load
  - 100% success rate for standard operations

### Deployment Command

For production deployment with 20+ concurrent user support, use:

```bash
gunicorn --bind 0.0.0.0:5000 \
    --workers 4 \
    --threads 2 \
    --worker-class gthread \
    --timeout 60 \
    --keep-alive 5 \
    --max-requests 2000 \
    --max-requests-jitter 100 \
    --preload \
    main:app
```

### Configuration Explanation

- **`--workers 4`**: Creates 4 worker processes for parallel request handling
- **`--threads 2`**: Each worker handles 2 threads (total 8 concurrent handlers)
- **`--worker-class gthread`**: Uses threaded workers for better concurrency
- **`--timeout 60`**: Allows longer operations like bulk scanning
- **`--keep-alive 5`**: Maintains connections for better performance
- **`--max-requests 2000`**: Restarts workers after 2000 requests to prevent memory leaks
- **`--max-requests-jitter 100`**: Adds randomness to restart timing
- **`--preload`**: Loads application before forking for faster startup

### Resource Requirements

- **Memory:** ~200-300 MB per worker (1.2 GB total)
- **CPU:** Benefits from 2-4 CPU cores
- **Database Connections:** Pool size configured for 50+ connections

### Scaling Guidelines

| Concurrent Users | Workers | Threads | Total Handlers |
|-----------------|---------|---------|----------------|
| 5-10            | 2       | 2       | 4              |
| 10-20           | 3       | 2       | 6              |
| 20-30           | 4       | 2       | 8              |
| 30-50           | 4       | 3       | 12             |

### Monitoring

Monitor these metrics in production:
- Response times (target < 500ms for scans)
- Success rate (target > 99%)
- Worker memory usage
- Database connection pool usage

### Deployment Steps

1. Update the workflow command to use the optimized configuration
2. Deploy the application
3. Monitor initial performance
4. Adjust workers/threads based on actual load patterns

### Important Notes

- Single worker configuration is insufficient for production use
- The application requires multi-worker setup for 20+ concurrent users
- Database and caching layers are already optimized for high concurrency
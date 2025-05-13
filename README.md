# TraceTrack

TraceTrack is a QR-based supply chain traceability web application focused on agricultural product tracking. The system enables tracking of "parent bags" and their associated "child bags" through QR code scanning at various locations.

## Performance Optimizations for High Concurrency

This application has been optimized to handle 100+ concurrent users with excellent performance. Key optimizations include:

### Database Optimizations
- Enhanced connection pooling with optimal settings (`pool_size`, `max_overflow`, etc.)
- Connection recycling to prevent stale connections
- Pool pre-ping for connection validation before use

### Server Optimizations
- Gevent-based WSGI server for improved concurrency
- Worker processes calculated based on CPU cores
- Maximum request limits to prevent worker fatigue
- Graceful timeout handling

### Caching System
- API response caching system
- Template fragment caching
- Data access caching for expensive database operations
- Intelligent cache invalidation on data modifications

### Frontend Optimizations
- Resource hints (dns-prefetch, preconnect) for faster resource loading
- Deferred JavaScript loading
- Integrity attributes for security and cache optimization
- Offline capabilities with cache manifests

### Monitoring and Logging
- Request timing middleware for performance tracking
- Structured logging with rotating file handlers
- Server timing headers for client-side performance monitoring

## Running the Application

### Development Mode
```bash
python main.py
```

### Production Mode (High Concurrency)
```bash
./run_server.sh
```

## User Roles

- **Employee**: Can scan bags and track movements
- **Admin**: Additional privileges to manage the system, view reports, and link bags to bills

## QR Code Format

- Parent bags: Format `P123-10` (where 10 is the child count)
- Child bags: Format `C123`

## Project Structure

- `app.py`: Application configuration
- `main.py`: Application entry point
- `models.py`: Database models
- `routes.py`: Route handlers
- `api.py`: API endpoints
- `cache_utils.py`: Caching system
- `template_utils.py`: Template optimization utilities
- `logging_config.py`: Advanced logging configuration
- `gunicorn_config.py`: Production server configuration
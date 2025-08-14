# TraceTrack API v2 - Optimized Performance Documentation

## Overview
The TraceTrack API v2 is designed for maximum performance with minimal resource usage. All endpoints are optimized for speed and include caching, batch processing, and efficient database queries.

## Performance Features
- **Response Caching**: Frequently accessed data cached for 10-60 seconds
- **Batch Operations**: Process multiple items in single transactions
- **Optimized Queries**: Direct SQL with indexed columns
- **Rate Limiting**: Prevents abuse while allowing high throughput
- **Connection Pooling**: Efficient database connection management

## Authentication
All API endpoints (except login and health) require authentication via session cookies.

## Endpoints

### Authentication

#### POST /api/v2/login
**Rate Limit**: 10 per minute
```json
Request:
{
  "username": "string",
  "password": "string"
}

Response:
{
  "success": true,
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin"
  }
}
```

### User Management

#### GET /api/v2/users
**Rate Limit**: 100 per minute
**Cache**: 30 seconds
**Auth**: Admin only

Returns list of all users with statistics.
```json
Response:
{
  "success": true,
  "users": [
    {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "role": "admin",
      "dispatch_area": null,
      "created_at": "2024-01-01T00:00:00",
      "scan_count": 150,
      "last_scan": "2024-01-20T10:30:00"
    }
  ]
}
```

### Bag Operations

#### GET /api/v2/bags/search
**Rate Limit**: 100 per minute
**Auth**: Required

Search for bags by QR code or name.
```
Query Parameters:
- q: Search query (required)
- limit: Max results (default: 50, max: 100)

Response:
{
  "success": true,
  "bags": [...],
  "count": 10
}
```

### Scanning

#### POST /api/v2/scan
**Rate Limit**: 500 per minute
**Auth**: Required

Scan a single QR code.
```json
Request:
{
  "qr_id": "P000001",
  "type": "parent"  // or "child"
}

Response:
{
  "success": true,
  "bag": {
    "id": 1,
    "type": "parent",
    "name": "Premium Rice Bag",
    "dispatch_area": "North Zone"
  }
}
```

#### POST /api/v2/batch/scan
**Rate Limit**: 50 per minute
**Auth**: Required

Batch scan up to 100 QR codes at once.
```json
Request:
{
  "qr_codes": ["P000001", "P000002", "C000001"]
}

Response:
{
  "success": true,
  "results": [
    {
      "qr_code": "P000001",
      "success": true,
      "bag": {...}
    },
    {
      "qr_code": "INVALID",
      "success": false,
      "message": "Not found"
    }
  ]
}
```

### Statistics

#### GET /api/v2/stats
**Rate Limit**: 100 per minute
**Cache**: 10 seconds
**Auth**: Required

Get system-wide statistics.
```json
Response:
{
  "success": true,
  "stats": {
    "total_bags": 10000,
    "parent_bags": 5000,
    "child_bags": 5000,
    "total_scans": 25000,
    "scans_today": 150,
    "total_users": 100,
    "total_bills": 500
  }
}
```

### System

#### GET /api/v2/health
**Rate Limit**: 1000 per minute
**Auth**: Not required

Health check endpoint for monitoring.
```json
Response:
{
  "status": "healthy",
  "timestamp": 1705843200.123,
  "cache_size": 42
}
```

#### POST /api/v2/cache/clear
**Rate Limit**: 10 per minute
**Auth**: Admin only

Clear the API cache.
```json
Response:
{
  "success": true,
  "message": "Cache cleared"
}
```

## Performance Tips

1. **Use Batch Operations**: When scanning multiple QR codes, use `/api/v2/batch/scan` instead of multiple individual scans.

2. **Implement Client-Side Caching**: Cache user lists and statistics on the client for the TTL duration.

3. **Respect Rate Limits**: Implement exponential backoff when hitting rate limits.

4. **Use Efficient Queries**: When searching, use exact QR codes when possible instead of partial matches.

5. **Monitor Health Endpoint**: Use `/api/v2/health` for uptime monitoring without authentication overhead.

## Error Responses

All endpoints return consistent error responses:
```json
{
  "success": false,
  "message": "Error description",
  "error": "ERROR_CODE"  // Optional
}
```

HTTP Status Codes:
- 200: Success
- 400: Bad Request
- 401: Authentication Required
- 403: Forbidden (insufficient permissions)
- 404: Not Found
- 429: Too Many Requests (rate limited)
- 500: Internal Server Error

## Migration from v1 to v2

Key differences:
1. All endpoints now under `/api/v2/` prefix
2. Batch operations available for scanning
3. Response caching implemented
4. Stricter rate limiting
5. Optimized response formats (less nested data)
# Request ID Tracking - Implementation Summary

## Overview
Request tracking middleware provides distributed tracing capabilities through unique request IDs, timing information, and comprehensive logging.

## Features Implemented ✅
- **Unique Request IDs**: Every request gets a UUID4 identifier
- **Client ID Passthrough**: Supports client-provided request IDs via `X-Request-ID` header
- **Request Start/End Logging**: All requests logged with method, path, duration
- **Exception Logging**: All errors logged via `got_request_exception` signal
- **Timing Tracking**: Request duration calculated and logged
- **Slow Request Detection**: Warnings for requests >1 second
- **Response Headers**: X-Request-ID and X-Response-Time on successful responses

## Logging Examples

### Successful Request
```
2025-10-25 15:29:15,275 - request_tracking - INFO - [13076ab3-e18f-4489-9aeb-ce3b39891c54] Request started: GET /
2025-10-25 15:29:15,276 - request_tracking - INFO - [13076ab3-e18f-4489-9aeb-ce3b39891c54] Request completed: GET / - Status: 200 - Duration: 0ms
```

### HTTP Error (404)
```
2025-10-25 15:32:16,147 - request_tracking - INFO - [0c01ac9d-37d5-49f1-a7aa-df9a0734dffa] Request started: HEAD /nonexistent-page
2025-10-25 15:32:16,169 - request_tracking - WARNING - [0c01ac9d-37d5-49f1-a7aa-df9a0734dffa] HTTP error: HEAD /nonexistent-page - Status: 404 - Duration: 22ms
```

### Unexpected Exception
```
2025-10-25 15:XX:XX,XXX - request_tracking - ERROR - [XXXXXX] Unhandled exception: ValueError: Invalid data - Duration: XXXms
(stack trace follows)
```

## Usage

### Accessing Request ID in Code
```python
from request_tracking import get_request_id

request_id = get_request_id()
logger.info(f"Processing order {order_id}", extra={'request_id': request_id})
```

### Decorator for Functions
```python
from request_tracking import with_request_id

@with_request_id
def process_payment(amount):
    # Automatically includes request ID in logs
    logger.info(f"Processing payment: ${amount}")
```

### Getting Trace Context for External Calls
```python
from request_tracking import get_trace_context

context = get_trace_context()
headers = context['headers']  # {'X-Request-ID': '...', 'X-Correlation-ID': '...'}

# Pass to external API
requests.post(external_api_url, headers=headers, ...)
```

### Logging with Context
```python
from request_tracking import log_with_context

log_with_context("Payment processed successfully", level='info', amount=100)
# Automatically includes request ID
```

## Complete Features ✅

### All Responses Include Tracking Headers
- ✅ Successful requests (200, 201, etc.): X-Request-ID, X-Response-Time
- ✅ Client errors (404, 403, etc.): X-Request-ID, X-Response-Time  
- ✅ Server errors (500, etc.): X-Request-ID, X-Response-Time
- ✅ Preserves existing error templates (no regression)

**Example Error Response:**
```bash
$ curl -I http://localhost:5000/nonexistent-page
HTTP/1.1 404 NOT FOUND
X-Request-ID: 8e08826e-79ae-471e-a41f-99d3cab8a73f
X-Response-Time: 22ms
```

## Testing

### Check Request ID Headers
```bash
curl -I http://localhost:5000/
# Look for: X-Request-ID: <uuid>
# Look for: X-Response-Time: <duration>ms
```

### Provide Your Own Request ID
```bash
curl -H "X-Request-ID: my-custom-id-12345" http://localhost:5000/
# The response and logs will use your provided ID
```

### View Logs
```bash
grep "request_tracking" /tmp/logs/Start_application_*.log
```

## Architecture

### Components
1. **before_request**: Generate/extract request ID, start timer
2. **after_request**: Log completion, add headers (successful requests)
3. **teardown_request**: Cleanup, log if not already logged
4. **got_request_exception signal**: Log all exceptions before error handlers

### Request Flow
```
1. Request arrives
2. before_request: Generate ID, start timer, log start
3. Application processes request
   - If successful: after_request logs completion, adds headers
   - If exception: got_request_exception logs error
4. teardown_request: Final cleanup
5. Response returned
```

## Performance Impact
- **Minimal**: UUID generation and timing adds <1ms per request
- **Memory**: Negligible (stores only ID and timestamp in request context)
- **Logs**: Adds 2-3 log lines per request (start, end, optional error)

## Production Deployment

### Recommended Log Aggregation
Use log aggregation tools to make full use of request IDs:
- **Datadog**: Group logs by request_id field
- **Splunk**: Search by request_id
- **ELK Stack**: Filter on request_id field
- **CloudWatch**: Create metric filters on request_id

### Example Log Query (Datadog)
```
request_id:<specific-id>
```
This will show all log entries for a specific request across all services.

## Troubleshooting

### Request ID Not Appearing in Logs
- Check that request_tracking middleware is initialized
- Verify log format includes request_id field
- Use `log_with_context()` helper function

### Slow Request Warnings
If you see many slow request warnings:
- Review the specific endpoints flagged
- Check database query performance
- Consider caching frequently accessed data
- Review connection pool settings

### Missing Request Context
If `get_request_id()` returns None:
- Ensure you're calling it within a request context
- Check that before_request handler ran successfully
- Verify middleware initialization order

## Security Considerations
- Request IDs are logged but not exposed to end users (except in headers)
- No sensitive data should be logged with request IDs
- Request IDs can help with security incident investigation

## Related Files
- `request_tracking.py` - Main implementation
- `app.py` - Integration point
- `error_handlers.py` - Custom error handling (preserved by this implementation)

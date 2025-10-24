# TraceTrack - Bag Tracking System

## Overview
TraceTrack is a high-performance bag tracking system for warehouse and logistics operations, designed to manage parent-child bag relationships, scanning, and bill generation. It aims to support 100+ concurrent users and 1.5M+ bags with millisecond-level response times. The system provides a web-based interface for dispatchers, billers, and administrators, offering real-time tracking capabilities. Its purpose is to deliver a robust, scalable, and efficient solution for demanding logistics environments, streamlining operations and improving accuracy.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### UI/UX Decisions
The application uses Flask for server-side rendered templates, enhanced with Bootstrap. The interface is optimized for a Coconut wireless 2D barcode scanner, capturing keyboard input, and features AJAX-powered dashboards for real-time updates. All scanner pages use autofocus inputs for instant readiness and keyboard wedge mode, removing camera dependencies for faster page loads. A new toast notification system provides user feedback.

### Technical Implementations
The backend is a modular Flask application using blueprint-based routing and SQLAlchemy ORM with optimized query patterns. It includes session-based authentication with role-based access control (administrators, billers, dispatchers). A multi-layer caching strategy with Redis and an in-memory fallback uses intelligent TTL and pattern-based invalidation. Performance is optimized with Gunicorn and gevent for asynchronous workers, advanced database connection pooling (PgBouncer-like), and filesystem-based session storage. Asynchronous operations are handled via `asyncpg` for non-blocking database queries.

### Feature Specifications
- **Bag Management**: Supports flexible parent-child bag relationships and linking parent bags to bills.
- **Scanner Integration**: Uses Coconut wireless 2D barcode scanners (USB HID keyboard device) for instant, accurate input and auto-submission. Bill parent scanning includes validation to ensure bags exist before linking to bills.
- **Bill Generation**: Dynamically calculates weight based on child bag count.
- **Excel Upload**: Handles 80,000+ bags efficiently with flexible formats, duplicate detection, and batch processing.
- **API Endpoints**: Optimized for low latency, including a `/api/bag/<qr_id>` endpoint for individual bag details.

### System Design Choices
- **Database**: PostgreSQL (version 12+) with connection pooling, composite/partial indexes, and audit logs.
- **Caching**: Redis as the primary cache, aiming for sub-millisecond cache hits.
- **Concurrency**: Gunicorn with gevent workers and optimized database connection pooling for high concurrency.
- **Security**: CSRF protection, input validation, secure session management, API rate limiting, and SQL injection prevention.
- **Scalability**: Designed to support 100+ concurrent users and 1.5M+ bags with millisecond response times.

## External Dependencies

### Database Services
- **PostgreSQL**: Primary relational database.
- **AWS RDS**: Managed PostgreSQL service for production.

### Caching Services
- **Redis**: In-memory data store for caching and session management.

### Python Libraries
- **Flask**: Web framework.
- **Flask-Session**: Server-side session management.
- **SQLAlchemy**: ORM for database interaction.
- **asyncpg**: Asynchronous PostgreSQL adapter.
- **bcrypt**: For password hashing.
- **psycopg2-binary**: PostgreSQL database adapter.
- **redis**: Python client for Redis.
- **hiredis**: High-performance Redis parser.
- **gunicorn**: WSGI HTTP server.
- **gevent**: Asynchronous I/O framework.
- **Flask-WTF**: Integration with WTForms for form handling and CSRF protection.
- **Flask-Login**: User session management.
- **Flask-Limiter**: Rate limiting for API endpoints.
- **Werkzeug**: WSGI utility library.

### Monitoring and Analytics
- **psutil**: System utility for process and system monitoring.

## Deployment Configuration

### Package Management
The project uses pip for dependency management:
- **`requirements.txt`**: Contains all Python dependencies
- **Replit Auto-Install**: Replit automatically installs packages from `requirements.txt` during deployment
- **No Manual Installation**: Never manually run `pip install` - Replit handles this automatically

### Production Deployment
The application is configured for Replit Autoscale Deployment with production-grade settings:

**Deployment Script:** `deploy.sh`
```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 --worker-class gevent --worker-connections 1000 --timeout 120 --preload main:app
```

**Configuration:**
- **Workers**: 4 processes for concurrent request handling
- **Worker Class**: gevent for asynchronous I/O operations
- **Worker Connections**: 1000 connections per worker (4000 total)
- **Timeout**: 120 seconds for long-running requests
- **Port**: 5000 (Replit maps to external port 80)
- **Preload**: App preloaded for faster startup

### Deployment Requirements

**Required Environment Variables:**
- `DATABASE_URL` - PostgreSQL connection string
- `SESSION_SECRET` - Secret key for session management
- `ADMIN_PASSWORD` - Admin user password

**Optional Environment Variables:**
- `CREATE_TEST_USERS=true` - Enable test user creation
- `BILLER_PASSWORD` - Password for test biller user (if CREATE_TEST_USERS enabled)
- `DISPATCHER_PASSWORD` - Password for test dispatcher user (if CREATE_TEST_USERS enabled)

### .replit Configuration

The `.replit` file is correctly configured for deployment:

```toml
[deployment]
deploymentTarget = "autoscale"
run = ["sh", "-c", "./deploy.sh"]
```

**Important Notes:**
- **No build command**: Replit automatically installs packages from `requirements.txt`
- **Do NOT add** `build = [""]` or any build commands - this blocks automatic package installation
- The deployment section should only have `deploymentTarget` and `run` fields

### Post-Deployment Verification

After publishing, verify the deployment:

1. **Health Check:** Visit `/api/health` - should return `{"status": "healthy"}`
2. **Login Page:** Accessible at `/login`
3. **Dashboard:** Login and verify statistics load correctly
4. **Performance:** Test bag scanning and bill management workflows
5. **Database:** Verify PostgreSQL connection works
6. **Sessions:** Test login persistence
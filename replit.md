# TraitorTrack - Bag Tracking System

## Overview
TraitorTrack is a high-performance, web-based bag tracking system for warehouse and logistics. It manages parent-child bag relationships, streamlines scanning, and automates bill generation. The system supports over 100 concurrent users and up to 1.8 million bags, enhancing operational efficiency and providing real-time tracking for dispatchers, billers, and administrators.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Application Structure
The project uses a standard Flask application structure with modules for models, routes, API, and forms.

### Technical Implementation

**Backend Stack:**
-   **Flask 3.1+**: Python web framework.
-   **SQLAlchemy 2.0+**: ORM for database interactions.
-   **PostgreSQL**: Primary relational database.
-   **Gunicorn + gevent**: Asynchronous WSGI server for production.
-   **Flask-Login**: User authentication.
-   **Flask-WTF**: Form validation and CSRF protection.
-   **Flask-Limiter**: In-memory rate limiting.
-   **ujson**: High-performance JSON parsing.

**UI/UX Decisions:**
-   Clean, production-ready interfaces for various user roles.
-   AJAX-powered dashboard for real-time statistics.
-   Full-screen warehouse operation interfaces with large fonts and controls.
-   Visual and audio feedback for scanning operations.
-   Optimized for mobile scanners with simplified UI, audio/vibration feedback, and aggressive auto-focus.
-   Agriculture industry-themed color scheme (forest green, earth-tone beige, golden accents).
-   Enhanced readability with increased button sizes and clear text.
-   Mobile-first optimization for core warehouse pages, including minimal scrolling, compressed spacing, reduced icon sizes, and collapsed secondary content.
-   Fixed mobile bottom navigation bar with four primary actions.

**System Design Choices:**
-   **Live Data Architecture**: All caching removed; queries fetch fresh data directly from PostgreSQL using optimized indexes.
-   **Production-Scale Optimizations**: Includes optimized connection pooling, API pagination, comprehensive database indexing, high-performance query optimizer using direct SQL, optimized request logging, and streamlined authentication.
-   **Ultra-Optimized Query Performance**: Critical endpoints leverage PostgreSQL CTEs, bulk fetching, and direct SQL to prevent N+1 query issues. Dashboard statistics are real-time via aggregate queries.
-   **Mobile-First UI Enhancements**: Responsive card layout for mobile bag management; comprehensive pagination controls.
-   **Session Management**: Flask's native stateless signed cookie sessions for Autoscale-ready deployments.
-   **Two-Factor Authentication (2FA)**: TOTP-based 2FA for admin users with QR code provisioning and rate limiting.
-   **Security Features**: Scrypt for password hashing, CSRF protection, robust session validation, security headers, comprehensive rate limiting, auto-detection of production environment for HTTPS-only cookies, QR code validation, and strong password policy.
-   **Login Rate Limiting**: Dynamic rate limiting on login attempts.
-   **Comprehensive Audit Logging**: Tracks critical security events with GDPR-compliant PII anonymization.
-   **System Health Monitoring**: Real-time metrics endpoint and admin dashboard.
-   **Deployment**: Configured for Autoscale and cloud environments using Gunicorn, with environment variable-driven configuration.
-   **Production Environment Detection**: Automatically detects production environment via `REPLIT_DEPLOYMENT` or `REPLIT_ENVIRONMENT`, enabling HTTPS-only cookies, HSTS headers, strict rate limiting, and CSP.
-   **Automatic Database Migrations**: Uses Flask-Migrate for automated migrations on application startup, including schema verification and backfill for critical Bill columns.
-   **Offline Support**: `localStorage`-based offline queue with auto-retry and optimistic UI updates.
-   **Undo Functionality**: Backend endpoint and UI for undoing the most recent scan within a one-hour window.
-   **Concurrency Control**: Atomic locking to prevent race conditions.
-   **Parent Bag Capacity Tracking System**: Comprehensive capacity tracking for bills with progressive linking, auto-completion, and type-specific weight calculation.

### Feature Specifications

**Production-Ready Features:**
-   **Bag Management**: Supports parent-child bag relationships and flexible linking, with two parent bag QR code formats.
-   **Scanner Integration**: Designed for HID keyboard scanners with robust error handling, duplicate prevention, and rapid scan throttling.
-   **Bill Generation**: Dynamic weight calculation based on child bag counts, with flexible completion logic.
-   **API Endpoints**: Comprehensive REST API with mobile-first optimizations, V2 optimized endpoints (sub-50ms), Gzip compression, field filtering, and smart pagination.
-   **Real-time Dashboard**: Displays statistics via AJAX with live database queries.
-   **System Health Dashboard**: Admin-only interface for system metrics, including database schema health.
-   **Comprehensive Audit Logging**: Enterprise-grade audit trail with state snapshots and PII anonymization.
-   **Automatic Session Security**: Secure session management with dual timeouts and secure cookie handling.
-   **Brute Force Protection**: Comprehensive rate limiting on authentication endpoints and account lockout.
-   **Search & Filtering**: Fast search capabilities across bags, bills, and users with pagination.
-   **Dedicated Bag Search (/search)**: Mobile-friendly bag lookup with full relationship display and recent scan history.
-   **Data Import/Export**: Optimized CSV/Excel export and bulk import with validation.
-   **Batch Import**: Excel-based batch import for child→parent and parent→bill relationships, featuring QR code label extraction, duplicate handling, and batch-level error recovery. Supports multi-file processing with comprehensive error reporting.
-   **Global Error Handlers**: User-friendly error pages for HTTP errors (400, 403, 404, 405, 429, 500, 502, 503) with appropriate status codes and navigation.
-   **Role-Based UI Visibility**: Features are hidden at the UI level based on user roles (Admin, Biller, Dispatcher) with backend access controls as a safety net.

### Database Models
-   **User**: Manages users with roles and authentication.
-   **Bag**: Represents individual bags with QR IDs, type, and relationships.
-   **Scan**: Records bag scanning events.
-   **AuditLog**: Comprehensive audit trail.
-   **PromotionRequest**: Manages admin promotion requests.
-   **Notification**: In-app user notifications.
-   **Bill**: Manages bill generation, including `linked_parent_count`, `parent_bag_count`, `total_weight_kg`, `expected_weight_kg`, `total_child_bags`.
-   **Link**: Defines parent-child bag relationships with a UNIQUE constraint on `child_bag_id`.
-   **BillBag**: Association table linking bills to parent bags.

## External Dependencies
-   **PostgreSQL**: Primary relational database.
-   **Gunicorn**: WSGI HTTP Server.
-   **psutil**: System and process monitoring.
-   **Flask-Login**: User session and authentication management.
-   **Flask-WTF**: Web forms and CSRF protection.
-   **Flask-Limiter**: In-memory rate limiting (per-worker).
-   **werkzeug**: Secure password hashing.
-   **pyotp**: TOTP generation and verification.
-   **qrcode**: QR code generation for 2FA setup.
-   **SendGrid**: Email service for password reset and notifications.

## Production Deployment

### Autoscale-Ready Architecture

The application is optimized for Replit Autoscale deployments:
- **Fast startup**: Server opens port 5000 within seconds (no blocking migrations)
- **Pre-deployment migrations**: `run_migrations.py` runs BEFORE server starts via `deploy.sh`
- **Stateless sessions**: Signed cookie sessions work across any number of workers

### Database Migration for Production

**Latest Migration**: `h4i5j6k7l8m9` - Drops unused legacy columns from `scan` and `bag` tables.

**How migrations work:**
1. `deploy.sh` runs `python run_migrations.py` BEFORE starting Gunicorn
2. Migrations complete, then HTTP server starts immediately
3. No blocking during server startup = fast port 5000 availability

**To run migrations manually:**
```bash
python run_migrations.py
# Or the traditional Flask way:
flask db upgrade
```

**Migration Details (h4i5j6k7l8m9)**:
This migration safely drops unused columns (preserves all row data):

| Table | Dropped Columns | Reason |
|-------|-----------------|--------|
| `scan` | bag_id, scan_type, scan_location, device_info, scan_duration_ms, dispatch_area, location, duration_seconds | Redundant/unused - system uses parent_bag_id/child_bag_id instead |
| `bag` | created_by, current_location, qr_code, bag_type | Duplicates of existing columns (user_id, qr_id, type) |

**Schema After Migration**:
- `scan`: 5 columns (id, timestamp, parent_bag_id, child_bag_id, user_id)
- `bag`: 12 columns (id, qr_id, type, name, child_count, parent_id, user_id, dispatch_area, status, weight_kg, created_at, updated_at)

### Recent Changes (December 2025)
- **Fixed bill scanning workflow**: Improved barcode scanner auto-submission, fixed "Save & Continue Later" to actually persist status to database
- **Schema alignment**: Dropped 12 unused legacy columns to sync development and production databases
- **Bill scanning stability improvements (Dec 2)**:
  - Fixed reopen_bill to use valid 'processing' status instead of invalid 'active'
  - Unified capacity enforcement across all scan routes
  - Added Bill.validate_and_fix_capacity() for data integrity auto-correction
  - Front-end network resilience: fetchWithCSRF with exponential backoff retry (3 attempts)
  - Session timeout detection: 401 responses trigger login modal
  - Client-side scan deduplication: 3-second cooldown after successful scans
  - Server-side scan deduplication: Thread-safe, bill+bag keyed, 3-second cooldown (prevents race conditions across devices)
- **Capacity sync fix (Dec 5)**: Server now returns `safe_parent_bag_count` in all API responses to ensure consistent capacity synchronization when bill capacity is edited
- **Deployment optimization (Dec 5)**:
  - Added early health endpoints (/health, /status, /ready) that respond before heavy initialization
  - Lazy loading for pool monitoring, slow query logging, and admin user check
  - Migration timeout (15s default) to prevent blocking port 5000 opening
  - Graceful timeout added to Gunicorn configuration
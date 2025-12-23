# TraitorTrack - Bag Tracking System

## Overview
TraitorTrack is a high-performance, web-based bag tracking system designed for warehouse and logistics operations. Its primary purpose is to manage parent-child bag relationships, streamline scanning processes, and automate bill generation. The system is built to support over 100 concurrent users and handle up to 1.8 million bags, significantly enhancing operational efficiency and providing real-time tracking capabilities for dispatchers, billers, and administrators.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Application Structure
The project utilizes a standard Flask application architecture, organizing code into modules for models, routes, API, and forms.

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
-   Clean, production-ready interfaces tailored for various user roles.
-   AJAX-powered dashboard for real-time statistics.
-   Full-screen warehouse operation interfaces featuring large fonts and controls.
-   Visual and audio feedback for scanning operations.
-   Mobile-first optimization for core warehouse pages, including simplified UI, audio/vibration feedback, aggressive auto-focus for mobile scanners, minimal scrolling, compressed spacing, reduced icon sizes, and collapsed secondary content.
-   A fixed mobile bottom navigation bar with four primary actions.
-   Agriculture industry-themed color scheme (forest green, earth-tone beige, golden accents) with increased button sizes and clear text for enhanced readability.

**System Design Choices:**
-   **Live Data Architecture**: All data is fetched directly from PostgreSQL using optimized indexes, with no caching, ensuring real-time accuracy.
-   **Production-Scale Optimizations**: Includes optimized connection pooling, API pagination, comprehensive database indexing, high-performance query optimization using direct SQL, optimized request logging, and streamlined authentication.
-   **Ultra-Optimized Query Performance**: Critical endpoints use PostgreSQL CTEs, bulk fetching, and direct SQL to eliminate N+1 query issues. Dashboard statistics are real-time via aggregate queries.
-   **Session Management**: Uses Flask's native stateless signed cookie sessions for Autoscale-ready deployments.
-   **Security Features**: Implements Scrypt for password hashing, CSRF protection, robust session validation, security headers, comprehensive rate limiting, auto-detection of production environment for HTTPS-only cookies, QR code validation, and a strong password policy.
-   **Two-Factor Authentication (2FA)**: TOTP-based 2FA for admin users with QR code provisioning.
-   **Comprehensive Audit Logging**: Tracks critical security events with GDPR-compliant PII anonymization.
-   **System Health Monitoring**: Real-time metrics endpoint and admin dashboard.
-   **Deployment**: Configured for Autoscale and cloud environments using Gunicorn, with environment variable-driven configuration and automatic production environment detection.
-   **Automatic Database Migrations**: Uses Flask-Migrate for automated migrations on application startup, including schema verification and backfill.
-   **Offline Support**: `localStorage`-based offline queue with auto-retry and optimistic UI updates.
-   **Undo Functionality**: Backend endpoint and UI to undo the most recent scan within a one-hour window.
-   **Concurrency Control**: Atomic locking prevents race conditions.
-   **Parent Bag Capacity Tracking System**: Comprehensive capacity tracking for bills with progressive linking, auto-completion, and type-specific weight calculation.

### Feature Specifications

**Production-Ready Features:**
-   **Bag Management**: Supports parent-child bag relationships and flexible linking, accommodating two parent bag QR code formats.
-   **Scanner Integration**: Designed for HID keyboard scanners with robust error handling, duplicate prevention, and rapid scan throttling.
-   **Bill Generation**: Dynamic weight calculation based on child bag counts, with flexible completion logic.
-   **API Endpoints**: Comprehensive REST API with mobile-first optimizations, V2 optimized endpoints (sub-50ms), Gzip compression, field filtering, and smart pagination.
-   **Real-time Dashboard**: Displays statistics via AJAX with live database queries.
-   **System Health Dashboard**: Admin-only interface for system metrics, including database schema health.
-   **Automatic Session Security**: Secure session management with dual timeouts and secure cookie handling.
-   **Brute Force Protection**: Comprehensive rate limiting on authentication endpoints and account lockout.
-   **Search & Filtering**: Fast search capabilities across bags, bills, and users with pagination, including a dedicated mobile-friendly bag search (`/search`).
-   **Data Import/Export**: Optimized CSV/Excel export and bulk import with validation, including Excel-based batch import for relationships with QR code label extraction and error recovery. Multi-sheet Excel files are fully supported with per-sheet row numbering and sheet context in error messages. **Import Policy**: Existing parent bags are automatically used when found (children are linked to them); only duplicate child bags are rejected.
-   **Large-Scale Import Performance**: `LargeScaleChildParentImporter` handles lakhs (100,000+) of bags efficiently:
    -   **ULTRA-OPTIMIZED**: Two-pass bulk processing with raw SQL inserts
    -   Throughput: ~500+ bags/second (~3-4 minutes for 1 lakh bags, 5-6x faster)
    -   Memory: ~4 MB peak (streaming + result limiting)
    -   Single query duplicate detection (vs per-parent queries)
    -   Raw SQL bulk inserts (100x faster than ORM)
    -   Chunk-level transactions with 1000-row batches
    -   Intra-file duplicate detection (parent and child)
    -   All errors preserved; success results capped at 5,000
    -   Downloadable Excel result file with Successes and Errors sheets
-   **Global Error Handlers**: User-friendly error pages for common HTTP errors with appropriate status codes and navigation.
-   **Role-Based UI Visibility**: Features are hidden at the UI level based on user roles (Admin, Biller, Dispatcher) with backend access controls.
-   **IPT (Inter Party Transfer)**: Return ticket system for dealers/distributors returning parent bags at C&F points. Scanned bags are automatically unlinked from bills and made available for re-assignment. Tracks original bill, child counts, and weights at return time.

### Database Models
-   **User**: Manages users with roles and authentication.
-   **Bag**: Represents individual bags with QR IDs, type, and relationships.
-   **Scan**: Records bag scanning events.
-   **AuditLog**: Comprehensive audit trail.
-   **PromotionRequest**: Manages admin promotion requests.
-   **Notification**: In-app user notifications.
-   **Bill**: Manages bill generation, including linked and total parent bag counts, total and expected weights, and total child bags.
-   **Link**: Defines parent-child bag relationships with a unique constraint on `child_bag_id`.
-   **BillBag**: Association table linking bills to parent bags.
-   **ReturnTicket**: IPT return ticket for tracking parent bags returned.
-   **ReturnTicketBag**: Association between return tickets and returned parent bags with snapshot data.
-   **BillReturnEvent**: History of bill modifications during IPT return operations.

## Database Management Scripts

-   **run_production_migrations.py**: Runs Alembic migrations against production database (uses PRODUCTION_DATABASE_URL).
-   **check_db_sync.py**: Compares development and production database schemas (Alembic revisions, table structures). Usage: `python check_db_sync.py --verbose`
-   **safe_production_cleanup.py**: Safely deletes production data while preserving specific records (superadmin users, M444-00001 to M444-00600 parent bags, and related data). Runs in dry-run mode by default; use `--execute` to actually delete.
-   **deploy.sh**: Production deployment script that runs schema sync check, applies migrations, then starts Gunicorn.

## Production Deployment

### Deployment Configuration
The application is configured for Replit Autoscale deployment:
-   **Deployment Target**: Autoscale (configured in `.replit`)
-   **Run Command**: `./deploy.sh` (handles migrations and server startup)
-   **Port**: Uses `$PORT` environment variable (provided by Autoscale) or defaults to 5000

### Required Secrets (Production)
The following secrets must be configured in Replit Secrets for production deployment:
-   **SESSION_SECRET**: Cryptographic key for session signing (generate with `python3 -c 'import secrets; print(secrets.token_hex(32))'`)
-   **ADMIN_PASSWORD**: Secure password for the admin account (min 12 chars, mixed case, numbers, symbols)
-   **PRODUCTION_DATABASE_URL**: PostgreSQL connection string for production database (e.g., AWS RDS)
-   **DATABASE_URL**: Development database connection (auto-provided by Replit PostgreSQL)
-   **SENDGRID_API_KEY**: (Optional) For email notifications and password reset

### Deployment Process
1. **Schema Sync Check**: Compares development and production database schemas
2. **Run Migrations**: Applies any pending Alembic migrations to production database
3. **Post-Migration Verification**: Confirms schemas are in sync after migrations
4. **Start Gunicorn**: Launches gevent-based async server with optimized worker settings

### Migration Chain
Current migration head: `j6k7l8m9n0o1` (13 migrations total)
-   Migrations are managed by Flask-Migrate/Alembic
-   Production migrations run automatically during deployment via `deploy.sh`
-   Schema verification ensures development and production stay in sync

### How to Publish
1. Ensure all required secrets are configured in Replit Secrets
2. Click the "Publish" button in Replit
3. Select "Autoscale" deployment target
4. The `deploy.sh` script will automatically handle migrations and server startup

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
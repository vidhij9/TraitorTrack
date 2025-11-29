# TraitorTrack - Bag Tracking System

## Overview
TraitorTrack is a high-performance, web-based bag tracking system designed for warehouse and logistics operations. Its primary purpose is to manage parent-child bag relationships, streamline scanning processes, and automate bill generation. The system is built for scalability, supporting over 100 concurrent users and managing up to 1.8 million bags, aiming to enhance operational efficiency and provide real-time tracking for dispatchers, billers, and administrators.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Application Structure
The project utilizes a standard Flask application structure, organizing code into modules for models, routes, API, and forms.

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
-   Full-screen warehouse operation interfaces with large fonts and controls.
-   Visual and audio feedback for scanning operations.
-   Optimized for mobile scanners on low-grade devices, featuring simplified UI, audio/vibration feedback, and aggressive auto-focus.
-   Agriculture industry-themed color scheme (forest green, earth-tone beige, golden accents).
-   Enhanced readability with increased button sizes and clear text.
-   Mobile-first optimization for core warehouse pages, including minimal scrolling, compressed spacing, reduced icon sizes, and collapsed secondary content.
-   Fixed mobile bottom navigation bar with four primary actions (Home, Scan, Search, Bills).

**System Design Choices:**
-   **Live Data Architecture**: All caching has been removed; every query fetches fresh data directly from PostgreSQL, utilizing optimized indexes for rapid response times.
-   **Production-Scale Optimizations**: Includes optimized connection pooling, API pagination, comprehensive database indexing, high-performance query optimizer using direct SQL, optimized request logging, and streamlined authentication.
-   **Ultra-Optimized Query Performance**: Critical endpoints leverage PostgreSQL CTEs, bulk fetching, and direct SQL to prevent N+1 query issues. Dashboard statistics are calculated in real-time using aggregate queries.
-   **Mobile-First UI Enhancements**: Features a responsive card layout for bag management on mobile, with desktop table views hidden and vice-versa. Includes comprehensive pagination controls.
-   **Session Management**: Uses Flask's native stateless signed cookie sessions (no server-side storage required). Session data is cryptographically signed and stored in the client cookie, enabling true Autoscale-ready deployments across any number of workers/instances.
-   **Two-Factor Authentication (2FA)**: TOTP-based 2FA for admin users, including QR code provisioning and stringent rate limiting.
-   **Security Features**: Incorporates scrypt for password hashing, CSRF protection, robust session validation, security headers, comprehensive rate limiting, auto-detection of production environment for HTTPS-only cookies, QR code validation, and a strong password policy.
-   **Login Rate Limiting**: Dynamic rate limiting applied to login attempts.
-   **Comprehensive Audit Logging**: Tracks critical security events, with GDPR-compliant PII anonymization.
-   **System Health Monitoring**: Provides a real-time metrics endpoint and an admin dashboard.
-   **Deployment**: Configured for Autoscale and cloud environments using Gunicorn, with fully environment variable-driven configuration. Rate limiting (RATE_LIMIT_PER_DAY/HOUR/MINUTE) and database pool sizing (DB_POOL_SIZE, DB_MAX_OVERFLOW) are configurable via environment variables.
-   **Production Environment Detection**: Automatically detects the production environment via `REPLIT_DEPLOYMENT` or `REPLIT_ENVIRONMENT`, enabling HTTPS-only cookies, HSTS headers, strict rate limiting, and CSP.
-   **Automatic Database Migrations**: Uses Flask-Migrate for automated migrations upon application startup.
-   **Offline Support**: Implements a `localStorage`-based offline queue with auto-retry mechanisms and optimistic UI updates.
-   **Undo Functionality**: Provides a backend endpoint and UI for undoing the most recent scan within a one-hour window.
-   **Concurrency Control**: Utilizes atomic locking to prevent race conditions.

### Feature Specifications

**Production-Ready Features:**
-   **Bag Management**: Supports parent-child bag relationships and flexible linking, with two parent bag QR code formats.
-   **Scanner Integration**: Designed for HID keyboard scanners with robust error handling, duplicate prevention, and rapid scan throttling.
-   **Bill Generation**: Dynamic weight calculation based on child bag counts.
-   **API Endpoints**: Comprehensive REST API with mobile-first optimizations, V2 optimized endpoints (sub-50ms), Gzip compression, field filtering, and smart pagination.
-   **Real-time Dashboard**: Displays statistics via AJAX with live database queries.
-   **System Health Dashboard**: Admin-only interface for system metrics.
-   **Comprehensive Audit Logging**: Enterprise-grade audit trail with state snapshots and PII anonymization.
-   **Automatic Session Security**: Secure session management with dual timeouts and secure cookie handling.
-   **Brute Force Protection**: Comprehensive rate limiting on authentication endpoints and account lockout.
-   **Search & Filtering**: Fast search capabilities across bags, bills, and users with pagination.
-   **Dedicated Bag Search (/search)**: Mobile-friendly bag lookup with full relationship display - shows linked child bags (for parents), parent bag (for children), bill details, and recent scan history. Accessible from main nav, dashboard, and mobile bottom nav.
-   **Data Import/Export**: Optimized CSV/Excel export and bulk import with validation.
-   **Batch Import**: Excel-based batch import for child→parent and parent→bill relationships, featuring QR code label extraction, duplicate handling, and batch-level error recovery. Parent bags must exist before linking children; batches with missing parents are rejected with clear error messages showing row numbers and parent codes, ensuring data integrity.
-   **Multi-File Batch Import**: Allows simultaneous upload and processing of multiple Excel files with comprehensive error reporting and downloadable Excel error reports. Utilizes file-based temporary storage to handle large error reports without session size limitations, with automatic cleanup of reports older than 1 hour.

### Database Models
-   **User**: Manages users with roles and authentication.
-   **Bag**: Represents individual bags with QR IDs, type, and relationships.
-   **Scan**: Records bag scanning events.
-   **AuditLog**: Comprehensive audit trail.
-   **PromotionRequest**: Manages admin promotion requests.
-   **Notification**: In-app user notifications.
-   **Bill**: Manages bill generation.
-   **Link**: Defines parent-child bag relationships with a UNIQUE constraint on `child_bag_id` (ensuring one child has only one parent).
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

## Recent Changes (November 2025)

### Bug Fixes & Optimizations
1. **Bill ID Validation Enhancement**: Added robust input sanitization using regex `[\x00-\x1F\x7F\u200B-\u200D\uFEFF]` to remove invisible scanner characters (null bytes, control characters, zero-width spaces) from barcode scanner input. Implemented case-insensitive duplicate detection with `UPPER(bill_id)`.

2. **Flexible Bill Completion**: Removed rigid parent bag count requirement - bills can now be completed with ANY number of linked bags (≥1) instead of requiring an exact match. This allows for real-world flexibility in warehouse operations.

3. **Real-Time Weight Tracking**: Added weight tracking display to bill scanning page showing:
   - Current Weight: Sum of all linked bags' child counts × 1kg
   - Expected Weight: Expected parent bag count × 30kg
   - Updates dynamically when bags are added or removed using server-returned child counts

4. **Global Error Handlers**: Added user-friendly error pages for HTTP errors (400, 403, 404, 405, 429, 500, 502, 503) with:
   - Friendly error messages without technical jargon
   - Navigation buttons (Dashboard, Back, Login where appropriate)
   - Proper HTTP status codes returned (not masked as 200)
   - JSON responses for AJAX requests

5. **Mobile Optimization**: Enhanced mobile user management with role-based dispatch area toggles, compact headers, and improved touch targets for warehouse workers.

6. **Role-Based UI Visibility**: Implemented comprehensive role-based feature visibility so users only see features they can access:
   - **Admin**: Full access to all features (Bills, Users, Import, Delete, etc.)
   - **Biller**: Access to Bills management (create, edit, scan) but NOT Users management
   - **Dispatcher**: Access to Scanning and Search only - NO Bills or Users access
   - Features are hidden at the UI level (buttons, links don't appear) rather than showing error messages
   - Backend access controls remain in place as a safety net
   - Uses `can_edit_bills()` helper method for consistent role checks across templates

7. **Parent Bag Capacity Tracking System**: Added comprehensive capacity tracking for bills with progressive linking:
   - **Capacity Fields**: Bill model includes `linked_parent_count` (current), `parent_bag_count` (capacity), `total_weight_kg`, `expected_weight_kg`, `total_child_bags`
   - **Progressive Linking**: Each parent bag scan immediately commits to the database; if 10/500 scanned, those 10 are saved
   - **Auto-Close**: Bills automatically set status to `at_capacity` when `linked_parent_count` reaches `parent_bag_count`
   - **Weight Calculation**: Actual weight = total child bags × 1kg; Expected weight = capacity × 30kg per parent bag
   - **Edit Bill**: Full edit capability for capacity, status, and description with server-side validation
   - **Status Management**: Manual status override available (new, processing, at_capacity, completed)
   - **Capacity Validation**: Cannot reduce capacity below already linked count; maximum 500 parent bags
   - **Recalculation**: Weights and linked counts recalculate after any capacity or status change
   - **Database Migration**: Migration `f2g3h4i5j6k7` adds `linked_parent_count` column with default 0
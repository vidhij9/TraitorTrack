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
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
-   **Session Management**: Employs secure, stateless signed cookie sessions, with optional Redis-backed sessions offering dual timeouts, activity tracking, user warnings, and secure cookie handling. Redis is strictly used for sessions/rate-limiting, not for data caching.
-   **Two-Factor Authentication (2FA)**: TOTP-based 2FA for admin users, including QR code provisioning and stringent rate limiting.
-   **Security Features**: Incorporates scrypt for password hashing, CSRF protection, robust session validation, security headers, comprehensive rate limiting, auto-detection of production environment for HTTPS-only cookies, QR code validation, and a strong password policy.
-   **Login Rate Limiting**: Dynamic rate limiting applied to login attempts.
-   **Comprehensive Audit Logging**: Tracks critical security events, with GDPR-compliant PII anonymization.
-   **System Health Monitoring**: Provides a real-time metrics endpoint and an admin dashboard.
-   **Deployment**: Configured for Autoscale and cloud environments using Gunicorn, with environment variable-driven configuration and optional Redis integration.
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
-   **Flask-Limiter**: Rate limiting.
-   **werkzeug**: Secure password hashing.
-   **pyotp**: TOTP generation and verification.
-   **qrcode**: QR code generation for 2FA setup.
-   **Redis**: Optional for production session management.
-   **SendGrid**: Email service for password reset and notifications.
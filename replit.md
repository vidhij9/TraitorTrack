# TraitorTrack - Bag Tracking System

## Overview
TraitorTrack is a high-performance, production-ready web-based bag tracking system for warehouse and logistics. It manages parent-child bag relationships, scanning, and bill generation, designed to support over 100 concurrent users and 1.8 million bags. Its core purpose is to streamline logistics, enhance operational efficiency, and provide robust, scalable bag management with real-time tracking for dispatchers, billers, and administrators.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Application Structure
The project uses a standard Flask application structure with modules for models, routes, API, and forms. Key components include `query_optimizer.py` for high-performance database operations and `cache_utils.py` for caching strategies.

### Technical Implementation

**Backend Stack:**
- **Flask 3.1+**: Python web framework.
- **SQLAlchemy 2.0+**: ORM with optimized connection pooling.
- **PostgreSQL**: Primary database.
- **Gunicorn + gevent**: Asynchronous WSGI server.
- **Flask-Login**: Session-based authentication.
- **Flask-WTF**: Form validation and CSRF protection.
- **Flask-Limiter**: In-memory rate limiting.
- **ujson**: High-performance JSON parsing for audit logging.

**UI/UX Decisions:**
- Clean, production-ready web interface for dispatchers, billers, and administrators.
- AJAX-powered dashboard for real-time statistics.
- Full-screen interfaces for warehouse operations with large, warehouse-friendly fonts and controls.
- Visual and audio feedback for scanning operations.
- Mobile scanner optimization for low-grade devices with simplified UI, audio/vibration feedback, and aggressive auto-focus.

**System Design Choices:**
- **Production-Scale Optimizations**: Statistics cache, optimized connection pooling, API pagination, comprehensive database indexing, high-performance query optimizer, role-aware caching with invalidation, optimized request logging, and streamlined authentication.
- **Session Management**: Secure, filesystem-based sessions (development) and Redis-backed sessions (production) with dual timeout, activity tracking, user warnings, and secure cookie handling.
- **Two-Factor Authentication (2FA)**: TOTP-based 2FA for admin users with QR code provisioning and strict rate limiting.
- **Security Features**: Secure password hashing (scrypt), CSRF protection, session validation, security headers, comprehensive rate limiting on authentication routes, and auto-detection of production environment for HTTPS-only cookies. QR code validation prevents SQL injection and XSS.
- **Comprehensive Audit Logging**: All critical security events tracked with GDPR-compliant PII anonymization.
- **Rate Limiting Strategy**: In-memory Flask-Limiter with fixed-window strategy across various endpoints.
- **System Health Monitoring**: Real-time metrics endpoint and admin dashboard tracking database connection pool, cache performance, memory usage, database size, and error counts.
- **Deployment**: Utilizes `gunicorn` with sync workers, designed for cloud environments with environment variable-driven configuration.
- **Automatic Database Migrations**: Flask-Migrate configured to run migrations automatically on app startup, ensuring zero-downtime deployments with comprehensive logging and production-safe error handling.
- **Validation Framework**: Comprehensive input validation utilities for QR codes, search queries, HTML sanitization, pagination, email/username, numeric ranges, choice/enum, and file uploads.
- **Offline Support**: `localStorage`-based offline queue with auto-retry and optimistic UI updates.
- **Undo Functionality**: Backend endpoint `/api/unlink_child` and UI for removing the most recent scan within a 1-hour window.
- **Concurrency Control**: Atomic locking (e.g., `SELECT ... FOR UPDATE`) prevents race conditions, especially for critical operations like the 30-child limit.
- **Cache Coherence**: `QueryOptimizer` includes cache invalidation methods called after all bag/link mutations.

### Feature Specifications

**Production-Ready Features:**
- **Bag Management**: Supports parent-child bag relationships and flexible linking.
- **Scanner Integration**: Designed for HID keyboard scanners (keyboard wedge mode) with robust error handling, duplicate prevention, and rapid scan throttling.
- **Bill Generation**: Dynamic weight calculation based on child bag counts.
- **API Endpoints**: Provides various endpoints for bag, stats, and system health.
- **Real-time Dashboard**: Displays statistics via AJAX and optimized caching.
- **System Health Dashboard**: Admin-only interface for system metrics.
- **Two-Factor Authentication**: TOTP-based 2FA for admin users with QR code setup and brute force protection.
- **Comprehensive Audit Logging**: Enterprise-grade audit trail with state snapshots and PII anonymization.
- **Automatic Session Security**: Secure session management with dual timeouts and secure cookie handling.
- **Brute Force Protection**: Comprehensive rate limiting on authentication endpoints and account lockout.
- **Search & Filtering**: Fast search across bags, bills, and users with pagination.
- **Data Import/Export**: Optimized CSV/Excel export and bulk import with validation.

### Database Models
- **User**: Manages users with roles and authentication.
- **Bag**: Represents individual bags with QR IDs, type, and relationships.
- **Scan**: Records bag scanning events.
- **AuditLog**: Comprehensive audit trail.
- **PromotionRequest**: Manages admin promotion requests.
- **Notification**: In-app user notifications.
- **StatisticsCache**: Single-row table for dashboard statistics.
- **Bill**: Manages bill generation.
- **Link**: Defines parent-child bag relationships.
- **BillBag**: Association table linking bills to parent bags.

## External Dependencies
- **PostgreSQL**: Primary relational database.
- **Gunicorn**: WSGI HTTP Server.
- **psutil**: System and process monitoring.
- **Flask-Login**: User session and authentication management.
- **Flask-WTF**: Web forms and CSRF protection.
- **Flask-Limiter**: Rate limiting.
- **werkzeug**: Secure password hashing.
- **pyotp**: TOTP generation and verification.
- **qrcode**: QR code generation for 2FA setup.
- **Redis**: For production session management (mandatory in production environments).
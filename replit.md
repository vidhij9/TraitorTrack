# TraceTrack - Bag Tracking System

## Overview
TraceTrack is a high-performance, production-ready web-based bag tracking system designed for warehouse and logistics operations. It efficiently manages parent-child bag relationships, scanning processes, and bill generation. The system is built to support over 100 concurrent users and handle more than 1.8 million bags, providing real-time tracking capabilities for dispatchers, billers, and administrators. Its core purpose is to streamline logistics, enhance operational efficiency, and provide robust, scalable bag management.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Application Structure
The project follows a standard Flask application structure, separating concerns into `models.py`, `routes.py`, `api.py`, and `forms.py`. Key architectural components include `query_optimizer.py` for high-performance database operations and `cache_utils.py` for caching strategies.

### Technical Implementation

**Backend Stack:**
- **Flask 3.1+**: Python web framework.
- **SQLAlchemy 2.0+**: ORM with optimized connection pooling.
- **PostgreSQL**: Primary database.
- **Gunicorn + gevent**: Asynchronous WSGI server for concurrency.
- **Flask-Login**: Session-based authentication.
- **Flask-WTF**: Form validation and CSRF protection.
- **Flask-Limiter**: In-memory rate limiting.

**UI/UX Decisions:**
- Clean, production-ready web interface for dispatchers, billers, and administrators.
- AJAX-powered dashboard for real-time statistics.

**System Design Choices:**
- **Production-Scale Optimizations**: Includes a statistics cache system, optimized connection pooling, API pagination limits, database indexing on critical tables, a high-performance query optimizer, and smart role-aware caching with invalidation.
- **Session Management**: Filesystem-based sessions with dual timeout mechanism (1-hour absolute, 30-minute inactivity), activity tracking, user warnings, secure HTTPOnly/SameSite=Lax cookies, and automatic logout on browser close (non-permanent sessions for enhanced security).
- **Two-Factor Authentication (2FA)**: TOTP-based 2FA for admin users using pyotp library with QR code provisioning, enable/disable controls, password-protected disable, and strict rate limiting (5 per minute) on verification endpoints to prevent brute force attacks.
- **Security Features**: Secure password hashing (scrypt), CSRF protection, session validation, security headers, comprehensive rate limiting on all authentication routes (login, register, password reset, 2FA), and auto-detection of production environment for HTTPS-only cookies.
- **Comprehensive Audit Logging**: All critical security events tracked including login attempts (success/failure/account locked/2FA), logout, password changes, 2FA operations (enable/disable/verify), user registration, role changes, and data modifications. Each log includes username, IP address, timestamp, and contextual details with before/after snapshots for change tracking.
- **Rate Limiting Strategy**: In-memory Flask-Limiter with fixed-window strategy - Login (10/min), Register (5/min), Forgot Password (3/min), Password Reset (5/min), 2FA Setup (10/min), 2FA Enable (5/min), 2FA Disable (5/min), 2FA Verify (5/min), API endpoints (10000/min for high traffic), default (2000/day, 500/hour).
- **System Health Monitoring**: Real-time metrics endpoint and admin dashboard tracking database connection pool, cache performance, memory usage, database size, and error counts.
- **Deployment**: Utilizes `gunicorn` with sync workers, designed for cloud environments with environment variable-driven configuration.
- **Validation Framework**: Comprehensive input validation utilities (`validation_utils.py`) for QR codes, search queries, HTML sanitization, pagination, email/username, numeric ranges, choice/enum, and file uploads (size, type, path traversal).

### Feature Specifications

**Production-Ready Features:**
- **Bag Management**: Supports parent-child bag relationships and flexible linking.
- **Scanner Integration**: Designed for Coconut wireless 2D barcode scanners (keyboard wedge mode).
- **Bill Generation**: Dynamic weight calculation based on child bag counts.
- **API Endpoints**: Provides `/api/bag/<qr_id>`, `/api/stats`, `/api/system_health`, `/health` for various functionalities.
- **Real-time Dashboard**: Displays statistics powered by AJAX and an optimized caching system.
- **System Health Dashboard**: Admin-only interface showing database connections, cache hit rate, memory usage, and database size.
- **Two-Factor Authentication**: Admin users can enable TOTP-based 2FA with QR code setup, authenticator app support (Google Authenticator, Authy, etc.), and secure enable/disable controls. Includes brute force protection via rate limiting.
- **Comprehensive Audit Logging**: Enterprise-grade audit trail tracking all security events (login/logout, 2FA operations, password changes, registration, role changes, data modifications) with before/after state snapshots, IP addresses, timestamps, and request correlation. Supports compliance requirements and security monitoring.
- **Automatic Session Security**: Sessions expire automatically on browser close (non-permanent sessions), with dual timeout mechanism (1-hour absolute, 30-minute inactivity) and secure cookie handling (HTTPS-only in production).
- **Brute Force Protection**: Comprehensive rate limiting on all authentication endpoints - Login, registration, password reset, and 2FA operations have strict limits (3-10 per minute) to prevent automated attacks. Account lockout after multiple failed login attempts.
- **Search & Filtering**: Fast search across bags, bills, and users with pagination.
- **Data Import/Export**: Optimized CSV/Excel export (10K record limit) and bulk import with validation.

**Disabled Features:**
- **Excel Upload**: Temporarily disabled for system optimization, with API batch creation as an alternative.
- **Email Notifications**: Not yet configured, requires `SENDGRID_API_KEY`. Manual EOD summaries are available.

### Database Models
- **User**: Manages users with roles (admin, biller, dispatcher) and authentication. Includes 2FA fields (totp_secret, two_fa_enabled) for admin users.
- **Bag**: Represents individual bags with unique QR IDs, type (parent/child), and relationships.
- **Scan**: Records bag scanning events by users.
- **AuditLog**: Comprehensive audit trail with before/after state snapshots, IP addresses, request IDs, and contextual details for all critical operations. Indexes optimized for fast queries by user, timestamp, action, and entity.
- **StatisticsCache**: Single-row table updated via database triggers for fast dashboard statistics.
- **Bill**: Manages bill generation, including parent bag counts and total weights.
- **Link**: Defines parent-child bag relationships.

## External Dependencies
- **PostgreSQL**: Primary relational database for all application data.
- **Gunicorn**: WSGI HTTP Server for Python web applications.
- **psutil**: System and process monitoring for health metrics.
- **Flask-Login**: Manages user sessions and authentication.
- **Flask-WTF**: Integration with WTForms for web forms and CSRF protection.
- **Flask-Limiter**: Provides rate limiting functionality (in-memory) with comprehensive coverage across authentication and API endpoints.
- **werkzeug**: Used for secure password hashing.
- **pyotp**: TOTP generation and verification for two-factor authentication.
- **qrcode**: QR code generation for 2FA authenticator app setup.
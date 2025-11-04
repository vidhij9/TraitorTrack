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

**System Design Choices:**
- **Production-Scale Optimizations**: Includes a statistics cache system, optimized connection pooling, API pagination limits, comprehensive database indexing (50+ indexes), high-performance query optimizer, smart role-aware caching with invalidation, optimized request logging, and streamlined authentication checks.
- **Session Management**: Filesystem-based sessions with dual timeout (1-hour absolute, 30-minute inactivity), activity tracking, user warnings, secure HTTPOnly/SameSite=Lax cookies, and automatic logout on browser close.
- **Two-Factor Authentication (2FA)**: TOTP-based 2FA for admin users using `pyotp` with QR code provisioning, enable/disable controls, and strict rate limiting.
- **Security Features**: Secure password hashing (scrypt), CSRF protection, session validation, security headers, comprehensive rate limiting on all authentication routes, and auto-detection of production environment for HTTPS-only cookies.
- **Comprehensive Audit Logging**: All critical security events tracked including login attempts, logout, password changes, 2FA operations, user registration, role changes, and data modifications, with GDPR-compliant PII anonymization.
- **Rate Limiting Strategy**: In-memory Flask-Limiter with fixed-window strategy across various endpoints (Login, Register, Forgot Password, Password Reset, 2FA, API endpoints).
- **System Health Monitoring**: Real-time metrics endpoint and admin dashboard tracking database connection pool, cache performance, memory usage, database size, and error counts.
- **Deployment**: Utilizes `gunicorn` with sync workers, designed for cloud environments with environment variable-driven configuration.
- **Validation Framework**: Comprehensive input validation utilities for QR codes, search queries, HTML sanitization, pagination, email/username, numeric ranges, choice/enum, and file uploads.

### Feature Specifications

**Production-Ready Features:**
- **Bag Management**: Supports parent-child bag relationships and flexible linking.
- **Scanner Integration**: Designed for HID keyboard scanners (keyboard wedge mode).
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

**Disabled Features:**
- **Excel Upload**: Temporarily disabled.
- **Email Notifications**: Not yet configured.

### Database Models
- **User**: Manages users with roles and authentication, including 2FA fields. Optimized with 9 indexes.
- **Bag**: Represents individual bags with QR IDs, type, and relationships. Optimized with 11 indexes.
- **Scan**: Records bag scanning events. Optimized with 6 indexes.
- **AuditLog**: Comprehensive audit trail. Optimized with 7 indexes.
- **PromotionRequest**: Manages admin promotion requests. Optimized with 5 indexes.
- **Notification**: In-app user notifications. Optimized with 4 indexes.
- **StatisticsCache**: Single-row table for dashboard statistics.
- **Bill**: Manages bill generation. Optimized with 4 indexes.
- **Link**: Defines parent-child bag relationships. Optimized with 3 indexes.
- **BillBag**: Association table linking bills to parent bags. Optimized with 2 indexes.

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
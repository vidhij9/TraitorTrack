# TraitorTrack - Bag Tracking System

## Overview
TraitorTrack is a high-performance, web-based bag tracking system designed for warehouse and logistics operations. Its primary purpose is to manage parent-child bag relationships, scanning processes, and bill generation. The system is built to be scalable, supporting over 100 concurrent users and managing up to 1.8 million bags, thereby streamlining logistics, enhancing operational efficiency, and providing real-time tracking for dispatchers, billers, and administrators.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Application Structure
The project utilizes a standard Flask application structure, organizing code into modules for models, routes, API, and forms. It includes `query_optimizer.py` for high-performance database operations and `cache_utils.py` for managing caching strategies.

### Technical Implementation

**Backend Stack:**
- **Flask 3.1+**: Python web framework.
- **SQLAlchemy 2.0+**: ORM with optimized connection pooling.
- **PostgreSQL**: Primary database.
- **Gunicorn + gevent**: Asynchronous WSGI server.
- **Flask-Login**: Session-based authentication.
- **Flask-WTF**: Form validation and CSRF protection.
- **Flask-Limiter**: In-memory rate limiting.
- **ujson**: High-performance JSON parsing.

**UI/UX Decisions:**
- Clean, production-ready web interfaces for various user roles.
- AJAX-powered dashboard for real-time statistics.
- Full-screen interfaces for warehouse operations with large fonts and controls.
- Visual and audio feedback for scanning operations.
- Optimized for mobile scanners on low-grade devices, featuring simplified UI, audio/vibration feedback, and aggressive auto-focus.
- Redesigned color scheme to an agriculture industry theme (forest green, earth-tone beige, golden accents).
- Increased button sizes and enhanced text readability for warehouse workers.
- Mobile-first optimization for core warehouse pages with minimal scrolling, compressed spacing, reduced icon sizes, and collapsed secondary content.
- Implemented a fixed mobile bottom navigation bar with four primary actions (Home, Scan, Search, Bills) for quick access.

**System Design Choices:**
- **Production-Scale Optimizations**: Includes a statistics cache, optimized connection pooling, API pagination, comprehensive database indexing, a high-performance query optimizer, role-aware caching with invalidation, optimized request logging, and streamlined authentication.
- **Redis-Backed Multi-Worker Caching**: All caching layers support optional Redis for multi-worker coherence with immediate cache invalidation. Automatic fallback to in-memory caching when Redis is unavailable.
- **Ultra-Optimized Query Performance**: Critical endpoints refactored to eliminate N+1 queries using PostgreSQL CTEs and bulk fetching for significant speed improvements (e.g., `api_delete_bag`, `bag_details`, `view_bill`).
- **Mobile-First UI Enhancements**: Responsive card layout for bag management on mobile, with desktop table view hidden on mobile, and vice-versa. Comprehensive pagination controls preserve filter parameters.
- **Session Management**: Supports secure, stateless signed cookie sessions and optional Redis-backed sessions with dual timeouts, activity tracking, user warnings, and secure cookie handling.
- **Two-Factor Authentication (2FA)**: TOTP-based 2FA for admin users with QR code provisioning and strict rate limiting.
- **Security Features**: Secure password hashing (scrypt), CSRF protection, session validation, security headers, comprehensive rate limiting on authentication routes, auto-detection of production environment for HTTPS-only cookies, and QR code validation to prevent SQL injection and XSS. Password policy requires a minimum of 8 characters.
- **Login Rate Limiting**: Dynamic rate limit function for login attempts, with different settings for production and development, and custom 429 error handling.
- **Comprehensive Audit Logging**: Tracks all critical security events with GDPR-compliant PII anonymization.
- **System Health Monitoring**: Provides a real-time metrics endpoint and admin dashboard for tracking database connection pool, cache performance, memory usage, database size, and error counts.
- **Deployment**: Configured for Autoscale and cloud environments using `gunicorn` with environment variable-driven configuration. Redis is optional.
- **Production Environment Detection**: Uses REPLIT_DEPLOYMENT (=='1') or REPLIT_ENVIRONMENT (=='production') for automatic production mode detection. When detected, enables HTTPS-only cookies, HSTS headers, strict rate limiting (20 login attempts/hour), and CSP upgrade-insecure-requests. Development mode uses relaxed settings (HTTP cookies OK, 1000 login attempts/hour) for local testing.
- **Automatic Database Migrations**: Flask-Migrate is configured for automatic migrations on app startup.
- **Offline Support**: Features a `localStorage`-based offline queue with auto-retry and optimistic UI updates.
- **Undo Functionality**: Backend endpoint and UI for undoing the most recent scan within a 1-hour window.
- **Concurrency Control**: Employs atomic locking to prevent race conditions during critical operations.
- **Cache Coherence**: `QueryOptimizer` includes cache invalidation methods triggered after bag/link mutations.

### Feature Specifications

**Production-Ready Features:**
- **Bag Management**: Supports parent-child bag relationships and flexible linking, with support for two parent bag QR code formats (e.g., SB12345, M444-12345).
- **Scanner Integration**: Designed for HID keyboard scanners with robust error handling, duplicate prevention, and rapid scan throttling.
- **Bill Generation**: Dynamic weight calculation based on child bag counts.
- **API Endpoints**: Comprehensive REST API with mobile-first optimizations, including V2 optimized endpoints (sub-50ms response times), Gzip compression (60-80% bandwidth reduction), field filtering, and smart pagination.
- **Real-time Dashboard**: Displays statistics via AJAX and optimized caching.
- **System Health Dashboard**: Admin-only interface for system metrics.
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
- **Redis**: For production session management.
- **SendGrid**: Email service for password reset and notifications.
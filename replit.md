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
- **Session Management**: Filesystem-based sessions with dual timeout mechanism (1-hour absolute, 30-minute inactivity), activity tracking, user warnings, and secure HTTPOnly/SameSite=Lax cookies.
- **Security Features**: Secure password hashing (scrypt), CSRF protection, session validation, security headers, in-memory rate limiting, and auto-detection of production environment for HTTPS-only cookies.
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
- **Audit Logging**: Complete tracking of all user actions with timestamp and user information.
- **Search & Filtering**: Fast search across bags, bills, and users with pagination.
- **Data Import/Export**: Optimized CSV/Excel export (10K record limit) and bulk import with validation.

**Disabled Features:**
- **Excel Upload**: Temporarily disabled for system optimization, with API batch creation as an alternative.
- **Email Notifications**: Not yet configured, requires `SENDGRID_API_KEY`. Manual EOD summaries are available.

### Database Models
- **User**: Manages users with roles (admin, biller, dispatcher) and authentication.
- **Bag**: Represents individual bags with unique QR IDs, type (parent/child), and relationships.
- **Scan**: Records bag scanning events by users.
- **AuditLog**: Tracks user actions for auditing purposes.
- **StatisticsCache**: Single-row table updated via database triggers for fast dashboard statistics.
- **Bill**: Manages bill generation, including parent bag counts and total weights.
- **Link**: Defines parent-child bag relationships.

## External Dependencies
- **PostgreSQL**: Primary relational database for all application data.
- **Gunicorn**: WSGI HTTP Server for Python web applications.
- **psutil**: System and process monitoring for health metrics.
- **Flask-Login**: Manages user sessions and authentication.
- **Flask-WTF**: Integration with WTForms for web forms and CSRF protection.
- **Flask-Limiter**: Provides rate limiting functionality (in-memory).
- **werkzeug**: Used for secure password hashing.
# TraceTrack - Bag Tracking System

## Overview
TraceTrack is a high-performance web-based bag tracking system designed for warehouse and logistics operations. It efficiently manages parent-child bag relationships, scanning processes, and bill generation. The system is built to support over 100 concurrent users and handle more than 1.8 million bags, providing a production-ready interface for dispatchers, billers, and administrators with real-time tracking capabilities. Its core purpose is to streamline logistics, enhance operational efficiency, and provide robust, scalable bag management.

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
- **Production-Scale Optimizations**:
    - **Statistics Cache System**: `statistics_cache` table with comprehensive database triggers ensures real-time, sub-10ms dashboard stats at any scale by avoiding expensive `COUNT(*)` queries.
    - **Connection Pool Optimization**: Configured for multi-worker environments (25 base + 15 overflow per worker, 80 total for 2 workers), ensuring high concurrency without exceeding database limits.
    - **API Pagination & Performance**: Strict limits (200 rows max, 10,000 max offset) and smart count strategies prevent performance bottlenecks for large datasets.
    - **Database Indexes**: Composite indexes on critical tables (Scan, AuditLog) optimize common query patterns for 1.8M+ records.
    - **High-Performance Query Optimizer (`query_optimizer.py`)**: Implements raw SQL and in-memory caching for critical operations like `get_bag_by_qr()`, `get_child_count_fast()`, and batch linking, significantly improving scanner and bill-linking workflow speeds.
- **Session Management**: Filesystem-based sessions with a 1-hour lifetime, secured with HTTPOnly and SameSite=Lax cookies.
- **Security Features**: Requires `SESSION_SECRET` environment variable, uses secure password hashing, CSRF protection, session validation, and security headers.
- **Deployment**: Utilizes `gunicorn` with `gevent` workers for efficient resource management, designed for cloud environments like Cloud Run with environment variable-driven configuration.

### Feature Specifications
- **Bag Management**: Supports parent-child bag relationships and flexible linking.
- **Scanner Integration**: Designed for Coconut wireless 2D barcode scanners (keyboard wedge mode).
- **Bill Generation**: Dynamic weight calculation based on child bag counts.
- **Excel Upload**: Bulk import of up to 80,000 bags with duplicate detection.
- **API Endpoints**: Provides `/api/bag/<qr_id>`, `/health`, and `/api/health` for various functionalities.
- **Real-time Dashboard**: Displays statistics powered by AJAX and an optimized caching system.

### Database Models
- **User**: Manages users with roles (admin, biller, dispatcher) and authentication.
- **Bag**: Represents individual bags with unique QR IDs, type (parent/child), and relationships.
- **Scan**: Records bag scanning events by users.
- **AuditLog**: Tracks user actions for auditing purposes.
- **StatisticsCache**: A single-row table automatically updated via database triggers to provide fast, real-time statistics for the dashboard.
- **Bill**: Manages bill generation, including parent bag counts and total weights.
- **Link**: Defines parent-child bag relationships.

## External Dependencies
- **PostgreSQL**: Primary relational database for all application data.
- **Gunicorn**: WSGI HTTP Server for Python web applications.
- **gevent**: Greenlet-based evented I/O for Gunicorn workers.
- **Flask-Login**: Manages user sessions and authentication.
- **Flask-WTF**: Integration with WTForms for web forms and CSRF protection.
- **Flask-Limiter**: Provides rate limiting functionality (in-memory).
- **werkzeug**: Used for secure password hashing.
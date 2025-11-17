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
- Clean, production-ready web interfaces for various user roles (dispatchers, billers, administrators).
- AJAX-powered dashboard for real-time statistics.
- Full-screen interfaces for warehouse operations with large fonts and controls.
- Visual and audio feedback for scanning operations.
- Optimized for mobile scanners on low-grade devices, featuring simplified UI, audio/vibration feedback, and aggressive auto-focus.
- Redesigned color scheme to an agriculture industry theme (forest green, earth-tone beige, golden accents).
- Increased button sizes (minimum 44px height, 18px fonts) and enhanced text readability (heavier font weights, WCAG AA-compliant contrast ratios) for warehouse workers.
- Mobile-first optimization for core warehouse pages (375px+ screens) with minimal scrolling, compressed spacing, reduced icon sizes, and collapsed secondary content.
- Implemented a fixed mobile bottom navigation bar (64px) with four primary actions (Home, Scan, Search, Bills) for quick access.

**System Design Choices:**
- **Production-Scale Optimizations**: Includes a statistics cache, optimized connection pooling, API pagination, comprehensive database indexing, a high-performance query optimizer, role-aware caching with invalidation, optimized request logging, and streamlined authentication.
- **Redis-Backed Multi-Worker Caching (November 2025)**: All caching layers support optional Redis for multi-worker coherence with immediate cache invalidation:
  - `query_optimizer.py`: Bag ID lookups use Redis with 30s TTL (tt:bag_id:* keys), falling back to in-memory in development or when Redis unavailable
  - `cache_utils.py`: Statistics and role-based caching use Redis backend (tt:global:* and tt:user:* keys) when available
  - Unified `tt:*` namespace for all cache types ensures centralized invalidation
  - Cache invalidation propagates across all workers via Redis using SCAN (non-blocking)
  - Stale keys are immediately deleted when underlying data is removed (cache coherency)
  - Automatic fallback to in-memory caching when Redis is unavailable (per-worker cache)
  - **Autoscale Deployment Support (November 2025)**: Application works without Redis using signed cookie sessions and per-worker caching
- **Ultra-Optimized Query Performance (November 2025)**: Critical endpoints refactored to eliminate N+1 queries using PostgreSQL CTEs and bulk fetching:
  - `api_delete_bag`: Single CTE query consolidates all validations (bill links, multi-parent checks, child counts) reducing 10+ queries to 2-3 queries total. Atomic deletion using cascading CTEs.
  - `bag_details`: Single CTE query fetches bag, children, parent, and bills using row_to_json/json_agg, then bulk-loads all Bag/Bill objects in 2 additional queries (total: 3 queries vs. N+1 previously).
  - `view_bill`: Single CTE query with json_agg fetches all parent bags and their children, then bulk-loads all Bag objects in 1 query (total: 3 queries vs. N²+1 previously). Expected 90-95% speed improvement on bills with 50+ parent bags.
  - `bag_management`: Already optimized with batch queries for child counts, parent links, bill links, and last scans (4-5 total queries for any page size).
- **Mobile-First UI Enhancements (November 2025)**: 
  - Responsive card layout for bag management on screens <768px with touch-optimized buttons and badges.
  - Desktop table view hidden on mobile, mobile card view hidden on desktop for optimal rendering.
  - Comprehensive pagination controls with page numbers, prev/next buttons, and result count indicators that preserve all filter parameters.
- **Session Management**: Supports secure, stateless signed cookie sessions (Autoscale-ready) and optional Redis-backed sessions (multi-worker optimal) with dual timeouts, activity tracking, user warnings, and secure cookie handling. Works without Redis for Autoscale deployments.
- **Two-Factor Authentication (2FA)**: TOTP-based 2FA for admin users with QR code provisioning and strict rate limiting.
- **Security Features**: Secure password hashing (scrypt), CSRF protection, session validation, security headers, comprehensive rate limiting on authentication routes, and auto-detection of production environment for HTTPS-only cookies. QR code validation prevents SQL injection and XSS.
- **Comprehensive Audit Logging**: Tracks all critical security events with GDPR-compliant PII anonymization.
- **Rate Limiting Strategy**: Utilizes in-memory Flask-Limiter with a fixed-window strategy across various endpoints.
- **System Health Monitoring**: Provides a real-time metrics endpoint and admin dashboard for tracking database connection pool, cache performance, memory usage, database size, and error counts.
- **Deployment**: Configured for Autoscale and cloud environments using `gunicorn` with environment variable-driven configuration. Redis is optional (recommended for multi-worker optimization but not required).
- **Automatic Database Migrations**: Flask-Migrate is configured for automatic migrations on app startup, ensuring zero-downtime deployments.
- **Validation Framework**: Comprehensive input validation utilities for various data types and inputs.
- **Offline Support**: Features a `localStorage`-based offline queue with auto-retry and optimistic UI updates.
- **Undo Functionality**: Backend endpoint `/api/unlink_child` and UI for undoing the most recent scan within a 1-hour window.
- **Concurrency Control**: Employs atomic locking (e.g., `SELECT ... FOR UPDATE`) to prevent race conditions during critical operations.
- **Cache Coherence**: The `QueryOptimizer` includes cache invalidation methods that are triggered after all bag/link mutations.

### Feature Specifications

**Production-Ready Features:**
- **Bag Management**: Supports parent-child bag relationships and flexible linking. **Parent Bag Format Support (November 2025)**: Supports two parent bag QR code formats for different product types:
  - **Mustard bags**: SB followed by exactly 5 digits (e.g., SB12345, SB00001)
  - **Moong bags**: M444- followed by exactly 5 digits (e.g., M444-12345, M444-00001)
  - Validation pattern: `^(?:SB\d{5}|M444-\d{5})$`
  - Case-insensitive input with automatic uppercase normalization
  - Both formats function identically for child linking and bill generation
- **Scanner Integration**: Designed for HID keyboard scanners with robust error handling, duplicate prevention, and rapid scan throttling.
- **Bill Generation**: Dynamic weight calculation based on child bag counts.
- **API Endpoints**: Provides various endpoints for bag, statistics, and system health management.
- **Real-time Dashboard**: Displays statistics via AJAX and optimized caching.
- **System Health Dashboard**: Admin-only interface for system metrics.
- **Two-Factor Authentication**: TOTP-based 2FA for admin users.
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
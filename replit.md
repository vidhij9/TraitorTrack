# TraceTrack - Bag Tracking System

## Overview
TraceTrack is a high-performance bag tracking system designed for warehouse and logistics operations. It manages parent-child bag relationships, scanning operations, and bill generation. The system is built to support **100+ concurrent users** and **1.5M+ bags** with millisecond-level response times. It provides a web-based interface for dispatchers, billers, and administrators with real-time tracking capabilities. The project aims to provide a robust, scalable, and efficient solution for demanding logistics environments, streamlining operations and improving accuracy.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
The application uses a Flask web framework for server-side rendered templates, enhanced with Bootstrap for UI. The interface is optimized for a Coconut wireless 2D barcode scanner, capturing keyboard input. It features session-based authentication with role-based access control and AJAX-powered dashboards for real-time updates.

### Backend Architecture
The backend is a modular Flask application utilizing blueprint-based routing. It uses SQLAlchemy ORM for database abstraction with optimized query patterns. Key features include role-based access control for administrators, billers, and dispatchers, a multi-layer caching strategy with Redis, and a circuit breaker pattern for fault tolerance under high load.

### Database Design
PostgreSQL (version 12+) is the primary database, configured for production with connection pooling and query optimization. The schema design includes tables for Users (with role-based permissions), Bags (supporting parent-child relationships), Links (for many-to-many bag relationships), Scans, and Bills, along with audit logs. Performance is enhanced with composite and partial indexes, and connection pooling supports 50+ concurrent connections, targeting sub-50ms query response times.

### Caching Strategy
A multi-level caching system is implemented, with Redis as the primary cache and an in-memory fallback. It employs intelligent TTL (Time-To-Live) based on data volatility and pattern-based cache invalidation to maintain data consistency. The goal is sub-millisecond cache hits and <100ms cache misses.

### Performance Optimizations
The system is configured with Gunicorn and gevent for asynchronous workers to achieve high concurrency. Database connection pooling is optimized for 50+ concurrent connections. Aggressive query caching and batch operations are used. Real-time monitoring tracks response times, CPU, memory, and throughput. Load testing has validated support for 50-75 concurrent users with sub-300ms response times for database operations. For 100+ concurrent users, further scaling considerations include read replicas, Redis-based session stores, and connection pooling proxies.

### Security Features
Security measures include CSRF protection on all forms, comprehensive input validation and sanitization, secure session management with timeout handling, API endpoint rate limiting, and SQL injection prevention through parameterized queries.

### Key Features and Implementations
- **Scanner Integration**: Transitioned from camera-based scanning to Coconut wireless 2D barcode scanner (USB HID keyboard device) for instant, accurate input and auto-submission.
- **Bag Management**: Supports flexible parent-child bag relationships, allowing any number of child bags per parent and linking parent bags to bills regardless of child count.
- **Bill Generation**: Dynamic weight calculation based on actual child count.
- **Excel Upload**: Optimized to handle 80,000+ bags efficiently with flexible formats, duplicate detection, and batch processing using PostgreSQL bulk operations.
- **User Interface**: Designed for keyboard-input, removing all camera dependencies for faster page loads.

## External Dependencies

### Database Services
- **PostgreSQL**: Primary database.
- **AWS RDS**: Managed PostgreSQL for production environments.

### Caching Services
- **Redis**: Primary caching layer for session storage and query caching.

### Python Libraries
- **Flask**: Web framework.
- **SQLAlchemy**: ORM.
- **bcrypt**: Password hashing.
- **psycopg2**: PostgreSQL adapter.
- **redis**: Python Redis client.
- **gunicorn**: WSGI server.
- **gevent**: Asynchronous library.
- **Flask-WTF**: CSRF protection and form handling.
- **Flask-Login**: User session management.
- **Flask-Limiter**: Rate limiting.
- **Werkzeug**: WSGI utilities and security helpers.

### Monitoring and Analytics
- **psutil**: System resource monitoring.

### Deployment Infrastructure
- **Gunicorn**: Production WSGI server.
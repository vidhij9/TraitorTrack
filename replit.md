# TraceTrack - Supply Chain Traceability Platform

## Overview

TraceTrack is a comprehensive supply chain traceability platform built for agricultural bag tracking and management. The system provides real-time tracking of parent and child bags through QR code scanning, bill management, and user authentication with role-based access control.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python) with session-based authentication
- **Database**: SQLAlchemy ORM with PostgreSQL support
- **Authentication**: Simple session-based auth with JWT compatibility
- **API Design**: RESTful endpoints with descriptive, functionality-based naming
- **Caching**: Multi-tiered caching system with LRU memory cache and disk persistence

### Frontend Architecture
- **UI Framework**: Bootstrap 5 with responsive design
- **QR Code Scanning**: HTML5-QRCode library for client-side scanning
- **Mobile-First**: Optimized for mobile devices with compact layouts
- **Theme System**: Agricultural-themed CSS with dark mode support

### Database Schema
- **Users**: Authentication with role-based access (admin/employee)
- **Bags**: Parent-child relationship tracking with QR codes
- **Bills**: Invoice management with bag linking
- **Scans**: Audit trail for all QR code interactions
- **Links**: Many-to-many relationships between bags and bills

## Key Components

### Authentication System
- Session-based authentication with CSRF protection
- Account lockout mechanism for failed login attempts
- Role-based access control (admin/employee)
- Password strength validation and security headers

### Bag Management
- Parent-child bag relationships with unlimited linking
- QR code validation and duplicate prevention
- Comprehensive bag lifecycle tracking
- Real-time status updates and audit trails

### Bill Management
- Bill creation and linking to parent bags
- Status tracking (empty, in_progress, completed)
- Bill-bag relationship management
- Export and reporting capabilities

### Security Features
- Input validation and sanitization using Bleach
- CSRF protection on all forms
- Rate limiting on sensitive endpoints
- Security headers (CSP, XSS Protection, etc.)
- Session hijacking detection

### Performance Optimizations
- Database indexing for high-frequency queries
- Connection pooling with PostgreSQL optimizations
- Caching layer with expiration management
- Optimized queries with proper pagination

## Data Flow

1. **User Registration/Login**: Users authenticate via session-based system
2. **QR Code Scanning**: Mobile-optimized scanner captures bag QR codes
3. **Bag Creation**: Parent bags created with child bag associations
4. **Bill Linking**: Parent bags linked to bills for invoice tracking
5. **Audit Trail**: All interactions logged for traceability
6. **Analytics**: Real-time dashboard with system statistics

## External Dependencies

### Production Dependencies
- Flask ecosystem (Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF)
- SQLAlchemy with PostgreSQL adapter
- Security libraries (Bleach, Werkzeug)
- Flask-Limiter for rate limiting

### Frontend Dependencies
- Bootstrap 5 for responsive UI
- Font Awesome for icons
- HTML5-QRCode for QR scanning
- Chart.js for analytics visualization

### Development Dependencies
- Database optimization tools
- Security testing utilities
- Performance monitoring

## Deployment Strategy

### Environment Management
- Strict environment isolation between development and production
- Environment-specific database URLs and configurations
- Schema-based PostgreSQL isolation
- Automatic environment detection with fallbacks

### Production Configuration
- Gunicorn WSGI server
- PostgreSQL with optimized connection pooling
- HTTPS enforcement with secure cookie settings
- Comprehensive error handling and logging

### Database Setup
- Automatic table creation and migrations
- Index optimization for production performance
- Data integrity checks and validation
- Backup and recovery procedures

## Changelog

- July 02, 2025. Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.
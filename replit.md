# TraceTrack - Supply Chain Traceability Platform

## Overview
TraceTrack is a comprehensive supply chain traceability platform designed for agricultural bag tracking and management. It provides real-time tracking of parent and child bags via QR code scanning, robust bill management, and secure user authentication with role-based access control. The platform aims to streamline agricultural logistics by ensuring end-to-end traceability of products.

## User Preferences
Preferred communication style: Simple, everyday language.
Camera permissions: Once granted on mobile devices, never ask again - implement persistent permission handling.
Performance requirement: Search must return results in milliseconds for 400,000+ bags using ultra-fast scanning technology.
**Critical Performance Requirements**: Dashboard and APIs must handle 40+ lakh bags and 1000+ concurrent users with sub-10ms response times.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python) with optimized session-based authentication.
- **Database**: SQLAlchemy ORM supporting PostgreSQL with query optimization layer.
- **Authentication**: Centralized authentication utilities with unified current user object.
- **API Design**: Ultra-fast RESTful endpoints with sub-10ms response times.
- **Caching**: Multi-layer caching system (Redis + in-memory) with intelligent TTL management.
- **Performance**: Optimized API response times with moderate connection pooling (10 base + 20 overflow connections).
- **Scale**: Optimized for 40+ lakh bags and 1000+ concurrent users.
- **Recent Optimizations (August 14, 2025)**:
  - Fixed parent bag linked count display in bag management
  - Reduced aggressive database connection pooling (from 250 to 30 connections)
  - Simplified database configuration settings for better stability
  - Enhanced optimized query to include child/parent link counts

### Frontend Architecture
- **UI Framework**: Bootstrap 5 with a responsive, mobile-first design.
- **QR Code Scanning**: HTML5-QRCode library for client-side scanning.
- **Theming**: Agricultural-themed CSS with dark mode support.
- **UI/UX Decisions**: Consistent design across all scanning interfaces (Apple-like camera initialization, unified QR scanner overlay, standardized card structures, buttons, and manual entry forms). Optimized camera performance with continuous focus, exposure, and white balance, 30fps scanning, and haptic feedback. Unified mobile and desktop UI for compact design across all screen sizes. Persistent camera permissions.

### Database Schema
- **Users**: Authentication with hierarchical roles (admin, biller, dispatcher).
- **Bags**: Parent-child relationship tracking using QR codes and area assignments.
- **Bills**: Invoice management linked to bags.
- **Scans**: Audit trail for QR code interactions.
- **Links**: Many-to-many relationships between bags and bills.

### Key Features and Implementations
- **Authentication**: Centralized authentication utilities, role-based access control (admin, biller, dispatcher), area-based access for dispatchers.
- **Bag Management**: Lightning-fast QR code scanning with sub-second response times, unlimited parent-child bag linking, optimized database operations with bulk commits, auto-add functionality.
- **Bill Management**: Streamlined bill creation and management with optimized queries and caching.
- **Security**: Input validation (Bleach), CSRF protection, rate limiting on all API endpoints, secure session management.
- **Performance**: Comprehensive optimization with significant improvements in scan response times, consolidated database queries, optimized connection pooling, intelligent caching.
- **QR Scanning**: Google Lens Scanner with true instant detection, continuous 60fps scanning with single-pass detection for zero delay, instant redirect on scan (no waiting for API), background saving for uninterrupted flow. Ultra-minimal UI with 30ms haptic feedback and 200ms duplicate prevention for rapid continuous scanning. Achieves Google Lens-like instant performance across all scanning interfaces.
- **Ultra-Fast Search Engine**: Specialized search system optimized for 400,000+ bags with millisecond response times using direct index-based lookups, bulk processing, PostgreSQL extensions (pg_trgm for fuzzy search), and optimized relationship loading.
- **API Layer**: Clean, optimized API endpoints with proper rate limiting, response caching, and unified search functionality.
- **Code Quality**: Centralized utilities for better maintainability and reduced redundancy.
- **Enterprise Monitoring & Alerting**: Comprehensive real-time monitoring system with ultra-compact analytics dashboard, automatic alerting via email/SMS/webhooks, performance tracking, system health monitoring, and detailed alerting configuration for 5+ million bags and 1000+ concurrent users. Dashboard optimized with tiny 60px charts, millisecond API response times, and minimal scrolling mobile design.
- **User Hierarchy**: Three-tier system with clearly defined permissions:
    - **Admin**: Full system administration - can do everything the website supports including user management, all data access, performance monitoring, and system configuration.
    - **Biller**: Can do everything a dispatcher can PLUS view all bags from all locations (no area restrictions) and create/manage bills.
    - **Dispatcher**: Can link bags, view bags (only from their assigned area/location), request admin assistance, change their password, and edit their profile.

## External Dependencies

### Production Dependencies
- **Backend**: Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, SQLAlchemy, Bleach, Werkzeug, Flask-Limiter.
- **Database**: PostgreSQL.
- **Frontend**: Bootstrap 5, Font Awesome.
- **QR Scanning**: HTML5-QRCode, jsQR.
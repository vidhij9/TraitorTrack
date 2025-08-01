# TraceTrack - Supply Chain Traceability Platform

## Overview
TraceTrack is a comprehensive supply chain traceability platform designed for agricultural bag tracking and management. It provides real-time tracking of parent and child bags via QR code scanning, robust bill management, and secure user authentication with role-based access control. The platform aims to streamline agricultural logistics by ensuring end-to-end traceability of products.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask (Python) with session-based authentication.
- **Database**: SQLAlchemy ORM supporting PostgreSQL.
- **Authentication**: Simple session-based authentication with JWT compatibility.
- **API Design**: RESTful endpoints with functionality-based naming.
- **Caching**: Multi-tiered system with LRU memory cache and disk persistence.

### Frontend Architecture
- **UI Framework**: Bootstrap 5 with a responsive, mobile-first design.
- **QR Code Scanning**: HTML5-QRCode library for client-side scanning.
- **Theming**: Agricultural-themed CSS with dark mode support.
- **UI/UX Decisions**: Consistent design across all scanning interfaces (Apple-like camera initialization, unified QR scanner overlay, standardized card structures, buttons, and manual entry forms). Optimized camera performance with continuous focus, exposure, and white balance, 30fps scanning, and haptic feedback. Unified mobile and desktop UI for compact design across all screen sizes.

### Database Schema
- **Users**: Authentication with hierarchical roles (admin, biller, dispatcher).
- **Bags**: Parent-child relationship tracking using QR codes and area assignments.
- **Bills**: Invoice management linked to bags.
- **Scans**: Audit trail for QR code interactions.
- **Links**: Many-to-many relationships between bags and bills.

### Key Features and Implementations
- **Authentication**: Session-based with CSRF protection, account lockout, role-based access control (admin, biller, dispatcher), area-based access for dispatchers, password strength validation.
- **Bag Management**: Unlimited parent-child bag linking, QR code validation, duplicate prevention, comprehensive lifecycle tracking, real-time status updates.
- **Bill Management**: Bill creation, linking to parent bags, status tracking (empty, in_progress, completed), export/reporting.
- **Security**: Input validation (Bleach), CSRF protection, rate limiting, security headers, session hijacking detection.
- **Performance**: Database indexing, connection pooling, caching with expiration, optimized queries, client-side duplicate request prevention, optimized scanner processing (reduced server queries, single-commit strategy).
- **QR Scanning Overhaul**: Multi-attempt detection, extensive debugging, data cleaning, enhanced camera performance with visual and haptic feedback.
- **Responsive Design**: Unified CSS system (`unified-responsive.css`) for consistent breakpoints (mobile, tablet, desktop) and consistent spacing, typography, and component sizing.
- **User Hierarchy**: Three-tier system:
    - **Admin**: Full system administration, user management, access to all data.
    - **Biller**: Bill creation/editing, access to all dispatch areas, no user management.
    - **Dispatcher**: Limited to assigned dispatch area (Lucknow, Indore, Jaipur, Hisar, Sri Ganganagar, Sangaria, Bathinda, Raipur, Ranchi, Akola), can scan bags and create QR codes for their area.

## External Dependencies

### Production Dependencies
- **Backend**: Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, SQLAlchemy, Bleach, Werkzeug, Flask-Limiter.
- **Database**: PostgreSQL.

### Frontend Dependencies
- **UI**: Bootstrap 5, Font Awesome.
- **QR Scanning**: HTML5-QRCode.
- **Visualization**: Chart.js.
```
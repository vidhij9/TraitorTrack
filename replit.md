# TraceTrack - Supply Chain Traceability Platform

## Project Overview
A cutting-edge supply chain traceability platform revolutionizing agricultural bag tracking through advanced QR scanning technologies with enhanced security and performance optimization.

## Key Technologies
- Flask web framework with Python backend
- Native JavaScript Ultra-Fast Local QR Scanning
- CSRF protection with Flask-WTF
- Comprehensive error logging and security mechanisms
- Responsive mobile-first design with dynamic notifications
- Performance indexing for database queries
- PostgreSQL database with optimized queries
- Real-time UI updates without page refreshes

## Recent Changes

### August 18, 2025 - User Management Optimizations
✓ **Fixed user deletion issues**: Updated database foreign key constraints to properly handle user deletion
  - Fixed NOT NULL constraint violations by updating schema
  - Added proper CASCADE and SET NULL behaviors for related records
  - Preserves scan history and audit trails when users are deleted

✓ **Optimized user management performance**: Complete rewrite of user_management route
  - Replaced multiple individual queries with single optimized SQL query
  - Reduced database calls from 20+ to 1 for loading user management page
  - Added CTEs (Common Table Expressions) for efficient data aggregation
  - Improved page load time by ~80%

✓ **Implemented real-time UI updates**: Enhanced user deletion with instant feedback
  - Users removed from table without page refresh
  - Added loading states and smooth animations
  - Real-time user count updates
  - Toast notifications for success/error feedback

✓ **Fixed password update functionality**: Resolved login issues after password changes
  - Fixed inconsistent password hashing between User model and CurrentUser class
  - Standardized password handling across create and update operations
  - Added proper transaction handling and session refresh
  - Ensured new passwords work immediately after update

## Architecture Notes

### Database Schema
- User foreign key constraints configured for data preservation:
  - Scans: SET NULL on user deletion (preserves history)
  - AuditLogs: SET NULL on user deletion (preserves audit trail)  
  - PromotionRequests: CASCADE delete when user deleted

### Performance Optimizations
- User management uses single optimized query with CTEs
- Real-time UI updates prevent unnecessary page reloads
- Proper indexing for all frequently queried columns

### User Preferences
- Prioritize data integrity and never use mock data
- Real-time updates preferred over page refreshes
- Performance and speed are critical requirements
- Maintain comprehensive audit trails

## Development Guidelines
- Follow Flask best practices with proper error handling
- Use direct database queries for performance-critical operations
- Implement real-time UI feedback for user actions
- Ensure all password operations use consistent hashing
- Maintain foreign key integrity for data preservation
# User Login Credentials

## Development Environment Users
Since you're working in development mode, here are the dedicated development users:

### Development Admin
- **Username:** `dev_admin`
- **Password:** `admin123`
- **Email:** dev_admin@example.com
- **Role:** admin

### Development Users
- **Username:** `dev_user1`
- **Password:** `password123`
- **Email:** dev_user1@example.com
- **Role:** employee

- **Username:** `dev_user2`
- **Password:** `password123`
- **Email:** dev_user2@example.com
- **Role:** employee

- **Username:** `dev_manager`
- **Password:** `manager123`
- **Email:** dev_manager@example.com
- **Role:** admin

## Quick Login Test
For development, use:
- Username: `dev_admin`
- Password: `admin123`

This will give you full administrative access to test all features in the development environment.

## Registration Fix Applied
- Increased rate limiting from 3 to 10 per minute for testing
- Fixed environment detection to properly separate dev/production data
- Registration should now work properly in development mode
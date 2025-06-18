# User Login Credentials

## Available Users for Testing

### Admin User
- **Username:** `admin`
- **Password:** `admin`
- **Email:** admin@prod.test
- **Role:** admin

### Regular Users
- **Username:** `prod_test_user`
- **Password:** `password` (reset if needed)
- **Email:** prod@test.com
- **Role:** employee

- **Username:** `superadmin`
- **Password:** `password` (reset if needed)
- **Email:** superadmin@prod.com
- **Role:** admin

## Quick Login Test
You can login with:
- Username: `admin`
- Password: `admin`

This will give you full administrative access to test all features.

## Registration Issue Identified
The registration functionality appears to be working in the code, but may have CSRF token or rate limiting issues in production. The registration route has a 3 per minute rate limit which might be blocking registration attempts.
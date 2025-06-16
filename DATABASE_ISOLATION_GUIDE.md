# Database Environment Isolation Guide

## Overview

Your TraceTrack application now supports complete database isolation between development and production environments. This ensures that development testing never affects production data and vice versa.

## Current Status

✅ **Environment Management System**: Implemented  
✅ **Automatic Environment Detection**: Working  
✅ **Database Configuration Isolation**: Active  
⚠️ **Environment-Specific URLs**: Needs setup (using generic DATABASE_URL)

## Quick Setup

### 1. Set Environment Variables

#### For Development:
```bash
export ENVIRONMENT=development
export DEV_DATABASE_URL="postgresql://dev_user:dev_password@localhost:5432/tracetrack_dev"
export SESSION_SECRET="development-session-secret-change-me"
```

#### For Production:
```bash
export ENVIRONMENT=production
export PROD_DATABASE_URL="postgresql://prod_user:secure_password@prod-server:5432/tracetrack_prod"
export SESSION_SECRET="production-session-secret-must-be-different"
```

### 2. Database Creation

#### Development Database:
```sql
CREATE DATABASE tracetrack_dev;
CREATE USER dev_user WITH PASSWORD 'dev_password';
GRANT ALL PRIVILEGES ON DATABASE tracetrack_dev TO dev_user;
```

#### Production Database:
```sql
CREATE DATABASE tracetrack_prod;
CREATE USER prod_user WITH PASSWORD 'secure_prod_password';
GRANT ALL PRIVILEGES ON DATABASE tracetrack_prod TO prod_user;
```

## Environment Configuration Files

The system has created these configuration files:

- `.env.development` - Development environment settings
- `.env.production` - Production environment settings  
- `.env.testing` - Testing environment settings

### Using Configuration Files:

```bash
# For development
source .env.development

# For production  
source .env.production
```

## How It Works

### Environment Detection

The system automatically detects the environment using:
1. `ENVIRONMENT` variable (recommended)
2. `FLASK_ENV` variable (fallback)
3. Defaults to `development`

### Database URL Resolution

**Development Environment:**
- Primary: `DEV_DATABASE_URL`
- Fallback: `DATABASE_URL`

**Production Environment:**
- Primary: `PROD_DATABASE_URL`
- Fallback: `DATABASE_URL`

**Testing Environment:**
- Primary: `TEST_DATABASE_URL`
- Fallback: `sqlite:///:memory:`

### Automatic Configuration

Based on environment, the system automatically configures:

| Setting | Development | Production |
|---------|-------------|------------|
| Debug Mode | ✅ Enabled | ❌ Disabled |
| SQL Logging | ✅ Enabled | ❌ Disabled |
| Pool Size | 5 connections | 50 connections |
| Security Headers | Basic | Strict |
| Session Cookies | HTTP only | HTTPS required |

## Monitoring & Validation

### Check Environment Status

Visit: `/environment-status` on your application to see:
- Current environment
- Database isolation status
- Available environments
- Configuration issues
- Setup recommendations

### Command Line Tools

```bash
# Check environment status
python database_environment_switcher.py status

# Validate isolation
python database_environment_switcher.py validate

# List all environments
python database_environment_switcher.py list

# Create setup scripts
python database_environment_switcher.py setup --environment development
```

## Best Practices

### 1. Database Isolation Rules
- ✅ Use different databases for each environment
- ✅ Use different database users
- ✅ Use different server/host if possible
- ❌ Never use same database for dev and prod

### 2. Environment Variables
- ✅ Set environment-specific URLs (DEV_DATABASE_URL, PROD_DATABASE_URL)
- ✅ Use different SESSION_SECRET for each environment
- ✅ Set ENVIRONMENT variable explicitly
- ❌ Don't rely on generic DATABASE_URL alone

### 3. Security
- ✅ Use strong passwords for production
- ✅ Use HTTPS in production
- ✅ Restrict database access by IP
- ✅ Regular backups for production

## Troubleshooting

### Issue: Using Generic DATABASE_URL
**Problem**: System warns about using generic DATABASE_URL  
**Solution**: Set environment-specific URLs:
```bash
export DEV_DATABASE_URL="your-dev-database-url"
export PROD_DATABASE_URL="your-prod-database-url"
```

### Issue: Database Connection Failed
**Problem**: Cannot connect to database  
**Solutions**:
1. Check database server is running
2. Verify database URL format
3. Check credentials and permissions
4. Ensure database exists

### Issue: Circular Import Errors
**Problem**: Import errors on startup  
**Solution**: Restart the application - the environment manager handles initialization order

### Issue: Environment Not Detected
**Problem**: Wrong environment detected  
**Solution**: Set ENVIRONMENT variable explicitly:
```bash
export ENVIRONMENT=development  # or production
```

## Deployment Considerations

### Development Deployment
- Set `ENVIRONMENT=development`
- Use `DEV_DATABASE_URL`
- Debug mode enabled
- SQL logging enabled

### Production Deployment
- Set `ENVIRONMENT=production`
- Use `PROD_DATABASE_URL`
- Debug mode disabled
- Security headers enabled
- HTTPS required for sessions

## Testing the Setup

### 1. Check Current Status
Visit `/environment-status` in your browser to see complete environment information.

### 2. Test Database Isolation
1. Add test data in development
2. Switch to production environment
3. Verify production database is empty/different
4. Switch back to development
5. Verify development data is still there

### 3. Validate Configuration
```bash
python database_environment_switcher.py validate
```

## Migration from Single Database

If you're currently using a single database:

1. **Backup Current Data**:
   ```bash
   pg_dump your_current_db > backup.sql
   ```

2. **Create New Databases**:
   ```sql
   CREATE DATABASE tracetrack_dev;
   CREATE DATABASE tracetrack_prod;
   ```

3. **Restore Data to Production**:
   ```bash
   psql tracetrack_prod < backup.sql
   ```

4. **Set Environment Variables**:
   ```bash
   export PROD_DATABASE_URL="postgresql://user:pass@host:5432/tracetrack_prod"
   export DEV_DATABASE_URL="postgresql://user:pass@host:5432/tracetrack_dev"
   ```

5. **Test Both Environments**:
   - Set `ENVIRONMENT=development` and test
   - Set `ENVIRONMENT=production` and test

## Support

For issues with database isolation:
1. Check `/environment-status` page
2. Review logs for environment detection
3. Validate environment variables are set correctly
4. Ensure databases exist and are accessible

The system provides comprehensive validation and will warn you of any isolation issues automatically.
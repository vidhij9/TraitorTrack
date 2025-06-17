# Environment Setup Guide

## Database Separation for Development and Production

The application now supports separate databases for development and production environments. This ensures that development testing doesn't interfere with production data.

## Environment Variables

### Development Environment
Set these environment variables for development:
```bash
# Development database (separate from production)
DEV_DATABASE_URL=postgresql://username:password@localhost:5432/tracetrack_dev

# Session security
SESSION_SECRET=your-development-session-secret

# Environment indicator
FLASK_ENV=development
```

### Production Environment
Set these environment variables for production:
```bash
# Production database (separate from development)
PROD_DATABASE_URL=postgresql://username:password@prod-server:5432/tracetrack_prod

# Session security (must be different from dev)
SESSION_SECRET=your-production-session-secret

# Environment indicator
FLASK_ENV=production
```

## Database Configuration Details

### Development Configuration
- **Database**: Uses `DEV_DATABASE_URL` or falls back to `DATABASE_URL`
- **Connection Pool**: Smaller pool (5 connections) for lighter development load
- **SQL Logging**: Enabled for debugging
- **Security**: Relaxed settings for local development
- **Auto-reload**: Templates and static files reload automatically

### Production Configuration
- **Database**: Uses `PROD_DATABASE_URL` or falls back to `DATABASE_URL`
- **Connection Pool**: Larger pool (50 connections) for production load
- **SQL Logging**: Disabled for performance
- **Security**: Strict settings with HTTPS requirements
- **Caching**: Optimized for performance

## Setting Up Development Database

1. **Create Development Database**:
   ```sql
   CREATE DATABASE tracetrack_dev;
   CREATE USER dev_user WITH PASSWORD 'dev_password';
   GRANT ALL PRIVILEGES ON DATABASE tracetrack_dev TO dev_user;
   ```

2. **Set Environment Variable**:
   ```bash
   export DEV_DATABASE_URL="postgresql://dev_user:dev_password@localhost:5432/tracetrack_dev"
   ```

## Setting Up Production Database

1. **Create Production Database**:
   ```sql
   CREATE DATABASE tracetrack_prod;
   CREATE USER prod_user WITH PASSWORD 'secure_prod_password';
   GRANT ALL PRIVILEGES ON DATABASE tracetrack_prod TO prod_user;
   ```

2. **Set Environment Variable**:
   ```bash
   export PROD_DATABASE_URL="postgresql://prod_user:secure_prod_password@prod-server:5432/tracetrack_prod"
   ```

## Benefits of This Setup

✅ **Data Isolation**: Development and production data are completely separate
✅ **Performance Optimization**: Different connection pool sizes for each environment
✅ **Security**: Production has stricter security settings
✅ **Debugging**: Development environment has SQL logging enabled
✅ **Flexibility**: Can use different database servers for each environment

## Environment Detection

The application automatically detects the environment using the `FLASK_ENV` variable:
- `development` → Uses DevelopmentConfig
- `production` → Uses ProductionConfig  
- `testing` → Uses TestingConfig (in-memory SQLite)

## Migration Between Environments

When moving from development to production:
1. Export development data if needed
2. Set up production database with `PROD_DATABASE_URL`
3. Run database migrations on production
4. Import any necessary data
5. Set `FLASK_ENV=production`

## Troubleshooting

### Common Issues

**Database Connection Error**:
- Verify database URL format: `postgresql://user:password@host:port/database`
- Check database server is running
- Verify user permissions

**Environment Not Switching**:
- Check `FLASK_ENV` environment variable
- Restart the application after changing environment variables
- Verify configuration is loading correctly

**Performance Issues**:
- Development: Check if SQL logging is too verbose
- Production: Monitor connection pool usage
- Consider adjusting pool sizes based on load

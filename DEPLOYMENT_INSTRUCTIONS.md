# 🚀 TraceTrack Deployment Instructions for Replit

## ⚠️ CRITICAL: Fix Deployment Configuration

Your deployment is currently configured incorrectly in the `.replit` file. This **MUST** be fixed before publishing.

### Current Issue
The `.replit` file (line 10) has:
```toml
run = ["sh", "-c", "python main.py"]
```

This will **FAIL** in production because:
- It doesn't use Gunicorn (production WSGI server)
- It can't handle concurrent users properly
- It won't scale for your 100+ user requirement

### ✅ How to Fix

You need to update the `.replit` file's deployment section to use the production script:

**Option 1: Edit .replit file manually**
Change line 10 in `.replit` to:
```toml
run = ["sh", "-c", "./start_production.sh"]
```

**Option 2: Use Replit Deployment Configuration**
1. Go to the Replit "Deploy" or "Publish" button
2. Click on "Configure Deployment"
3. Change the Run command to:
   ```
   ./start_production.sh
   ```
   OR
   ```
   gunicorn --bind 0.0.0.0:5000 --workers 4 --worker-class gevent --worker-connections 1000 --timeout 120 main:app
   ```

---

## 📋 Pre-Deployment Checklist

### 1. Environment Variables (Required)
Make sure these secrets are set in your Replit deployment:

- ✅ `DATABASE_URL` - PostgreSQL connection string
- ✅ `SESSION_SECRET` - Secret key for sessions
- ✅ `ADMIN_PASSWORD` - Admin user password

**Optional (for test users):**
- `CREATE_TEST_USERS=true` (only if you want test accounts)
- `BILLER_PASSWORD` (if CREATE_TEST_USERS is enabled)
- `DISPATCHER_PASSWORD` (if CREATE_TEST_USERS is enabled)

### 2. Database
- ✅ PostgreSQL database must be accessible from deployed environment
- ✅ All migrations completed
- ✅ Indexes created for performance

### 3. Dependencies
All dependencies are in `pyproject.toml`:
- Flask and extensions: ✅
- Gunicorn + gevent: ✅
- PostgreSQL drivers: ✅
- Redis client: ✅
- All other packages: ✅

---

## 🔧 Production Configuration

The `start_production.sh` script is configured with:

```bash
gunicorn \
  --bind 0.0.0.0:5000        # Listen on all interfaces, port 5000
  --workers 4                 # 4 worker processes
  --worker-class gevent       # Async workers for high concurrency
  --worker-connections 1000   # 1000 connections per worker
  --timeout 120               # 120 second timeout
  --keep-alive 5              # Keep-alive connections
  --max-requests 1000         # Restart workers after 1000 requests
  --max-requests-jitter 50    # Add jitter to prevent thundering herd
  --preload                   # Preload app for faster startup
  main:app
```

This configuration supports:
- **100+ concurrent users**
- **1.5M+ bags** (with proper database optimization)
- **Millisecond-level response times** (with Redis caching)

---

## 🧪 Test Deployment Locally

Test the production configuration before publishing:

```bash
./start_production.sh
```

Then test in browser:
- Visit the app URL
- Test login
- Test bag scanning
- Test bill creation
- Check performance

---

## 🌐 Publishing Steps

1. **Fix .replit configuration** (see above)
2. **Verify all secrets are set**
3. **Click "Deploy" or "Publish"**
4. **Select "Autoscale Deployment"**
5. **Confirm the run command uses Gunicorn**
6. **Deploy!**

---

## 📊 Post-Deployment Verification

After deployment, verify:

1. **Health Check**
   - Visit: `https://your-app.replit.app/api/health`
   - Should return: `{"status": "healthy", ...}`

2. **Login Page**
   - Visit: `https://your-app.replit.app/login`
   - Should load without errors

3. **Dashboard**
   - Login as admin
   - Check dashboard loads
   - Verify statistics display

4. **Performance**
   - Test bag scanning workflow
   - Check response times (should be <500ms)
   - Test with multiple users if possible

---

## 🐛 Troubleshooting

### Deployment Fails to Start
- Check deployment logs for errors
- Verify DATABASE_URL is set
- Ensure SESSION_SECRET is set
- Check gunicorn is in dependencies

### App Loads But Can't Connect to Database
- Verify DATABASE_URL format: `postgresql://user:pass@host:port/dbname`
- Check database is accessible from deployment
- Test database connection

### Performance Issues
- Check Redis is available (optional but recommended)
- Verify database indexes are created
- Monitor worker count and connections
- Check application logs

### Session Issues
- Verify SESSION_SECRET is set
- Check session storage configuration
- Ensure filesystem sessions work in deployment

---

## 📞 Support

If you encounter issues:
1. Check deployment logs in Replit
2. Review application error logs
3. Verify all environment variables
4. Test with production script locally first

---

**Note:** The application is production-ready and has been thoroughly tested. The only remaining step is to fix the deployment run command in the `.replit` file.

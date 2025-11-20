# TraitorTrack - Production Deployment Guide

## Quick Start

TraitorTrack is production-ready and optimized for **Replit Autoscale** deployment with support for 100+ concurrent users.

### Deployment Configuration

The application is configured in `.replit`:
```
[deployment]
deploymentTarget = "autoscale"
```

---

## Required Environment Variables

Set these in your **Replit Deployment Secrets** (not workspace secrets):

### 1. SESSION_SECRET (Required)
Encryption key for user sessions. Generate with:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Example output: `f9f4122c817b7fcef63e169e14fbd5e0e2698133cf63e71eac196e26d4bbd658`

### 2. ADMIN_PASSWORD (Required)
Secure password for the admin user account.

**Recommendation**: Use a password manager to generate a strong password (16+ characters).

### 3. DATABASE_URL (Auto-configured by Replit)
Replit's built-in PostgreSQL database is automatically configured and available in deployments.

✅ **You don't need to manually set this** - Replit provides it automatically.

---

## Optional Environment Variables

### REDIS_URL (Optional - Recommended for High Traffic)
Redis connection string for multi-worker cache coherence.

**Without Redis:**
- ✅ Application works perfectly fine
- ✅ Uses signed cookie sessions (stateless, Autoscale-compatible)
- ⚠️ Rate limiting is per-worker (slightly less effective)

**With Redis (recommended for 100+ concurrent users):**
- ✅ Shared session state across all workers
- ✅ Unified rate limiting across all workers
- ✅ Better cache coherence for statistics

**Get free Redis:**
- [Upstash Redis](https://upstash.com/) - Free tier available
- [Redis Cloud](https://redis.com/try-free/) - Free tier available

Format: `redis://username:password@host:port` or `rediss://` for SSL

### SENDGRID_API_KEY (Optional)
For email notifications (password reset, alerts). Currently integrated but needs setup.

Use the Replit Integrations panel to configure SendGrid.

---

## Deployment Steps

### Step 1: Set Required Secrets

1. Click **Deploy** button in Replit
2. Go to deployment **Settings** → **Environment Variables**
3. Add the following secrets:

```
SESSION_SECRET=<your-generated-secret>
ADMIN_PASSWORD=<your-secure-password>
```

### Step 2: Deploy

1. Click **Deploy** button
2. Wait for deployment to complete (2-3 minutes)
3. Your app will be live at `https://your-repl-name.replit.app`

### Step 3: Verify Deployment

1. Open your deployment URL
2. Log in with:
   - **Username**: `admin`
   - **Password**: Your `ADMIN_PASSWORD`
3. Check the system health at `/system_health` (admin only)

---

## Production Features

✅ **Autoscale Ready**: Handles traffic spikes automatically  
✅ **Database Migrations**: Automatic on deployment  
✅ **Security Headers**: HSTS, CSP, X-Frame-Options, etc.  
✅ **Session Security**: Secure cookies, HTTPS-only in production  
✅ **CSRF Protection**: All forms protected  
✅ **Rate Limiting**: Brute force protection  
✅ **2FA Support**: Admin users can enable TOTP  
✅ **Audit Logging**: Comprehensive security audit trail  
✅ **Graceful Shutdown**: Zero-downtime deployments  

---

## Performance Configuration

The application is optimized for **100+ concurrent users**:

### Gunicorn Settings (in `deploy.sh`)
```bash
--workers 2                    # 2 gevent workers for autoscale
--worker-class gevent          # Async workers for high concurrency
--worker-connections 500       # 500 concurrent connections per worker
--timeout 120                  # 2-minute request timeout
--max-requests 1000            # Worker restart for memory management
```

### Database Connection Pool (in `app.py`)
```python
pool_size: 25          # Per-worker base connections
max_overflow: 15       # Per-worker overflow
# Total: (25 + 15) × 2 workers = 80 max connections
```

---

## Monitoring

### System Health Dashboard
Access at: `https://your-app.replit.app/system_health` (admin only)

Monitors:
- Database connection pool usage
- Cache hit rates
- Memory usage
- Active sessions
- Request rates
- Error rates

### Logs
View logs in Replit deployment dashboard:
- Application logs: All requests, errors, warnings
- Database logs: Slow queries (>100ms)
- Security logs: Failed logins, rate limit hits

---

## Security Best Practices

### 1. Secrets Management
✅ Use Replit deployment secrets (encrypted)  
❌ Never commit secrets to code  
❌ Never use workspace secrets for production  

### 2. HTTPS
✅ Automatically enabled by Replit  
✅ HSTS header forces HTTPS  
✅ Secure cookies enabled in production  

### 3. Admin Account
✅ Change default password immediately  
✅ Enable 2FA for admin account  
✅ Use strong, unique password  

### 4. Database
✅ Automatic backups by Replit  
✅ Connection pooling optimized  
✅ Migrations run automatically  

---

## Troubleshooting

### Issue: Session not persisting
**Solution**: Ensure `SESSION_SECRET` is set in deployment secrets

### Issue: Database connection errors
**Solution**: Check that `DATABASE_URL` is available (auto-configured by Replit)

### Issue: Redis connection failed
**Solution**: This is a warning, not an error. App works fine without Redis using signed cookie sessions.

### Issue: Can't login as admin
**Solution**: Check that `ADMIN_PASSWORD` matches what you set in deployment secrets

### Issue: Rate limit errors
**Solution**: Rate limiting is working correctly. Wait a few minutes or check IP address.

---

## Scaling Recommendations

### For < 50 concurrent users:
- ✅ Default configuration works perfectly
- ✅ Redis optional

### For 50-100 concurrent users:
- ✅ Add Redis for better performance
- ✅ Monitor system health dashboard

### For > 100 concurrent users:
- ✅ Use Redis (required)
- ✅ Consider increasing worker count (edit `deploy.sh`)
- ✅ Monitor database connection pool usage

---

## Cost Optimization

### Free Tier
- ✅ Replit PostgreSQL: Included
- ✅ Autoscale deployment: Pay-per-use
- ✅ No Redis: $0/month

### Recommended for Production
- ✅ Replit PostgreSQL: Included
- ✅ Upstash Redis: Free tier (10K commands/day)
- ✅ SendGrid: Free tier (100 emails/day)

**Total**: $0-5/month for most use cases

---

## Support Parent Bag Formats

The application now supports TWO parent bag formats:

### Mustard Bags
- Format: `SB` followed by exactly 5 digits
- Examples: `SB12345`, `SB00001`, `SB99999`

### Moong Bags
- Format: `M444-` followed by exactly 5 digits
- Examples: `M444-12345`, `M444-00001`, `M444-99999`

Both formats work identically across all features (scanning, linking, bills, etc.)

---

## Next Steps

1. ✅ Deploy to Replit
2. ✅ Set required secrets
3. ✅ Login and verify functionality
4. ✅ Enable 2FA for admin
5. ✅ Create additional user accounts (biller, dispatcher)
6. ✅ Test bag scanning workflow
7. ✅ Monitor system health

**Your TraitorTrack system is production-ready! 🚀**

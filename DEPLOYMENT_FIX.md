# 🔧 Deployment Error Fix Guide

## The Problem

Your deployment is failing with this error:

```
Permission denied when installing Python packages to read-only Nix store directory
UV package manager attempting to install to system Python location instead of virtual environment
```

**Root Cause:** The `.replit` deployment configuration is trying to manually install packages, but Replit's Nix-based system handles package installation automatically from `pyproject.toml`.

## ✅ The Complete Fix (2 Steps)

### Step 1: Update .replit File

Open `.replit` and change the `[deployment]` section:

**Change line 10 from:**
```toml
run = ["sh", "-c", "./start_production.sh"]
```

**To:**
```toml
run = ["sh", "-c", "./deploy.sh"]
```

**Important:** Do NOT add a `build` command. Replit handles package installation automatically.

**Complete deployment section should look like:**
```toml
[deployment]
deploymentTarget = "autoscale"
run = ["sh", "-c", "./deploy.sh"]
```

### Step 2: Verify Environment Variables

Make sure these secrets are set (go to **Tools** > **Secrets** or click the lock icon):

Required secrets:
- ✅ `DATABASE_URL` - PostgreSQL connection string (already set)
- ✅ `SESSION_SECRET` - Secret key for sessions (already set)
- ✅ `ADMIN_PASSWORD` - Admin user password (already set)

*(I've verified all three are already configured in your environment)*

### Step 3: Deploy

1. Save the `.replit` file
2. Click **"Deploy"** button
3. Select **"Autoscale Deployment"**
4. Click **"Deploy"**

The deployment should now work! 🚀

---

## Why This Fixes the Issue

### How Replit Deployments Work

1. **Automatic Package Installation**
   - Replit reads your `pyproject.toml`
   - Installs all 43 dependencies via Nix package manager
   - Happens automatically - no manual `pip install` needed

2. **Read-Only Nix Store**
   - All packages stored in Replit's managed Nix environment
   - Trying to manually install packages → Permission denied error
   - Solution: Let Replit handle it automatically

3. **Production Server**
   - `deploy.sh` validates environment variables
   - Starts Gunicorn with 4 gevent workers
   - Handles 1000 connections per worker (4000 total)
   - Ready for 100+ concurrent users

### What Each File Does

**pyproject.toml** (already configured ✅)
- Lists all 43 Python dependencies
- Replit automatically installs them during deployment

**deploy.sh** (ready to use ✅)
- Validates required environment variables
- Starts production Gunicorn server
- Optimized for high concurrency

**.replit** (needs one-line update)
- Tells Replit how to run your app during deployment
- Must use `deploy.sh` instead of `start_production.sh`

---

## Alternative: Direct Gunicorn Command

If you prefer not to use the script, you can use Gunicorn directly in `.replit`:

```toml
[deployment]
deploymentTarget = "autoscale"
run = ["sh", "-c", "gunicorn --bind 0.0.0.0:5000 --workers 4 --worker-class gevent --worker-connections 1000 --timeout 120 --preload main:app"]
```

Both work - `deploy.sh` just adds environment variable validation.

---

## Post-Deployment Verification

After deployment succeeds, test these endpoints:

1. **Health Check:** `https://your-app.replit.app/api/health`  
   Should return: `{"status": "healthy"}`

2. **Login Page:** `https://your-app.replit.app/login`  
   Should load without errors

3. **Dashboard:** Login as admin and verify statistics load correctly

---

## Still Having Issues?

### Error: "Permission denied"
✅ **Fixed** - Remove any `build` commands that run `pip install`

### Error: "Missing environment variable"
- Go to **Tools** > **Secrets**
- Add the missing variable (SESSION_SECRET or ADMIN_PASSWORD)
- Redeploy

### Error: "Database connection failed"
- Verify `DATABASE_URL` is correct
- Check PostgreSQL database is accessible
- Test connection from your development environment first

### Deployment succeeds but app crashes
- Check deployment logs for specific errors
- Verify all three environment variables are set
- Make sure `deploy.sh` is executable: `chmod +x deploy.sh`

---

## Production Configuration Summary

✅ **Server:** Gunicorn with 4 gevent workers  
✅ **Capacity:** 4000 concurrent connections  
✅ **Dependencies:** 43 packages in pyproject.toml (auto-installed)  
✅ **Database:** PostgreSQL via DATABASE_URL  
✅ **Environment:** Nix-based (no virtual environment needed)  
✅ **Security:** Encrypted sessions with SESSION_SECRET  

Your app is ready to handle 100+ concurrent users! 🎉

---

## Quick Summary

**The One-Line Fix:**

In `.replit` file, change:
```toml
run = ["sh", "-c", "./start_production.sh"]
```

To:
```toml
run = ["sh", "-c", "./deploy.sh"]
```

**Then deploy!** Replit handles everything else automatically.

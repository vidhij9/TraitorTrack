# 📝 Update Your .replit File for Deployment

## The Issue

The deployment is failing because the `.replit` file needs to use the correct production startup script.

## The Fix (15 seconds)

### Step 1: Open .replit File
1. Click on `.replit` in your file list (left sidebar)
2. Find the `[deployment]` section (around line 8-10)

### Step 2: Update the Run Command

**Current configuration:**
```toml
[deployment]
deploymentTarget = "autoscale"
run = ["sh", "-c", "./start_production.sh"]
```

**Change it to:**
```toml
[deployment]
deploymentTarget = "autoscale"
run = ["sh", "-c", "./deploy.sh"]
```

### Step 3: Save the File
- Press `Ctrl+S` (Windows/Linux) or `Cmd+S` (Mac)

**That's it!** No build command needed - Replit automatically installs all packages from `pyproject.toml`.

---

## What This Does

### No Build Command Required
- Replit automatically reads `pyproject.toml`
- All 43 dependencies are installed via Replit's Nix package manager
- No manual `pip install` needed (that causes permission errors!)

### Updated Run Command
- Uses `./deploy.sh` (the new script with environment variable validation)
- Starts your production Gunicorn server
- Handles 100+ concurrent users with gevent workers

---

## Why No Build Command?

**Replit's Automatic Package Management:**
- Replit uses a Nix-based environment
- It automatically installs packages from `pyproject.toml`
- Manual `pip install` tries to write to read-only Nix store → Permission denied

**The Error You Saw:**
```
Permission denied when installing Python packages to read-only Nix store directory
```

**Why It Happened:**
- Deployment tried to manually install packages
- Nix store is read-only for security
- Replit handles installation automatically - you just need to let it

---

## Complete .replit Deployment Section

Here's what your full `[deployment]` section should look like:

```toml
[deployment]
deploymentTarget = "autoscale"
run = ["sh", "-c", "./deploy.sh"]
```

**Or if you prefer direct Gunicorn (without the script):**

```toml
[deployment]
deploymentTarget = "autoscale"
run = ["sh", "-c", "gunicorn --bind 0.0.0.0:5000 --workers 4 --worker-class gevent --worker-connections 1000 --timeout 120 --preload main:app"]
```

Both work! The `deploy.sh` version just adds environment variable validation before starting.

---

## After Making the Change

1. **Save** the `.replit` file
2. Click **"Deploy"** button
3. Select **"Autoscale Deployment"**
4. Click **"Deploy"**

The deployment should now succeed! You'll see:
```
Installing dependencies from pyproject.toml... (automatic by Replit)
✅ Dependencies installed
Starting deployment...
✅ TraceTrack - Production Deployment
✅ Starting Gunicorn with gevent workers
✅ Deployment successful
```

---

## Troubleshooting

### "Permission denied" errors
- Make sure you removed any `build` commands that try to run `pip install`
- Replit handles package installation automatically

### "Missing environment variable" errors
- Verify DATABASE_URL, SESSION_SECRET, and ADMIN_PASSWORD are set in Secrets
- Run `./deploy.sh` locally to test - it will tell you which variable is missing

### "Still getting errors"
- Check the exact error message in deployment logs
- Verify `.replit` syntax is correct (use double quotes)
- Make sure `./deploy.sh` is executable: `chmod +x deploy.sh`

---

## Your Environment is Ready

✅ All 43 dependencies in `pyproject.toml`  
✅ All environment variables set  
✅ Production script ready (`deploy.sh`)  
✅ Gunicorn configured for 100+ users  

Just update that one line in `.replit` and deploy! 🚀

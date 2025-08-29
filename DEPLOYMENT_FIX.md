# Production Deployment Fix for TraceTrack

## Problem Summary
The deployment is failing because:
1. The application tries to connect to AWS RDS PostgreSQL server at startup
2. The connection times out, preventing the app from opening port 5000
3. Replit Autoscale requires the app to open port 5000 quickly

## Solution

### Option 1: Use Replit's Built-in Database (Recommended)
Instead of using AWS RDS, use Replit's built-in PostgreSQL database which is already configured and available via the `DATABASE_URL` environment variable.

**Steps:**
1. Remove the `PRODUCTION_DATABASE_URL` secret that points to AWS RDS
2. The app will automatically use Replit's PostgreSQL database
3. Deploy normally

### Option 2: Fix AWS RDS Connection
If you must use AWS RDS, ensure:

1. **Check AWS RDS Security Group**:
   - Allow inbound traffic on port 5432 from Replit's IP ranges
   - Or temporarily allow from 0.0.0.0/0 for testing

2. **Verify RDS Instance Status**:
   - Ensure the RDS instance is running
   - Check it's publicly accessible (set in RDS settings)

3. **Update Connection String**:
   - Format: `postgresql://username:password@hostname:5432/database`
   - Ensure no special characters need URL encoding

### Option 3: Use the Production-Optimized Main File

1. **Rename Files**:
   ```bash
   mv main.py main_old.py
   mv main_production.py main.py
   ```

2. **Update .replit file**:
   ```
   [deployment]
   deploymentTarget = "autoscale"
   run = ["sh", "-c", "gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 --preload main:app"]
   ```

3. **Set Environment Variables**:
   - Remove `PRODUCTION_DATABASE_URL` if using Replit's database
   - Or fix the AWS RDS connection string

### Option 4: Quick Fix - Use SQLite for Testing

1. **Create a minimal deployment file** (`main_quick.py`):
   ```python
   from flask import Flask
   import os
   
   app = Flask(__name__)
   app.secret_key = os.environ.get("SESSION_SECRET", "test-key")
   
   @app.route('/health')
   def health():
       return {'status': 'healthy'}, 200
   
   @app.route('/')
   def index():
       return '<h1>TraceTrack</h1><p>Application is running!</p>'
   
   if __name__ == "__main__":
       app.run(host="0.0.0.0", port=5000)
   ```

2. **Update .replit**:
   ```
   run = "python main_quick.py"
   ```

## Recommended Immediate Action

1. **Remove AWS RDS connection** (for now):
   - Go to Secrets tab
   - Delete or rename `PRODUCTION_DATABASE_URL`

2. **Use Replit's database**:
   - It's already configured via `DATABASE_URL`
   - No additional setup needed

3. **Deploy again**:
   - The app will use the local Replit PostgreSQL
   - Port 5000 will open immediately
   - Database will initialize properly

## Testing After Deployment

1. Visit `/health` - Should return `{"status": "healthy"}`
2. Visit `/ready` - Should show database connection status
3. Visit `/login` - Should load the login page

## Long-term Solution

For production with external database:
1. Use the `production_deployment.py` module
2. Implement lazy database initialization
3. Add connection pooling and retry logic
4. Use environment-specific configurations

## Support

If issues persist:
1. Check deployment logs for specific errors
2. Verify all environment variables are set correctly
3. Test database connection separately
4. Consider using Replit's built-in database for simplicity
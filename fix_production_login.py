#!/usr/bin/env python3
"""
Production Database Migration Fix Script
Fixes the missing columns issue that's causing login failures in production
"""

import os
import sys
import subprocess
from datetime import datetime

def print_header(message):
    """Print a formatted header message"""
    print("\n" + "=" * 60)
    print(f"  {message}")
    print("=" * 60 + "\n")

def run_command(command, description):
    """Run a shell command and display results"""
    print(f"⏳ {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - Success!")
            if result.stdout:
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} - Failed!")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description} - Exception occurred: {str(e)}")
        return False

def main():
    print_header("Production Database Migration Fix")
    
    print("This script will fix the production login issue by applying")
    print("missing database migrations that add security-related columns.")
    print("\n⚠️  IMPORTANT: This script should be run in your production environment")
    
    # Check if we're in production
    env = os.environ.get('FLASK_ENV', 'development')
    if env != 'production':
        print(f"\n⚠️  Warning: Current environment is '{env}', not 'production'")
        response = input("Do you want to continue anyway? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborting...")
            sys.exit(0)
    
    print_header("Step 1: Checking Current Migration Status")
    
    # Check current migration version
    if not run_command("flask db current", "Checking current migration version"):
        print("\n❌ Could not check migration status. Trying alternative approach...")
    
    print_header("Step 2: Applying Pending Migrations")
    
    print("The following migrations will be applied:")
    print("  • Password reset fields (password_reset_token, password_reset_token_expires)")
    print("  • Two-factor auth fields (totp_secret, two_fa_enabled)")
    print("  • Account lockout fields (failed_login_attempts, locked_until, last_failed_login)")
    print("")
    
    response = input("Proceed with migration? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborting...")
        sys.exit(0)
    
    # Apply migrations
    if run_command("flask db upgrade", "Applying database migrations"):
        print_header("✅ Migration Successful!")
        print("Your production login should now work correctly.")
        print("\nVerifying migration status...")
        run_command("flask db current", "Final migration status")
    else:
        print_header("⚠️  Flask-Migrate Failed - Using Direct SQL")
        print("Attempting to apply migrations using direct SQL commands...")
        
        # Try direct SQL approach
        sql_commands = """
-- Add account lockout fields
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS last_failed_login TIMESTAMP;

-- Add password reset fields
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS password_reset_token VARCHAR(100);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS password_reset_token_expires TIMESTAMP;

-- Add two-factor authentication fields
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(32);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS two_fa_enabled BOOLEAN DEFAULT FALSE;

-- Update migration version table
INSERT INTO alembic_version (version_num) 
VALUES ('986e81b92e8e')
ON CONFLICT (version_num) DO NOTHING;
        """
        
        # Write SQL to temporary file
        with open('/tmp/fix_production.sql', 'w') as f:
            f.write(sql_commands)
        
        print("\nSQL commands have been written to: /tmp/fix_production.sql")
        print("\nTo apply manually, run:")
        print("  psql $DATABASE_URL < /tmp/fix_production.sql")
        print("\nOr connect to your database and run the SQL commands directly.")
    
    print_header("Migration Complete")
    print("Please test the login functionality to confirm the fix.")

if __name__ == "__main__":
    main()
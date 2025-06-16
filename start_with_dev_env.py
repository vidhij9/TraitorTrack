#!/usr/bin/env python3
"""
Start the application with proper development environment variables
"""
import os
import subprocess
import sys

def main():
    # Set development environment variables
    env = os.environ.copy()
    env['FLASK_ENV'] = 'development'
    env['DEV_DATABASE_URL'] = f"postgresql://{env.get('PGUSER')}:{env.get('PGPASSWORD')}@{env.get('PGHOST')}:{env.get('PGPORT')}/tracetrack_dev"
    env['PROD_DATABASE_URL'] = "postgresql://neondb_owner:npg_mznV9XNHSeP6@ep-yellow-truth-a5j5ivuq.us-east-2.aws.neon.tech/neondb?sslmode=require"
    
    print("Starting application with development database separation:")
    print(f"FLASK_ENV: {env['FLASK_ENV']}")
    print(f"Development DB: tracetrack_dev")
    print(f"Production DB: neondb (original)")
    
    # Start the application with gunicorn
    cmd = ['gunicorn', '--bind', '0.0.0.0:5000', '--reuse-port', '--reload', 'main:app']
    
    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        print("\nApplication stopped.")
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
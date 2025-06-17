#!/usr/bin/env python3
"""
Environment Switcher - Quick switch between development and production configurations
"""

import os
import sys
from pathlib import Path

def create_env_file(env_type):
    """Create environment-specific configuration file"""
    env_files = {
        'development': {
            'file': '.env.development',
            'content': '''# Development Environment
export FLASK_ENV=development
export DEV_DATABASE_URL=postgresql://tracetrack_dev_user:dev_password_change_me@localhost:5432/tracetrack_dev
export SESSION_SECRET=development-session-secret-change-me

# Load development environment
echo "Switched to DEVELOPMENT environment"
echo "Database: Development (separate from production)"
echo "Debug mode: Enabled"
echo "Security: Relaxed for local development"
'''
        },
        'production': {
            'file': '.env.production',
            'content': '''# Production Environment
export FLASK_ENV=production
export PROD_DATABASE_URL=postgresql://tracetrack_prod_user:prod_password_change_me@localhost:5432/tracetrack_prod
export SESSION_SECRET=production-session-secret-must-be-secure

# Load production environment
echo "Switched to PRODUCTION environment"
echo "Database: Production (separate from development)"
echo "Debug mode: Disabled"
echo "Security: Strict HTTPS required"
'''
        }
    }
    
    env_config = env_files.get(env_type)
    if not env_config:
        return None
    
    with open(env_config['file'], 'w') as f:
        f.write(env_config['content'])
    
    return env_config['file']

def switch_environment(env_type):
    """Switch to specified environment"""
    if env_type not in ['development', 'production']:
        print(f"Invalid environment: {env_type}")
        print("Valid options: development, production")
        return False
    
    # Create environment file
    env_file = create_env_file(env_type)
    if not env_file:
        print(f"Failed to create environment file for {env_type}")
        return False
    
    print(f"Environment configuration created: {env_file}")
    print(f"\nTo activate {env_type} environment, run:")
    print(f"source {env_file}")
    print(f"\nOr set the variables manually:")
    
    if env_type == 'development':
        print("export FLASK_ENV=development")
        print("export DEV_DATABASE_URL=postgresql://tracetrack_dev_user:dev_password_change_me@localhost:5432/tracetrack_dev")
        print("export SESSION_SECRET=development-session-secret-change-me")
    else:
        print("export FLASK_ENV=production")
        print("export PROD_DATABASE_URL=postgresql://tracetrack_prod_user:prod_password_change_me@localhost:5432/tracetrack_prod")
        print("export SESSION_SECRET=production-session-secret-must-be-secure")
    
    return True

def show_current_environment():
    """Show current environment configuration"""
    current_env = os.environ.get('FLASK_ENV', 'not set')
    dev_db = os.environ.get('DEV_DATABASE_URL', 'not set')
    prod_db = os.environ.get('PROD_DATABASE_URL', 'not set')
    session_secret = os.environ.get('SESSION_SECRET', 'not set')
    
    print("Current Environment Configuration:")
    print(f"FLASK_ENV: {current_env}")
    print(f"DEV_DATABASE_URL: {dev_db}")
    print(f"PROD_DATABASE_URL: {prod_db}")
    print(f"SESSION_SECRET: {'***set***' if session_secret != 'not set' else 'not set'}")
    
    # Determine which database will be used
    if current_env == 'production':
        active_db = prod_db if prod_db != 'not set' else os.environ.get('DATABASE_URL', 'not set')
        print(f"Active Database: Production - {active_db}")
    else:
        active_db = dev_db if dev_db != 'not set' else os.environ.get('DATABASE_URL', 'not set')
        print(f"Active Database: Development - {active_db}")

def main():
    """Main command interface"""
    if len(sys.argv) < 2:
        print("TraceTrack Environment Switcher")
        print("\nUsage: python switch_environment.py <command>")
        print("\nCommands:")
        print("  dev        - Switch to development environment")
        print("  prod       - Switch to production environment")
        print("  status     - Show current environment status")
        print("  help       - Show this help message")
        return
    
    command = sys.argv[1].lower()
    
    if command in ['dev', 'development']:
        switch_environment('development')
    elif command in ['prod', 'production']:
        switch_environment('production')
    elif command == 'status':
        show_current_environment()
    elif command in ['help', '-h', '--help']:
        main()
    else:
        print(f"Unknown command: {command}")
        print("Run 'python switch_environment.py help' for usage information")

if __name__ == "__main__":
    main()

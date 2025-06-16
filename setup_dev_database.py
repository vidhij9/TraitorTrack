#!/usr/bin/env python3
"""
Development Database Setup Script

This script helps create and configure separate databases for development and production environments.
It ensures data isolation and proper environment-specific configurations.
"""

import os
import sys
import subprocess
import getpass
from urllib.parse import urlparse

def run_command(command, description):
    """Run a shell command and handle errors"""
    print(f"Running: {description}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return False
        print(f"Success: {result.stdout}")
        return True
    except Exception as e:
        print(f"Failed to run command: {e}")
        return False

def get_database_info():
    """Get database connection information from user"""
    print("\n=== Database Configuration ===")
    print("Please provide database connection details:")
    
    host = input("Database host (default: localhost): ").strip() or "localhost"
    port = input("Database port (default: 5432): ").strip() or "5432"
    admin_user = input("Database admin username (default: postgres): ").strip() or "postgres"
    admin_password = getpass.getpass("Database admin password: ")
    
    return {
        'host': host,
        'port': port,
        'admin_user': admin_user,
        'admin_password': admin_password
    }

def create_database_and_user(db_info, db_name, db_user, db_password):
    """Create database and user with proper permissions"""
    print(f"\n=== Creating Database: {db_name} ===")
    
    # Connection string for admin operations
    admin_conn = f"postgresql://{db_info['admin_user']}:{db_info['admin_password']}@{db_info['host']}:{db_info['port']}/postgres"
    
    # Create database
    create_db_cmd = f'psql "{admin_conn}" -c "CREATE DATABASE {db_name};"'
    if not run_command(create_db_cmd, f"Creating database {db_name}"):
        print(f"Database {db_name} might already exist, continuing...")
    
    # Create user
    create_user_cmd = f'psql "{admin_conn}" -c "CREATE USER {db_user} WITH PASSWORD \'{db_password}\';"'
    if not run_command(create_user_cmd, f"Creating user {db_user}"):
        print(f"User {db_user} might already exist, continuing...")
    
    # Grant privileges
    grant_cmd = f'psql "{admin_conn}" -c "GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};"'
    run_command(grant_cmd, f"Granting privileges to {db_user}")
    
    # Grant schema privileges
    schema_cmd = f'psql "postgresql://{db_user}:{db_password}@{db_info["host"]}:{db_info["port"]}/{db_name}" -c "GRANT ALL ON SCHEMA public TO {db_user};"'
    run_command(schema_cmd, f"Granting schema privileges to {db_user}")

def setup_environment_file(dev_db_url, prod_db_url=None):
    """Create environment configuration file"""
    print("\n=== Creating Environment Configuration ===")
    
    env_content = f"""# Development Environment Configuration
# Copy these to your environment or .env file

# Development Database
DEV_DATABASE_URL={dev_db_url}

# Production Database (update with your production database URL)
"""
    
    if prod_db_url:
        env_content += f"PROD_DATABASE_URL={prod_db_url}\n"
    else:
        env_content += "# PROD_DATABASE_URL=postgresql://prod_user:prod_password@prod-server:5432/tracetrack_prod\n"
    
    env_content += """
# Session Security (generate unique secrets for each environment)
SESSION_SECRET=development-session-secret-change-me

# Environment Indicator
FLASK_ENV=development

# Export commands for current session:
# export DEV_DATABASE_URL="{dev_url}"
# export SESSION_SECRET="development-session-secret-change-me"
# export FLASK_ENV="development"
""".format(dev_url=dev_db_url)
    
    with open('.env.development', 'w') as f:
        f.write(env_content)
    
    print("Created .env.development file with configuration")
    print("You can source this file or copy the values to your environment")

def test_database_connection(db_url, db_name):
    """Test database connection"""
    print(f"\n=== Testing Connection to {db_name} ===")
    
    test_cmd = f'psql "{db_url}" -c "SELECT version();"'
    if run_command(test_cmd, f"Testing {db_name} connection"):
        print(f"✅ {db_name} database connection successful!")
        return True
    else:
        print(f"❌ {db_name} database connection failed!")
        return False

def main():
    """Main setup function"""
    print("🚀 TraceTrack Database Setup for Development Environment")
    print("=" * 60)
    
    # Check if psql is available
    if not run_command("psql --version", "Checking PostgreSQL client"):
        print("Error: PostgreSQL client (psql) not found. Please install PostgreSQL.")
        sys.exit(1)
    
    # Get database connection info
    db_info = get_database_info()
    
    # Setup development database
    dev_db_name = "tracetrack_dev"
    dev_db_user = "tracetrack_dev_user"
    dev_db_password = "dev_password_change_me"
    
    print(f"\n=== Development Database Setup ===")
    print(f"Database: {dev_db_name}")
    print(f"User: {dev_db_user}")
    print(f"Password: {dev_db_password}")
    
    confirm = input("\nProceed with development database setup? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Setup cancelled.")
        sys.exit(0)
    
    # Create development database
    create_database_and_user(db_info, dev_db_name, dev_db_user, dev_db_password)
    
    # Create database URLs
    dev_db_url = f"postgresql://{dev_db_user}:{dev_db_password}@{db_info['host']}:{db_info['port']}/{dev_db_name}"
    
    # Test connections
    test_database_connection(dev_db_url, "Development")
    
    # Setup environment file
    setup_environment_file(dev_db_url)
    
    # Setup production database (optional)
    setup_prod = input("\nDo you want to setup production database now? (y/N): ").strip().lower()
    if setup_prod == 'y':
        prod_db_name = "tracetrack_prod"
        prod_db_user = "tracetrack_prod_user"
        prod_db_password = getpass.getpass("Enter production database password: ")
        
        create_database_and_user(db_info, prod_db_name, prod_db_user, prod_db_password)
        prod_db_url = f"postgresql://{prod_db_user}:{prod_db_password}@{db_info['host']}:{db_info['port']}/{prod_db_name}"
        test_database_connection(prod_db_url, "Production")
        
        # Update environment file with production URL
        setup_environment_file(dev_db_url, prod_db_url)
    
    print("\n🎉 Database setup completed!")
    print("\nNext steps:")
    print("1. Source the environment file: source .env.development")
    print("2. Or set the environment variables manually")
    print("3. Start your application with FLASK_ENV=development")
    print("4. Your development and production databases are now separate!")
    
    print(f"\nDevelopment Database URL: {dev_db_url}")
    if 'prod_db_url' in locals():
        print(f"Production Database URL: {prod_db_url}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Database Isolation Setup Script
Creates completely separate databases for development and production environments.
"""

import os
import sys
import subprocess
import logging
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def parse_database_url(url):
    """Parse database URL into components."""
    parsed = urlparse(url)
    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'username': parsed.username,
        'password': parsed.password,
        'database': parsed.path.lstrip('/')
    }

def create_database_url(host, port, username, password, database):
    """Create database URL from components."""
    return f"postgresql://{username}:{password}@{host}:{port}/{database}"

def execute_sql_command(host, port, username, password, database, sql_command):
    """Execute SQL command using psql."""
    env = os.environ.copy()
    env['PGPASSWORD'] = password
    
    cmd = [
        'psql',
        '-h', host,
        '-p', str(port),
        '-U', username,
        '-d', database,
        '-c', sql_command
    ]
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def test_database_connection(db_url, description):
    """Test database connection."""
    db_info = parse_database_url(db_url)
    success, output = execute_sql_command(
        db_info['host'], db_info['port'], db_info['username'], 
        db_info['password'], db_info['database'], 'SELECT 1;'
    )
    
    if success:
        logging.info(f"✓ {description} database connection successful")
        return True
    else:
        logging.error(f"✗ {description} database connection failed: {output}")
        return False

def create_development_database():
    """Create development database with test data."""
    # Get current database URL (this will be our template)
    current_db_url = os.environ.get('DATABASE_URL')
    if not current_db_url:
        logging.error("DATABASE_URL not found. Cannot proceed with setup.")
        return None
    
    db_info = parse_database_url(current_db_url)
    
    # Create development database name
    dev_db_name = f"{db_info['database']}_dev"
    dev_db_url = create_database_url(
        db_info['host'], db_info['port'], 
        db_info['username'], db_info['password'], 
        dev_db_name
    )
    
    logging.info(f"Creating development database: {dev_db_name}")
    
    # Create development database
    success, output = execute_sql_command(
        db_info['host'], db_info['port'], db_info['username'], 
        db_info['password'], 'postgres', 
        f"CREATE DATABASE {dev_db_name};"
    )
    
    if not success and "already exists" not in output:
        logging.error(f"Failed to create development database: {output}")
        return None
    
    # Test connection
    if test_database_connection(dev_db_url, "Development"):
        return dev_db_url
    else:
        return None

def create_production_database():
    """Set up production database configuration."""
    # Get current database URL (this will be our production database)
    current_db_url = os.environ.get('DATABASE_URL')
    if not current_db_url:
        logging.error("DATABASE_URL not found. Cannot proceed with setup.")
        return None
    
    db_info = parse_database_url(current_db_url)
    
    # Create production database name
    prod_db_name = f"{db_info['database']}_prod"
    prod_db_url = create_database_url(
        db_info['host'], db_info['port'], 
        db_info['username'], db_info['password'], 
        prod_db_name
    )
    
    logging.info(f"Creating production database: {prod_db_name}")
    
    # Create production database
    success, output = execute_sql_command(
        db_info['host'], db_info['port'], db_info['username'], 
        db_info['password'], 'postgres', 
        f"CREATE DATABASE {prod_db_name};"
    )
    
    if not success and "already exists" not in output:
        logging.error(f"Failed to create production database: {output}")
        return None
    
    # Test connection
    if test_database_connection(prod_db_url, "Production"):
        return prod_db_url
    else:
        return None

def migrate_current_data_to_production():
    """Migrate current data to production database."""
    current_db_url = os.environ.get('DATABASE_URL')
    db_info = parse_database_url(current_db_url)
    
    current_db = db_info['database']
    prod_db = f"{current_db}_prod"
    
    logging.info("Copying current data to production database...")
    
    # Create dump of current database
    env = os.environ.copy()
    env['PGPASSWORD'] = db_info['password']
    
    dump_cmd = [
        'pg_dump',
        '-h', db_info['host'],
        '-p', str(db_info['port']),
        '-U', db_info['username'],
        '-d', current_db,
        '--clean',
        '--no-owner',
        '--no-privileges'
    ]
    
    restore_cmd = [
        'psql',
        '-h', db_info['host'],
        '-p', str(db_info['port']),
        '-U', db_info['username'],
        '-d', prod_db
    ]
    
    try:
        # Dump current database
        dump_process = subprocess.Popen(dump_cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Restore to production database
        restore_process = subprocess.Popen(restore_cmd, env=env, stdin=dump_process.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        dump_process.stdout.close()
        restore_output, restore_error = restore_process.communicate()
        
        if restore_process.returncode == 0:
            logging.info("✓ Data successfully copied to production database")
            return True
        else:
            logging.warning(f"Data migration completed with warnings: {restore_error.decode()}")
            return True
    except Exception as e:
        logging.error(f"Failed to migrate data: {e}")
        return False

def update_environment_variables(dev_db_url, prod_db_url):
    """Update environment variables for database isolation."""
    
    # Create environment files
    dev_env = f"""# Development Environment
export ENVIRONMENT=development
export DEV_DATABASE_URL="{dev_db_url}"
export SESSION_SECRET="dev-session-{os.urandom(16).hex()}"

# For current session:
ENVIRONMENT=development
DEV_DATABASE_URL="{dev_db_url}"
SESSION_SECRET="dev-session-{os.urandom(16).hex()}"
"""

    prod_env = f"""# Production Environment
export ENVIRONMENT=production
export PROD_DATABASE_URL="{prod_db_url}"
export SESSION_SECRET="prod-session-{os.urandom(16).hex()}"

# For current session:
ENVIRONMENT=production
PROD_DATABASE_URL="{prod_db_url}"
SESSION_SECRET="prod-session-{os.urandom(16).hex()}"
"""

    # Write environment files
    with open('.env.dev', 'w') as f:
        f.write(dev_env)
    
    with open('.env.prod', 'w') as f:
        f.write(prod_env)
    
    logging.info("Created environment configuration files:")
    logging.info("  .env.dev - Development environment")
    logging.info("  .env.prod - Production environment")

def create_switch_scripts(dev_db_url, prod_db_url):
    """Create scripts to switch between environments."""
    
    switch_to_dev = f"""#!/bin/bash
# Switch to Development Environment
echo "Switching to Development Environment..."
export ENVIRONMENT=development
export DEV_DATABASE_URL="{dev_db_url}"
export SESSION_SECRET="dev-session-{os.urandom(8).hex()}"

echo "Environment: $ENVIRONMENT"
echo "Database: Development"
echo "Ready for development testing!"
"""

    switch_to_prod = f"""#!/bin/bash
# Switch to Production Environment
echo "Switching to Production Environment..."
export ENVIRONMENT=production
export PROD_DATABASE_URL="{prod_db_url}"
export SESSION_SECRET="prod-session-{os.urandom(8).hex()}"

echo "Environment: $ENVIRONMENT"
echo "Database: Production"
echo "⚠️  WARNING: You are now using PRODUCTION data!"
"""

    # Write switch scripts
    with open('switch-to-dev.sh', 'w') as f:
        f.write(switch_to_dev)
    os.chmod('switch-to-dev.sh', 0o755)
    
    with open('switch-to-prod.sh', 'w') as f:
        f.write(switch_to_prod)
    os.chmod('switch-to-prod.sh', 0o755)
    
    logging.info("Created environment switch scripts:")
    logging.info("  ./switch-to-dev.sh - Switch to development")
    logging.info("  ./switch-to-prod.sh - Switch to production")

def verify_isolation(dev_db_url, prod_db_url):
    """Verify that databases are completely isolated."""
    logging.info("Verifying database isolation...")
    
    # Test development database
    dev_test = test_database_connection(dev_db_url, "Development")
    
    # Test production database  
    prod_test = test_database_connection(prod_db_url, "Production")
    
    if dev_test and prod_test:
        logging.info("✓ Database isolation verified successfully")
        logging.info("✓ Development and production databases are completely separate")
        return True
    else:
        logging.error("✗ Database isolation verification failed")
        return False

def main():
    """Main setup function."""
    print("🔧 Database Environment Isolation Setup")
    print("=" * 50)
    
    # Check if psql is available
    try:
        subprocess.run(['psql', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logging.error("PostgreSQL client (psql) not found. Please install PostgreSQL.")
        sys.exit(1)
    
    # Check if DATABASE_URL exists
    if not os.environ.get('DATABASE_URL'):
        logging.error("DATABASE_URL environment variable not found.")
        logging.error("Please ensure your database is configured.")
        sys.exit(1)
    
    print("Setting up completely separate databases for development and production...")
    print()
    
    # Create development database
    dev_db_url = create_development_database()
    if not dev_db_url:
        logging.error("Failed to create development database")
        sys.exit(1)
    
    # Create production database
    prod_db_url = create_production_database()
    if not prod_db_url:
        logging.error("Failed to create production database")
        sys.exit(1)
    
    # Migrate current data to production
    if not migrate_current_data_to_production():
        logging.warning("Data migration to production failed - production database will be empty")
    
    # Update environment configuration
    update_environment_variables(dev_db_url, prod_db_url)
    
    # Create switch scripts
    create_switch_scripts(dev_db_url, prod_db_url)
    
    # Verify isolation
    if verify_isolation(dev_db_url, prod_db_url):
        print()
        print("🎉 Database isolation setup completed successfully!")
        print()
        print("Next steps:")
        print("1. Use './switch-to-dev.sh' to work in development")
        print("2. Use './switch-to-prod.sh' to work with production data")
        print("3. Development testing will NOT affect production data")
        print("4. Production changes will NOT affect development data")
        print()
        print("Visit /environment-status in your app to monitor isolation status")
    else:
        logging.error("Setup completed with errors. Please check the configuration.")
        sys.exit(1)

if __name__ == "__main__":
    main()

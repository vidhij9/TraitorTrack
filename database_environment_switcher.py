"""
Database Environment Switcher
Provides tools to safely switch between development and production databases
with complete isolation and validation.
"""

import os
import sys
import subprocess
import logging
from typing import Dict, List, Optional, Tuple
from environment_manager import get_environment_manager


class DatabaseEnvironmentSwitcher:
    """
    Manages switching between different database environments while ensuring
    complete isolation and preventing accidental cross-environment access.
    """
    
    def __init__(self):
        self.env_manager = get_environment_manager()
        self.current_env = self.env_manager.current_env
        
    def list_available_environments(self) -> Dict[str, Dict[str, str]]:
        """List all available database environments and their configurations."""
        environments = {}
        
        # Check development environment
        dev_url = os.environ.get('DEV_DATABASE_URL')
        if dev_url:
            environments['development'] = {
                'database_url': self.env_manager._mask_database_url(dev_url),
                'status': 'configured',
                'description': 'Development database for testing and development'
            }
        else:
            environments['development'] = {
                'database_url': 'Not configured',
                'status': 'missing',
                'description': 'Development database (DEV_DATABASE_URL not set)'
            }
        
        # Check production environment
        prod_url = os.environ.get('PROD_DATABASE_URL')
        if prod_url:
            environments['production'] = {
                'database_url': self.env_manager._mask_database_url(prod_url),
                'status': 'configured',
                'description': 'Production database for live application'
            }
        else:
            environments['production'] = {
                'database_url': 'Not configured',
                'status': 'missing',
                'description': 'Production database (PROD_DATABASE_URL not set)'
            }
        
        # Check testing environment
        test_url = os.environ.get('TEST_DATABASE_URL', 'sqlite:///:memory:')
        environments['testing'] = {
            'database_url': self.env_manager._mask_database_url(test_url),
            'status': 'configured',
            'description': 'Testing database for automated tests'
        }
        
        # Check generic fallback
        generic_url = os.environ.get('DATABASE_URL')
        if generic_url:
            environments['generic'] = {
                'database_url': self.env_manager._mask_database_url(generic_url),
                'status': 'configured',
                'description': 'Generic database fallback'
            }
        
        return environments
    
    def validate_environment_isolation(self) -> Dict[str, any]:
        """Validate that environments are properly isolated."""
        validation_results = {
            'is_isolated': True,
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        environments = self.list_available_environments()
        urls = {}
        
        # Collect actual URLs for comparison
        for env_name, config in environments.items():
            if config['status'] == 'configured' and env_name != 'generic':
                url_var = f"{env_name.upper()}_DATABASE_URL" if env_name != 'testing' else 'TEST_DATABASE_URL'
                actual_url = os.environ.get(url_var)
                if actual_url:
                    urls[env_name] = actual_url
        
        # Check for duplicate URLs
        url_to_envs = {}
        for env, url in urls.items():
            if url in url_to_envs:
                url_to_envs[url].append(env)
            else:
                url_to_envs[url] = [env]
        
        # Report duplicates
        for url, envs in url_to_envs.items():
            if len(envs) > 1:
                validation_results['is_isolated'] = False
                validation_results['errors'].append(
                    f"Multiple environments using same database: {', '.join(envs)}"
                )
        
        # Check for missing environment-specific URLs
        if not os.environ.get('DEV_DATABASE_URL'):
            validation_results['warnings'].append(
                "DEV_DATABASE_URL not set - using generic DATABASE_URL for development"
            )
            validation_results['recommendations'].append(
                "Set DEV_DATABASE_URL for better isolation"
            )
        
        if not os.environ.get('PROD_DATABASE_URL'):
            validation_results['warnings'].append(
                "PROD_DATABASE_URL not set - using generic DATABASE_URL for production"
            )
            validation_results['recommendations'].append(
                "Set PROD_DATABASE_URL for production isolation"
            )
        
        return validation_results
    
    def create_database_setup_script(self, environment: str) -> str:
        """Create a database setup script for a specific environment."""
        if environment == 'development':
            return self._create_dev_setup_script()
        elif environment == 'production':
            return self._create_prod_setup_script()
        elif environment == 'testing':
            return self._create_test_setup_script()
        else:
            raise ValueError(f"Unknown environment: {environment}")
    
    def _create_dev_setup_script(self) -> str:
        """Create development database setup script."""
        return """#!/bin/bash
# Development Database Setup Script

echo "Setting up Development Database..."

# Set environment variables
export ENVIRONMENT=development
export FLASK_ENV=development
export DEV_DATABASE_URL="postgresql://dev_user:dev_password@localhost:5432/tracetrack_dev"
export SESSION_SECRET="development-session-secret-change-me"

# Create development database (requires PostgreSQL to be running)
echo "Creating development database..."
createdb tracetrack_dev 2>/dev/null || echo "Database may already exist"

# Create development user
psql -d postgres -c "CREATE USER dev_user WITH PASSWORD 'dev_password';" 2>/dev/null || echo "User may already exist"
psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE tracetrack_dev TO dev_user;" 2>/dev/null

echo "Development database setup complete!"
echo "Database URL: $DEV_DATABASE_URL"
echo ""
echo "To activate this environment, run:"
echo "export ENVIRONMENT=development"
echo "export DEV_DATABASE_URL='$DEV_DATABASE_URL'"
echo "export SESSION_SECRET='$SESSION_SECRET'"
"""
    
    def _create_prod_setup_script(self) -> str:
        """Create production database setup script."""
        return """#!/bin/bash
# Production Database Setup Script

echo "Setting up Production Database..."
echo "WARNING: This will create a production database!"
echo "Make sure you're running this on the correct server!"

read -p "Continue with production setup? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Production setup cancelled."
    exit 1
fi

# Set environment variables
export ENVIRONMENT=production
export FLASK_ENV=production

# Prompt for production database credentials
read -p "Enter production database host: " DB_HOST
read -p "Enter production database name: " DB_NAME
read -p "Enter production database user: " DB_USER
read -s -p "Enter production database password: " DB_PASSWORD
echo

# Create production database URL
export PROD_DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:5432/$DB_NAME"

# Prompt for session secret
read -s -p "Enter production session secret (strong password): " SESSION_SECRET
echo
export SESSION_SECRET="$SESSION_SECRET"

echo "Production database configuration complete!"
echo "Database URL: postgresql://$DB_USER:***@$DB_HOST:5432/$DB_NAME"
echo ""
echo "To activate this environment, set:"
echo "export ENVIRONMENT=production"
echo "export PROD_DATABASE_URL='<your-production-url>'"
echo "export SESSION_SECRET='<your-secure-secret>'"
"""
    
    def _create_test_setup_script(self) -> str:
        """Create testing database setup script."""
        return """#!/bin/bash
# Testing Database Setup Script

echo "Setting up Testing Database..."

# Set environment variables
export ENVIRONMENT=testing
export FLASK_ENV=testing
export TEST_DATABASE_URL="sqlite:///:memory:"
export SESSION_SECRET="testing-session-secret"

echo "Testing database setup complete!"
echo "Database URL: $TEST_DATABASE_URL"
echo ""
echo "To activate this environment, run:"
echo "export ENVIRONMENT=testing"
echo "export TEST_DATABASE_URL='$TEST_DATABASE_URL'"
echo "export SESSION_SECRET='$SESSION_SECRET'"
"""
    
    def check_database_connectivity(self, environment: str) -> Tuple[bool, str]:
        """Check if we can connect to the database for a specific environment."""
        try:
            # Get the database URL for the environment
            if environment == 'development':
                db_url = os.environ.get('DEV_DATABASE_URL') or os.environ.get('DATABASE_URL')
            elif environment == 'production':
                db_url = os.environ.get('PROD_DATABASE_URL') or os.environ.get('DATABASE_URL')
            elif environment == 'testing':
                db_url = os.environ.get('TEST_DATABASE_URL', 'sqlite:///:memory:')
            else:
                return False, f"Unknown environment: {environment}"
            
            if not db_url:
                return False, f"No database URL configured for {environment}"
            
            # Test connection using SQLAlchemy
            from sqlalchemy import create_engine, text
            
            engine = create_engine(db_url)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            return True, f"Successfully connected to {environment} database"
            
        except Exception as e:
            return False, f"Failed to connect to {environment} database: {str(e)}"
    
    def get_current_environment_status(self) -> Dict[str, any]:
        """Get comprehensive status of the current environment."""
        status = {
            'current_environment': self.current_env,
            'database_configured': False,
            'database_accessible': False,
            'isolation_valid': False,
            'recommendations': []
        }
        
        # Check database configuration
        try:
            db_url = self.env_manager.config.get('database_url')
            status['database_configured'] = bool(db_url)
            
            if db_url:
                # Test connectivity
                is_accessible, message = self.check_database_connectivity(self.current_env)
                status['database_accessible'] = is_accessible
                status['connectivity_message'] = message
            
        except Exception as e:
            status['error'] = str(e)
        
        # Check isolation
        validation = self.validate_environment_isolation()
        status['isolation_valid'] = validation['is_isolated']
        status['isolation_warnings'] = validation['warnings']
        status['isolation_errors'] = validation['errors']
        
        # Add recommendations
        if not status['database_configured']:
            status['recommendations'].append(f"Configure database URL for {self.current_env} environment")
        
        if not status['database_accessible']:
            status['recommendations'].append("Ensure database server is running and accessible")
        
        if not status['isolation_valid']:
            status['recommendations'].append("Fix database isolation issues")
        
        status['recommendations'].extend(validation['recommendations'])
        
        return status
    
    def switch_environment(self, target_environment: str) -> Tuple[bool, str]:
        """
        Switch to a different environment.
        Note: This changes environment variables for the current process only.
        """
        if target_environment not in ['development', 'production', 'testing']:
            return False, f"Invalid environment: {target_environment}"
        
        try:
            # Set the environment variable
            os.environ['ENVIRONMENT'] = target_environment
            os.environ['FLASK_ENV'] = target_environment
            
            # Update the environment manager
            self.env_manager = get_environment_manager()
            self.current_env = target_environment
            
            # Validate the switch
            is_accessible, message = self.check_database_connectivity(target_environment)
            
            if is_accessible:
                return True, f"Successfully switched to {target_environment} environment"
            else:
                return False, f"Switched to {target_environment} but database not accessible: {message}"
                
        except Exception as e:
            return False, f"Failed to switch environment: {str(e)}"


def main():
    """Command-line interface for database environment management."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Database Environment Management')
    parser.add_argument('action', choices=['list', 'validate', 'status', 'switch', 'setup'], 
                       help='Action to perform')
    parser.add_argument('--environment', '-e', choices=['development', 'production', 'testing'],
                       help='Target environment for switch/setup actions')
    
    args = parser.parse_args()
    
    switcher = DatabaseEnvironmentSwitcher()
    
    if args.action == 'list':
        print("Available Database Environments:")
        print("=" * 50)
        environments = switcher.list_available_environments()
        for name, config in environments.items():
            status_symbol = "✓" if config['status'] == 'configured' else "✗"
            print(f"{status_symbol} {name.upper()}")
            print(f"   URL: {config['database_url']}")
            print(f"   Description: {config['description']}")
            print()
    
    elif args.action == 'validate':
        print("Database Environment Isolation Validation:")
        print("=" * 50)
        validation = switcher.validate_environment_isolation()
        
        if validation['is_isolated']:
            print("✓ Database environments are properly isolated")
        else:
            print("✗ Database isolation issues found")
        
        if validation['errors']:
            print("\nERRORS:")
            for error in validation['errors']:
                print(f"  • {error}")
        
        if validation['warnings']:
            print("\nWARNINGS:")
            for warning in validation['warnings']:
                print(f"  • {warning}")
        
        if validation['recommendations']:
            print("\nRECOMMENDATIONS:")
            for rec in validation['recommendations']:
                print(f"  • {rec}")
    
    elif args.action == 'status':
        print("Current Environment Status:")
        print("=" * 30)
        status = switcher.get_current_environment_status()
        
        print(f"Environment: {status['current_environment']}")
        print(f"Database Configured: {'✓' if status['database_configured'] else '✗'}")
        print(f"Database Accessible: {'✓' if status['database_accessible'] else '✗'}")
        print(f"Isolation Valid: {'✓' if status['isolation_valid'] else '✗'}")
        
        if 'connectivity_message' in status:
            print(f"Connectivity: {status['connectivity_message']}")
        
        if status['recommendations']:
            print("\nRecommendations:")
            for rec in status['recommendations']:
                print(f"  • {rec}")
    
    elif args.action == 'switch':
        if not args.environment:
            print("Error: --environment required for switch action")
            sys.exit(1)
        
        success, message = switcher.switch_environment(args.environment)
        print(message)
        
        if not success:
            sys.exit(1)
    
    elif args.action == 'setup':
        if not args.environment:
            print("Error: --environment required for setup action")
            sys.exit(1)
        
        try:
            script = switcher.create_database_setup_script(args.environment)
            filename = f"setup_{args.environment}_db.sh"
            
            with open(filename, 'w') as f:
                f.write(script)
            
            # Make script executable
            os.chmod(filename, 0o755)
            
            print(f"Database setup script created: {filename}")
            print(f"Run: ./{filename}")
            
        except Exception as e:
            print(f"Error creating setup script: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()

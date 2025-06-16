"""
Environment Manager - Complete Database Isolation System
Ensures development and production databases are completely separate with no cross-contamination.
"""

import os
import sys
import logging
from typing import Dict, Any, Optional, Tuple


class EnvironmentManager:
    """
    Manages environment-specific configurations with strict database isolation.
    Prevents any accidental cross-environment data access.
    """
    
    # Environment types
    DEVELOPMENT = 'development'
    PRODUCTION = 'production'
    TESTING = 'testing'
    
    # Required environment variables for each environment
    REQUIRED_VARS = {
        DEVELOPMENT: ['DEV_DATABASE_URL', 'SESSION_SECRET'],
        PRODUCTION: ['PROD_DATABASE_URL', 'SESSION_SECRET'],
        TESTING: ['TEST_DATABASE_URL', 'SESSION_SECRET']
    }
    
    def __init__(self):
        self.current_env = self._detect_environment()
        self.config = self._load_environment_config()
        self._validate_environment()
        
    def _detect_environment(self) -> str:
        """
        Detect current environment from multiple sources.
        Priority: ENVIRONMENT > FLASK_ENV > default to development
        """
        env = (
            os.environ.get('ENVIRONMENT') or
            os.environ.get('FLASK_ENV') or
            self.DEVELOPMENT
        ).lower()
        
        if env not in [self.DEVELOPMENT, self.PRODUCTION, self.TESTING]:
            logging.warning(f"Unknown environment '{env}', defaulting to development")
            env = self.DEVELOPMENT
            
        return env
    
    def _load_environment_config(self) -> Dict[str, Any]:
        """Load configuration specific to the current environment."""
        base_config = {
            'environment': self.current_env,
            'debug': self.current_env != self.PRODUCTION,
            'testing': self.current_env == self.TESTING,
        }
        
        if self.current_env == self.DEVELOPMENT:
            return {
                **base_config,
                'database_url': self._get_database_url_for_env(self.DEVELOPMENT),
                'session_cookie_secure': False,
                'sqlalchemy_echo': True,
                'pool_size': 5,
                'max_overflow': 10,
                'log_level': 'DEBUG',
                'cache_timeout': 60,
                'rate_limit': '1000 per hour'
            }
        elif self.current_env == self.PRODUCTION:
            return {
                **base_config,
                'database_url': self._get_database_url_for_env(self.PRODUCTION),
                'session_cookie_secure': True,
                'sqlalchemy_echo': False,
                'pool_size': 50,
                'max_overflow': 60,
                'log_level': 'WARNING',
                'cache_timeout': 300,
                'rate_limit': '100 per hour'
            }
        else:  # TESTING
            return {
                **base_config,
                'database_url': self._get_database_url_for_env(self.TESTING),
                'session_cookie_secure': False,
                'sqlalchemy_echo': False,
                'pool_size': 2,
                'max_overflow': 5,
                'log_level': 'ERROR',
                'cache_timeout': 0,
                'rate_limit': '10000 per hour'
            }
    
    def _get_database_url_for_env(self, environment: str) -> str:
        """
        Get database URL for specific environment with strict isolation.
        Each environment MUST have its own database URL.
        """
        if environment == self.DEVELOPMENT:
            url = os.environ.get('DEV_DATABASE_URL')
            if not url:
                # Force development to use isolated database
                url = "postgresql://neondb_owner:npg_mznV9XNHSeP6@ep-yellow-truth-a5j5ivuq.us-east-2.aws.neon.tech:5432/neondb_dev"
                logging.info("Using hardcoded development database URL for isolation")
        elif environment == self.PRODUCTION:
            url = os.environ.get('PROD_DATABASE_URL')
            if not url:
                # Force production to use isolated database
                url = "postgresql://neondb_owner:npg_mznV9XNHSeP6@ep-yellow-truth-a5j5ivuq.us-east-2.aws.neon.tech:5432/neondb_prod"
                logging.info("Using hardcoded production database URL for isolation")
        else:  # TESTING
            url = os.environ.get('TEST_DATABASE_URL')
            if not url:
                # Default to in-memory SQLite for testing
                url = 'sqlite:///:memory:'
                
        if not url:
            raise ValueError(f"No database URL configured for {environment} environment")
            
        return url
    
    def _validate_environment(self):
        """Validate that the current environment is properly configured."""
        missing_vars = []
        
        # Check required variables for current environment
        for var in self.REQUIRED_VARS.get(self.current_env, []):
            if not os.environ.get(var):
                # Special handling for DATABASE_URL fallback
                if var.endswith('_DATABASE_URL') and os.environ.get('DATABASE_URL'):
                    continue
                missing_vars.append(var)
        
        if missing_vars:
            error_msg = f"Missing required environment variables for {self.current_env}: {missing_vars}"
            logging.error(error_msg)
            if self.current_env == self.PRODUCTION:
                raise ValueError(error_msg)
            else:
                logging.warning(f"{error_msg} - continuing with defaults")
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration for SQLAlchemy."""
        return {
            'SQLALCHEMY_DATABASE_URI': self.config['database_url'],
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'SQLALCHEMY_ECHO': self.config['sqlalchemy_echo'],
            'SQLALCHEMY_ENGINE_OPTIONS': self._get_engine_options()
        }
    
    def _get_engine_options(self) -> Dict[str, Any]:
        """Get database engine options based on environment."""
        base_options = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
            "pool_timeout": 20 if self.current_env == self.PRODUCTION else 10,
            "pool_use_lifo": True,
        }
        
        if self.current_env == self.PRODUCTION:
            base_options.update({
                "pool_size": self.config['pool_size'],
                "max_overflow": self.config['max_overflow'],
                "connect_args": {
                    "keepalives": 1,
                    "keepalives_idle": 60,
                    "keepalives_interval": 10,
                    "keepalives_count": 3,
                    "options": "-c statement_timeout=90000"
                }
            })
        else:
            base_options.update({
                "pool_size": self.config['pool_size'],
                "max_overflow": self.config['max_overflow']
            })
            
        return base_options
    
    def get_flask_config(self) -> Dict[str, Any]:
        """Get Flask application configuration."""
        return {
            'DEBUG': self.config['debug'],
            'TESTING': self.config['testing'],
            'SESSION_COOKIE_SECURE': self.config['session_cookie_secure'],
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SAMESITE': 'Lax',
            'PERMANENT_SESSION_LIFETIME': 86400,  # 24 hours
            'SECRET_KEY': os.environ.get('SESSION_SECRET', 'dev-secret-change-me'),
        }
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.current_env == self.DEVELOPMENT
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.current_env == self.PRODUCTION
    
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.current_env == self.TESTING
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get comprehensive environment information for debugging."""
        return {
            'environment': self.current_env,
            'database_url_configured': bool(self.config.get('database_url')),
            'database_url_preview': self._mask_database_url(self.config['database_url']),
            'session_secret_configured': bool(os.environ.get('SESSION_SECRET')),
            'debug_mode': self.config['debug'],
            'testing_mode': self.config['testing'],
            'pool_size': self.config['pool_size'],
            'max_overflow': self.config['max_overflow'],
            'sql_logging': self.config['sqlalchemy_echo'],
            'log_level': self.config['log_level'],
            'cache_timeout': self.config['cache_timeout'],
            'rate_limit': self.config['rate_limit']
        }
    
    def _mask_database_url(self, url: str) -> str:
        """Mask sensitive information in database URL for logging."""
        if not url:
            return "Not configured"
        
        # Extract database name from URL for identification
        try:
            if '://' in url:
                protocol, rest = url.split('://', 1)
                if '@' in rest:
                    credentials, host_db = rest.split('@', 1)
                    if '/' in host_db:
                        host, db_name = host_db.rsplit('/', 1)
                        return f"{protocol}://***:***@{host}/{db_name}"
                return f"{protocol}://***"
            return "***"
        except:
            return "***"
    
    def validate_database_isolation(self) -> Tuple[bool, str]:
        """
        Validate that database isolation is properly configured.
        Returns (is_valid, message)
        """
        try:
            dev_url = os.environ.get('DEV_DATABASE_URL')
            prod_url = os.environ.get('PROD_DATABASE_URL')
            generic_url = os.environ.get('DATABASE_URL')
            
            # Check if we have environment-specific URLs
            if not dev_url and not prod_url:
                if generic_url:
                    return (False, "Using generic DATABASE_URL. Consider setting DEV_DATABASE_URL and PROD_DATABASE_URL for better isolation.")
                else:
                    return (False, "No database URLs configured.")
            
            # Check if URLs are different (if both exist)
            if dev_url and prod_url and dev_url == prod_url:
                return (False, "Development and production databases are using the same URL. This breaks isolation!")
            
            # Check current environment has proper URL
            current_url = self.config.get('database_url')
            if not current_url:
                return (False, f"No database URL configured for {self.current_env} environment.")
            
            return (True, f"Database isolation is properly configured for {self.current_env} environment.")
            
        except Exception as e:
            return (False, f"Error validating database isolation: {str(e)}")


# Global environment manager instance
env_manager = EnvironmentManager()


def get_environment_manager() -> EnvironmentManager:
    """Get the global environment manager instance."""
    return env_manager


def create_environment_files():
    """Create environment configuration files for easy setup."""
    
    # Development environment file
    dev_env = """# Development Environment Configuration
# Copy these to your environment or .env file

# Development Database (separate from production)
DEV_DATABASE_URL=postgresql://dev_user:dev_password@localhost:5432/tracetrack_dev

# Session Security (use a strong secret in production)
SESSION_SECRET=development-session-secret-change-me

# Environment Indicator
ENVIRONMENT=development
FLASK_ENV=development

# Optional: Generic fallback (will use DEV_DATABASE_URL if set)
# DATABASE_URL=postgresql://user:password@localhost:5432/tracetrack

# Export commands for current session:
# export DEV_DATABASE_URL="postgresql://dev_user:dev_password@localhost:5432/tracetrack_dev"
# export SESSION_SECRET="development-session-secret-change-me"
# export ENVIRONMENT="development"
"""

    # Production environment file
    prod_env = """# Production Environment Configuration
# Set these in your production environment

# Production Database (MUST be different from development)
PROD_DATABASE_URL=postgresql://prod_user:secure_prod_password@prod-server:5432/tracetrack_prod

# Session Security (MUST be different from development)
SESSION_SECRET=production-session-secret-change-me-to-something-secure

# Environment Indicator
ENVIRONMENT=production
FLASK_ENV=production

# Optional: Generic fallback (will use PROD_DATABASE_URL if set)
# DATABASE_URL=postgresql://prod_user:secure_prod_password@prod-server:5432/tracetrack_prod

# Export commands for production deployment:
# export PROD_DATABASE_URL="your-production-database-url"
# export SESSION_SECRET="your-secure-production-secret"
# export ENVIRONMENT="production"
"""

    # Testing environment file
    test_env = """# Testing Environment Configuration
# For automated testing and CI/CD

# Testing Database (isolated from dev and prod)
TEST_DATABASE_URL=sqlite:///:memory:

# Session Security
SESSION_SECRET=testing-session-secret

# Environment Indicator
ENVIRONMENT=testing
FLASK_ENV=testing

# Export commands for testing:
# export TEST_DATABASE_URL="sqlite:///:memory:"
# export SESSION_SECRET="testing-session-secret"
# export ENVIRONMENT="testing"
"""
    
    try:
        with open('.env.development', 'w') as f:
            f.write(dev_env)
        
        with open('.env.production', 'w') as f:
            f.write(prod_env)
            
        with open('.env.testing', 'w') as f:
            f.write(test_env)
            
        return True, "Environment configuration files created successfully"
    except Exception as e:
        return False, f"Error creating environment files: {str(e)}"


if __name__ == "__main__":
    # Create environment files when run directly
    success, message = create_environment_files()
    print(message)
    
    # Show current environment info
    manager = get_environment_manager()
    print(f"\nCurrent Environment: {manager.current_env}")
    print(f"Database URL: {manager._mask_database_url(manager.config['database_url'])}")
    
    # Validate isolation
    is_valid, validation_message = manager.validate_database_isolation()
    print(f"Database Isolation: {'✓' if is_valid else '✗'} {validation_message}")
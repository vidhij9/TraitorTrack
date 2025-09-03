#!/usr/bin/env python
"""
Test script to verify environment detection and database configuration
"""
import os

def get_current_environment():
    """Detect current environment - matching app_clean.py logic"""
    # Check explicit environment variable first
    env = os.environ.get('ENVIRONMENT', '').lower()
    if env == 'production':
        return 'production'
    
    # Check if we're on the actual production domain
    replit_domains = os.environ.get('REPLIT_DOMAINS', '')
    
    # Production detection - must be on traitor-track.replit.app but NOT on replit.dev
    if 'traitor-track.replit.app' in replit_domains and 'replit.dev' not in replit_domains:
        return 'production'
    
    # Default to development for Replit testing and local dev
    return 'development'

def get_database_url():
    """Get appropriate database URL based on environment"""
    current_env = get_current_environment()
    
    # For production, use AWS RDS
    if current_env == 'production':
        prod_url = os.environ.get('PRODUCTION_DATABASE_URL')
        if prod_url:
            return ('AWS RDS (Production)', prod_url[:50] + '...' if len(prod_url) > 50 else prod_url)
        else:
            # Fall back to regular DATABASE_URL even in production if AWS not configured
            dev_url = os.environ.get('DATABASE_URL')
            if dev_url:
                return ('Replit DB (Production Fallback)', dev_url[:50] + '...')
    
    # For development/testing, use Replit's DATABASE_URL
    dev_url = os.environ.get('DATABASE_URL')
    if dev_url:
        return ('Replit DB (Testing)', dev_url[:50] + '...')
    
    return ('No Database', 'No database URL configured')

# Run the test
print("=" * 60)
print("Environment Configuration Test")
print("=" * 60)

# Check environment
current_env = get_current_environment()
print(f"\n1. DETECTED ENVIRONMENT: {current_env}")
print(f"   - ENVIRONMENT var: {os.environ.get('ENVIRONMENT', 'not set')}")
print(f"   - REPLIT_DOMAINS: {os.environ.get('REPLIT_DOMAINS', 'not set')[:100]}")

# Check database configuration
db_type, db_url = get_database_url()
print(f"\n2. DATABASE CONFIGURATION:")
print(f"   - Type: {db_type}")
print(f"   - URL: {db_url}")

# Check if both database URLs are available
print(f"\n3. AVAILABLE DATABASE URLS:")
prod_db = os.environ.get('PRODUCTION_DATABASE_URL')
dev_db = os.environ.get('DATABASE_URL')

if prod_db:
    print(f"   ✓ PRODUCTION_DATABASE_URL (AWS RDS): Configured")
    if 'amazonaws.com' in prod_db:
        print(f"     - Confirmed AWS RDS endpoint")
else:
    print(f"   ✗ PRODUCTION_DATABASE_URL (AWS RDS): Not configured")

if dev_db:
    print(f"   ✓ DATABASE_URL (Replit): Configured")
else:
    print(f"   ✗ DATABASE_URL (Replit): Not configured")

print("\n" + "=" * 60)
print("CONFIGURATION SUMMARY:")
print("=" * 60)

if current_env == 'production':
    if prod_db:
        print("✓ PRODUCTION MODE: Using AWS RDS database")
        print("  This is the correct configuration for traitor-track.replit.app")
    else:
        print("⚠ PRODUCTION MODE: AWS RDS not configured, using Replit DB as fallback")
        print("  Consider setting PRODUCTION_DATABASE_URL for AWS RDS")
else:
    print("✓ TESTING/DEVELOPMENT MODE: Using Replit database")
    print("  This is the correct configuration for testing on replit.dev")
    if prod_db:
        print("  Note: AWS RDS is configured but not used in testing mode")

print("\n" + "=" * 60)
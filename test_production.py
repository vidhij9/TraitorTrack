#!/usr/bin/env python3
"""
Production deployment test script
Tests database connectivity and environment detection
"""
import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_production_environment():
    """Test production environment detection and database connection"""
    print("=== PRODUCTION DEPLOYMENT TEST ===")
    
    # Test 1: Environment Detection
    print("\n1. Testing Environment Detection:")
    replit_domains = os.environ.get('REPLIT_DOMAINS', 'not-set')
    print(f"   REPLIT_DOMAINS: {replit_domains}")
    
    # Simulate production environment
    os.environ['REPLIT_DOMAINS'] = 'traitortrack.replit.app'
    
    try:
        import app_clean
        env = app_clean.get_current_environment()
        print(f"   Environment detected: {env}")
        print("   ✓ Environment detection: PASS")
    except Exception as e:
        print(f"   ❌ Environment detection: FAIL - {e}")
        return False
    
    # Test 2: Database URL
    print("\n2. Testing Database Configuration:")
    try:
        db_url = app_clean.get_database_url()
        print("   ✓ Database URL retrieval: PASS")
        print("   ✓ Using production database")
    except Exception as e:
        print(f"   ❌ Database URL: FAIL - {e}")
        return False
    
    # Test 3: Flask App Creation
    print("\n3. Testing Flask App Creation:")
    try:
        app = app_clean.app
        print(f"   ✓ Flask app created: {app.name}")
        print("   ✓ App configuration: PASS")
    except Exception as e:
        print(f"   ❌ Flask app creation: FAIL - {e}")
        return False
    
    # Test 4: Database Connection
    print("\n4. Testing Database Connection:")
    try:
        with app.app_context():
            from app_clean import db
            # Test database connection with a simple query
            result = db.engine.execute("SELECT 1")
            print("   ✓ Database connection: PASS")
            print("   ✓ Production database accessible")
    except Exception as e:
        print(f"   ❌ Database connection: FAIL - {e}")
        print("   This is likely the deployment issue!")
        return False
    
    print("\n=== ALL TESTS PASSED ===")
    print("Production deployment should work correctly.")
    return True

if __name__ == "__main__":
    success = test_production_environment()
    sys.exit(0 if success else 1)
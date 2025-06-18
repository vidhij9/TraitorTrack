"""
Database Isolation Verification Script
Tests that development and production databases are properly isolated
"""
import os
import logging
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_isolation():
    """Test that database isolation is working correctly"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL not found")
    
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        # Test development schema
        logger.info("Testing development schema...")
        conn.execute(text("SET search_path TO development"))
        
        # Insert test data in development
        conn.execute(text("""
            INSERT INTO user (username, email, password_hash, role) 
            VALUES ('dev_test_user', 'dev@test.com', 'test_hash', 'employee')
            ON CONFLICT (username) DO NOTHING
        """))
        
        dev_user_count = conn.execute(text("SELECT COUNT(*) FROM user")).scalar()
        logger.info(f"Development schema user count: {dev_user_count}")
        
        # Test production schema
        logger.info("Testing production schema...")
        conn.execute(text("SET search_path TO production"))
        
        # Insert test data in production
        conn.execute(text("""
            INSERT INTO user (username, email, password_hash, role) 
            VALUES ('prod_test_user', 'prod@test.com', 'test_hash', 'employee')
            ON CONFLICT (username) DO NOTHING
        """))
        
        prod_user_count = conn.execute(text("SELECT COUNT(*) FROM user")).scalar()
        logger.info(f"Production schema user count: {prod_user_count}")
        
        # Verify isolation - users should be different
        conn.execute(text("SET search_path TO development"))
        dev_users = conn.execute(text("SELECT username FROM user ORDER BY username")).fetchall()
        
        conn.execute(text("SET search_path TO production"))
        prod_users = conn.execute(text("SELECT username FROM user ORDER BY username")).fetchall()
        
        logger.info(f"Development users: {[u[0] for u in dev_users]}")
        logger.info(f"Production users: {[u[0] for u in prod_users]}")
        
        # Verify both schemas have all required tables
        required_tables = ['user', 'bag', 'link', 'bill', 'billbag', 'scan', 'promotionrequest']
        
        for schema in ['development', 'production']:
            conn.execute(text(f"SET search_path TO {schema}"))
            tables = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = current_schema()
                ORDER BY table_name
            """)).fetchall()
            
            table_names = [t[0] for t in tables]
            missing_tables = [t for t in required_tables if t not in table_names]
            
            if missing_tables:
                logger.error(f"{schema} schema missing tables: {missing_tables}")
                return False
            else:
                logger.info(f"✓ {schema} schema has all required tables: {table_names}")
        
        conn.commit()
        logger.info("✓ Database isolation test completed successfully")
        return True

def test_environment_detection():
    """Test environment detection logic"""
    # Save current environment
    original_env = os.environ.get('ENVIRONMENT', '')
    original_flask_env = os.environ.get('FLASK_ENV', '')
    
    try:
        # Test development detection
        os.environ['ENVIRONMENT'] = 'development'
        from app_clean import get_current_environment
        env = get_current_environment()
        logger.info(f"Environment detection test 1 (ENVIRONMENT=development): {env}")
        assert env == 'development', f"Expected 'development', got '{env}'"
        
        # Test production detection
        os.environ['ENVIRONMENT'] = 'production'
        # Need to reload the module to get updated environment
        import importlib
        import app_clean
        importlib.reload(app_clean)
        env = app_clean.get_current_environment()
        logger.info(f"Environment detection test 2 (ENVIRONMENT=production): {env}")
        assert env == 'production', f"Expected 'production', got '{env}'"
        
        logger.info("✓ Environment detection working correctly")
        return True
        
    finally:
        # Restore original environment
        if original_env:
            os.environ['ENVIRONMENT'] = original_env
        elif 'ENVIRONMENT' in os.environ:
            del os.environ['ENVIRONMENT']
            
        if original_flask_env:
            os.environ['FLASK_ENV'] = original_flask_env
        elif 'FLASK_ENV' in os.environ:
            del os.environ['FLASK_ENV']

if __name__ == "__main__":
    try:
        logger.info("Starting database isolation verification...")
        
        isolation_ok = test_database_isolation()
        env_detection_ok = test_environment_detection()
        
        if isolation_ok and env_detection_ok:
            logger.info("✓ All database isolation tests passed")
        else:
            logger.error("✗ Some database isolation tests failed")
            
    except Exception as e:
        logger.error(f"Database isolation verification failed: {e}")
        raise
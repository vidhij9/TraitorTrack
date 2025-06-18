"""
Database Isolation Fix Script
Ensures proper separation between development and production databases
"""
import os
import logging
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.exc import ProgrammingError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get the database URL from environment"""
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise ValueError("DATABASE_URL environment variable not set")
    return url

def create_schemas_and_tables():
    """Create proper schemas and ensure all tables exist in both environments"""
    database_url = get_database_url()
    if not database_url:
        raise ValueError("DATABASE_URL not found")
    
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        # Create schemas if they don't exist
        try:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS development"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS production"))
            logger.info("✓ Schemas created successfully")
        except Exception as e:
            logger.error(f"Schema creation error: {e}")
        
        # Set search path to development for table creation
        conn.execute(text("SET search_path TO development"))
        
        # Create all tables in development schema
        create_tables_in_schema(conn, 'development')
        
        # Set search path to production for table creation
        conn.execute(text("SET search_path TO production"))
        
        # Create all tables in production schema
        create_tables_in_schema(conn, 'production')
        
        # Reset search path
        conn.execute(text("SET search_path TO public"))
        
        conn.commit()
        logger.info("✓ Database isolation setup completed")

def create_tables_in_schema(conn, schema_name):
    """Create all required tables in the specified schema"""
    logger.info(f"Creating tables in {schema_name} schema...")
    
    # User table
    conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {schema_name}.user (
            id SERIAL PRIMARY KEY,
            username VARCHAR(64) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
            password_hash VARCHAR(256) NOT NULL,
            role VARCHAR(20) DEFAULT 'employee',
            verification_token VARCHAR(100),
            verified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Bag table
    conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {schema_name}.bag (
            id SERIAL PRIMARY KEY,
            qr_id VARCHAR(255) UNIQUE NOT NULL,
            type VARCHAR(10) NOT NULL,
            name VARCHAR(100),
            child_count INTEGER,
            parent_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # Link table
    conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {schema_name}.link (
            id SERIAL PRIMARY KEY,
            parent_bag_id INTEGER NOT NULL,
            child_bag_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_bag_id) REFERENCES {schema_name}.bag(id) ON DELETE CASCADE,
            FOREIGN KEY (child_bag_id) REFERENCES {schema_name}.bag(id) ON DELETE CASCADE,
            UNIQUE(parent_bag_id, child_bag_id)
        )
    """))
    
    # Bill table
    conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {schema_name}.bill (
            id SERIAL PRIMARY KEY,
            bill_id VARCHAR(50) UNIQUE NOT NULL,
            description TEXT,
            parent_bag_count INTEGER DEFAULT 1,
            status VARCHAR(20) DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    # BillBag table
    conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {schema_name}.billbag (
            id SERIAL PRIMARY KEY,
            bill_id INTEGER NOT NULL,
            parent_bag_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (bill_id) REFERENCES {schema_name}.bill(id) ON DELETE CASCADE,
            FOREIGN KEY (parent_bag_id) REFERENCES {schema_name}.bag(id) ON DELETE CASCADE,
            UNIQUE(bill_id, parent_bag_id)
        )
    """))
    
    # Scan table
    conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {schema_name}.scan (
            id SERIAL PRIMARY KEY,
            parent_bag_id INTEGER,
            child_bag_id INTEGER,
            user_id INTEGER NOT NULL,
            location VARCHAR(100),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            scan_type VARCHAR(20) DEFAULT 'regular',
            notes TEXT,
            FOREIGN KEY (parent_bag_id) REFERENCES {schema_name}.bag(id) ON DELETE SET NULL,
            FOREIGN KEY (child_bag_id) REFERENCES {schema_name}.bag(id) ON DELETE SET NULL,
            FOREIGN KEY (user_id) REFERENCES {schema_name}.user(id) ON DELETE CASCADE
        )
    """))
    
    # PromotionRequest table
    conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {schema_name}.promotionrequest (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            current_role_name VARCHAR(20) NOT NULL,
            requested_role_name VARCHAR(20) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_date TIMESTAMP,
            approved_by INTEGER,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES {schema_name}.user(id) ON DELETE CASCADE,
            FOREIGN KEY (approved_by) REFERENCES {schema_name}.user(id) ON DELETE SET NULL
        )
    """))
    
    # Create indexes for performance
    create_indexes_for_schema(conn, schema_name)
    
    logger.info(f"✓ All tables created in {schema_name} schema")

def create_indexes_for_schema(conn, schema_name):
    """Create performance indexes for the schema"""
    indexes = [
        f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_bag_qr_id ON {schema_name}.bag(qr_id)",
        f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_bag_type ON {schema_name}.bag(type)",
        f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_bag_created_at ON {schema_name}.bag(created_at)",
        f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_scan_timestamp ON {schema_name}.scan(timestamp)",
        f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_scan_parent_bag ON {schema_name}.scan(parent_bag_id)",
        f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_scan_child_bag ON {schema_name}.scan(child_bag_id)",
        f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_user_username ON {schema_name}.user(username)",
        f"CREATE INDEX IF NOT EXISTS idx_{schema_name}_bill_bill_id ON {schema_name}.bill(bill_id)",
    ]
    
    for index_sql in indexes:
        try:
            conn.execute(text(index_sql))
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")

def verify_schemas():
    """Verify that both schemas have all required tables"""
    database_url = get_database_url()
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        # Check development schema
        dev_tables = conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'development'
            ORDER BY table_name
        """)).fetchall()
        
        # Check production schema
        prod_tables = conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'production'
            ORDER BY table_name
        """)).fetchall()
        
        dev_table_names = [t[0] for t in dev_tables]
        prod_table_names = [t[0] for t in prod_tables]
        
        logger.info(f"Development schema tables: {dev_table_names}")
        logger.info(f"Production schema tables: {prod_table_names}")
        
        required_tables = ['user', 'bag', 'link', 'bill', 'billbag', 'scan', 'promotionrequest']
        
        dev_missing = [t for t in required_tables if t not in dev_table_names]
        prod_missing = [t for t in required_tables if t not in prod_table_names]
        
        if dev_missing:
            logger.error(f"Missing tables in development: {dev_missing}")
        else:
            logger.info("✓ All required tables present in development schema")
            
        if prod_missing:
            logger.error(f"Missing tables in production: {prod_missing}")
        else:
            logger.info("✓ All required tables present in production schema")
        
        return len(dev_missing) == 0 and len(prod_missing) == 0

def fix_environment_detection():
    """Fix the environment detection logic"""
    return """
# Fixed environment detection based on multiple indicators
def get_current_environment():
    # Check explicit environment variable first
    env = os.environ.get('ENVIRONMENT', '').lower()
    if env in ['production', 'prod']:
        return 'production'
    elif env in ['development', 'dev']:
        return 'development'
    
    # Check Flask environment
    flask_env = os.environ.get('FLASK_ENV', '').lower()
    if flask_env == 'production':
        return 'production'
    elif flask_env in ['development', 'dev']:
        return 'development'
    
    # Check Replit environment indicators
    replit_env = os.environ.get('REPLIT_ENVIRONMENT', '').lower()
    if replit_env == 'production':
        return 'production'
    
    # Default to development for safety
    return 'development'
"""

if __name__ == "__main__":
    try:
        logger.info("Starting database isolation fix...")
        create_schemas_and_tables()
        
        logger.info("Verifying schema setup...")
        if verify_schemas():
            logger.info("✓ Database isolation setup completed successfully")
        else:
            logger.error("✗ Database isolation setup incomplete")
            
    except Exception as e:
        logger.error(f"Database isolation fix failed: {e}")
        raise
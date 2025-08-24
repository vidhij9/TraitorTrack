
import os
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
import psycopg2

# Ultra-optimized connection pool configuration
DATABASE_URL = os.environ.get('DATABASE_URL')

# Create optimized engine
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=50,           # Base pool size for 50 concurrent users
    max_overflow=100,       # Allow up to 150 total connections
    pool_timeout=10,        # Wait max 10 seconds for connection
    pool_recycle=300,       # Recycle connections every 5 minutes
    pool_pre_ping=True,     # Verify connections before use
    echo_pool=False,        # Disable pool logging for performance
    
    # Connection arguments
    connect_args={
        'connect_timeout': 10,
        'options': '-c statement_timeout=30000',  # 30 second statement timeout
        'keepalives': 1,
        'keepalives_idle': 30,
        'keepalives_interval': 10,
        'keepalives_count': 5,
        'sslmode': 'prefer'
    },
    
    # Execution options
    execution_options={
        "isolation_level": "READ COMMITTED",
        "postgresql_readonly": False,
        "postgresql_deferrable": False
    }
)

# Warm up the pool
def warm_pool():
    """Pre-create connections for faster initial responses"""
    connections = []
    for i in range(min(20, engine.pool.size())):
        try:
            conn = engine.connect()
            connections.append(conn)
        except:
            pass
    
    # Close connections to return to pool
    for conn in connections:
        conn.close()

# Call on startup
warm_pool()

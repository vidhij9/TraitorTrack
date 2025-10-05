"""
Load 1.5M test bags into PostgreSQL using COPY for maximum speed
"""
import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

def get_db_url():
    """Get database URL from environment"""
    return os.environ.get('DATABASE_URL')

def load_data():
    """Load CSV data into database using COPY"""
    db_url = get_db_url()
    if not db_url:
        print("ERROR: DATABASE_URL not found!")
        return
    
    print("=" * 60)
    print("LOADING TEST DATA INTO DATABASE")
    print("=" * 60)
    print()
    
    # Create engine without pooling for bulk operations
    engine = create_engine(db_url, poolclass=NullPool)
    
    with engine.connect() as conn:
        # Start timing
        total_start = time.time()
        
        # 1. Disable triggers and indexes temporarily (optional, for speed)
        print("Step 1: Preparing database...")
        conn.execute(text("SET session_replication_role = replica;"))
        conn.commit()
        
        # 2. Load parent bags
        print("\nStep 2: Loading parent bags...")
        start = time.time()
        
        # First, insert directly with raw SQL for speed
        conn.execute(text("""
            COPY bag (qr_id, type, user_id, dispatch_area, created_at)
            FROM '/tmp/parent_bags.csv'
            WITH (FORMAT csv)
        """))
        conn.commit()
        
        elapsed = time.time() - start
        print(f"  ✓ Loaded parent bags in {elapsed:.2f}s")
        
        # 3. Load child bags
        print("\nStep 3: Loading child bags...")
        start = time.time()
        
        conn.execute(text("""
            COPY bag (qr_id, type, user_id, dispatch_area, created_at)
            FROM '/tmp/child_bags.csv'
            WITH (FORMAT csv)
        """))
        conn.commit()
        
        elapsed = time.time() - start
        print(f"  ✓ Loaded child bags in {elapsed:.2f}s")
        
        # 4. Load links
        print("\nStep 4: Loading parent-child links...")
        start = time.time()
        
        # Note: Adjust table/column names based on your schema
        conn.execute(text("""
            COPY link (parent_bag_id, child_bag_id, created_at)
            FROM '/tmp/bag_links.csv'
            WITH (FORMAT csv)
        """))
        conn.commit()
        
        elapsed = time.time() - start
        print(f"  ✓ Loaded links in {elapsed:.2f}s")
        
        # 5. Re-enable triggers and rebuild indexes
        print("\nStep 5: Rebuilding indexes...")
        start = time.time()
        
        conn.execute(text("SET session_replication_role = DEFAULT;"))
        conn.execute(text("VACUUM ANALYZE bag;"))
        conn.execute(text("VACUUM ANALYZE link;"))
        conn.commit()
        
        elapsed = time.time() - start
        print(f"  ✓ Rebuilt indexes in {elapsed:.2f}s")
        
        # 6. Verify counts
        print("\nStep 6: Verifying data...")
        result = conn.execute(text("SELECT COUNT(*) FROM bag WHERE type = 'parent'"))
        parent_count = result.scalar()
        
        result = conn.execute(text("SELECT COUNT(*) FROM bag WHERE type = 'child'"))
        child_count = result.scalar()
        
        result = conn.execute(text("SELECT COUNT(*) FROM link"))
        link_count = result.scalar()
        
        total_elapsed = time.time() - total_start
        
        print()
        print("=" * 60)
        print("✓ DATA LOAD COMPLETE!")
        print()
        print(f"Parent bags: {parent_count:,}")
        print(f"Child bags:  {child_count:,}")
        print(f"Total bags:  {parent_count + child_count:,}")
        print(f"Links:       {link_count:,}")
        print()
        print(f"Total time:  {total_elapsed:.2f}s")
        print(f"Speed:       {(parent_count + child_count) / total_elapsed:,.0f} bags/sec")
        print("=" * 60)

if __name__ == '__main__':
    load_data()

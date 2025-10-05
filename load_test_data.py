"""
Load 1.5M test bags into PostgreSQL using bulk inserts
Works with remote databases like Neon
"""
import os
import time
import csv
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

def get_db_url():
    """Get database URL from environment"""
    return os.environ.get('DATABASE_URL')

def load_data_bulk():
    """Load CSV data using bulk inserts (works with remote DB)"""
    db_url = get_db_url()
    if not db_url:
        print("ERROR: DATABASE_URL not found!")
        return
    
    print("=" * 60)
    print("LOADING TEST DATA INTO DATABASE")
    print("Using bulk INSERT (Neon-compatible)")
    print("=" * 60)
    print()
    
    # Create engine
    engine = create_engine(db_url, poolclass=NullPool)
    
    with engine.connect() as conn:
        total_start = time.time()
        
        # 1. Load parent bags
        print("Step 1: Loading 50,000 parent bags...")
        start = time.time()
        
        with open('/tmp/parent_bags.csv', 'r') as f:
            reader = csv.reader(f)
            batch = []
            batch_size = 5000
            total_inserted = 0
            
            for row in reader:
                qr_id, bag_type, user_id, dispatch_area, created_at = row
                batch.append({
                    'qr_id': qr_id,
                    'type': bag_type,
                    'user_id': int(user_id),
                    'dispatch_area': dispatch_area,
                    'created_at': created_at
                })
                
                if len(batch) >= batch_size:
                    # Execute batch insert
                    conn.execute(
                        text("""
                            INSERT INTO bag (qr_id, type, user_id, dispatch_area, created_at)
                            VALUES (:qr_id, :type, :user_id, :dispatch_area, :created_at)
                        """),
                        batch
                    )
                    conn.commit()
                    total_inserted += len(batch)
                    print(f"  Inserted {total_inserted:,} parent bags...")
                    batch = []
            
            # Insert remaining
            if batch:
                conn.execute(
                    text("""
                        INSERT INTO bag (qr_id, type, user_id, dispatch_area, created_at)
                        VALUES (:qr_id, :type, :user_id, :dispatch_area, :created_at)
                    """),
                    batch
                )
                conn.commit()
                total_inserted += len(batch)
        
        elapsed = time.time() - start
        print(f"  ✓ Loaded {total_inserted:,} parent bags in {elapsed:.2f}s")
        print(f"    Speed: {total_inserted/elapsed:,.0f} bags/sec")
        
        # 2. Load child bags
        print("\nStep 2: Loading 1,450,000 child bags...")
        print("  (This will take 3-5 minutes...)")
        start = time.time()
        
        with open('/tmp/child_bags.csv', 'r') as f:
            reader = csv.reader(f)
            batch = []
            batch_size = 10000  # Larger batch for children
            total_inserted = 0
            
            for row in reader:
                qr_id, bag_type, user_id, dispatch_area, created_at = row
                batch.append({
                    'qr_id': qr_id,
                    'type': bag_type,
                    'user_id': int(user_id),
                    'dispatch_area': dispatch_area,
                    'created_at': created_at
                })
                
                if len(batch) >= batch_size:
                    conn.execute(
                        text("""
                            INSERT INTO bag (qr_id, type, user_id, dispatch_area, created_at)
                            VALUES (:qr_id, :type, :user_id, :dispatch_area, :created_at)
                        """),
                        batch
                    )
                    conn.commit()
                    total_inserted += len(batch)
                    if total_inserted % 100000 == 0:
                        elapsed_so_far = time.time() - start
                        print(f"  Inserted {total_inserted:,} child bags... ({elapsed_so_far:.1f}s)")
                    batch = []
            
            if batch:
                conn.execute(
                    text("""
                        INSERT INTO bag (qr_id, type, user_id, dispatch_area, created_at)
                        VALUES (:qr_id, :type, :user_id, :dispatch_area, :created_at)
                    """),
                    batch
                )
                conn.commit()
                total_inserted += len(batch)
        
        elapsed = time.time() - start
        print(f"  ✓ Loaded {total_inserted:,} child bags in {elapsed:.2f}s")
        print(f"    Speed: {total_inserted/elapsed:,.0f} bags/sec")
        
        # 3. Create parent-child relationships using UPDATE (faster than links table)
        print("\nStep 3: Creating parent-child relationships...")
        print("  (Linking children to parents using parent_id...)")
        start = time.time()
        
        # Read links and batch update
        with open('/tmp/bag_links.csv', 'r') as f:
            reader = csv.reader(f)
            updates = []
            batch_size = 10000
            total_updated = 0
            
            for row in reader:
                parent_bag_id, child_bag_id, _ = row
                updates.append({
                    'parent_id': int(parent_bag_id),
                    'child_id': int(child_bag_id)
                })
                
                if len(updates) >= batch_size:
                    # Bulk update using CASE statement
                    case_stmt = " ".join([
                        f"WHEN {u['child_id']} THEN {u['parent_id']}"
                        for u in updates
                    ])
                    ids = ",".join([str(u['child_id']) for u in updates])
                    
                    conn.execute(text(f"""
                        UPDATE bag
                        SET parent_id = CASE id {case_stmt} END
                        WHERE id IN ({ids})
                    """))
                    conn.commit()
                    
                    total_updated += len(updates)
                    if total_updated % 100000 == 0:
                        elapsed_so_far = time.time() - start
                        print(f"  Linked {total_updated:,} children... ({elapsed_so_far:.1f}s)")
                    updates = []
            
            if updates:
                case_stmt = " ".join([
                    f"WHEN {u['child_id']} THEN {u['parent_id']}"
                    for u in updates
                ])
                ids = ",".join([str(u['child_id']) for u in updates])
                
                conn.execute(text(f"""
                    UPDATE bag
                    SET parent_id = CASE id {case_stmt} END
                    WHERE id IN ({ids})
                """))
                conn.commit()
                total_updated += len(updates)
        
        elapsed = time.time() - start
        print(f"  ✓ Linked {total_updated:,} children in {elapsed:.2f}s")
        
        # 4. Update parent bag child counts
        print("\nStep 4: Updating parent bag child counts...")
        start = time.time()
        
        conn.execute(text("""
            UPDATE bag AS parent
            SET child_count = (
                SELECT COUNT(*)
                FROM bag AS child
                WHERE child.parent_id = parent.id
            )
            WHERE parent.type = 'parent'
        """))
        conn.commit()
        
        elapsed = time.time() - start
        print(f"  ✓ Updated child counts in {elapsed:.2f}s")
        
        # 5. Create indexes for performance
        print("\nStep 5: Creating performance indexes...")
        start = time.time()
        
        # Create indexes if they don't exist
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_bag_qr_id ON bag(qr_id);
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_bag_type ON bag(type);
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_bag_parent_id ON bag(parent_id);
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_bag_dispatch_area ON bag(dispatch_area);
        """))
        conn.commit()
        
        elapsed = time.time() - start
        print(f"  ✓ Created indexes in {elapsed:.2f}s")
        
        # 6. Analyze for query optimization
        print("\nStep 6: Analyzing tables...")
        start = time.time()
        
        conn.execute(text("ANALYZE bag;"))
        conn.commit()
        
        elapsed = time.time() - start
        print(f"  ✓ Analyzed tables in {elapsed:.2f}s")
        
        # 7. Verify counts
        print("\nStep 7: Verifying data...")
        result = conn.execute(text("SELECT COUNT(*) FROM bag WHERE type = 'parent'"))
        parent_count = result.scalar()
        
        result = conn.execute(text("SELECT COUNT(*) FROM bag WHERE type = 'child'"))
        child_count = result.scalar()
        
        result = conn.execute(text("SELECT COUNT(*) FROM bag WHERE parent_id IS NOT NULL"))
        linked_count = result.scalar()
        
        total_elapsed = time.time() - total_start
        
        print()
        print("=" * 60)
        print("✓ DATA LOAD COMPLETE!")
        print()
        print(f"Parent bags:     {parent_count:,}")
        print(f"Child bags:      {child_count:,}")
        print(f"Total bags:      {parent_count + child_count:,}")
        print(f"Linked children: {linked_count:,}")
        print()
        print(f"Total time:      {total_elapsed/60:.1f} minutes")
        print(f"Average speed:   {(parent_count + child_count) / total_elapsed:,.0f} bags/sec")
        print("=" * 60)
        print()
        print("✓ Database is ready for load testing!")
        print("  Run: locust -f locustfile.py --host=http://localhost:5000")

if __name__ == '__main__':
    load_data_bulk()

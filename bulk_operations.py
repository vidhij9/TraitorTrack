"""
Bulk Operations for TraceTrack
Handles 800,000+ bags with millisecond performance
"""
import time
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from app import db
from models import Bag, Bill, BillBag, Scan
import threading
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import psycopg2
from psycopg2.extras import execute_values
import os

DATABASE_URL = os.environ.get('DATABASE_URL')

class BulkOperations:
    def __init__(self):
        self.batch_size = 1000
        self.queue = Queue()
        self.executor = ThreadPoolExecutor(max_workers=10)
        
    def bulk_insert_bags(self, bags_data):
        """Insert bags in bulk using PostgreSQL COPY"""
        start_time = time.time()
        
        # Prepare data for COPY
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        try:
            # Use COPY for ultra-fast insertion
            from io import StringIO
            buffer = StringIO()
            
            for bag in bags_data:
                line = f"{bag['qr_id']}\t{bag['type']}\t{bag.get('parent_bag_id', '\\N')}\t"
                line += f"{bag.get('status', 'pending')}\t{bag.get('weight_kg', 0)}\t"
                line += f"{bag.get('created_at', 'now()')}\n"
                buffer.write(line)
            
            buffer.seek(0)
            cur.copy_from(
                buffer,
                'bag',
                columns=('qr_id', 'type', 'parent_bag_id', 'status', 'weight_kg', 'created_at'),
                sep='\t',
                null='\\N'
            )
            conn.commit()
            
            elapsed = time.time() - start_time
            print(f"✅ Inserted {len(bags_data)} bags in {elapsed*1000:.2f}ms")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Bulk insert error: {e}")
            return False
        finally:
            cur.close()
            conn.close()
    
    def bulk_update_bag_status(self, bag_ids, new_status):
        """Update multiple bag statuses in one query"""
        start_time = time.time()
        
        try:
            # Use SQLAlchemy bulk update
            db.session.execute(
                text("""
                    UPDATE bag 
                    SET status = :status, updated_at = NOW()
                    WHERE id = ANY(:bag_ids)
                """),
                {'status': new_status, 'bag_ids': bag_ids}
            )
            db.session.commit()
            
            elapsed = time.time() - start_time
            print(f"✅ Updated {len(bag_ids)} bags in {elapsed*1000:.2f}ms")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Bulk update error: {e}")
            return False
    
    def bulk_link_bags_to_bill(self, bill_id, bag_ids):
        """Link multiple bags to a bill in one operation"""
        start_time = time.time()
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        try:
            # Prepare bulk insert data
            data = [(bill_id, bag_id) for bag_id in bag_ids]
            
            # Use execute_values for efficient bulk insert
            execute_values(
                cur,
                "INSERT INTO bill_bag (bill_id, bag_id) VALUES %s ON CONFLICT DO NOTHING",
                data
            )
            
            # Update bill totals in one query
            cur.execute("""
                UPDATE bill 
                SET total_child_bags = (
                    SELECT COUNT(*) * 30
                    FROM bill_bag bb
                    JOIN bag b ON bb.bag_id = b.id
                    WHERE bb.bill_id = %s AND b.type = 'parent'
                ),
                total_weight_kg = (
                    SELECT COALESCE(SUM(b.weight_kg), 0)
                    FROM bill_bag bb
                    JOIN bag b ON bb.bag_id = b.id
                    WHERE bb.bill_id = %s
                )
                WHERE id = %s
            """, (bill_id, bill_id, bill_id))
            
            conn.commit()
            
            elapsed = time.time() - start_time
            print(f"✅ Linked {len(bag_ids)} bags to bill in {elapsed*1000:.2f}ms")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Bulk link error: {e}")
            return False
        finally:
            cur.close()
            conn.close()
    
    def bulk_create_parent_child_relationships(self, parent_child_map):
        """Create parent-child relationships in bulk"""
        start_time = time.time()
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        try:
            # Update all children in one query per parent
            for parent_qr, child_qrs in parent_child_map.items():
                cur.execute("""
                    UPDATE bag 
                    SET parent_bag_id = (
                        SELECT id FROM bag WHERE qr_id = %s AND type = 'parent'
                    )
                    WHERE qr_id = ANY(%s) AND type = 'child'
                """, (parent_qr, child_qrs))
            
            # Update parent bag statuses and weights
            cur.execute("""
                UPDATE bag p
                SET status = CASE 
                    WHEN (SELECT COUNT(*) FROM bag c WHERE c.parent_bag_id = p.id) = 30 
                    THEN 'completed'
                    ELSE 'pending'
                END,
                weight_kg = (SELECT COUNT(*) FROM bag c WHERE c.parent_bag_id = p.id)
                WHERE p.type = 'parent' AND p.qr_id = ANY(%s)
            """, (list(parent_child_map.keys()),))
            
            conn.commit()
            
            elapsed = time.time() - start_time
            total_children = sum(len(children) for children in parent_child_map.values())
            print(f"✅ Created {len(parent_child_map)} parent-child relationships ({total_children} children) in {elapsed*1000:.2f}ms")
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Bulk relationship error: {e}")
            return False
        finally:
            cur.close()
            conn.close()
    
    def bulk_search_bags(self, search_terms):
        """Search multiple bags in parallel"""
        start_time = time.time()
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        try:
            # Use ANY for multiple search terms
            cur.execute("""
                SELECT qr_id, type, status, weight_kg
                FROM bag
                WHERE qr_id = ANY(%s)
                LIMIT 1000
            """, (search_terms,))
            
            results = cur.fetchall()
            
            elapsed = time.time() - start_time
            print(f"✅ Searched {len(search_terms)} terms, found {len(results)} results in {elapsed*1000:.2f}ms")
            return results
            
        except Exception as e:
            print(f"❌ Bulk search error: {e}")
            return []
        finally:
            cur.close()
            conn.close()
    
    def generate_test_bags(self, count=800000):
        """Generate test bag data for load testing"""
        print(f"Generating {count:,} test bags...")
        
        parent_count = count // 30
        bags_data = []
        
        # Generate parent bags
        for i in range(parent_count):
            bags_data.append({
                'qr_id': f'SB{i:05d}',
                'type': 'parent',
                'parent_bag_id': None,
                'status': 'pending',
                'weight_kg': 0
            })
        
        # Generate child bags
        for i in range(count - parent_count):
            parent_idx = i // 30
            bags_data.append({
                'qr_id': f'CB{i:06d}',
                'type': 'child',
                'parent_bag_id': None,  # Will be linked later
                'status': 'pending',
                'weight_kg': 1
            })
        
        return bags_data
    
    def parallel_bulk_insert(self, bags_data, num_threads=10):
        """Insert bags in parallel for maximum speed"""
        start_time = time.time()
        
        # Split data into chunks
        chunk_size = len(bags_data) // num_threads
        chunks = [bags_data[i:i+chunk_size] for i in range(0, len(bags_data), chunk_size)]
        
        # Insert chunks in parallel
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(self.bulk_insert_bags, chunk) for chunk in chunks]
            results = [f.result() for f in futures]
        
        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if r)
        print(f"✅ Parallel insert completed: {success_count}/{num_threads} threads successful in {elapsed:.2f}s")
        
        return all(results)

# Singleton instance
bulk_ops = BulkOperations()

def optimize_for_bulk():
    """Optimize database for bulk operations"""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    try:
        # Temporarily disable triggers and constraints for bulk ops
        cur.execute("SET session_replication_role = 'replica'")
        
        # Increase work memory for this session
        cur.execute("SET work_mem = '256MB'")
        cur.execute("SET maintenance_work_mem = '512MB'")
        
        # Disable autovacuum temporarily
        cur.execute("ALTER TABLE bag SET (autovacuum_enabled = false)")
        cur.execute("ALTER TABLE bill_bag SET (autovacuum_enabled = false)")
        
        conn.commit()
        print("✅ Database optimized for bulk operations")
        
    except Exception as e:
        print(f"⚠️  Optimization warning: {e}")
    finally:
        cur.close()
        conn.close()

def restore_normal_mode():
    """Restore normal database operations"""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    try:
        # Re-enable triggers and constraints
        cur.execute("SET session_replication_role = 'origin'")
        
        # Re-enable autovacuum
        cur.execute("ALTER TABLE bag SET (autovacuum_enabled = true)")
        cur.execute("ALTER TABLE bill_bag SET (autovacuum_enabled = true)")
        
        # Run ANALYZE to update statistics
        cur.execute("ANALYZE bag")
        cur.execute("ANALYZE bill_bag")
        
        conn.commit()
        print("✅ Database restored to normal mode")
        
    except Exception as e:
        print(f"⚠️  Restore warning: {e}")
    finally:
        cur.close()
        conn.close()
#!/usr/bin/env python3
"""
SQL Query Profiler for Ultra-Fast Bill Scanning
================================================

Profiles individual SQL query execution times to identify optimization opportunities.
"""

import os
import sys
import time
import statistics

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from app import app, db
from models import Bag, Bill, User


def profile_individual_queries():
    """Profile individual SQL query execution times"""
    
    print("="*70)
    print("SQL QUERY PROFILER")
    print("="*70)
    
    with app.app_context():
        # Get test data
        user = User.query.filter_by(username='superadmin').first() or User.query.first()
        bill = Bill.query.filter_by(status='processing').first() or Bill.query.first()
        
        if not user or not bill:
            print("No test data found")
            return
        
        print(f"\nTest Bill ID: {bill.id}, User ID: {user.id}")
        print("-"*70)
        
        # Create a test bag
        test_qr = f"PROFILE-{int(time.time())}"
        bag = Bag(qr_id=test_qr, type='parent', name=f'Profile Test')
        db.session.add(bag)
        db.session.commit()
        bag_id = bag.id
        
        # Profile individual query components
        queries = {
            "Advisory Lock": f"SELECT pg_advisory_xact_lock({100000 + bill.id})",
            
            "Simple SELECT": "SELECT 1",
            
            "Bag Lookup (lower index)": f"SELECT id FROM bag WHERE lower(qr_id) = lower('{test_qr}')",
            
            "Bag Lookup (exact)": f"SELECT id FROM bag WHERE qr_id = '{test_qr}'",
            
            "Bill Validation": f"SELECT id, status, parent_bag_count, linked_parent_count FROM bill WHERE id = {bill.id}",
            
            "Bill-Bag Check": f"SELECT 1 FROM bill_bag WHERE bill_id = {bill.id} AND bag_id = {bag_id}",
            
            "Cross-Bill Check": f"""
                SELECT bb.bill_id 
                FROM bill_bag bb 
                JOIN bill b ON bb.bill_id = b.id 
                WHERE bb.bag_id = {bag_id} 
                AND b.status IN ('processing', 'pending')
            """,
            
            "Count Current Bags": f"SELECT COUNT(*) FROM bill_bag WHERE bill_id = {bill.id}",
            
            "Full CTE Query (without lock)": f"""
                WITH 
                bag_lookup AS (
                    SELECT id, qr_id, type 
                    FROM bag 
                    WHERE lower(qr_id) = lower('{test_qr}')
                ),
                bill_check AS (
                    SELECT id, status, parent_bag_count, linked_parent_count
                    FROM bill 
                    WHERE id = {bill.id}
                ),
                existing_link AS (
                    SELECT 1 AS found
                    FROM bill_bag 
                    WHERE bill_id = {bill.id} 
                    AND bag_id = (SELECT id FROM bag_lookup)
                ),
                cross_bill AS (
                    SELECT bb.bill_id
                    FROM bill_bag bb
                    JOIN bill b ON bb.bill_id = b.id
                    WHERE bb.bag_id = (SELECT id FROM bag_lookup)
                    AND bb.bill_id != {bill.id}
                    AND b.status IN ('processing', 'pending')
                    LIMIT 1
                ),
                current_count AS (
                    SELECT COUNT(*) as cnt FROM bill_bag WHERE bill_id = {bill.id}
                )
                SELECT 
                    bl.id as bag_id, bl.qr_id, bl.type,
                    bc.status as bill_status, bc.parent_bag_count, bc.linked_parent_count,
                    el.found as already_linked,
                    cb.bill_id as cross_bill_id,
                    cc.cnt as current_count
                FROM bag_lookup bl, bill_check bc, current_count cc
                LEFT JOIN existing_link el ON true
                LEFT JOIN cross_bill cb ON true
            """
        }
        
        results = []
        
        for name, query in queries.items():
            times = []
            for _ in range(10):
                start = time.time()
                db.session.execute(text(query))
                elapsed = (time.time() - start) * 1000
                times.append(elapsed)
            
            avg = statistics.mean(times)
            p95 = sorted(times)[int(len(times) * 0.95)]
            results.append((name, avg, p95))
            print(f"\n{name}:")
            print(f"  Avg: {avg:.3f}ms, P95: {p95:.3f}ms")
        
        # Profile INSERT
        print("\n" + "-"*70)
        print("INSERT Performance:")
        insert_times = []
        for i in range(10):
            insert_qr = f"INSERT-TEST-{i}"
            start = time.time()
            db.session.execute(text(f"""
                INSERT INTO bill_bag (bill_id, bag_id) 
                VALUES ({bill.id}, (SELECT id FROM bag WHERE qr_id = '{test_qr}'))
                ON CONFLICT DO NOTHING
            """))
            db.session.commit()
            elapsed = (time.time() - start) * 1000
            insert_times.append(elapsed)
            # Remove for next iteration
            db.session.execute(text(f"DELETE FROM bill_bag WHERE bag_id = {bag_id}"))
            db.session.commit()
        
        avg = statistics.mean(insert_times)
        p95 = sorted(insert_times)[int(len(insert_times) * 0.95)]
        print(f"  Insert + Commit Avg: {avg:.3f}ms, P95: {p95:.3f}ms")
        
        # Profile Python overhead
        print("\n" + "-"*70)
        print("Python Overhead Test:")
        
        overhead_times = []
        for _ in range(100):
            start = time.time()
            # Just dict creation and basic operations
            result = {
                'success': True,
                'bag_id': bag_id,
                'qr_id': test_qr,
                'message': 'Test message'
            }
            elapsed = (time.time() - start) * 1000
            overhead_times.append(elapsed)
        
        print(f"  Dict creation Avg: {statistics.mean(overhead_times):.4f}ms")
        
        # Profile SQLAlchemy session overhead
        session_times = []
        for _ in range(10):
            start = time.time()
            db.session.execute(text("SELECT 1"))
            elapsed = (time.time() - start) * 1000
            session_times.append(elapsed)
        
        print(f"  Session.execute(SELECT 1) Avg: {statistics.mean(session_times):.3f}ms")
        
        # Cleanup
        Bag.query.filter_by(qr_id=test_qr).delete()
        db.session.commit()
        
        # Summary
        print("\n" + "="*70)
        print("📊 PROFILING SUMMARY")
        print("="*70)
        print("\nBreakdown of ~15ms total operation time:")
        print("-"*50)
        
        # Estimate components
        lock_time = next(r[1] for r in results if "Advisory Lock" in r[0])
        cte_time = next(r[1] for r in results if "Full CTE" in r[0])
        insert_time = avg
        session_overhead = statistics.mean(session_times)
        
        total_estimate = lock_time + cte_time + insert_time + session_overhead
        
        print(f"  Advisory Lock: ~{lock_time:.2f}ms")
        print(f"  CTE Query: ~{cte_time:.2f}ms")
        print(f"  Insert + Commit: ~{insert_time:.2f}ms")
        print(f"  Session Overhead: ~{session_overhead:.2f}ms")
        print(f"  ─────────────────────────")
        print(f"  Estimated Total: ~{total_estimate:.2f}ms")
        
        print("\n🔍 Optimization Recommendations:")
        if cte_time > 5:
            print("  - CTE query could benefit from PREPARE statement")
        if insert_time > 5:
            print("  - INSERT could benefit from connection pooling tune")
        if lock_time > 3:
            print("  - Advisory lock overhead is significant")


if __name__ == "__main__":
    profile_individual_queries()

#!/usr/bin/env python3
"""
Simple Load Test for Ultra-Fast Bill Scanning
==============================================

Runs concurrent requests against the fast scan endpoint and measures response times.
Uses the app's database connection directly for setup and testing.

Usage:
    python tests/load/simple_load_test.py
"""

import os
import sys
import time
import threading
import statistics
import random
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import from the app
from app import app, db
from models import Bag, Bill, BillBag, Scan, User
from query_optimizer import query_optimizer


def run_direct_performance_test():
    """Test query_optimizer methods directly without HTTP overhead"""
    
    print("="*70)
    print("ULTRA-FAST SCAN DIRECT PERFORMANCE TEST")
    print("="*70)
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Testing query_optimizer methods directly (no HTTP overhead)")
    print("-"*70)
    
    with app.app_context():
        # Find or create test data
        print("\n1. Setting up test data...")
        
        # Find a user
        user = User.query.filter_by(username='superadmin').first()
        if not user:
            user = User.query.first()
        if not user:
            print("   ❌ No users found!")
            return
        print(f"   Using user: {user.username} (ID: {user.id})")
        
        # Find or create a test bill
        bill = Bill.query.filter_by(status='processing').first()
        if not bill:
            bill = Bill.query.first()
        if not bill:
            print("   ❌ No bills found!")
            return
        print(f"   Using bill ID: {bill.id} (status: {bill.status})")
        
        # Create test parent bags
        print("\n2. Creating test parent bags...")
        test_bags = []
        for i in range(100):
            qr = f"PERFTEST-{random.randint(10000, 99999)}"
            bag = Bag(qr_id=qr, type='parent', name=f'Perf Test {qr}')
            db.session.add(bag)
            test_bags.append(qr)
        db.session.commit()
        print(f"   Created {len(test_bags)} test bags")
        
        # Run scan performance tests
        print("\n3. Running SCAN performance tests...")
        scan_times = []
        scan_successes = 0
        
        for i, qr in enumerate(test_bags[:50]):
            start = time.time()
            result = query_optimizer.ultra_fast_bill_parent_scan(bill.id, qr, user.id)
            elapsed = (time.time() - start) * 1000
            scan_times.append(elapsed)
            if result.get('success'):
                scan_successes += 1
            
            if (i + 1) % 10 == 0:
                print(f"      Completed {i + 1}/50 scans...")
        
        # Run remove performance tests
        print("\n4. Running REMOVE performance tests...")
        remove_times = []
        remove_successes = 0
        
        for i, qr in enumerate(test_bags[:50]):
            start = time.time()
            result = query_optimizer.ultra_fast_remove_bag_from_bill(bill.id, qr, user.id)
            elapsed = (time.time() - start) * 1000
            remove_times.append(elapsed)
            if result.get('success'):
                remove_successes += 1
            
            if (i + 1) % 10 == 0:
                print(f"      Completed {i + 1}/50 removes...")
        
        # Clean up test bags (must delete scans first due to foreign key)
        print("\n5. Cleaning up test data...")
        for qr in test_bags:
            bag = Bag.query.filter_by(qr_id=qr).first()
            if bag:
                # Delete associated scans first
                Scan.query.filter((Scan.parent_bag_id == bag.id) | (Scan.child_bag_id == bag.id)).delete()
                # Delete associated bill_bag links
                BillBag.query.filter_by(bag_id=bag.id).delete()
                # Now delete the bag
                db.session.delete(bag)
        db.session.commit()
        print("   Cleanup complete")
        
        # Calculate statistics
        def calc_stats(times):
            sorted_times = sorted(times)
            return {
                'count': len(times),
                'avg': statistics.mean(times) if times else 0,
                'min': min(times) if times else 0,
                'max': max(times) if times else 0,
                'p50': sorted_times[int(len(sorted_times) * 0.5)] if times else 0,
                'p95': sorted_times[int(len(sorted_times) * 0.95)] if times else 0,
                'p99': sorted_times[int(len(sorted_times) * 0.99)] if times else 0
            }
        
        scan_stats = calc_stats(scan_times)
        remove_stats = calc_stats(remove_times)
        
        # Print report
        print("\n" + "="*70)
        print("📊 PERFORMANCE RESULTS (Direct Method Calls)")
        print("="*70)
        
        print("\n🔍 SCAN (ultra_fast_bill_parent_scan)")
        print("-"*50)
        print(f"  Samples: {scan_stats['count']}")
        print(f"  Successes: {scan_successes}")
        print(f"  Average: {scan_stats['avg']:.2f}ms")
        print(f"  Min: {scan_stats['min']:.2f}ms")
        print(f"  Max: {scan_stats['max']:.2f}ms")
        print(f"  P50: {scan_stats['p50']:.2f}ms")
        p95_status = '✅' if scan_stats['p95'] < 10 else ('⚠️' if scan_stats['p95'] < 100 else '❌')
        print(f"  P95: {scan_stats['p95']:.2f}ms {p95_status} (Target: <10ms)")
        print(f"  P99: {scan_stats['p99']:.2f}ms")
        
        print("\n🗑️  REMOVE (ultra_fast_remove_bag_from_bill)")
        print("-"*50)
        print(f"  Samples: {remove_stats['count']}")
        print(f"  Successes: {remove_successes}")
        print(f"  Average: {remove_stats['avg']:.2f}ms")
        print(f"  Min: {remove_stats['min']:.2f}ms")
        print(f"  Max: {remove_stats['max']:.2f}ms")
        print(f"  P50: {remove_stats['p50']:.2f}ms")
        p95_status = '✅' if remove_stats['p95'] < 10 else ('⚠️' if remove_stats['p95'] < 100 else '❌')
        print(f"  P95: {remove_stats['p95']:.2f}ms {p95_status} (Target: <10ms)")
        print(f"  P99: {remove_stats['p99']:.2f}ms")
        
        # Verdict
        print("\n" + "="*70)
        avg_p95 = (scan_stats['p95'] + remove_stats['p95']) / 2
        if avg_p95 < 10:
            print("🏆 VERDICT: EXCELLENT - P95 < 10ms achieved!")
        elif avg_p95 < 50:
            print("✅ VERDICT: GOOD - P95 < 50ms (acceptable for production)")
        elif avg_p95 < 100:
            print("⚠️  VERDICT: ACCEPTABLE - P95 < 100ms (optimization recommended)")
        else:
            print("❌ VERDICT: NEEDS OPTIMIZATION - P95 > 100ms")
        print(f"   Combined P95: {avg_p95:.2f}ms")
        print("="*70)
        
        return scan_stats, remove_stats


def run_concurrent_stress_test(num_workers=20, duration_seconds=10):
    """Run concurrent stress test with multiple workers"""
    
    print("\n" + "="*70)
    print("CONCURRENT STRESS TEST")
    print("="*70)
    print(f"Workers: {num_workers}, Duration: {duration_seconds}s")
    print("-"*70)
    
    stop_event = threading.Event()
    all_results = []
    results_lock = threading.Lock()
    
    with app.app_context():
        # Get test data
        user = User.query.filter_by(username='superadmin').first() or User.query.first()
        bill = Bill.query.filter_by(status='processing').first() or Bill.query.first()
        
        if not user or not bill:
            print("❌ No user or bill found!")
            return
        
        user_id = user.id
        bill_id = bill.id
    
    def worker(worker_id):
        """Worker that continuously scans and removes"""
        local_results = []
        req_num = 0
        
        with app.app_context():
            while not stop_event.is_set():
                qr = f"STRESS-W{worker_id}-{req_num}-{random.randint(1000, 9999)}"
                req_num += 1
                
                # Create bag first
                bag = Bag(qr_id=qr, type='parent', name=f'Stress {qr}')
                db.session.add(bag)
                db.session.commit()
                
                # Scan
                start = time.time()
                result = query_optimizer.ultra_fast_bill_parent_scan(bill_id, qr, user_id)
                scan_time = (time.time() - start) * 1000
                
                # Remove
                start = time.time()
                result = query_optimizer.ultra_fast_remove_bag_from_bill(bill_id, qr, user_id)
                remove_time = (time.time() - start) * 1000
                
                # Cleanup - delete scans and bill_bag links first
                bag = Bag.query.filter_by(qr_id=qr).first()
                if bag:
                    Scan.query.filter((Scan.parent_bag_id == bag.id) | (Scan.child_bag_id == bag.id)).delete()
                    BillBag.query.filter_by(bag_id=bag.id).delete()
                    db.session.delete(bag)
                    db.session.commit()
                
                local_results.append({
                    'scan': scan_time,
                    'remove': remove_time
                })
        
        with results_lock:
            all_results.extend(local_results)
    
    # Start workers
    print(f"\nStarting {num_workers} concurrent workers...")
    threads = []
    start_time = time.time()
    
    for i in range(num_workers):
        t = threading.Thread(target=worker, args=(i,), daemon=True)
        t.start()
        threads.append(t)
    
    # Run for duration
    time.sleep(duration_seconds)
    stop_event.set()
    
    # Wait for threads
    for t in threads:
        t.join(timeout=5)
    
    actual_duration = time.time() - start_time
    
    if not all_results:
        print("❌ No results collected!")
        return
    
    # Calculate stats
    scan_times = [r['scan'] for r in all_results]
    remove_times = [r['remove'] for r in all_results]
    
    sorted_scan = sorted(scan_times)
    sorted_remove = sorted(remove_times)
    
    total_ops = len(all_results) * 2  # scan + remove
    rps = total_ops / actual_duration
    
    print(f"\n📊 STRESS TEST RESULTS")
    print("-"*50)
    print(f"  Total Operations: {total_ops}")
    print(f"  Duration: {actual_duration:.1f}s")
    print(f"  Throughput: {rps:.1f} ops/sec")
    
    print(f"\n  Scan P95: {sorted_scan[int(len(sorted_scan) * 0.95)]:.2f}ms")
    print(f"  Remove P95: {sorted_remove[int(len(sorted_remove) * 0.95)]:.2f}ms")
    
    avg_p95 = (sorted_scan[int(len(sorted_scan) * 0.95)] + sorted_remove[int(len(sorted_remove) * 0.95)]) / 2
    status = '✅' if avg_p95 < 10 else ('⚠️' if avg_p95 < 100 else '❌')
    print(f"  Combined P95: {avg_p95:.2f}ms {status}")


if __name__ == "__main__":
    # Run direct performance test
    run_direct_performance_test()
    
    # Run stress test
    run_concurrent_stress_test(num_workers=20, duration_seconds=10)

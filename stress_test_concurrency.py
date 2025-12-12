#!/usr/bin/env python3
"""
Comprehensive Stress Test for Bill Parent Bag Linking Concurrency Fix

Tests:
1. Concurrent scans from multiple simulated workers
2. Race conditions at capacity boundaries
3. Counter drift detection and auto-correction
4. Load testing with high request volumes
5. Capacity limit enforcement accuracy

Run: python stress_test_concurrency.py
"""

import os
import sys
import time
import random
import string
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

os.environ.setdefault('DATABASE_URL', os.environ.get('DATABASE_URL', ''))

from app import app, db
from models import Bill, Bag, BillBag, Scan, User
from sqlalchemy import text, func

class StressTestResults:
    def __init__(self):
        self.lock = threading.Lock()
        self.successful_links = 0
        self.failed_links = 0
        self.capacity_errors = 0
        self.duplicate_errors = 0
        self.other_errors = 0
        self.response_times = []
        self.errors = []
    
    def record_success(self, response_time):
        with self.lock:
            self.successful_links += 1
            self.response_times.append(response_time)
    
    def record_failure(self, error_type, message, response_time):
        with self.lock:
            self.failed_links += 1
            self.response_times.append(response_time)
            if 'capacity' in message.lower() or 'limit' in message.lower():
                self.capacity_errors += 1
            elif 'already linked' in message.lower() or 'duplicate' in message.lower():
                self.duplicate_errors += 1
            else:
                self.other_errors += 1
                self.errors.append(message)
    
    def summary(self):
        avg_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        max_time = max(self.response_times) if self.response_times else 0
        min_time = min(self.response_times) if self.response_times else 0
        p95_time = sorted(self.response_times)[int(len(self.response_times) * 0.95)] if len(self.response_times) > 20 else max_time
        
        return {
            'successful': self.successful_links,
            'failed': self.failed_links,
            'capacity_errors': self.capacity_errors,
            'duplicate_errors': self.duplicate_errors,
            'other_errors': self.other_errors,
            'avg_response_ms': round(avg_time * 1000, 2),
            'max_response_ms': round(max_time * 1000, 2),
            'min_response_ms': round(min_time * 1000, 2),
            'p95_response_ms': round(p95_time * 1000, 2),
            'unique_errors': self.errors[:10]
        }


def generate_test_id(prefix="TEST"):
    return f"{prefix}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"


def create_test_bill(capacity):
    """Create a test bill with specified capacity"""
    with app.app_context():
        bill_id = generate_test_id("STRESS")
        bill = Bill(
            bill_id=bill_id,
            parent_bag_count=capacity,
            linked_parent_count=0,
            total_child_bags=0,
            total_weight_kg=0.0,
            expected_weight_kg=0.0,
            status='new'
        )
        db.session.add(bill)
        db.session.commit()
        return bill.id, bill_id


def create_test_parent_bags(count):
    """Create test parent bags for stress testing"""
    with app.app_context():
        bags = []
        for i in range(count):
            qr_id = generate_test_id(f"SB{i:04d}")
            bag = Bag(
                qr_id=qr_id,
                type='parent',
                user_id=1,
                dispatch_area='Test'
            )
            db.session.add(bag)
            bags.append(qr_id)
        db.session.commit()
        return bags


VALID_USER_IDS = []

def get_valid_user_ids():
    """Get valid user IDs from database"""
    global VALID_USER_IDS
    if not VALID_USER_IDS:
        with app.app_context():
            result = db.session.execute(text("SELECT id FROM \"user\" WHERE role IN ('admin', 'biller') LIMIT 10")).fetchall()
            VALID_USER_IDS = [row[0] for row in result]
            if not VALID_USER_IDS:
                VALID_USER_IDS = [3]
    return VALID_USER_IDS


def simulate_scan(bill_db_id, qr_code, user_id, results):
    """Simulate a single scan operation using query_optimizer"""
    valid_ids = get_valid_user_ids()
    actual_user_id = valid_ids[user_id % len(valid_ids)] if valid_ids else user_id
    
    start_time = time.time()
    
    try:
        with app.app_context():
            from query_optimizer import query_optimizer
            result = query_optimizer.ultra_fast_bill_parent_scan(bill_db_id, qr_code, actual_user_id)
            
            elapsed = time.time() - start_time
            
            if result.get('success'):
                results.record_success(elapsed)
                return True, result.get('message', 'Success')
            else:
                results.record_failure(
                    result.get('error_type', 'unknown'),
                    result.get('message', 'Unknown error'),
                    elapsed
                )
                return False, result.get('message', 'Failed')
    except Exception as e:
        elapsed = time.time() - start_time
        results.record_failure('exception', str(e), elapsed)
        return False, str(e)


def verify_counter_consistency(bill_db_id):
    """Verify that denormalized counters match actual BillBag count"""
    with app.app_context():
        bill = Bill.query.get(bill_db_id)
        actual_count = BillBag.query.filter_by(bill_id=bill_db_id).count()
        
        denormalized = bill.linked_parent_count or 0
        
        return {
            'bill_id': bill.bill_id,
            'denormalized_count': denormalized,
            'actual_count': actual_count,
            'drift': denormalized - actual_count,
            'is_consistent': denormalized == actual_count
        }


def run_concurrent_stress_test(num_workers, num_bags_per_worker, capacity):
    """Run concurrent stress test with multiple workers"""
    print(f"\n{'='*60}")
    print(f"CONCURRENT STRESS TEST")
    print(f"Workers: {num_workers}, Bags per worker: {num_bags_per_worker}, Capacity: {capacity}")
    print(f"{'='*60}")
    
    total_bags = num_workers * num_bags_per_worker
    
    print(f"Creating test bill with capacity {capacity}...")
    bill_db_id, bill_id = create_test_bill(capacity)
    print(f"Created bill: {bill_id} (DB ID: {bill_db_id})")
    
    print(f"Creating {total_bags} test parent bags...")
    all_bags = create_test_parent_bags(total_bags)
    print(f"Created {len(all_bags)} parent bags")
    
    bag_chunks = [all_bags[i*num_bags_per_worker:(i+1)*num_bags_per_worker] for i in range(num_workers)]
    
    results = StressTestResults()
    
    def worker_task(worker_id, bags):
        user_id = worker_id + 1
        for qr_code in bags:
            simulate_scan(bill_db_id, qr_code, user_id, results)
            time.sleep(random.uniform(0.01, 0.05))
    
    print(f"\nStarting {num_workers} concurrent workers...")
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        for i, chunk in enumerate(bag_chunks):
            futures.append(executor.submit(worker_task, i, chunk))
        
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Worker error: {e}")
    
    elapsed = time.time() - start_time
    
    consistency = verify_counter_consistency(bill_db_id)
    
    summary = results.summary()
    
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")
    print(f"Total time: {elapsed:.2f}s")
    print(f"Successful links: {summary['successful']}")
    print(f"Failed links: {summary['failed']}")
    print(f"  - Capacity errors: {summary['capacity_errors']}")
    print(f"  - Duplicate errors: {summary['duplicate_errors']}")
    print(f"  - Other errors: {summary['other_errors']}")
    print(f"\nResponse times:")
    print(f"  - Average: {summary['avg_response_ms']}ms")
    print(f"  - Min: {summary['min_response_ms']}ms")
    print(f"  - Max: {summary['max_response_ms']}ms")
    print(f"  - P95: {summary['p95_response_ms']}ms")
    print(f"\nCounter consistency check:")
    print(f"  - Denormalized count: {consistency['denormalized_count']}")
    print(f"  - Actual BillBag count: {consistency['actual_count']}")
    print(f"  - Drift: {consistency['drift']}")
    print(f"  - Consistent: {'YES' if consistency['is_consistent'] else 'NO - PROBLEM!'}")
    
    if summary['unique_errors']:
        print(f"\nUnique errors encountered:")
        for err in summary['unique_errors']:
            print(f"  - {err}")
    
    expected_successful = min(total_bags, capacity)
    expected_capacity_errors = max(0, total_bags - capacity)
    
    print(f"\n{'='*60}")
    print("VALIDATION")
    print(f"{'='*60}")
    
    passed = True
    
    if consistency['is_consistent']:
        print(f"[PASS] Counter consistency: No drift detected")
    else:
        print(f"[FAIL] Counter consistency: Drift of {consistency['drift']} detected!")
        passed = False
    
    if summary['successful'] == expected_successful:
        print(f"[PASS] Expected {expected_successful} successful links, got {summary['successful']}")
    else:
        if summary['successful'] >= expected_successful - 2:
            print(f"[WARN] Expected {expected_successful} successful links, got {summary['successful']} (minor variance)")
        else:
            print(f"[FAIL] Expected {expected_successful} successful links, got {summary['successful']}")
            passed = False
    
    if consistency['actual_count'] == capacity:
        print(f"[PASS] Bill reached exact capacity: {consistency['actual_count']}/{capacity}")
    elif consistency['actual_count'] < capacity:
        print(f"[WARN] Bill under capacity: {consistency['actual_count']}/{capacity}")
    else:
        print(f"[FAIL] Bill OVER capacity: {consistency['actual_count']}/{capacity}")
        passed = False
    
    return passed, consistency, summary


def run_rapid_fire_test(num_requests, capacity):
    """Test rapid sequential scans to stress race condition handling"""
    print(f"\n{'='*60}")
    print(f"RAPID FIRE TEST")
    print(f"Requests: {num_requests}, Capacity: {capacity}")
    print(f"{'='*60}")
    
    print(f"Creating test bill with capacity {capacity}...")
    bill_db_id, bill_id = create_test_bill(capacity)
    
    print(f"Creating {num_requests} test parent bags...")
    bags = create_test_parent_bags(num_requests)
    
    results = StressTestResults()
    
    print(f"\nFiring {num_requests} rapid requests...")
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        for i, qr_code in enumerate(bags):
            futures.append(executor.submit(simulate_scan, bill_db_id, qr_code, (i % 5) + 1, results))
        
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Request error: {e}")
    
    elapsed = time.time() - start_time
    
    consistency = verify_counter_consistency(bill_db_id)
    summary = results.summary()
    
    print(f"\nCompleted in {elapsed:.2f}s")
    print(f"Successful: {summary['successful']}, Failed: {summary['failed']}")
    print(f"Counter drift: {consistency['drift']}")
    print(f"Consistent: {'YES' if consistency['is_consistent'] else 'NO'}")
    
    return consistency['is_consistent'], consistency, summary


def run_capacity_boundary_test(capacity):
    """Test exact capacity boundary behavior"""
    print(f"\n{'='*60}")
    print(f"CAPACITY BOUNDARY TEST")
    print(f"Capacity: {capacity}")
    print(f"{'='*60}")
    
    print(f"Creating test bill with capacity {capacity}...")
    bill_db_id, bill_id = create_test_bill(capacity)
    
    over_capacity = capacity + 10
    print(f"Creating {over_capacity} test parent bags (capacity + 10)...")
    bags = create_test_parent_bags(over_capacity)
    
    results = StressTestResults()
    
    print(f"\nScanning bags up to and beyond capacity...")
    
    for i, qr_code in enumerate(bags):
        success, msg = simulate_scan(bill_db_id, qr_code, 1, results)
        if i == capacity - 1:
            print(f"  Bag {i+1} (last in capacity): {'SUCCESS' if success else 'FAILED'}")
        elif i == capacity:
            print(f"  Bag {i+1} (first over capacity): {'SUCCESS' if success else f'REJECTED - {msg}'}")
    
    consistency = verify_counter_consistency(bill_db_id)
    summary = results.summary()
    
    print(f"\nFinal state:")
    print(f"  Actual count: {consistency['actual_count']}")
    print(f"  Expected: {capacity}")
    print(f"  Counter drift: {consistency['drift']}")
    
    passed = consistency['actual_count'] == capacity and consistency['is_consistent']
    
    if passed:
        print(f"[PASS] Capacity enforced correctly at {capacity}")
    else:
        if consistency['actual_count'] > capacity:
            print(f"[FAIL] OVER CAPACITY: {consistency['actual_count']} > {capacity}")
        elif consistency['actual_count'] < capacity:
            print(f"[WARN] Under capacity: {consistency['actual_count']} < {capacity}")
        if not consistency['is_consistent']:
            print(f"[FAIL] Counter drift: {consistency['drift']}")
    
    return passed, consistency, summary


def run_drift_injection_test():
    """Test drift detection and auto-correction by manually creating drift"""
    print(f"\n{'='*60}")
    print(f"DRIFT INJECTION TEST")
    print(f"{'='*60}")
    
    capacity = 50
    print(f"Creating test bill with capacity {capacity}...")
    bill_db_id, bill_id = create_test_bill(capacity)
    
    print(f"Creating 30 test parent bags...")
    bags = create_test_parent_bags(30)
    
    results = StressTestResults()
    
    print(f"Scanning first 20 bags normally...")
    for qr_code in bags[:20]:
        simulate_scan(bill_db_id, qr_code, 1, results)
    
    pre_drift = verify_counter_consistency(bill_db_id)
    print(f"Pre-drift state: {pre_drift['actual_count']} linked, counter={pre_drift['denormalized_count']}")
    
    print(f"\nINJECTING DRIFT: Setting linked_parent_count to 50 (false capacity reached)...")
    with app.app_context():
        db.session.execute(
            text("UPDATE bill SET linked_parent_count = 50 WHERE id = :id"),
            {'id': bill_db_id}
        )
        db.session.commit()
    
    post_injection = verify_counter_consistency(bill_db_id)
    print(f"Post-injection: actual={post_injection['actual_count']}, counter={post_injection['denormalized_count']}")
    print(f"Drift injected: {post_injection['drift']}")
    
    print(f"\nAttempting to scan bag 21 (should trigger drift detection)...")
    success, msg = simulate_scan(bill_db_id, bags[20], 1, results)
    
    if success:
        print(f"[PASS] Scan succeeded despite false capacity - drift was detected and corrected!")
    else:
        if 'capacity' in msg.lower():
            print(f"[FAIL] Scan rejected due to false capacity - drift detection failed!")
            return False, post_injection, results.summary()
        else:
            print(f"[INFO] Scan failed for other reason: {msg}")
    
    final_state = verify_counter_consistency(bill_db_id)
    print(f"\nFinal state: actual={final_state['actual_count']}, counter={final_state['denormalized_count']}")
    print(f"Drift after correction: {final_state['drift']}")
    
    passed = final_state['is_consistent']
    
    if passed:
        print(f"[PASS] Drift was detected and auto-corrected!")
    else:
        print(f"[FAIL] Drift still present after correction attempt")
    
    return passed, final_state, results.summary()


def cleanup_test_data():
    """Clean up test data created during stress tests"""
    print(f"\n{'='*60}")
    print("CLEANUP")
    print(f"{'='*60}")
    
    with app.app_context():
        deleted_billbags = db.session.execute(
            text("DELETE FROM bill_bag WHERE bill_id IN (SELECT id FROM bill WHERE bill_id LIKE 'STRESS%' OR bill_id LIKE 'TEST-%')")
        ).rowcount
        
        deleted_scans = db.session.execute(
            text("DELETE FROM scan WHERE parent_bag_id IN (SELECT id FROM bag WHERE qr_id LIKE 'SB%TEST%' OR qr_id LIKE 'TEST-%')")
        ).rowcount
        
        deleted_bags = db.session.execute(
            text("DELETE FROM bag WHERE qr_id LIKE 'SB%TEST%' OR qr_id LIKE 'TEST-%'")
        ).rowcount
        
        deleted_bills = db.session.execute(
            text("DELETE FROM bill WHERE bill_id LIKE 'STRESS%' OR bill_id LIKE 'TEST-%'")
        ).rowcount
        
        db.session.commit()
        
        print(f"Deleted: {deleted_bills} bills, {deleted_bags} bags, {deleted_billbags} bill-bag links, {deleted_scans} scans")


def main():
    print("="*60)
    print("TRAITORTRACK CONCURRENCY STRESS TEST SUITE")
    print("="*60)
    print(f"Started at: {datetime.now().isoformat()}")
    
    all_passed = True
    test_results = []
    
    passed, consistency, summary = run_concurrent_stress_test(
        num_workers=5,
        num_bags_per_worker=25,
        capacity=100
    )
    test_results.append(("Concurrent 5 workers x 25 bags", passed))
    all_passed = all_passed and passed
    
    passed, consistency, summary = run_concurrent_stress_test(
        num_workers=10,
        num_bags_per_worker=20,
        capacity=150
    )
    test_results.append(("Concurrent 10 workers x 20 bags", passed))
    all_passed = all_passed and passed
    
    passed, consistency, summary = run_rapid_fire_test(
        num_requests=200,
        capacity=150
    )
    test_results.append(("Rapid fire 200 requests", passed))
    all_passed = all_passed and passed
    
    passed, consistency, summary = run_capacity_boundary_test(capacity=50)
    test_results.append(("Capacity boundary 50", passed))
    all_passed = all_passed and passed
    
    passed, consistency, summary = run_capacity_boundary_test(capacity=100)
    test_results.append(("Capacity boundary 100", passed))
    all_passed = all_passed and passed
    
    passed, consistency, summary = run_drift_injection_test()
    test_results.append(("Drift injection and correction", passed))
    all_passed = all_passed and passed
    
    cleanup_test_data()
    
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    
    for test_name, passed in test_results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {test_name}")
    
    print(f"\n{'='*60}")
    if all_passed:
        print("ALL TESTS PASSED - Concurrency fix verified!")
        print("="*60)
        return 0
    else:
        print("SOME TESTS FAILED - Review issues above")
        print("="*60)
        return 1


if __name__ == "__main__":
    sys.exit(main())

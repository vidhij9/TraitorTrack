#!/usr/bin/env python3
"""
Extreme Load Test for Production Readiness
Tests high concurrency scenarios that simulate production traffic.
"""

import os
import sys
import time
import random
import string
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

os.environ.setdefault('DATABASE_URL', os.environ.get('DATABASE_URL', ''))

from app import app, db
from models import Bill, Bag, BillBag
from sqlalchemy import text

VALID_USER_IDS = []

def get_valid_user_ids():
    global VALID_USER_IDS
    if not VALID_USER_IDS:
        with app.app_context():
            result = db.session.execute(text("SELECT id FROM \"user\" WHERE role IN ('admin', 'biller') LIMIT 10")).fetchall()
            VALID_USER_IDS = [row[0] for row in result]
            if not VALID_USER_IDS:
                VALID_USER_IDS = [3]
    return VALID_USER_IDS


def generate_id(prefix):
    return f"{prefix}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"


def run_extreme_concurrent_test():
    """Test with 20 workers, 500 bags, capacity 400"""
    print("="*60)
    print("EXTREME CONCURRENT LOAD TEST")
    print("20 workers, 500 bags, capacity 400")
    print("="*60)
    
    with app.app_context():
        bill = Bill(
            bill_id=generate_id("EXTREME"),
            parent_bag_count=400,
            linked_parent_count=0,
            status='new'
        )
        db.session.add(bill)
        db.session.commit()
        bill_id = bill.id
        print(f"Created bill ID: {bill_id}")
        
        bags = []
        for i in range(500):
            bag = Bag(qr_id=generate_id(f"EX{i:03d}"), type='parent', user_id=get_valid_user_ids()[0])
            db.session.add(bag)
            bags.append(bag.qr_id)
        db.session.commit()
        print(f"Created {len(bags)} bags")
    
    from query_optimizer import query_optimizer
    
    results = {'success': 0, 'capacity': 0, 'other': 0}
    lock = threading.Lock()
    user_ids = get_valid_user_ids()
    
    def scan(qr, worker_id):
        uid = user_ids[worker_id % len(user_ids)]
        with app.app_context():
            result = query_optimizer.ultra_fast_bill_parent_scan(bill_id, qr, uid)
            with lock:
                if result.get('success'):
                    results['success'] += 1
                elif 'capacity' in result.get('message', '').lower():
                    results['capacity'] += 1
                else:
                    results['other'] += 1
    
    print("\nStarting 20 concurrent workers...")
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(scan, qr, i % 20) for i, qr in enumerate(bags)]
        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                print(f"Error: {e}")
    
    elapsed = time.time() - start
    
    with app.app_context():
        bill = db.session.get(Bill, bill_id)
        actual = BillBag.query.filter_by(bill_id=bill_id).count()
        denorm = bill.linked_parent_count or 0
        
        print(f"\nCompleted in {elapsed:.2f}s ({500/elapsed:.1f} scans/sec)")
        print(f"Results: {results['success']} success, {results['capacity']} capacity, {results['other']} other")
        print(f"Actual: {actual}, Denormalized: {denorm}, Drift: {denorm - actual}")
        
        db.session.execute(text("DELETE FROM bill_bag WHERE bill_id = :id"), {'id': bill_id})
        db.session.execute(text("DELETE FROM bill WHERE id = :id"), {'id': bill_id})
        db.session.execute(text("DELETE FROM bag WHERE qr_id LIKE 'EX%-%'"))
        db.session.commit()
    
    passed = results['success'] == 400 and actual == 400 and denorm == actual
    print(f"\n{'[PASS]' if passed else '[FAIL]'} Extreme load test")
    return passed


def run_rapid_burst_test():
    """Test rapid bursts of scans to a single bill"""
    print("\n" + "="*60)
    print("RAPID BURST TEST")
    print("50 workers, 150 bags, capacity 100, simultaneous start")
    print("="*60)
    
    with app.app_context():
        bill = Bill(
            bill_id=generate_id("BURST"),
            parent_bag_count=100,
            linked_parent_count=0,
            status='new'
        )
        db.session.add(bill)
        db.session.commit()
        bill_id = bill.id
        
        bags = []
        for i in range(150):
            bag = Bag(qr_id=generate_id(f"BR{i:03d}"), type='parent', user_id=get_valid_user_ids()[0])
            db.session.add(bag)
            bags.append(bag.qr_id)
        db.session.commit()
        print(f"Created bill and {len(bags)} bags")
    
    from query_optimizer import query_optimizer
    
    results = {'success': 0, 'capacity': 0, 'other': 0}
    lock = threading.Lock()
    user_ids = get_valid_user_ids()
    barrier = threading.Barrier(50)
    
    def scan(qr, worker_id):
        uid = user_ids[worker_id % len(user_ids)]
        barrier.wait()
        with app.app_context():
            result = query_optimizer.ultra_fast_bill_parent_scan(bill_id, qr, uid)
            with lock:
                if result.get('success'):
                    results['success'] += 1
                elif 'capacity' in result.get('message', '').lower():
                    results['capacity'] += 1
                else:
                    results['other'] += 1
    
    print("Starting 50 workers with synchronized burst...")
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(scan, bags[i], i) for i in range(min(50, len(bags)))]
        
        for i in range(50, len(bags)):
            futures.append(executor.submit(scan, bags[i], i))
        
        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                pass
    
    elapsed = time.time() - start
    
    with app.app_context():
        bill = db.session.get(Bill, bill_id)
        actual = BillBag.query.filter_by(bill_id=bill_id).count()
        denorm = bill.linked_parent_count or 0
        
        print(f"\nCompleted in {elapsed:.2f}s")
        print(f"Results: {results['success']} success, {results['capacity']} capacity")
        print(f"Actual: {actual}, Denormalized: {denorm}, Drift: {denorm - actual}")
        
        db.session.execute(text("DELETE FROM bill_bag WHERE bill_id = :id"), {'id': bill_id})
        db.session.execute(text("DELETE FROM bill WHERE id = :id"), {'id': bill_id})
        db.session.execute(text("DELETE FROM bag WHERE qr_id LIKE 'BR%-%'"))
        db.session.commit()
    
    passed = results['success'] == 100 and actual == 100 and denorm == actual
    print(f"\n{'[PASS]' if passed else '[FAIL]'} Rapid burst test")
    return passed


def run_multi_bill_test():
    """Test concurrent operations across multiple bills"""
    print("\n" + "="*60)
    print("MULTI-BILL CONCURRENT TEST")
    print("5 bills, 50 bags each, 10 workers per bill")
    print("="*60)
    
    bills = []
    all_bags = {}
    
    with app.app_context():
        for i in range(5):
            bill = Bill(
                bill_id=generate_id(f"MULTI{i}"),
                parent_bag_count=40,
                linked_parent_count=0,
                status='new'
            )
            db.session.add(bill)
            db.session.commit()
            bills.append(bill.id)
            
            bags = []
            for j in range(50):
                bag = Bag(qr_id=generate_id(f"MB{i}{j:02d}"), type='parent', user_id=get_valid_user_ids()[0])
                db.session.add(bag)
                bags.append(bag.qr_id)
            db.session.commit()
            all_bags[bill.id] = bags
        print(f"Created {len(bills)} bills with {sum(len(b) for b in all_bags.values())} total bags")
    
    from query_optimizer import query_optimizer
    
    results = {bid: {'success': 0, 'capacity': 0} for bid in bills}
    lock = threading.Lock()
    user_ids = get_valid_user_ids()
    
    def scan(bill_id, qr, worker_id):
        uid = user_ids[worker_id % len(user_ids)]
        with app.app_context():
            result = query_optimizer.ultra_fast_bill_parent_scan(bill_id, qr, uid)
            with lock:
                if result.get('success'):
                    results[bill_id]['success'] += 1
                else:
                    results[bill_id]['capacity'] += 1
    
    print("Starting concurrent scans across all bills...")
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = []
        for bid in bills:
            for i, qr in enumerate(all_bags[bid]):
                futures.append(executor.submit(scan, bid, qr, i))
        
        for f in as_completed(futures):
            try:
                f.result()
            except:
                pass
    
    elapsed = time.time() - start
    
    all_passed = True
    with app.app_context():
        print(f"\nCompleted in {elapsed:.2f}s")
        for bid in bills:
            bill = db.session.get(Bill, bid)
            actual = BillBag.query.filter_by(bill_id=bid).count()
            denorm = bill.linked_parent_count or 0
            drift = denorm - actual
            passed = actual == 40 and drift == 0
            all_passed = all_passed and passed
            status = "PASS" if passed else "FAIL"
            print(f"  Bill {bid}: {actual}/40 bags, drift={drift} [{status}]")
        
        for bid in bills:
            db.session.execute(text("DELETE FROM bill_bag WHERE bill_id = :id"), {'id': bid})
            db.session.execute(text("DELETE FROM bill WHERE id = :id"), {'id': bid})
        db.session.execute(text("DELETE FROM bag WHERE qr_id LIKE 'MB%-%'"))
        db.session.commit()
    
    print(f"\n{'[PASS]' if all_passed else '[FAIL]'} Multi-bill test")
    return all_passed


if __name__ == "__main__":
    print("="*60)
    print("EXTREME LOAD TEST SUITE FOR PRODUCTION READINESS")
    print("="*60)
    
    all_passed = True
    
    passed = run_extreme_concurrent_test()
    all_passed = all_passed and passed
    
    passed = run_rapid_burst_test()
    all_passed = all_passed and passed
    
    passed = run_multi_bill_test()
    all_passed = all_passed and passed
    
    print("\n" + "="*60)
    if all_passed:
        print("ALL EXTREME LOAD TESTS PASSED!")
        print("System is ready for production deployment.")
    else:
        print("SOME TESTS FAILED - Review issues above")
    print("="*60)
    
    sys.exit(0 if all_passed else 1)

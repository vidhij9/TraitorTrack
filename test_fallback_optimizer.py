#!/usr/bin/env python3
"""
Test the fallback optimizer path to ensure it handles concurrency correctly.
"""

import os
import sys
import time
import random
import string
from concurrent.futures import ThreadPoolExecutor, as_completed

os.environ.setdefault('DATABASE_URL', os.environ.get('DATABASE_URL', ''))

from app import app, db
from models import Bill, Bag, BillBag
from sqlalchemy import text

def generate_test_id(prefix="FALLBACK"):
    return f"{prefix}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"

def get_valid_user_id():
    with app.app_context():
        result = db.session.execute(text("SELECT id FROM \"user\" WHERE role IN ('admin', 'biller') LIMIT 1")).fetchone()
        return result[0] if result else 3

def test_fallback_optimizer():
    """Test the fallback optimizer implementation directly"""
    print("="*60)
    print("FALLBACK OPTIMIZER TEST")
    print("="*60)
    
    from routes import query_optimizer_fallback
    fallback = query_optimizer_fallback()
    
    with app.app_context():
        bill_id = generate_test_id()
        bill = Bill(
            bill_id=bill_id,
            parent_bag_count=20,
            linked_parent_count=0,
            status='new'
        )
        db.session.add(bill)
        db.session.commit()
        bill_db_id = bill.id
        print(f"Created test bill: {bill_id} (ID: {bill_db_id})")
        
        bags = []
        for i in range(25):
            qr_id = generate_test_id(f"SB{i:02d}")
            bag = Bag(qr_id=qr_id, type='parent', user_id=get_valid_user_id())
            db.session.add(bag)
            bags.append(qr_id)
        db.session.commit()
        print(f"Created {len(bags)} test bags")
    
    user_id = get_valid_user_id()
    successful = 0
    capacity_errors = 0
    other_errors = 0
    
    print(f"\nScanning 25 bags with fallback optimizer (capacity=20)...")
    
    for i, qr_code in enumerate(bags):
        with app.app_context():
            result = fallback.ultra_fast_bill_parent_scan(bill_db_id, qr_code, user_id)
            
            if result.get('success'):
                successful += 1
            elif 'capacity' in result.get('message', '').lower():
                capacity_errors += 1
            else:
                other_errors += 1
                print(f"  Error on bag {i+1}: {result.get('message')}")
    
    with app.app_context():
        bill = db.session.get(Bill, bill_db_id)
        actual_count = BillBag.query.filter_by(bill_id=bill_db_id).count()
        denormalized = bill.linked_parent_count or 0
        
        print(f"\nResults:")
        print(f"  Successful: {successful}")
        print(f"  Capacity errors: {capacity_errors}")
        print(f"  Other errors: {other_errors}")
        print(f"  Actual BillBag count: {actual_count}")
        print(f"  Denormalized count: {denormalized}")
        print(f"  Drift: {denormalized - actual_count}")
        
        db.session.execute(text("DELETE FROM bill_bag WHERE bill_id = :id"), {'id': bill_db_id})
        db.session.execute(text("DELETE FROM bill WHERE id = :id"), {'id': bill_db_id})
        db.session.execute(text("DELETE FROM bag WHERE qr_id LIKE 'FALLBACK%' OR qr_id LIKE 'SB%FALLBACK%'"))
        db.session.commit()
        print("\nCleaned up test data")
    
    passed = successful == 20 and capacity_errors == 5 and actual_count == 20 and denormalized == actual_count
    
    if passed:
        print("\n[PASS] Fallback optimizer working correctly!")
    else:
        print("\n[FAIL] Fallback optimizer issues detected")
    
    return passed


def test_fallback_concurrent():
    """Test fallback optimizer under concurrent load"""
    print("\n" + "="*60)
    print("FALLBACK OPTIMIZER CONCURRENT TEST")
    print("="*60)
    
    from routes import query_optimizer_fallback
    fallback = query_optimizer_fallback()
    
    with app.app_context():
        bill_id = generate_test_id("CONC")
        bill = Bill(
            bill_id=bill_id,
            parent_bag_count=50,
            linked_parent_count=0,
            status='new'
        )
        db.session.add(bill)
        db.session.commit()
        bill_db_id = bill.id
        print(f"Created test bill: {bill_id} (capacity=50)")
        
        bags = []
        for i in range(60):
            qr_id = generate_test_id(f"CB{i:02d}")
            bag = Bag(qr_id=qr_id, type='parent', user_id=get_valid_user_id())
            db.session.add(bag)
            bags.append(qr_id)
        db.session.commit()
        print(f"Created {len(bags)} test bags")
    
    import threading
    results = {'success': 0, 'capacity': 0, 'other': 0}
    lock = threading.Lock()
    user_id = get_valid_user_id()
    
    def scan_bag(qr_code):
        with app.app_context():
            result = fallback.ultra_fast_bill_parent_scan(bill_db_id, qr_code, user_id)
            with lock:
                if result.get('success'):
                    results['success'] += 1
                elif 'capacity' in result.get('message', '').lower():
                    results['capacity'] += 1
                else:
                    results['other'] += 1
    
    print(f"\nScanning 60 bags concurrently (5 workers)...")
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(scan_bag, qr) for qr in bags]
        for f in as_completed(futures):
            f.result()
    
    elapsed = time.time() - start
    
    with app.app_context():
        bill = db.session.get(Bill, bill_db_id)
        actual = BillBag.query.filter_by(bill_id=bill_db_id).count()
        denorm = bill.linked_parent_count or 0
        
        print(f"\nResults (completed in {elapsed:.2f}s):")
        print(f"  Successful: {results['success']}")
        print(f"  Capacity errors: {results['capacity']}")
        print(f"  Other errors: {results['other']}")
        print(f"  Actual count: {actual}")
        print(f"  Denormalized: {denorm}")
        print(f"  Drift: {denorm - actual}")
        
        db.session.execute(text("DELETE FROM bill_bag WHERE bill_id = :id"), {'id': bill_db_id})
        db.session.execute(text("DELETE FROM bill WHERE id = :id"), {'id': bill_db_id})
        db.session.execute(text("DELETE FROM bag WHERE qr_id LIKE '%CONC%' OR qr_id LIKE 'CB%FALLBACK%'"))
        db.session.commit()
        print("Cleaned up test data")
    
    passed = results['success'] == 50 and actual == 50 and denorm == actual
    
    if passed:
        print("\n[PASS] Fallback concurrent test passed!")
    else:
        print(f"\n[FAIL] Issues detected (expected 50 success, got {results['success']})")
    
    return passed


if __name__ == "__main__":
    all_passed = True
    
    passed = test_fallback_optimizer()
    all_passed = all_passed and passed
    
    passed = test_fallback_concurrent()
    all_passed = all_passed and passed
    
    print("\n" + "="*60)
    if all_passed:
        print("ALL FALLBACK OPTIMIZER TESTS PASSED!")
    else:
        print("SOME TESTS FAILED")
    print("="*60)
    
    sys.exit(0 if all_passed else 1)

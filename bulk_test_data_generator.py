#!/usr/bin/env python3
"""
Bulk Test Data Generator for Ultra-Fast Search Testing
Creates 4+ lakh (400,000+) bag records for performance testing
"""

import sys
import time
import random
from datetime import datetime, timedelta
from app_clean import app, db
from models import Bag, BagType, User, Bill, Link, Scan
from werkzeug.security import generate_password_hash

def create_bulk_test_data(num_bags=400000):
    """Create bulk test data optimized for ultra-fast search testing"""
    print(f"🚀 Creating {num_bags:,} bags for ultra-fast search testing...")
    start_time = time.time()
    
    with app.app_context():
        # Clear existing data (development only)
        print("📊 Clearing existing test data...")
        db.session.query(Link).delete()
        db.session.query(Scan).delete()
        db.session.query(Bag).delete()
        db.session.query(Bill).delete()
        db.session.query(User).delete()
        db.session.query(BagType).delete()
        db.session.commit()
        
        # Create bag types
        print("📝 Creating bag types...")
        parent_type = BagType(name='parent', description='Parent container bag')
        child_type = BagType(name='child', description='Child item bag')
        db.session.add(parent_type)
        db.session.add(child_type)
        db.session.commit()
        
        # Create test user
        print("👤 Creating test users...")
        admin = User(
            username='admin',
            email='admin@tracetrack.com',
            password_hash=generate_password_hash('admin'),
            role='admin'
        )
        biller = User(
            username='biller1',
            email='biller@tracetrack.com',
            password_hash=generate_password_hash('biller123'),
            role='biller'
        )
        dispatcher = User(
            username='dispatcher1',
            email='dispatcher@tracetrack.com',
            password_hash=generate_password_hash('dispatch123'),
            role='dispatcher',
            dispatch_area='Area-A'
        )
        db.session.add_all([admin, biller, dispatcher])
        db.session.commit()
        
        # Bulk create bags with optimized batch processing
        print("🏭 Bulk creating bags...")
        batch_size = 5000
        bags_created = 0
        areas = ['Area-A', 'Area-B', 'Area-C', 'Area-D', 'Area-E']
        
        # Create parent bags (30% of total)
        parent_count = int(num_bags * 0.3)
        print(f"📦 Creating {parent_count:,} parent bags...")
        
        for batch_start in range(0, parent_count, batch_size):
            batch_bags = []
            batch_end = min(batch_start + batch_size, parent_count)
            
            for i in range(batch_start, batch_end):
                qr_id = f"P{i+1:06d}"
                bag = Bag(
                    qr_id=qr_id,
                    type_id=parent_type.id,
                    dispatch_area=random.choice(areas),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 365))
                )
                batch_bags.append(bag)
            
            db.session.bulk_save_objects(batch_bags)
            db.session.commit()
            bags_created += len(batch_bags)
            
            if bags_created % 50000 == 0:
                elapsed = time.time() - start_time
                rate = bags_created / elapsed if elapsed > 0 else 0
                print(f"   ✓ {bags_created:,} bags created ({rate:.0f}/sec)")
        
        # Create child bags (70% of total)
        child_count = num_bags - parent_count
        print(f"🏷️ Creating {child_count:,} child bags...")
        
        # Get parent bags for linking
        parent_bags = db.session.query(Bag).filter_by(type_id=parent_type.id).all()
        parent_ids = [p.id for p in parent_bags]
        
        for batch_start in range(0, child_count, batch_size):
            batch_bags = []
            batch_end = min(batch_start + batch_size, child_count)
            
            for i in range(batch_start, batch_end):
                qr_id = f"C{i+1:06d}"
                # Link to random parent
                parent_id = random.choice(parent_ids) if parent_ids else None
                
                bag = Bag(
                    qr_id=qr_id,
                    type_id=child_type.id,
                    parent_id=parent_id,
                    dispatch_area=random.choice(areas),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 365))
                )
                batch_bags.append(bag)
            
            db.session.bulk_save_objects(batch_bags)
            db.session.commit()
            bags_created += len(batch_bags)
            
            if bags_created % 50000 == 0:
                elapsed = time.time() - start_time
                rate = bags_created / elapsed if elapsed > 0 else 0
                print(f"   ✓ {bags_created:,} bags created ({rate:.0f}/sec)")
        
        # Create some bills for testing
        print("📋 Creating test bills...")
        bills = []
        for i in range(1000):
            bill = Bill(
                bill_id=f"BILL{i+1:04d}",
                created_by_id=biller.id,
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
            )
            bills.append(bill)
        
        db.session.bulk_save_objects(bills)
        db.session.commit()
        
        # Create some bag-bill links
        print("🔗 Creating bag-bill relationships...")
        all_bags = db.session.query(Bag).limit(10000).all()  # Link first 10k bags
        all_bills = db.session.query(Bill).all()
        
        links = []
        for i in range(5000):
            bag = random.choice(all_bags)
            bill = random.choice(all_bills)
            link = Link(bag_id=bag.id, bill_id=bill.id)
            links.append(link)
        
        db.session.bulk_save_objects(links)
        db.session.commit()
        
        # Create some scan history
        print("📱 Creating scan history...")
        scans = []
        for i in range(20000):
            bag = random.choice(all_bags[:1000])  # Scans for first 1k bags
            scan = Scan(
                bag_id=bag.id,
                scanned_by_id=dispatcher.id,
                scanned_at=datetime.utcnow() - timedelta(days=random.randint(1, 7)),
                scan_type='lookup'
            )
            scans.append(scan)
        
        db.session.bulk_save_objects(scans)
        db.session.commit()
        
        # Final statistics
        total_time = time.time() - start_time
        total_bags = db.session.query(Bag).count()
        total_bills = db.session.query(Bill).count()
        total_links = db.session.query(Link).count()
        total_scans = db.session.query(Scan).count()
        
        print("🎉 Bulk data generation complete!")
        print(f"📊 Statistics:")
        print(f"   📦 Total bags: {total_bags:,}")
        print(f"   📋 Total bills: {total_bills:,}")
        print(f"   🔗 Total links: {total_links:,}")
        print(f"   📱 Total scans: {total_scans:,}")
        print(f"   ⏱️ Total time: {total_time:.2f} seconds")
        print(f"   🚀 Average rate: {total_bags/total_time:.0f} bags/second")
        
        print(f"\n✅ Ultra-fast search system ready for testing with {total_bags:,} bags!")
        print("🔍 Test searches:")
        print("   - Try 'P000001' (first parent bag)")
        print("   - Try 'C000001' (first child bag)")
        print("   - Try 'P100000' (middle parent bag)")
        print("   - Try partial matches like 'P0001' or 'C9999'")

if __name__ == "__main__":
    # Default to 400,000 bags, allow override
    num_bags = int(sys.argv[1]) if len(sys.argv) > 1 else 400000
    create_bulk_test_data(num_bags)
#!/usr/bin/env python3
"""
Create test data in the isolated development environment
"""

import os
from datetime import datetime, timedelta
import random

# Set development environment
os.environ['ENVIRONMENT'] = 'development'

from app_clean import app, db
from models import User, Bag, Scan, Bill, BillBag, Link
from werkzeug.security import generate_password_hash

def create_test_users():
    """Create test users for development"""
    users = [
        {
            'username': 'admin',
            'email': 'admin@test.com',
            'role': 'admin',
            'password': 'admin123'
        },
        {
            'username': 'operator1',
            'email': 'op1@test.com', 
            'role': 'operator',
            'password': 'op123'
        },
        {
            'username': 'operator2',
            'email': 'op2@test.com',
            'role': 'operator', 
            'password': 'op123'
        }
    ]
    
    created_users = []
    for user_data in users:
        # Check if user already exists
        existing = User.query.filter_by(username=user_data['username']).first()
        if not existing:
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                role=user_data['role'],
                password_hash=generate_password_hash(user_data['password']),
                verified=True
            )
            db.session.add(user)
            created_users.append(user)
        else:
            created_users.append(existing)
    
    db.session.commit()
    print(f"Created {len([u for u in created_users if u.id is None])} new users")
    return created_users

def create_test_bags():
    """Create test parent and child bags"""
    # Create parent bags
    parent_bags = []
    for i in range(1, 6):  # 5 parent bags
        qr_id = f"P{i:03d}"
        existing = Bag.query.filter_by(qr_id=qr_id).first()
        if not existing:
            bag = Bag(
                qr_id=qr_id,
                type='parent',
                name=f'Parent Bag {i}',
                child_count=random.randint(2, 5)
            )
            db.session.add(bag)
            parent_bags.append(bag)
        else:
            parent_bags.append(existing)
    
    db.session.commit()
    
    # Create child bags
    child_bags = []
    child_counter = 1
    for parent in parent_bags:
        for j in range(parent.child_count):
            qr_id = f"C{child_counter:03d}"
            existing = Bag.query.filter_by(qr_id=qr_id).first()
            if not existing:
                bag = Bag(
                    qr_id=qr_id,
                    type='child',
                    name=f'Child Bag {child_counter}',
                    parent_id=parent.id
                )
                db.session.add(bag)
                child_bags.append(bag)
            else:
                child_bags.append(existing)
            child_counter += 1
    
    db.session.commit()
    print(f"Created {len(parent_bags)} parent bags and {len(child_bags)} child bags")
    return parent_bags, child_bags

def create_test_links(parent_bags, child_bags):
    """Create links between parent and child bags"""
    links = []
    for parent in parent_bags:
        children = [c for c in child_bags if c.parent_id == parent.id]
        for child in children:
            existing = Link.query.filter_by(parent_bag_id=parent.id, child_bag_id=child.id).first()
            if not existing:
                link = Link(
                    parent_bag_id=parent.id,
                    child_bag_id=child.id
                )
                db.session.add(link)
                links.append(link)
    
    db.session.commit()
    print(f"Created {len(links)} bag links")
    return links

def create_test_scans(users, parent_bags, child_bags):
    """Create test scan records"""
    scans = []
    
    # Create scans over the past 30 days
    for i in range(50):  # 50 scan records
        scan_time = datetime.now() - timedelta(days=random.randint(0, 30), 
                                              hours=random.randint(0, 23),
                                              minutes=random.randint(0, 59))
        
        # Random scan type
        if random.choice([True, False]):
            # Parent bag scan
            parent = random.choice(parent_bags)
            scan = Scan(
                timestamp=scan_time,
                parent_bag_id=parent.id,
                user_id=random.choice(users).id
            )
        else:
            # Child bag scan
            child = random.choice(child_bags)
            scan = Scan(
                timestamp=scan_time,
                child_bag_id=child.id,
                user_id=random.choice(users).id
            )
        
        db.session.add(scan)
        scans.append(scan)
    
    db.session.commit()
    print(f"Created {len(scans)} scan records")
    return scans

def create_test_bills(parent_bags):
    """Create test bills"""
    bills = []
    
    for i in range(1, 4):  # 3 bills
        bill_id = f"BILL{i:03d}"
        existing = Bill.query.filter_by(bill_id=bill_id).first()
        if not existing:
            bill = Bill(
                bill_id=bill_id,
                description=f'Test Bill {i} - Development Data',
                parent_bag_count=random.randint(2, 4),
                status=random.choice(['pending', 'approved', 'shipped'])
            )
            db.session.add(bill)
            bills.append(bill)
        else:
            bills.append(existing)
    
    db.session.commit()
    
    # Link bills to parent bags
    bill_bags = []
    for bill in bills:
        selected_parents = random.sample(parent_bags, min(bill.parent_bag_count, len(parent_bags)))
        for parent in selected_parents:
            existing = BillBag.query.filter_by(bill_id=bill.id, bag_id=parent.id).first()
            if not existing:
                bill_bag = BillBag(
                    bill_id=bill.id,
                    bag_id=parent.id
                )
                db.session.add(bill_bag)
                bill_bags.append(bill_bag)
    
    db.session.commit()
    print(f"Created {len(bills)} bills with {len(bill_bags)} bag associations")
    return bills

def main():
    """Create comprehensive test data for development environment"""
    with app.app_context():
        print("Creating test data in DEVELOPMENT environment...")
        print("=" * 50)
        
        # Verify we're in development database
        result = db.session.execute(db.text("SELECT current_database()"))
        current_db = result.scalar()
        if current_db != 'neondb_dev':
            print(f"ERROR: Not in development database! Currently: {current_db}")
            return
        
        print(f"✓ Confirmed development database: {current_db}")
        
        # Create test data
        users = create_test_users()
        parent_bags, child_bags = create_test_bags()
        links = create_test_links(parent_bags, child_bags)
        scans = create_test_scans(users, parent_bags, child_bags)
        bills = create_test_bills(parent_bags)
        
        # Verify data creation
        print("\nFinal counts:")
        print(f"Users: {User.query.count()}")
        print(f"Parent bags: {Bag.query.filter_by(type='parent').count()}")
        print(f"Child bags: {Bag.query.filter_by(type='child').count()}")
        print(f"Links: {Link.query.count()}")
        print(f"Scans: {Scan.query.count()}")
        print(f"Bills: {Bill.query.count()}")
        
        print("\n✓ Test data created successfully!")
        print("You can now log in with:")
        print("  Username: admin, Password: admin123")
        print("  Username: operator1, Password: op123")

if __name__ == "__main__":
    main()
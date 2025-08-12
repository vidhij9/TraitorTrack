#!/usr/bin/env python3
"""
Simple test data creator for ultra-fast search testing
"""

import time
import random
from datetime import datetime, timedelta
from app_clean import app, db
from models import Bag, User, Bill, Link, Scan
from werkzeug.security import generate_password_hash

def create_sample_data():
    """Create sample data for testing ultra-fast search"""
    print("Creating sample test data...")
    
    with app.app_context():
        # Check if data already exists
        existing_bags = db.session.query(Bag).count()
        if existing_bags > 0:
            print(f"Found {existing_bags} existing bags. Skipping data creation.")
            return
        
        # Create test user if doesn't exist
        admin = db.session.query(User).filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@tracetrack.com',
                password_hash=generate_password_hash('admin'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
        
        # Create sample bags for testing
        print("Creating sample bags...")
        areas = ['Area-A', 'Area-B', 'Area-C']
        
        # Create 100 parent bags
        parent_bags = []
        for i in range(1, 101):
            bag = Bag(
                qr_id=f"P{i:06d}",
                type='parent',
                dispatch_area=random.choice(areas),
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
            )
            parent_bags.append(bag)
        
        db.session.bulk_save_objects(parent_bags)
        db.session.commit()
        
        # Get parent IDs for linking
        parent_records = db.session.query(Bag).filter_by(type='parent').all()
        parent_ids = [p.id for p in parent_records]
        
        # Create 400 child bags
        child_bags = []
        for i in range(1, 401):
            bag = Bag(
                qr_id=f"C{i:06d}",
                type='child',
                parent_id=random.choice(parent_ids) if parent_ids else None,
                dispatch_area=random.choice(areas),
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
            )
            child_bags.append(bag)
        
        db.session.bulk_save_objects(child_bags)
        db.session.commit()
        
        # Create a few bills (simplified - check Bill model structure)
        print("Creating sample bills...")
        bills = []
        for i in range(1, 11):
            bill = Bill(
                bill_id=f"BILL{i:03d}",
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 10))
            )
            bills.append(bill)
        
        try:
            db.session.bulk_save_objects(bills)
            db.session.commit()
        except Exception as e:
            print(f"Note: Bill creation skipped - {e}")
            # Continue without bills if model doesn't match
        
        # Statistics
        total_bags = db.session.query(Bag).count()
        total_bills = db.session.query(Bill).count()
        
        print(f"✓ Created {total_bags} bags and {total_bills} bills")
        print("Test QR codes to try:")
        print("- P000001 (first parent bag)")
        print("- C000001 (first child bag)")
        print("- P000050 (middle parent bag)")
        print("- C000200 (middle child bag)")

if __name__ == "__main__":
    create_sample_data()
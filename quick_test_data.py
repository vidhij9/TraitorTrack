#!/usr/bin/env python3
"""Quick test data creation for development environment"""

import os
os.environ['ENVIRONMENT'] = 'development'

from app_clean import app, db
from models import User, Bag, Scan
from werkzeug.security import generate_password_hash
from datetime import datetime

def create_quick_data():
    with app.app_context():
        # Create admin user
        admin = User(
            username='admin',
            email='admin@test.com',
            role='admin',
            password_hash=generate_password_hash('admin123'),
            verified=True
        )
        db.session.add(admin)
        
        # Create a few bags
        parent1 = Bag(qr_id='P001', type='parent', name='Parent Bag 1', child_count=2)
        child1 = Bag(qr_id='C001', type='child', name='Child Bag 1')
        child2 = Bag(qr_id='C002', type='child', name='Child Bag 2')
        
        db.session.add_all([parent1, child1, child2])
        db.session.commit()
        
        # Link children to parent
        child1.parent_id = parent1.id
        child2.parent_id = parent1.id
        
        # Create some scans
        scan1 = Scan(timestamp=datetime.now(), parent_bag_id=parent1.id, user_id=admin.id)
        scan2 = Scan(timestamp=datetime.now(), child_bag_id=child1.id, user_id=admin.id)
        
        db.session.add_all([scan1, scan2])
        db.session.commit()
        
        print("Test data created successfully!")
        print(f"Users: {User.query.count()}")
        print(f"Bags: {Bag.query.count()}")
        print(f"Scans: {Scan.query.count()}")

if __name__ == "__main__":
    create_quick_data()
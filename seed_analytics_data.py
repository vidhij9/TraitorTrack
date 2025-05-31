#!/usr/bin/env python3
"""
Seed script to add sample data for analytics testing
"""
import os
import sys
from datetime import datetime, timedelta
import random

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_clean import app, db
from models import User, UserRole, Location, Bag, BagType, Scan

def seed_analytics_data():
    """Add sample data for analytics dashboard"""
    with app.app_context():
        print("Creating sample data for analytics...")
        
        # Create locations if they don't exist
        locations = [
            {'name': 'Warehouse A', 'address': '123 Storage St'},
            {'name': 'Warehouse B', 'address': '456 Logistics Ave'},
            {'name': 'Distribution Center', 'address': '789 Supply Chain Blvd'},
            {'name': 'Retail Store', 'address': '321 Commerce St'}
        ]
        
        for loc_data in locations:
            location = Location.query.filter_by(name=loc_data['name']).first()
            if not location:
                location = Location()
                location.name = loc_data['name']
                location.address = loc_data['address']
                db.session.add(location)
        
        db.session.commit()
        print("Locations created")
        
        # Create some bags if they don't exist
        for i in range(1, 21):  # 20 parent bags
            parent_qr = f"PAR{i:03d}"
            if not Bag.query.filter_by(qr_id=parent_qr).first():
                bag = Bag()
                bag.qr_id = parent_qr
                bag.type = BagType.PARENT.value
                bag.name = f"Parent Bag {i}"
                db.session.add(bag)
        
        for i in range(1, 51):  # 50 child bags
            child_qr = f"CHI{i:03d}"
            if not Bag.query.filter_by(qr_id=child_qr).first():
                bag = Bag()
                bag.qr_id = child_qr
                bag.type = BagType.CHILD.value
                bag.name = f"Child Bag {i}"
                db.session.add(bag)
        
        db.session.commit()
        print("Bags created")
        
        # Get the admin user
        admin_user = User.query.filter_by(role=UserRole.ADMIN.value).first()
        if not admin_user:
            print("No admin user found, creating one...")
            admin_user = User()
            admin_user.username = "admin"
            admin_user.email = "admin@tracetrack.com"
            admin_user.set_password("admin123")
            admin_user.role = UserRole.ADMIN.value
            admin_user.verified = True
            db.session.add(admin_user)
            db.session.commit()
        
        # Create sample scans for the last 7 days
        locations_list = Location.query.all()
        bags_list = Bag.query.all()
        
        if locations_list and bags_list:
            for days_ago in range(7):
                scan_date = datetime.now() - timedelta(days=days_ago)
                scans_for_day = random.randint(5, 15)
                
                for _ in range(scans_for_day):
                    scan = Scan()
                    scan.timestamp = scan_date.replace(
                        hour=random.randint(8, 18),
                        minute=random.randint(0, 59),
                        second=random.randint(0, 59)
                    )
                    scan.location_id = random.choice(locations_list).id
                    scan.user_id = admin_user.id
                    
                    # Randomly assign to parent or child bag
                    bag = random.choice(bags_list)
                    if bag.type == BagType.PARENT.value:
                        scan.parent_bag_id = bag.id
                    else:
                        scan.child_bag_id = bag.id
                    
                    db.session.add(scan)
            
            db.session.commit()
            print(f"Sample scans created for analytics")
        
        print("Analytics sample data creation completed!")

if __name__ == "__main__":
    seed_analytics_data()
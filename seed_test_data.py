import datetime
from app_clean import app, db
from models import User, Location, Bag, Link, Bill, BillBag, Scan, UserRole, BagType
from werkzeug.security import generate_password_hash

def seed_test_data():
    """
    Seed the database with test data for development and testing purposes.
    """
    with app.app_context():
        print("Seeding test data...")
        
        # Create test users
        print("Creating users...")
        admin_user = User(
            username="admin",
            email="admin@example.com",
            password_hash=generate_password_hash("admin123"),
            role=UserRole.ADMIN.value,
            verified=True
        )
        
        employee_user = User(
            username="employee",
            email="employee@example.com",
            password_hash=generate_password_hash("employee123"),
            role=UserRole.EMPLOYEE.value,
            verified=True
        )
        
        db.session.add_all([admin_user, employee_user])
        db.session.commit()
        
        # Create locations
        print("Creating locations...")
        locations = [
            Location(name="Warehouse A", description="Main warehouse facility"),
            Location(name="Warehouse B", description="Secondary warehouse facility"),
            Location(name="Distribution Center", description="Central distribution hub"),
            Location(name="Packing Facility", description="Product packing area")
        ]
        db.session.add_all(locations)
        db.session.commit()
        
        # Create parent bags
        print("Creating parent bags...")
        parent_bags = []
        for i in range(1, 6):
            child_count = i * 2  # Each parent bag will have 2, 4, 6, 8, or 10 child bags
            parent_bag = Bag(
                qr_id=f"P{i}-{child_count}",
                type=BagType.PARENT.value,
                name=f"Parent Bag {i}",
                child_count=child_count
            )
            parent_bags.append(parent_bag)
        
        db.session.add_all(parent_bags)
        db.session.commit()
        
        # Create child bags and link to parent bags
        print("Creating child bags and links...")
        child_id_counter = 1
        for parent_bag in parent_bags:
            child_bags = []
            for j in range(parent_bag.child_count):
                child_bag = Bag(
                    qr_id=f"C{child_id_counter}",
                    type=BagType.CHILD.value,
                    name=f"Child Bag {child_id_counter}",
                    parent_id=parent_bag.id
                )
                child_bags.append(child_bag)
                child_id_counter += 1
            
            db.session.add_all(child_bags)
            db.session.commit()
            
            # Create links between parent and child bags
            for child_bag in child_bags:
                link = Link(
                    parent_bag_id=parent_bag.id,
                    child_bag_id=child_bag.id
                )
                db.session.add(link)
            
            db.session.commit()
        
        # Create some scans
        print("Creating scan records...")
        # Get all bags
        all_bags = Bag.query.all()
        parent_bags = [bag for bag in all_bags if bag.type == BagType.PARENT.value]
        child_bags = [bag for bag in all_bags if bag.type == BagType.CHILD.value]
        
        # Create scans with different timestamps
        now = datetime.datetime.utcnow()
        
        # Create parent bag scans
        for i, parent_bag in enumerate(parent_bags):
            # Each parent bag scanned at a different location
            location = locations[i % len(locations)]
            scan = Scan(
                timestamp=now - datetime.timedelta(days=i),
                parent_bag_id=parent_bag.id,
                location_id=location.id,
                user_id=admin_user.id if i % 2 == 0 else employee_user.id
            )
            db.session.add(scan)
        
        # Create child bag scans
        for i, child_bag in enumerate(child_bags):
            # Each child bag scanned at a different location
            location = locations[i % len(locations)]
            scan = Scan(
                timestamp=now - datetime.timedelta(hours=i),
                child_bag_id=child_bag.id,
                location_id=location.id,
                user_id=admin_user.id if i % 2 == 0 else employee_user.id
            )
            db.session.add(scan)
        
        db.session.commit()
        
        # Create bills
        print("Creating bills...")
        bills = [
            Bill(bill_id="BILL-001", description="First test bill", parent_bag_count=2, status="completed"),
            Bill(bill_id="BILL-002", description="Second test bill", parent_bag_count=3, status="processing")
        ]
        db.session.add_all(bills)
        db.session.commit()
        
        # Link bills to parent bags
        print("Linking bills to parent bags...")
        # Link first bill to first 2 parent bags
        for i in range(2):
            bill_bag = BillBag(
                bill_id=bills[0].id,
                bag_id=parent_bags[i].id
            )
            db.session.add(bill_bag)
        
        # Link second bill to next 2 parent bags (out of 3 expected)
        for i in range(2, 4):
            bill_bag = BillBag(
                bill_id=bills[1].id,
                bag_id=parent_bags[i].id
            )
            db.session.add(bill_bag)
        
        db.session.commit()
        
        print("Test data seeded successfully!")

if __name__ == "__main__":
    seed_test_data()

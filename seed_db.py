"""
Seed the database with test data for development and testing.
This script should be run with 'flask shell < seed_db.py'
"""
from app import db
from models import User, UserRole, Bag, BagType, Location, Scan
import datetime

print("Seeding test data...")

# Create locations if they don't exist
locations = []
location_names = [
    {"name": "Warehouse A", "address": "123 Main St"},
    {"name": "Distribution Center", "address": "456 State St"},
    {"name": "Retail Store", "address": "789 Market St"}
]

for loc_data in location_names:
    location = Location.query.filter_by(name=loc_data["name"]).first()
    if not location:
        location = Location(name=loc_data["name"], address=loc_data["address"])
        db.session.add(location)
        print(f"Created location: {location.name}")
    locations.append(location)

# Create admin user if it doesn't exist
admin_user = User.query.filter_by(username="admin").first()
if not admin_user:
    admin_user = User(
        username="admin",
        email="admin@example.com",
        role="admin"
    )
    admin_user.set_password("adminpass")
    admin_user.verified = True
    db.session.add(admin_user)
    print("Created admin user")

db.session.commit()

# Make sure we have the first location
warehouse_location = Location.query.filter_by(name="Warehouse A").first()

# Create parent bags
parent_bags = []
for i in range(1, 4):  # Create 3 parent bags
    parent_qr = f"P{100+i}-10"  # P101-10, P102-10, P103-10
    
    # Check if this parent bag already exists
    existing_parent = Bag.query.filter_by(qr_id=parent_qr).first()
    if not existing_parent:
        parent_bag = Bag(
            qr_id=parent_qr,
            name=f"Parent Batch {i}",
            type="parent",
            child_count=10,
            notes=f"Test parent bag {i} with 10 expected children"
        )
        db.session.add(parent_bag)
        db.session.flush()  # Get the ID without committing
        parent_bags.append(parent_bag)
        print(f"Created parent bag: {parent_qr}")
    else:
        parent_bags.append(existing_parent)
        print(f"Parent bag already exists: {parent_qr}")

# Create child bags linked to each parent
for parent_bag in parent_bags:
    # Extract parent sequential number from QR ID (P101-10 -> 101)
    parent_num = int(parent_bag.qr_id.split('-')[0][1:])
    
    # Create 5 child bags for each parent
    for j in range(1, 6):
        child_qr = f"C{parent_num}{j}"  # e.g. C1011, C1012, C1013, etc.
        
        # Check if this child bag already exists
        existing_child = Bag.query.filter_by(qr_id=child_qr).first()
        if not existing_child:
            child_bag = Bag(
                qr_id=child_qr,
                name=f"Child Package {parent_num}{j}",
                type="child",
                parent_id=parent_bag.id,
                notes=f"Test child bag {j} for parent {parent_bag.qr_id}"
            )
            db.session.add(child_bag)
            print(f"Created child bag: {child_qr} linked to parent {parent_bag.qr_id}")
            
            # Create a scan record for this child bag
            if admin_user and warehouse_location:
                scan = Scan(
                    child_bag_id=child_bag.id,
                    parent_bag_id=parent_bag.id,
                    user_id=admin_user.id,
                    location_id=warehouse_location.id,
                    scan_type="child",
                    notes=f"Test scan of child bag {child_qr}",
                    timestamp=datetime.datetime.utcnow()
                )
                db.session.add(scan)
                print(f"Created scan record for child bag: {child_qr}")
        else:
            print(f"Child bag already exists: {child_qr}")

db.session.commit()
print("Database seeding completed successfully")
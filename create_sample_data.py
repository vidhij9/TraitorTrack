"""
Create sample data for TraceTrack application
"""
from app_clean import app, db
from models import User
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random
import string

def generate_qr_id():
    """Generate a random QR ID"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def create_sample_data():
    """Create comprehensive sample data for testing"""
    
    with app.app_context():
        print("Creating sample data...")
        
        # Create sample users
        users_data = [
            {'username': 'admin', 'email': 'admin@tracetrack.com', 'role': 'admin'},
            {'username': 'manager', 'email': 'manager@tracetrack.com', 'role': 'user'},
            {'username': 'operator1', 'email': 'operator1@tracetrack.com', 'role': 'user'},
            {'username': 'operator2', 'email': 'operator2@tracetrack.com', 'role': 'user'},
            {'username': 'scanner1', 'email': 'scanner1@tracetrack.com', 'role': 'user'},
        ]
        
        created_users = []
        for user_data in users_data:
            # Check if user already exists
            existing_user = User.query.filter_by(username=user_data['username']).first()
            if not existing_user:
                user = User()
                user.username = user_data['username']
                user.email = user_data['email']
                user.password_hash = generate_password_hash('password123')
                user.role = user_data['role']
                user.verified = True
                user.created_at = datetime.utcnow() - timedelta(days=random.randint(1, 30))
                user.is_active = True
                
                db.session.add(user)
                created_users.append(user)
                print(f"Created user: {user.username}")
        
        db.session.commit()
        
        # Get all users for foreign key references
        all_users = User.query.all()
        user_ids = [user.id for user in all_users]
        
        # Create sample parent bags
        parent_bags_data = []
        origins = ['Warehouse A', 'Warehouse B', 'Farm 1', 'Farm 2', 'Distribution Center']
        destinations = ['Store 1', 'Store 2', 'Market A', 'Market B', 'Export Terminal']
        
        for i in range(20):
            qr_id = f"PB{generate_qr_id()}"
            
            # Insert parent bag
            db.session.execute(db.text("""
                INSERT INTO bag (qr_id, type, name, child_count, created_at, updated_at)
                VALUES (:qr_id, 'parent', :name, :child_count, :created_at, :updated_at)
            """), {
                'qr_id': qr_id,
                'name': f"Parent Bag {i+1}",
                'child_count': random.randint(3, 8),
                'created_at': datetime.utcnow() - timedelta(days=random.randint(1, 15)),
                'updated_at': datetime.utcnow() - timedelta(days=random.randint(0, 5))
            })
            
            parent_bags_data.append({
                'qr_id': qr_id,
                'name': f"Parent Bag {i+1}",
                'child_count': random.randint(3, 8)
            })
        
        db.session.commit()
        print(f"Created {len(parent_bags_data)} parent bags")
        
        # Get parent bag IDs
        parent_bags = db.session.execute(db.text("SELECT id, qr_id, child_count FROM bag WHERE type = 'parent'")).fetchall()
        
        # Create child bags for each parent
        child_count = 0
        for parent in parent_bags:
            for j in range(parent.child_count):
                child_qr_id = f"CB{generate_qr_id()}"
                
                db.session.execute(db.text("""
                    INSERT INTO bag (qr_id, type, name, parent_id, created_at, updated_at)
                    VALUES (:qr_id, 'child', :name, :parent_id, :created_at, :updated_at)
                """), {
                    'qr_id': child_qr_id,
                    'name': f"Child Bag {child_count+1}",
                    'parent_id': parent.id,
                    'created_at': datetime.utcnow() - timedelta(days=random.randint(1, 15)),
                    'updated_at': datetime.utcnow() - timedelta(days=random.randint(0, 5))
                })
                child_count += 1
        
        db.session.commit()
        print(f"Created {child_count} child bags")
        
        # Create sample bills
        for i in range(15):
            bill_id = f"BILL-{datetime.now().year}-{str(i+1).zfill(4)}"
            
            db.session.execute(db.text("""
                INSERT INTO bill (bill_id, description, parent_bag_count, status, created_at, updated_at)
                VALUES (:bill_id, :description, :parent_bag_count, :status, :created_at, :updated_at)
            """), {
                'bill_id': bill_id,
                'description': f"Shipment bill for batch {i+1}",
                'parent_bag_count': random.randint(2, 6),
                'status': random.choice(['draft', 'completed', 'shipped']),
                'created_at': datetime.utcnow() - timedelta(days=random.randint(1, 20)),
                'updated_at': datetime.utcnow() - timedelta(days=random.randint(0, 10))
            })
        
        db.session.commit()
        print(f"Created 15 bills")
        
        # Link some parent bags to bills
        bills = db.session.execute(db.text("SELECT id FROM bill")).fetchall()
        parent_bag_list = list(parent_bags)
        
        for bill in bills:
            # Link 2-4 random parent bags to each bill
            num_bags = random.randint(2, 4)
            selected_bags = random.sample(parent_bag_list, min(num_bags, len(parent_bag_list)))
            
            for bag in selected_bags:
                try:
                    db.session.execute(db.text("""
                        INSERT INTO bill_bag (bill_id, parent_bag_id, created_at)
                        VALUES (:bill_id, :parent_bag_id, :created_at)
                    """), {
                        'bill_id': bill.id,
                        'parent_bag_id': bag.id,
                        'created_at': datetime.utcnow() - timedelta(days=random.randint(0, 10))
                    })
                except:
                    # Skip if already linked
                    pass
        
        db.session.commit()
        print("Linked parent bags to bills")
        
        # Create sample scans
        all_bags = db.session.execute(db.text("SELECT id, type FROM bag")).fetchall()
        
        for i in range(100):
            bag = random.choice(all_bags)
            user_id = random.choice(user_ids)
            
            scan_data = {
                'user_id': user_id,
                'timestamp': datetime.utcnow() - timedelta(days=random.randint(0, 20), 
                                                         hours=random.randint(0, 23),
                                                         minutes=random.randint(0, 59))
            }
            
            if bag.type == 'parent':
                scan_data['parent_bag_id'] = bag.id
                scan_data['child_bag_id'] = None
            else:
                scan_data['parent_bag_id'] = None
                scan_data['child_bag_id'] = bag.id
            
            db.session.execute(db.text("""
                INSERT INTO scan (parent_bag_id, child_bag_id, user_id, timestamp)
                VALUES (:parent_bag_id, :child_bag_id, :user_id, :timestamp)
            """), scan_data)
        
        db.session.commit()
        print("Created 100 scan records")
        
        # Create some promotion requests
        regular_users = [u for u in all_users if u.role != 'admin']
        for i in range(3):
            if regular_users:
                user = random.choice(regular_users)
                db.session.execute(db.text("""
                    INSERT INTO promotion_request (user_id, requested_role, reason, status, requested_at)
                    VALUES (:user_id, 'admin', :reason, :status, :requested_at)
                """), {
                    'user_id': user.id,
                    'reason': f"Request for admin access - {random.choice(['Experienced operator', 'Team lead', 'Senior staff'])}",
                    'status': random.choice(['pending', 'pending', 'approved', 'rejected']),
                    'requested_at': datetime.utcnow() - timedelta(days=random.randint(1, 10))
                })
        
        db.session.commit()
        print("Created promotion requests")
        
        print("\n=== Sample Data Creation Complete ===")
        print("Login credentials:")
        print("Username: admin, Password: password123 (Admin)")
        print("Username: manager, Password: password123 (User)")
        print("Username: operator1, Password: password123 (User)")
        print("Username: operator2, Password: password123 (User)")
        print("Username: scanner1, Password: password123 (User)")
        print("\nData summary:")
        
        # Get final counts
        stats = {}
        stats['users'] = db.session.execute(db.text("SELECT COUNT(*) FROM \"user\"")).scalar()
        stats['parent_bags'] = db.session.execute(db.text("SELECT COUNT(*) FROM bag WHERE type = 'parent'")).scalar()
        stats['child_bags'] = db.session.execute(db.text("SELECT COUNT(*) FROM bag WHERE type = 'child'")).scalar()
        stats['bills'] = db.session.execute(db.text("SELECT COUNT(*) FROM bill")).scalar()
        stats['scans'] = db.session.execute(db.text("SELECT COUNT(*) FROM scan")).scalar()
        stats['bill_bag_links'] = db.session.execute(db.text("SELECT COUNT(*) FROM bill_bag")).scalar()
        stats['promotion_requests'] = db.session.execute(db.text("SELECT COUNT(*) FROM promotion_request")).scalar()
        
        for key, value in stats.items():
            print(f"- {key.replace('_', ' ').title()}: {value}")

if __name__ == '__main__':
    create_sample_data()
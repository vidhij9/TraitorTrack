import os
import sys
import pytest
import tempfile

# Set test environment variables BEFORE importing app
os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'sqlite:///test.db')
os.environ['SESSION_SECRET'] = 'test-secret-key-for-testing-only'
os.environ['ADMIN_PASSWORD'] = 'admin123'
os.environ['TESTING'] = 'True'

# Add parent directory to path so we can import app and models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app, db
from models import User, Bag, Bill, Link, BillBag, Scan

# Import routes to register them with the app
import routes
import api

@pytest.fixture(scope='session')
def app():
    """Create and configure a test Flask app instance"""
    flask_app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,  # Disable CSRF for testing
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })
    
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        # Skip drop_all to avoid cascade issues in SQLite
        try:
            db.drop_all()
        except Exception:
            pass  # Ignore teardown errors in test environment

@pytest.fixture(scope='function')
def client(app):
    """Create a test client for the app"""
    return app.test_client()

@pytest.fixture(scope='function')
def db_session(app):
    """Create a new database session for a test"""
    with app.app_context():
        # Clear all tables
        db.session.query(Scan).delete()
        db.session.query(BillBag).delete()
        db.session.query(Link).delete()
        db.session.query(Bill).delete()
        db.session.query(Bag).delete()
        db.session.query(User).delete()
        db.session.commit()
        
        yield db.session
        
        # Cleanup
        db.session.rollback()

@pytest.fixture
def admin_user(db_session):
    """Create an admin user for testing"""
    user = User()
    user.username = 'admin'
    user.email = 'admin@test.com'
    user.set_password('admin123')
    user.role = 'admin'
    user.verified = True
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def biller_user(db_session):
    """Create a biller user for testing"""
    user = User()
    user.username = 'biller'
    user.email = 'biller@test.com'
    user.set_password('biller123')
    user.role = 'biller'
    user.verified = True
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def dispatcher_user(db_session):
    """Create a dispatcher user for testing"""
    user = User()
    user.username = 'dispatcher'
    user.email = 'dispatcher@test.com'
    user.set_password('dispatcher123')
    user.role = 'dispatcher'
    user.dispatch_area = 'lucknow'
    user.verified = True
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def parent_bag(db_session):
    """Create a parent bag for testing"""
    bag = Bag()
    bag.qr_id = 'PARENT001'
    bag.type = 'parent'
    bag.name = 'Test Parent Bag'
    bag.child_count = 0
    bag.status = 'pending'
    db_session.add(bag)
    db_session.commit()
    return bag

@pytest.fixture
def child_bags(db_session, parent_bag):
    """Create child bags linked to a parent bag"""
    bags = []
    for i in range(5):
        bag = Bag()
        bag.qr_id = f'CHILD00{i+1}'
        bag.type = 'child'
        bag.name = f'Test Child Bag {i+1}'
        bag.parent_id = parent_bag.id
        db_session.add(bag)
        bags.append(bag)
    
    # Commit bags first to get their IDs
    db_session.commit()
    
    # Now create links with proper IDs
    for bag in bags:
        link = Link()
        link.parent_bag_id = parent_bag.id
        link.child_bag_id = bag.id
        db_session.add(link)
    
    parent_bag.child_count = 5
    parent_bag.weight_kg = 5.0
    db_session.commit()
    return bags

@pytest.fixture
def bill(db_session, admin_user):
    """Create a bill for testing"""
    bill = Bill()
    bill.bill_id = 'BILL001'
    bill.description = 'Test Bill'
    bill.parent_bag_count = 0
    bill.total_weight_kg = 0.0
    bill.expected_weight_kg = 0.0
    bill.total_child_bags = 0
    bill.status = 'new'
    bill.created_by_id = admin_user.id
    db_session.add(bill)
    db_session.commit()
    return bill

@pytest.fixture
def authenticated_client(client, admin_user):
    """Create an authenticated client"""
    with client.session_transaction() as sess:
        sess['user_id'] = admin_user.id
        sess['logged_in'] = True
        sess['authenticated'] = True
    return client

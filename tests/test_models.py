import pytest
from models import User, Bag, Bill, Link, BillBag, UserRole, BagType

class TestUserModel:
    def test_create_user(self, db_session):
        """Test creating a user"""
        user = User()
        user.username = 'testuser'
        user.email = 'test@example.com'
        user.set_password('password123')
        user.role = 'dispatcher'
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.username == 'testuser'
        assert user.check_password('password123')
        assert not user.check_password('wrongpassword')
    
    def test_user_roles(self, admin_user, biller_user, dispatcher_user):
        """Test user role checking methods"""
        assert admin_user.is_admin()
        assert not admin_user.is_biller()
        assert not admin_user.is_dispatcher()
        
        assert biller_user.is_biller()
        assert not biller_user.is_admin()
        
        assert dispatcher_user.is_dispatcher()
        assert not dispatcher_user.is_admin()
    
    def test_user_permissions(self, admin_user, biller_user, dispatcher_user):
        """Test user permission methods"""
        assert admin_user.can_edit_bills()
        assert admin_user.can_manage_users()
        assert admin_user.can_access_area('lucknow')
        
        assert biller_user.can_edit_bills()
        assert not biller_user.can_manage_users()
        
        assert not dispatcher_user.can_edit_bills()
        assert not dispatcher_user.can_manage_users()
        assert dispatcher_user.can_access_area('lucknow')
        assert not dispatcher_user.can_access_area('indore')

class TestBagModel:
    def test_create_parent_bag(self, db_session):
        """Test creating a parent bag"""
        bag = Bag()
        bag.qr_id = 'PARENT123'
        bag.type = 'parent'
        bag.name = 'Test Parent'
        bag.child_count = 0
        db_session.add(bag)
        db_session.commit()
        
        assert bag.id is not None
        assert bag.qr_id == 'PARENT123'
        assert bag.type == 'parent'
    
    def test_create_child_bag(self, db_session):
        """Test creating a child bag"""
        bag = Bag()
        bag.qr_id = 'CHILD123'
        bag.type = 'child'
        bag.name = 'Test Child'
        db_session.add(bag)
        db_session.commit()
        
        assert bag.id is not None
        assert bag.type == 'child'
    
    def test_parent_child_relationship(self, parent_bag, child_bags, db_session):
        """Test parent-child bag relationships"""
        assert parent_bag.child_count == 5
        assert parent_bag.weight_kg == 5.0
        
        # Check links exist
        links = Link.query.filter_by(parent_bag_id=parent_bag.id).all()
        assert len(links) == 5

class TestBillModel:
    def test_create_bill(self, db_session, admin_user):
        """Test creating a bill"""
        bill = Bill()
        bill.bill_id = 'TEST001'
        bill.description = 'Test Bill'
        bill.created_by_id = admin_user.id
        db_session.add(bill)
        db_session.commit()
        
        assert bill.id is not None
        assert bill.bill_id == 'TEST001'
        assert bill.status == 'new'
    
    def test_bill_bag_linking(self, db_session, bill, parent_bag):
        """Test linking bags to bills"""
        bill_bag = BillBag()
        bill_bag.bill_id = bill.id
        bill_bag.bag_id = parent_bag.id
        db_session.add(bill_bag)
        db_session.commit()
        
        # Verify link exists
        link = BillBag.query.filter_by(bill_id=bill.id, bag_id=parent_bag.id).first()
        assert link is not None

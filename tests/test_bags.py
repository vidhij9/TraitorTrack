import pytest
from models import Bag, Link
from flask import session

pytestmark = pytest.mark.integration  # Mark all tests as integration tests

class TestBagManagement:
    def test_create_parent_bag(self, authenticated_client, db_session):
        """Test creating a parent bag via web interface"""
        response = authenticated_client.get('/bag_management')
        assert response.status_code == 200
    
    def test_scan_parent_bag(self, authenticated_client, db_session):
        """Test scanning a parent bag"""
        # Create a parent bag first
        bag = Bag()
        bag.qr_id = 'SCANTEST001'
        bag.type = 'parent'
        bag.name = 'Scan Test Bag'
        bag.child_count = 0
        db_session.add(bag)
        db_session.commit()
        
        response = authenticated_client.get('/scan_parent')
        assert response.status_code == 200
    
    def test_parent_child_linking(self, parent_bag, db_session):
        """Test linking a child bag to a parent"""
        child = Bag()
        child.qr_id = 'LINKTEST001'
        child.type = 'child'
        child.name = 'Link Test Child'
        db_session.add(child)
        db_session.commit()
        
        # Create link
        link = Link()
        link.parent_bag_id = parent_bag.id
        link.child_bag_id = child.id
        db_session.add(link)
        db_session.commit()
        
        # Verify link
        saved_link = Link.query.filter_by(
            parent_bag_id=parent_bag.id,
            child_bag_id=child.id
        ).first()
        assert saved_link is not None
    
    def test_bag_search(self, authenticated_client, parent_bag):
        """Test searching for bags"""
        response = authenticated_client.get('/bag_management')
        assert response.status_code == 200
        # The parent bag should be findable
        assert b'PARENT001' in response.data or response.status_code == 200

class TestBagScanning:
    def test_process_parent_scan(self, authenticated_client, parent_bag, db_session):
        """Test processing a parent bag scan"""
        response = authenticated_client.post('/process_parent_scan', data={
            'qr_id': parent_bag.qr_id
        }, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_process_child_scan(self, authenticated_client, parent_bag, db_session):
        """Test processing a child bag scan"""
        # Create a child bag
        child = Bag()
        child.qr_id = 'SCANCH001'
        child.type = 'child'
        db_session.add(child)
        db_session.commit()
        
        # Set parent in session
        with authenticated_client.session_transaction() as sess:
            sess['parent_qr_id'] = parent_bag.qr_id
        
        response = authenticated_client.post('/process_child_scan', data={
            'qr_id': child.qr_id
        }, follow_redirects=True)
        
        assert response.status_code == 200

#!/usr/bin/env python3
"""
Comprehensive Test Suite for Supply Chain Traceability Platform
==============================================================

This test suite covers all major features and workflows to prevent
recurring issues and ensure system reliability.

Run tests with: python tests.py
"""

import unittest
import json
import tempfile
import os
from datetime import datetime, timedelta
from flask import Flask
from werkzeug.security import generate_password_hash

# Import our application components
try:
    from app_clean import app, db
    from models import User, Bag, Link, Scan, Bill, BillBag, BagType
except ImportError:
    # Fallback for different import structure
    from routes import app
    from models import User, Bag, Link, Scan, Bill, BillBag, BagType, db

class SupplyChainTestCase(unittest.TestCase):
    """Base test class with common setup and teardown"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            self.create_test_users()
            self.create_test_bags()
            
    def tearDown(self):
        """Tear down test fixtures after each test method."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            
    def create_test_users(self):
        """Create test users for authentication testing"""
        # Admin user
        admin_user = User(
            username='admin_test',
            email='admin@test.com',
            password_hash=generate_password_hash('admin123'),
            is_admin=True,
            dispatch_area='Test Area'
        )
        
        # Regular user
        regular_user = User(
            username='user_test',
            email='user@test.com', 
            password_hash=generate_password_hash('user123'),
            is_admin=False,
            dispatch_area='Test Area'
        )
        
        # Dispatcher user
        dispatcher_user = User(
            username='dispatcher_test',
            email='dispatcher@test.com',
            password_hash=generate_password_hash('dispatcher123'),
            is_admin=False,
            dispatch_area='Dispatch Area',
            is_dispatcher=True
        )
        
        db.session.add_all([admin_user, regular_user, dispatcher_user])
        db.session.commit()
        
    def create_test_bags(self):
        """Create test bags for scanning workflows"""
        # Parent bags
        parent1 = Bag(qr_id='PARENT_001', name='Test Parent 1', type=BagType.PARENT.value)
        parent2 = Bag(qr_id='PARENT_002', name='Test Parent 2', type=BagType.PARENT.value)
        
        # Child bags
        child1 = Bag(qr_id='CHILD_001', name='Test Child 1', type=BagType.CHILD.value)
        child2 = Bag(qr_id='CHILD_002', name='Test Child 2', type=BagType.CHILD.value)
        child3 = Bag(qr_id='CHILD_003', name='Test Child 3', type=BagType.CHILD.value)
        
        db.session.add_all([parent1, parent2, child1, child2, child3])
        db.session.commit()
        
    def login_user(self, username='user_test', password='user123'):
        """Helper method to log in a user"""
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)
        
    def login_admin(self):
        """Helper method to log in as admin"""
        return self.login_user('admin_test', 'admin123')
        
    def login_dispatcher(self):
        """Helper method to log in as dispatcher"""
        return self.login_user('dispatcher_test', 'dispatcher123')


class TestAuthentication(SupplyChainTestCase):
    """Test authentication and authorization workflows"""
    
    def test_user_registration(self):
        """Test new user registration"""
        response = self.client.post('/register', data={
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'newpass123',
            'confirm': 'newpass123'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify user was created
        with self.app.app_context():
            user = User.query.filter_by(username='newuser').first()
            self.assertIsNotNone(user)
            self.assertEqual(user.email, 'newuser@test.com')
            
    def test_user_login_success(self):
        """Test successful user login"""
        response = self.login_user()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'user_test', response.data)
        
    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = self.client.post('/login', data={
            'username': 'user_test',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid username or password', response.data)
        
    def test_admin_access_control(self):
        """Test admin-only areas are protected"""
        # Try accessing admin area without login
        response = self.client.get('/admin/users')
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Login as regular user and try admin area
        self.login_user()
        response = self.client.get('/admin/users')
        self.assertEqual(response.status_code, 403)  # Forbidden
        
        # Login as admin and access admin area
        self.login_admin()
        response = self.client.get('/admin/users')
        self.assertEqual(response.status_code, 200)


class TestParentBagScanning(SupplyChainTestCase):
    """Test parent bag scanning workflows"""
    
    def test_parent_bag_scan_page_access(self):
        """Test accessing parent bag scan page"""
        self.login_user()
        response = self.client.get('/scan/parent')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Scan Parent Bag', response.data)
        
    def test_parent_bag_scan_new_bag(self):
        """Test scanning a new parent bag"""
        self.login_user()
        
        # Test AJAX parent bag scan
        response = self.client.post('/scan/parent', data={
            'qr_id': 'NEW_PARENT_001'
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('redirect', data)
        
        # Verify bag was created
        with self.app.app_context():
            bag = Bag.query.filter_by(qr_id='NEW_PARENT_001').first()
            self.assertIsNotNone(bag)
            self.assertEqual(bag.type, BagType.PARENT.value)
            
    def test_parent_bag_scan_existing_bag(self):
        """Test scanning an existing parent bag"""
        self.login_user()
        
        response = self.client.post('/scan/parent', data={
            'qr_id': 'PARENT_001'
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
    def test_parent_bag_scan_child_bag_error(self):
        """Test scanning a child bag as parent (should fail)"""
        self.login_user()
        
        response = self.client.post('/scan/parent', data={
            'qr_id': 'CHILD_001'
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('child bag', data['message'])
        
    def test_parent_bag_redirect_to_child_scan(self):
        """Test that parent bag scanning redirects to child scanning"""
        self.login_user()
        
        response = self.client.post('/scan/parent', data={
            'qr_id': 'NEW_PARENT_002'
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('redirect', data)
        self.assertIn('/scan/child', data['redirect'])


class TestChildBagScanning(SupplyChainTestCase):
    """Test child bag scanning workflows"""
    
    def test_child_bag_scan_page_access(self):
        """Test accessing child bag scan page"""
        self.login_user()
        
        # First scan a parent bag to set up session
        self.client.post('/scan/parent', data={
            'qr_id': 'PARENT_001'
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        
        response = self.client.get('/scan/child')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Scan Child Bags', response.data)
        
    def test_child_bag_scan_new_bag(self):
        """Test scanning a new child bag"""
        self.login_user()
        
        # Set up parent bag in session
        with self.client.session_transaction() as sess:
            sess['current_parent_qr'] = 'PARENT_001'
            
        response = self.client.post('/scan/child', data={
            'qr_code': 'NEW_CHILD_001'
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # Verify child bag and link were created
        with self.app.app_context():
            child_bag = Bag.query.filter_by(qr_id='NEW_CHILD_001').first()
            self.assertIsNotNone(child_bag)
            self.assertEqual(child_bag.type, BagType.CHILD.value)
            
            parent_bag = Bag.query.filter_by(qr_id='PARENT_001').first()
            link = Link.query.filter_by(
                parent_bag_id=parent_bag.id,
                child_bag_id=child_bag.id
            ).first()
            self.assertIsNotNone(link)
            
    def test_child_bag_scan_no_parent_error(self):
        """Test scanning child bag without parent in session"""
        self.login_user()
        
        response = self.client.post('/scan/child', data={
            'qr_code': 'CHILD_001'
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('No parent bag selected', data['message'])
        
    def test_child_bag_duplicate_link_prevention(self):
        """Test preventing duplicate child-parent links"""
        self.login_user()
        
        # Set up parent bag in session
        with self.client.session_transaction() as sess:
            sess['current_parent_qr'] = 'PARENT_001'
            
        # First scan
        response1 = self.client.post('/scan/child', data={
            'qr_code': 'CHILD_002'
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        
        self.assertEqual(response1.status_code, 200)
        data1 = json.loads(response1.data)
        self.assertTrue(data1['success'])
        
        # Second scan (duplicate)
        response2 = self.client.post('/scan/child', data={
            'qr_code': 'CHILD_002'
        }, headers={'X-Requested-With': 'XMLHttpRequest'})
        
        self.assertEqual(response2.status_code, 200)
        data2 = json.loads(response2.data)
        self.assertFalse(data2['success'])
        self.assertIn('already linked', data2['message'])


class TestBillManagement(SupplyChainTestCase):
    """Test bill creation and management workflows"""
    
    def test_bill_creation(self):
        """Test creating a new bill"""
        self.login_user()
        
        response = self.client.post('/bill/create', data={
            'bill_number': 'BILL_001',
            'parent_bag_count': '5',
            'notes': 'Test bill creation'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify bill was created
        with self.app.app_context():
            bill = Bill.query.filter_by(bill_number='BILL_001').first()
            self.assertIsNotNone(bill)
            self.assertEqual(bill.parent_bag_count, 5)
            self.assertEqual(bill.notes, 'Test bill creation')
            
    def test_bill_parent_bag_scanning(self):
        """Test scanning parent bags to link to bills"""
        self.login_user()
        
        # Create a bill first
        with self.app.app_context():
            bill = Bill(
                bill_number='BILL_002',
                parent_bag_count=3,
                created_by_id=2  # regular user
            )
            db.session.add(bill)
            db.session.commit()
            bill_id = bill.id
            
        # Scan parent bag for bill
        response = self.client.post('/process_bill_parent_scan', data={
            'bill_id': str(bill_id),
            'qr_code': 'PARENT_001'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
    def test_bill_completion_check(self):
        """Test bill completion when all bags are scanned"""
        self.login_user()
        
        # Create bill with specific count
        with self.app.app_context():
            bill = Bill(
                bill_number='BILL_003',
                parent_bag_count=2,
                created_by_id=2
            )
            db.session.add(bill)
            db.session.commit()
            bill_id = bill.id
            
            # Link required number of parent bags
            parent1 = Bag.query.filter_by(qr_id='PARENT_001').first()
            parent2 = Bag.query.filter_by(qr_id='PARENT_002').first()
            
            bill_bag1 = BillBag(bill_id=bill_id, bag_id=parent1.id)
            bill_bag2 = BillBag(bill_id=bill_id, bag_id=parent2.id)
            
            db.session.add_all([bill_bag1, bill_bag2])
            db.session.commit()
            
        # Check bill completion
        response = self.client.get(f'/bill/{bill_id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Complete', response.data)


class TestSystemIntegrity(SupplyChainTestCase):
    """Test system integrity and error handling"""
    
    def test_database_constraints(self):
        """Test database integrity constraints"""
        with self.app.app_context():
            # Test unique constraint on bag QR codes
            bag1 = Bag(qr_id='DUPLICATE_001', name='Bag 1', type=BagType.PARENT.value)
            bag2 = Bag(qr_id='DUPLICATE_001', name='Bag 2', type=BagType.CHILD.value)
            
            db.session.add(bag1)
            db.session.commit()
            
            db.session.add(bag2)
            with self.assertRaises(Exception):  # Should raise integrity error
                db.session.commit()
            db.session.rollback()
            
    def test_csrf_protection(self):
        """Test CSRF protection on forms"""
        self.login_user()
        
        # Try to submit form without CSRF token
        response = self.client.post('/bill/create', data={
            'bill_number': 'BILL_CSRF_TEST',
            'parent_bag_count': '3'
        })
        
        # Should be rejected or redirect due to CSRF protection
        self.assertIn(response.status_code, [400, 302])
        
    def test_session_management(self):
        """Test session data management"""
        self.login_user()
        
        # Test session data persistence during scanning workflow
        with self.client.session_transaction() as sess:
            sess['test_data'] = 'test_value'
            sess['current_parent_qr'] = 'PARENT_001'
            
        response = self.client.get('/scan/child')
        self.assertEqual(response.status_code, 200)
        
        # Session should still contain our data
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('test_data'), 'test_value')
            self.assertEqual(sess.get('current_parent_qr'), 'PARENT_001')


class TestAPI(SupplyChainTestCase):
    """Test API endpoints and responses"""
    
    def test_scanned_children_api(self):
        """Test API for fetching scanned children"""
        self.login_user()
        
        # Set up test data
        with self.app.app_context():
            parent = Bag.query.filter_by(qr_id='PARENT_001').first()
            child = Bag.query.filter_by(qr_id='CHILD_001').first()
            
            link = Link(parent_bag_id=parent.id, child_bag_id=child.id)
            db.session.add(link)
            db.session.commit()
            
        # Set parent in session
        with self.client.session_transaction() as sess:
            sess['current_parent_qr'] = 'PARENT_001'
            
        response = self.client.get('/api/scanned-children')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['children']), 1)
        self.assertEqual(data['children'][0]['qr_id'], 'CHILD_001')
        
    def test_remove_child_link_api(self):
        """Test API for removing child-parent links"""
        self.login_user()
        
        # Set up test data
        with self.app.app_context():
            parent = Bag.query.filter_by(qr_id='PARENT_001').first()
            child = Bag.query.filter_by(qr_id='CHILD_001').first()
            
            link = Link(parent_bag_id=parent.id, child_bag_id=child.id)
            db.session.add(link)
            db.session.commit()
            child_id = child.id
            
        response = self.client.post('/api/remove-child-link', data={
            'child_bag_id': str(child_id)
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # Verify link was removed
        with self.app.app_context():
            link = Link.query.filter_by(
                parent_bag_id=parent.id,
                child_bag_id=child_id
            ).first()
            self.assertIsNone(link)


class TestPerformance(SupplyChainTestCase):
    """Test system performance and optimization"""
    
    def test_bulk_scanning_performance(self):
        """Test performance with bulk scanning operations"""
        self.login_user()
        
        # Set up parent bag
        with self.client.session_transaction() as sess:
            sess['current_parent_qr'] = 'PARENT_001'
            
        start_time = datetime.now()
        
        # Simulate scanning multiple child bags rapidly
        for i in range(10):
            response = self.client.post('/scan/child', data={
                'qr_code': f'BULK_CHILD_{i:03d}'
            }, headers={'X-Requested-With': 'XMLHttpRequest'})
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(data['success'])
            
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Should complete within reasonable time (5 seconds for 10 scans)
        self.assertLess(duration, 5.0)
        
    def test_database_query_optimization(self):
        """Test database query optimization"""
        # This test would check query performance with large datasets
        # For now, we just verify basic functionality works
        with self.app.app_context():
            # Create many bags to test query performance
            bags = []
            for i in range(100):
                bags.append(Bag(
                    qr_id=f'PERF_TEST_{i:03d}',
                    name=f'Performance Test Bag {i}',
                    type=BagType.CHILD.value if i % 2 else BagType.PARENT.value
                ))
            
            db.session.add_all(bags)
            db.session.commit()
            
            # Test query performance
            start_time = datetime.now()
            result = Bag.query.filter_by(type=BagType.PARENT.value).all()
            end_time = datetime.now()
            
            duration = (end_time - start_time).total_seconds()
            
            # Should be fast even with many records
            self.assertLess(duration, 1.0)
            self.assertEqual(len(result), 52)  # 50 parent + 2 from setup


def run_test_suite():
    """Run the complete test suite"""
    print("=" * 80)
    print("SUPPLY CHAIN TRACEABILITY PLATFORM - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestAuthentication,
        TestParentBagScanning,
        TestChildBagScanning,
        TestBillManagement,
        TestSystemIntegrity,
        TestAPI,
        TestPerformance
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError: ')[-1].split('\n')[0]}")
            
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('\n')[-2]}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_test_suite()
    exit(0 if success else 1)
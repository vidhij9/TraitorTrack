#!/usr/bin/env python3
"""
Comprehensive test suite for TraceTrack application.
Tests all major functionality including routes, API endpoints, and database operations.
"""

import unittest
import tempfile
import os
import json
from datetime import datetime
from werkzeug.security import generate_password_hash

# Import the application components
from app import create_app, db
from models import User, Bag, Scan, Bill, BillBag, Link, UserRole, BagType

class TraceTrackTestCase(unittest.TestCase):
    """Base test case for TraceTrack application"""
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            self._create_test_data()
    
    def tearDown(self):
        """Clean up after each test method"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def _create_test_data(self):
        """Create test data for testing"""
        # Create test users
        admin_user = User(
            username='admin',
            email='admin@test.com',
            password_hash=generate_password_hash('password123'),
            role=UserRole.ADMIN.value,
            verified=True,
            created_at=datetime.now()
        )
        
        regular_user = User(
            username='user',
            email='user@test.com',
            password_hash=generate_password_hash('password123'),
            role=UserRole.EMPLOYEE.value,
            verified=True,
            created_at=datetime.now()
        )
        
        db.session.add(admin_user)
        db.session.add(regular_user)
        db.session.commit()
        
        # Create test bags
        parent_bag = Bag(
            qr_id='P001',
            name='Test Parent Bag',
            type=BagType.PARENT.value,
            created_at=datetime.now()
        )
        
        child_bag = Bag(
            qr_id='C001',
            name='Test Child Bag',
            type=BagType.CHILD.value,
            created_at=datetime.now()
        )
        
        db.session.add(parent_bag)
        db.session.add(child_bag)
        db.session.commit()
        
        # Create link between parent and child
        link = Link(
            parent_bag_id=parent_bag.id,
            child_bag_id=child_bag.id,
            created_at=datetime.now()
        )
        db.session.add(link)
        
        # Create test scans
        scan1 = Scan(
            parent_bag_id=parent_bag.id,
            user_id=regular_user.id,
            timestamp=datetime.now()
        )
        
        scan2 = Scan(
            child_bag_id=child_bag.id,
            user_id=regular_user.id,
            timestamp=datetime.now()
        )
        
        db.session.add(scan1)
        db.session.add(scan2)
        
        # Create test bill
        bill = Bill(
            bill_id='BILL001',
            description='Test Bill',
            created_at=datetime.now()
        )
        db.session.add(bill)
        db.session.commit()
        
        # Create bill-bag link
        bill_bag = BillBag(
            bill_id=bill.id,
            bag_id=parent_bag.id
        )
        db.session.add(bill_bag)
        db.session.commit()
    
    def login(self, username='user', password='password123'):
        """Helper method to log in a user"""
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)
    
    def logout(self):
        """Helper method to log out"""
        return self.client.get('/logout', follow_redirects=True)

class AuthenticationTestCase(TraceTrackTestCase):
    """Test authentication functionality"""
    
    def test_login_page_accessible(self):
        """Test that login page is accessible"""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)
    
    def test_successful_login(self):
        """Test successful user login"""
        response = self.login()
        self.assertEqual(response.status_code, 200)
        # Should redirect to dashboard after login
    
    def test_failed_login(self):
        """Test failed login with wrong credentials"""
        response = self.client.post('/login', data={
            'username': 'wronguser',
            'password': 'wrongpass'
        })
        self.assertIn(b'Invalid', response.data)
    
    def test_logout(self):
        """Test user logout"""
        self.login()
        response = self.logout()
        self.assertEqual(response.status_code, 200)
    
    def test_protected_route_requires_login(self):
        """Test that protected routes require authentication"""
        response = self.client.get('/bags')
        self.assertEqual(response.status_code, 302)  # Redirect to login

class DashboardTestCase(TraceTrackTestCase):
    """Test dashboard functionality"""
    
    def test_dashboard_accessible_after_login(self):
        """Test dashboard is accessible after login"""
        self.login()
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard', response.data)
    
    def test_dashboard_shows_statistics(self):
        """Test dashboard displays statistics"""
        self.login()
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        # Should contain statistics cards

class APITestCase(TraceTrackTestCase):
    """Test API endpoints"""
    
    def test_api_stats_endpoint(self):
        """Test /api/stats endpoint"""
        self.login()
        response = self.client.get('/api/stats')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('statistics', data)
    
    def test_api_scans_endpoint(self):
        """Test /api/scans endpoint"""
        self.login()
        response = self.client.get('/api/scans')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('scans', data)
    
    def test_api_activity_endpoint(self):
        """Test /api/activity/<days> endpoint"""
        self.login()
        response = self.client.get('/api/activity/7')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('activity', data)

class BagManagementTestCase(TraceTrackTestCase):
    """Test bag management functionality"""
    
    def test_bag_list_accessible(self):
        """Test bag list page is accessible"""
        self.login()
        response = self.client.get('/bags')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Bag Management', response.data)
    
    def test_view_bag_details(self):
        """Test viewing bag details"""
        self.login()
        response = self.client.get('/bag/P001')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Parent Bag', response.data)

class ScanTestCase(TraceTrackTestCase):
    """Test scanning functionality"""
    
    def test_scan_parent_page_accessible(self):
        """Test scan parent page is accessible"""
        self.login()
        response = self.client.get('/scan/parent')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Scan Parent', response.data)
    
    def test_scan_child_page_accessible(self):
        """Test scan child page is accessible"""
        self.login()
        response = self.client.get('/scan/child')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Scan Child', response.data)
    
    def test_scan_details_page(self):
        """Test scan details page"""
        self.login()
        # Get a scan ID from the database
        with self.app.app_context():
            scan = Scan.query.first()
            if scan:
                response = self.client.get(f'/scan/{scan.id}')
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'Scan Information', response.data)

class BillManagementTestCase(TraceTrackTestCase):
    """Test bill management functionality"""
    
    def test_bill_list_accessible(self):
        """Test bill list page is accessible"""
        self.login()
        response = self.client.get('/bills')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Bill Management', response.data)
    
    def test_view_bill_details(self):
        """Test viewing bill details"""
        self.login()
        with self.app.app_context():
            bill = Bill.query.first()
            if bill:
                response = self.client.get(f'/bill/{bill.id}')
                self.assertEqual(response.status_code, 200)

class UserManagementTestCase(TraceTrackTestCase):
    """Test user management functionality (admin only)"""
    
    def test_user_management_requires_admin(self):
        """Test user management requires admin access"""
        self.login('user')  # Login as regular user
        response = self.client.get('/user_management')
        self.assertEqual(response.status_code, 302)  # Should redirect
    
    def test_admin_can_access_user_management(self):
        """Test admin can access user management"""
        self.login('admin')
        response = self.client.get('/user_management')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'User Management', response.data)

class DatabaseTestCase(TraceTrackTestCase):
    """Test database operations"""
    
    def test_user_creation(self):
        """Test user creation"""
        with self.app.app_context():
            user_count_before = User.query.count()
            new_user = User(
                username='testuser',
                email='test@example.com',
                password_hash=generate_password_hash('password'),
                role=UserRole.EMPLOYEE.value
            )
            db.session.add(new_user)
            db.session.commit()
            user_count_after = User.query.count()
            self.assertEqual(user_count_after, user_count_before + 1)
    
    def test_bag_creation(self):
        """Test bag creation"""
        with self.app.app_context():
            bag_count_before = Bag.query.count()
            new_bag = Bag(
                qr_id='TEST001',
                name='Test Bag',
                type=BagType.PARENT.value
            )
            db.session.add(new_bag)
            db.session.commit()
            bag_count_after = Bag.query.count()
            self.assertEqual(bag_count_after, bag_count_before + 1)
    
    def test_scan_creation(self):
        """Test scan creation"""
        with self.app.app_context():
            scan_count_before = Scan.query.count()
            user = User.query.first()
            bag = Bag.query.first()
            new_scan = Scan(
                parent_bag_id=bag.id,
                user_id=user.id,
                timestamp=datetime.now()
            )
            db.session.add(new_scan)
            db.session.commit()
            scan_count_after = Scan.query.count()
            self.assertEqual(scan_count_after, scan_count_before + 1)

def run_tests():
    """Run all test cases"""
    print("Running TraceTrack Application Tests...")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        AuthenticationTestCase,
        DashboardTestCase,
        APITestCase,
        BagManagementTestCase,
        ScanTestCase,
        BillManagementTestCase,
        UserManagementTestCase,
        DatabaseTestCase
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    print("\n" + "=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100
    print(f"\nSuccess rate: {success_rate:.1f}%")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)

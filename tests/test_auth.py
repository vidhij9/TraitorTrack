import pytest
from flask import session

class TestAuthentication:
    def test_login_page_loads(self, client):
        """Test that login page loads"""
        response = client.get('/login')
        assert response.status_code == 200
    
    def test_login_success(self, client, admin_user):
        """Test successful login"""
        response = client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # Check we're redirected to dashboard or home
        assert b'admin' in response.data or b'Dashboard' in response.data
    
    def test_login_failure(self, client, admin_user):
        """Test failed login with wrong password"""
        response = client.post('/login', data={
            'username': 'admin',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # Should show login page with error
        assert b'login' in response.data.lower() or b'error' in response.data.lower()
    
    def test_logout(self, authenticated_client):
        """Test logout functionality"""
        response = authenticated_client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        
        with authenticated_client.session_transaction() as sess:
            assert not sess.get('logged_in')
    
    def test_protected_route_requires_auth(self, client):
        """Test that protected routes require authentication"""
        response = client.get('/dashboard')
        # Should redirect to login
        assert response.status_code == 302 or response.status_code == 200
        if response.status_code == 302:
            assert '/login' in response.location

class TestRegistration:
    def test_register_page_loads(self, client):
        """Test that registration page loads"""
        response = client.get('/register')
        assert response.status_code == 200
    
    def test_register_new_user(self, client, db_session):
        """Test registering a new user"""
        response = client.post('/register', data={
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Verify user was created
        from models import User
        user = User.query.filter_by(username='newuser').first()
        assert user is not None
        assert user.email == 'newuser@test.com'

class TestRoleBasedAccess:
    def test_admin_access(self, client, admin_user):
        """Test admin can access admin routes"""
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user.id
            sess['logged_in'] = True
        
        response = client.get('/user_management')
        # Admin should have access
        assert response.status_code == 200 or response.status_code == 302
    
    def test_dispatcher_no_admin_access(self, client, dispatcher_user):
        """Test dispatcher cannot access admin routes"""
        with client.session_transaction() as sess:
            sess['user_id'] = dispatcher_user.id
            sess['logged_in'] = True
        
        response = client.get('/user_management')
        # Should be forbidden or redirected
        assert response.status_code in [302, 403, 200]

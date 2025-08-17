#!/usr/bin/env python3
"""
Test the route directly with web context
"""

import sys
sys.path.append('.')

from app_clean import app, db
import requests

with app.test_client() as client:
    # First, we need to create a session and login
    print("Testing lookup route with authenticated session...")
    
    # Try to access the lookup page
    try:
        response = client.get('/lookup')
        print(f"GET /lookup status: {response.status_code}")
        
        if response.status_code == 302:
            print("Redirected to login - need authentication")
            
        # Let's try to login first
        response = client.get('/login') 
        print(f"GET /login status: {response.status_code}")
        
        # Let's try to login with test credentials
        login_data = {
            'username': 'admin',
            'password': 'admin123'
        }
        
        # Get CSRF token from login form
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.data, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrf_token'})
        if csrf_token:
            login_data['csrf_token'] = csrf_token['value']
            print("Found CSRF token")
        
        response = client.post('/login', data=login_data, follow_redirects=True)
        print(f"POST /login status: {response.status_code}")
        
        # Now try the lookup page
        response = client.get('/lookup')
        print(f"GET /lookup after login status: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Lookup page loads successfully!")
            print("Content preview:", response.data[:500].decode('utf-8'))
        else:
            print("✗ Lookup page failed to load")
            print("Response:", response.data.decode('utf-8')[:1000])
            
    except Exception as e:
        print(f"✗ Route test error: {e}")
        import traceback
        traceback.print_exc()
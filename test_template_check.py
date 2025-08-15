import requests
from bs4 import BeautifulSoup
import re

# Create session
session = requests.Session()

# Get login page and extract CSRF token
login_page = session.get('http://localhost:5000/login')
soup = BeautifulSoup(login_page.text, 'html.parser')
csrf_token = soup.find('input', {'name': 'csrf_token'})

if csrf_token:
    csrf_value = csrf_token.get('value')
    print(f"CSRF token found: {csrf_value[:20]}...")
    
    # Login with CSRF token
    login_data = {
        'username': 'admin',
        'password': 'admin123',
        'csrf_token': csrf_value
    }
    
    login_resp = session.post('http://localhost:5000/login', data=login_data, allow_redirects=True)
    print(f"Login response status: {login_resp.status_code}")
    
    # Now access the bill scan page
    scan_page = session.get('http://localhost:5000/bill/1/scan_parent')
    print(f"Scan page status: {scan_page.status_code}")
    
    # Check which template is being used based on content
    if 'id="reader"' in scan_page.text:
        print("\n✓ Found 'reader' container - using scan_bill_parent_simple.html")
    elif 'id="qr-reader"' in scan_page.text:
        print("\n✓ Found 'qr-reader' container - using scan_bill_parent.html")
    else:
        print("\n✗ No scanner container found")
    
    # Check for LiveQRScanner
    if 'live-qr-scanner.js' in scan_page.text:
        print("✓ LiveQRScanner script is included")
    else:
        print("✗ LiveQRScanner script is NOT included")
        
    # Check for initialization
    if 'new LiveQRScanner' in scan_page.text:
        print("✓ LiveQRScanner is being initialized")
    else:
        print("✗ LiveQRScanner is NOT being initialized")
        
else:
    print("No CSRF token found - login page issue")

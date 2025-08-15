import requests
from bs4 import BeautifulSoup

# Create session
session = requests.Session()

# Get login page and extract CSRF token
login_page = session.get('http://localhost:5000/login')
soup = BeautifulSoup(login_page.text, 'html.parser')
csrf_token = soup.find('input', {'name': 'csrf_token'})

if csrf_token:
    csrf_value = csrf_token.get('value')
    
    # Login with CSRF token
    login_data = {
        'username': 'admin',
        'password': 'admin123',
        'csrf_token': csrf_value
    }
    
    login_resp = session.post('http://localhost:5000/login', data=login_data, allow_redirects=True)
    
    # Now access the bill scan page
    scan_page = session.get('http://localhost:5000/bill/1/scan_parent')
    
    # Check for local script files
    if '/static/js/libs/html5-qrcode.min.js' in scan_page.text:
        print("✓ HTML5-QRCode loaded from local file")
    else:
        print("✗ HTML5-QRCode NOT loading from local")
        
    if '/static/js/libs/jsQR.js' in scan_page.text:
        print("✓ jsQR loaded from local file")
    else:
        print("✗ jsQR NOT loading from local")
        
    if 'live-qr-scanner.js' in scan_page.text:
        print("✓ LiveQRScanner script included")
    else:
        print("✗ LiveQRScanner script NOT included")
        
    if 'new LiveQRScanner' in scan_page.text:
        print("✓ LiveQRScanner initialization code present")
    else:
        print("✗ LiveQRScanner initialization missing")

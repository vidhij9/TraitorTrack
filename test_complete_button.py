import requests
from bs4 import BeautifulSoup

# Create session and login
session = requests.Session()
login_page = session.get('http://localhost:5000/login')
soup = BeautifulSoup(login_page.text, 'html.parser')
csrf_token = soup.find('input', {'name': 'csrf_token'})

if csrf_token:
    csrf_value = csrf_token.get('value')
    login_data = {
        'username': 'admin',
        'password': 'admin123',
        'csrf_token': csrf_value
    }
    
    login_resp = session.post('http://localhost:5000/login', data=login_data, allow_redirects=True)
    
    # Get the bill scan page
    scan_page = session.get('http://localhost:5000/bill/1/scan_parent')
    soup = BeautifulSoup(scan_page.text, 'html.parser')
    
    # Check for Complete button
    complete_btn = soup.find('a', string=lambda text: 'Complete Scanning' in text if text else False)
    if complete_btn:
        print("✓ Complete Scanning button found")
        print(f"  Links to: {complete_btn.get('href')}")
    else:
        print("✗ Complete Scanning button NOT found")
    
    # Check for Back button
    back_btn = soup.find('a', string=lambda text: 'Back to Bills' in text if text else False)
    if back_btn:
        print("✓ Back to Bills button found")
        print(f"  Links to: {back_btn.get('href')}")
    else:
        print("✗ Back to Bills button NOT found")

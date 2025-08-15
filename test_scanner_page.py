import requests

# Create a session to maintain cookies
session = requests.Session()

# First, get the login page to get CSRF token
login_page = session.get('http://localhost:5000/login')

# Login as admin
login_data = {
    'username': 'admin',
    'password': 'admin123'
}

# Try to login
login_response = session.post('http://localhost:5000/login', data=login_data)

# Now access the bill parent scan page
scan_page = session.get('http://localhost:5000/bill/1/scan_parent')

# Check if our scripts are loaded
if 'live-qr-scanner.js' in scan_page.text:
    print("✓ LiveQRScanner is loaded correctly")
else:
    print("✗ LiveQRScanner is NOT loaded")
    
if 'camera-permissions.js' in scan_page.text:
    print("✓ Camera permissions manager is loaded")
else:
    print("✗ Camera permissions manager is NOT loaded")

# Check for scanner container
if 'id="reader"' in scan_page.text:
    print("✓ Scanner container is present")
else:
    print("✗ Scanner container is missing")

# Print a sample of the scripts section
import re
scripts = re.findall(r'<script.*?</script>', scan_page.text, re.DOTALL)
print(f"\nFound {len(scripts)} script tags")
for script in scripts[-5:]:  # Last 5 scripts
    if 'qr' in script.lower() or 'scanner' in script.lower():
        print(f"  - {script[:100]}...")

import requests
from bs4 import BeautifulSoup

# Create a session
session = requests.Session()

# Login (simplified)
session.get('http://localhost:5000/login')  # Get CSRF
login_resp = session.post('http://localhost:5000/login', 
                          data={'username': 'admin', 'password': 'admin123'},
                          allow_redirects=True)

# Get the actual bill scan page  
resp = session.get('http://localhost:5000/bill/1/scan_parent')

# Parse the HTML
soup = BeautifulSoup(resp.text, 'html.parser')

# Check for scanner elements
if 'reader' in resp.text:
    print("✓ Scanner container 'reader' found")
else:
    print("✗ Scanner container 'reader' NOT found")

# Find all script tags
scripts = soup.find_all('script')
print(f"\nFound {len(scripts)} script tags:")

for script in scripts:
    src = script.get('src', '')
    if 'qr' in src.lower() or 'scanner' in src.lower() or 'camera' in src.lower():
        print(f"  - {src}")

# Check if we have the LiveQRScanner
if 'LiveQRScanner' in resp.text:
    print("\n✓ LiveQRScanner class found in page")
else:
    print("\n✗ LiveQRScanner class NOT found in page")
    
# Check if camera-permissions is loaded
if 'camera-permissions.js' in resp.text:
    print("✓ Camera permissions manager loaded")
else:
    print("✗ Camera permissions manager NOT loaded")

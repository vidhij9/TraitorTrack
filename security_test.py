"""
Security testing utility for TraceTrack application.
Run this script to check for common security vulnerabilities.
"""
import re
import os
import sys
import logging
import requests
from urllib.parse import urljoin

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Base URL for the application (change as needed)
BASE_URL = "http://localhost:5000"
# Admin credentials for testing (use test account)
ADMIN_USER = "admin"
ADMIN_PASS = "adminpass"

# Test strings for various attacks
XSS_PAYLOADS = [
    "<script>alert('XSS')</script>",
    "<img src=x onerror=alert('XSS')>",
    "\"><script>alert('XSS')</script>",
    "';alert('XSS');//"
]

SQL_INJECTION_PAYLOADS = [
    "' OR '1'='1",
    "'; DROP TABLE users; --",
    "1' UNION SELECT username, password FROM users; --",
    "' OR 1=1; --"
]

CSRF_TEST_PATHS = [
    "/process_parent_scan",
    "/process_child_scan",
    "/link_to_bill/P123-10"
]

def get_session():
    """Get an authenticated session for testing"""
    session = requests.Session()
    try:
        # First request to get CSRF token
        response = session.get(urljoin(BASE_URL, "/login"))
        
        # Extract CSRF token (varies based on implementation)
        csrf_token = None
        match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
        if match:
            csrf_token = match.group(1)
            logger.info(f"Found CSRF token: {csrf_token}")
        else:
            logger.warning("No CSRF token found in login page")
        
        # Login with admin credentials
        login_data = {
            "username": ADMIN_USER,
            "password": ADMIN_PASS
        }
        
        if csrf_token:
            login_data["csrf_token"] = csrf_token
            
        response = session.post(
            urljoin(BASE_URL, "/login"),
            data=login_data,
            allow_redirects=True
        )
        
        if "Logout" in response.text:
            logger.info("Successfully logged in as admin")
        else:
            logger.error("Failed to log in as admin")
            
    except Exception as e:
        logger.error(f"Error getting authenticated session: {str(e)}")
    
    return session

def test_xss_vulnerability():
    """Test for XSS vulnerabilities in forms"""
    logger.info("Testing for XSS vulnerabilities...")
    session = get_session()
    
    # Forms and fields to test
    test_targets = [
        {
            "name": "Parent Bag Notes",
            "url": "/scan_parent",
            "payload_field": "notes",
            "other_fields": {"qr_id": "P123-10"}
        },
        {
            "name": "Location Name",
            "url": "/locations",
            "payload_field": "location_name",
            "other_fields": {"location_address": "Test Address"}
        }
    ]
    
    vulnerable = False
    
    for target in test_targets:
        for payload in XSS_PAYLOADS:
            try:
                data = target["other_fields"].copy()
                data[target["payload_field"]] = payload
                
                response = session.post(
                    urljoin(BASE_URL, target["url"]),
                    data=data,
                    allow_redirects=True
                )
                
                # Check if the payload was reflected without encoding/escaping
                if payload in response.text:
                    logger.warning(f"Potential XSS vulnerability found in {target['name']} with payload: {payload}")
                    vulnerable = True
                    
            except Exception as e:
                logger.error(f"Error testing XSS in {target['name']}: {str(e)}")
    
    if not vulnerable:
        logger.info("No obvious XSS vulnerabilities found")
    
    return not vulnerable

def test_csrf_protection():
    """Test CSRF protection on forms"""
    logger.info("Testing CSRF protection...")
    session = get_session()
    
    protected = True
    
    for path in CSRF_TEST_PATHS:
        try:
            # Try a post request without CSRF token
            response = requests.post(
                urljoin(BASE_URL, path),
                data={"test": "data"},
                cookies=session.cookies,  # Use authenticated session cookies
                allow_redirects=False
            )
            
            # Check response - a 400 or 403 indicates CSRF protection worked
            if response.status_code not in [400, 403]:
                logger.warning(f"CSRF protection may be missing on {path} (Status: {response.status_code})")
                protected = False
            else:
                logger.info(f"CSRF protection working on {path}")
                
        except Exception as e:
            logger.error(f"Error testing CSRF protection on {path}: {str(e)}")
    
    return protected

def test_security_headers():
    """Test for presence of security headers"""
    logger.info("Testing security headers...")
    
    try:
        response = requests.get(BASE_URL)
        
        # Headers that should be present
        required_headers = {
            "Content-Security-Policy": "Content Security Policy header",
            "X-Content-Type-Options": "X-Content-Type-Options header",
            "X-Frame-Options": "X-Frame-Options header",
            "X-XSS-Protection": "XSS Protection header"
        }
        
        all_headers_present = True
        
        for header, description in required_headers.items():
            if header in response.headers:
                logger.info(f"✓ {description} is present: {response.headers[header]}")
            else:
                logger.warning(f"✗ {description} is missing")
                all_headers_present = False
                
        return all_headers_present
    
    except Exception as e:
        logger.error(f"Error testing security headers: {str(e)}")
        return False

def test_rate_limiting():
    """Test if rate limiting is working"""
    logger.info("Testing rate limiting...")
    
    try:
        # Send multiple rapid requests to a rate-limited endpoint (login)
        success_count = 0
        blocked_count = 0
        
        for i in range(15):  # Try 15 rapid requests
            response = requests.post(
                urljoin(BASE_URL, "/login"),
                data={"username": "wronguser", "password": "wrongpass"}
            )
            
            if response.status_code == 429:  # Too Many Requests
                blocked_count += 1
            else:
                success_count += 1
        
        if blocked_count > 0:
            logger.info(f"Rate limiting is working. Blocked {blocked_count} of 15 requests.")
            return True
        else:
            logger.warning("Rate limiting may not be working. All requests succeeded.")
            return False
            
    except Exception as e:
        logger.error(f"Error testing rate limiting: {str(e)}")
        return False

def run_all_tests():
    """Run all security tests"""
    logger.info("Running security tests on TraceTrack application...")
    
    results = {
        "XSS Protection": test_xss_vulnerability(),
        "CSRF Protection": test_csrf_protection(),
        "Security Headers": test_security_headers(),
        "Rate Limiting": test_rate_limiting()
    }
    
    # Print summary
    logger.info("\n--- SECURITY TEST RESULTS ---")
    all_passed = True
    
    for test, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        logger.info(f"{test}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        logger.info("\nAll security tests passed! 🎉")
    else:
        logger.warning("\nSome security tests failed. Please review the output above.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1]
    
    run_all_tests()
"""
TraitorTrack Load Testing with Locust
======================================

This file contains comprehensive load tests for the TraitorTrack warehouse system.
Tests validate the system can handle 100+ concurrent users and 1.8M+ bags.

Usage:
    # Run from project root
    locust -f tests/load/locustfile.py --host=http://localhost:5000

    # Web UI (recommended)
    locust -f tests/load/locustfile.py --host=http://localhost:5000
    # Then visit http://localhost:8089

    # Headless mode (for CI/CD)
    locust -f tests/load/locustfile.py --host=http://localhost:5000 --headless -u 100 -r 10 -t 5m

Performance Targets:
    - API endpoints: <100ms (p95)
    - Scan operations: <200ms (p95)
    - Search: <500ms (p95)
    - 100+ concurrent users sustained
    - Zero errors under normal load
"""

import random
import string
import time
from locust import HttpUser, task, between, SequentialTaskSet, tag
from locust.exception import RescheduleTask
from bs4 import BeautifulSoup


class AuthMixin:
    """Mixin to handle authentication for all user types with CSRF token support"""
    
    def extract_csrf_token(self, response):
        """Extract CSRF token from HTML response"""
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try meta tag first (most common in Flask apps)
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if csrf_meta and csrf_meta.get('content'):
                return csrf_meta['content']
            
            # Try hidden input field
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            if csrf_input and csrf_input.get('value'):
                return csrf_input['value']
            
            return None
        except Exception as e:
            print(f"Error extracting CSRF token: {e}")
            return None
    
    def login(self, username, password):
        """Login with CSRF token handling and session management"""
        try:
            # Step 1: GET the login page to establish session and get CSRF token
            with self.client.get("/login", catch_response=True, name="GET /login") as login_page:
                if login_page.status_code != 200:
                    login_page.failure(f"Failed to get login page: {login_page.status_code}")
                    print(f"❌ Failed to get login page: {login_page.status_code}")
                    return False
                
                # Extract CSRF token from the response
                csrf_token = self.extract_csrf_token(login_page)
                
                if not csrf_token:
                    login_page.failure("No CSRF token found in login page")
                    print(f"❌ No CSRF token found for {username}")
                    return False
                
                login_page.success()
            
            # Step 2: Prepare login form data (match Flask-WTF expectations)
            login_data = {
                "username": username,
                "password": password,
                "csrf_token": csrf_token
            }
            
            # Step 3: POST to login endpoint
            # Note: Locust's self.client maintains session cookies automatically
            with self.client.post("/login", 
                                 data=login_data,
                                 allow_redirects=False,  # Don't follow redirect so we can check 302
                                 catch_response=True,
                                 name="POST /login") as response:
                
                # Check for successful redirect (302 to dashboard)
                if response.status_code == 302:
                    redirect_url = response.headers.get('Location', '')
                    print(f"✅ Login successful for {username} - redirecting to {redirect_url}")
                    response.success()
                    
                    # Step 4: Verify we can access authenticated page
                    with self.client.get("/dashboard", catch_response=True, name="Verify Login") as dashboard:
                        if dashboard.status_code == 200:
                            dashboard.success()
                            print(f"✅ Dashboard access confirmed for {username}")
                            return True
                        else:
                            dashboard.failure(f"Cannot access dashboard after login: {dashboard.status_code}")
                            print(f"❌ Dashboard access failed: {dashboard.status_code}")
                            return False
                else:
                    # Login failed - mark as failure with details
                    response.failure(f"Login returned {response.status_code} instead of 302")
                    print(f"❌ Login failed for {username}: {response.status_code}")
                    
                    if response.status_code == 400:
                        print(f"   → CSRF validation failed - check token/session pairing")
                    elif response.status_code == 429:
                        print(f"   → Rate limit hit - too many login attempts")
                    elif response.status_code == 200:
                        print(f"   → Login page re-rendered - credentials or CSRF issue")
                    
                    return False
                
        except Exception as e:
            print(f"❌ Login exception for {username}: {e}")
            return False
    
    def ensure_logged_in(self):
        """Ensure user is logged in before performing actions"""
        # Check if we can access a protected page
        response = self.client.get("/dashboard", allow_redirects=False)
        if response.status_code == 302:
            # Need to login
            return self.login(self.username, self.password)
        return True
    
    def get_csrf_token_from_page(self, url):
        """Get CSRF token from any page"""
        try:
            response = self.client.get(url, catch_response=True)
            if response.status_code == 200:
                return self.extract_csrf_token(response)
            return None
        except Exception as e:
            print(f"Error getting CSRF from {url}: {e}")
            return None


class DispatcherBehavior(SequentialTaskSet, AuthMixin):
    """
    Realistic dispatcher workflow:
    1. Login
    2. View dashboard
    3. Scan bags (parent/child)
    4. Create new parent bags
    5. Link bags
    6. Search for bags
    """
    
    def on_start(self):
        """Login when task set starts"""
        self.username = "admin"  # Using existing admin for testing
        self.password = "vidhi2029"
        self.login(self.username, self.password)
        self.parent_bags = []
        self.child_bags = []
    
    @task(3)
    def view_dashboard(self):
        """View dashboard - most common action"""
        self.client.get("/dashboard", name="Dashboard")
    
    @task(5)
    def scan_parent_bag(self):
        """Simulate scanning a parent bag"""
        # Generate realistic mustard bag QR (SB##### format)
        qr_id = f"SB{random.randint(10000, 99999)}"
        
        response = self.client.post("/scan", data={
            "qr_id": qr_id
        }, name="Scan Parent Bag")
        
        if response.status_code == 200:
            self.parent_bags.append(qr_id)
    
    @task(7)
    def scan_child_bag(self):
        """Simulate scanning a child bag"""
        # Generate realistic moong bag QR (M444-##### format)
        qr_id = f"M444-{random.randint(10000, 99999)}"
        
        response = self.client.post("/scan", data={
            "qr_id": qr_id
        }, name="Scan Child Bag")
        
        if response.status_code == 200:
            self.child_bags.append(qr_id)
    
    @task(2)
    def create_parent_bag(self):
        """Create a new parent bag via API"""
        qr_id = f"SB{random.randint(10000, 99999)}"
        
        response = self.client.post("/api/bags", json={
            "qr_id": qr_id,
            "type": "parent",
            "name": f"Load Test Parent {qr_id}"
        }, name="Create Parent Bag API")
        
        if response.status_code in [200, 201]:
            self.parent_bags.append(qr_id)
    
    @task(2)
    def search_bags(self):
        """Search for bags"""
        search_terms = [
            f"SB{random.randint(10000, 99999)}",
            f"M444-{random.randint(10000, 99999)}",
            "parent",
            "child"
        ]
        
        search_term = random.choice(search_terms)
        self.client.get(f"/bag_management?search={search_term}", name="Search Bags")
    
    @task(1)
    def view_bag_management(self):
        """View bag management page"""
        self.client.get("/bag_management", name="Bag Management Page")
    
    def wait_time(self):
        """Realistic think time between actions (1-5 seconds)"""
        return random.uniform(1, 5)


class BillerBehavior(SequentialTaskSet, AuthMixin):
    """
    Realistic biller workflow:
    1. Login
    2. View bills
    3. Create new bills
    4. Add bags to bills
    5. Finalize bills
    6. Generate reports
    """
    
    def on_start(self):
        """Login when task set starts"""
        self.username = "admin"  # Using existing admin for testing
        self.password = "vidhi2029"
        self.login(self.username, self.password)
        self.created_bills = []
    
    @task(3)
    def view_bills(self):
        """View bills page"""
        self.client.get("/bills", name="View Bills")
    
    @task(2)
    def create_bill(self):
        """Create a new bill"""
        bill_id = f"LOAD{random.randint(1000, 9999)}"
        
        response = self.client.post("/bill/create", data={
            "bill_id": bill_id,
            "description": f"Load Test Bill {bill_id}"
        }, name="Create Bill")
        
        if response.status_code in [200, 302]:
            self.created_bills.append(bill_id)
    
    @task(2)
    def view_bill_details(self):
        """View bill details"""
        if self.created_bills:
            bill_id = random.choice(self.created_bills)
            self.client.get(f"/bill/{bill_id}", name="View Bill Details")
    
    @task(1)
    def search_bills(self):
        """Search for bills"""
        search_term = f"LOAD{random.randint(1000, 9999)}"
        self.client.get(f"/bills?search={search_term}", name="Search Bills")
    
    def wait_time(self):
        """Realistic think time between actions (2-8 seconds)"""
        return random.uniform(2, 8)


class AdminBehavior(SequentialTaskSet, AuthMixin):
    """
    Admin workflow:
    1. View dashboard
    2. User management
    3. System health monitoring
    4. Reports and exports
    """
    
    def on_start(self):
        """Login when task set starts"""
        self.username = "admin"
        self.password = "vidhi2029"
        self.login(self.username, self.password)
    
    @task(5)
    def view_dashboard(self):
        """View dashboard with statistics"""
        self.client.get("/dashboard", name="Admin Dashboard")
    
    @task(2)
    def view_users(self):
        """View user management"""
        self.client.get("/user_management", name="User Management")
    
    @task(1)
    def view_system_health(self):
        """View system health metrics"""
        self.client.get("/admin/system-health", name="System Health")
    
    @task(1)
    def view_audit_logs(self):
        """View audit logs"""
        self.client.get("/admin/audit-logs", name="Audit Logs")
    
    def wait_time(self):
        """Admin actions have longer think time (5-15 seconds)"""
        return random.uniform(5, 15)


class DispatcherUser(HttpUser):
    """Simulates a warehouse dispatcher"""
    tasks = [DispatcherBehavior]
    weight = 60  # 60% of users are dispatchers
    wait_time = between(1, 5)  # Wait 1-5 seconds between task sets
    
    def on_start(self):
        """Disable SSL verification for development/testing"""
        # WARNING: Never use this in production!
        self.client.verify = False


class BillerUser(HttpUser):
    """Simulates a biller creating and managing bills"""
    tasks = [BillerBehavior]
    weight = 30  # 30% of users are billers
    wait_time = between(2, 8)
    
    def on_start(self):
        """Disable SSL verification for development/testing"""
        self.client.verify = False


class AdminUser(HttpUser):
    """Simulates an admin monitoring the system"""
    tasks = [AdminBehavior]
    weight = 10  # 10% of users are admins
    wait_time = between(5, 15)
    
    def on_start(self):
        """Disable SSL verification for development/testing"""
        self.client.verify = False


class APIPerfUser(HttpUser):
    """
    Dedicated API performance testing user
    Tests critical API endpoints for performance without authentication
    
    Usage: locust -f tests/load/locustfile.py --host=http://localhost:5000 --users 50 --spawn-rate 5 --run-time 2m --only-summary
    """
    weight = 0  # Not included in normal load tests (set weight > 0 to include)
    wait_time = between(0.1, 0.5)  # Rapid-fire API testing
    
    def on_start(self):
        """Disable SSL verification for development/testing"""
        self.client.verify = False
    
    @tag('api-perf')
    @task(10)
    def test_api_bags_list(self):
        """Test /api/bags endpoint (most critical)"""
        self.client.get("/api/bags?page=1&per_page=50", name="API: List Bags")
    
    @tag('api-perf')
    @task(5)
    def test_api_bags_search(self):
        """Test bag search API"""
        qr = f"SB{random.randint(10000, 99999)}"
        self.client.get(f"/api/bags/search?q={qr}", name="API: Search Bags")
    
    @tag('api-perf')
    @task(5)
    def test_api_bills_list(self):
        """Test /api/bills endpoint"""
        self.client.get("/api/bills?page=1&per_page=50", name="API: List Bills")
    
    @tag('api-perf')
    @task(3)
    def test_api_stats(self):
        """Test statistics API"""
        self.client.get("/api/statistics", name="API: Statistics")


class QuickTestUser(HttpUser):
    """
    Simple test user for quick validation - no authentication required
    Tests public endpoints and basic functionality
    Useful for validating the load test setup works
    """
    weight = 100  # Used for quick tests
    wait_time = between(1, 3)
    
    def on_start(self):
        """Disable SSL verification for development/testing"""
        self.client.verify = False
    
    @task(5)
    def test_login_page(self):
        """Test login page loads"""
        self.client.get("/login", name="Login Page")
    
    @task(3)
    def test_home_redirect(self):
        """Test home page redirect"""
        self.client.get("/", name="Home Redirect")
    
    @task(1)
    def test_static_assets(self):
        """Test static assets load"""
        # Test that error pages work
        self.client.get("/nonexistent-page", name="404 Page")

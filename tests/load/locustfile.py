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


class AuthMixin:
    """Mixin to handle authentication for all user types"""
    
    def login(self, username, password):
        """Login and store session"""
        response = self.client.post("/login", data={
            "username": username,
            "password": password
        }, allow_redirects=False)
        
        if response.status_code != 302:
            print(f"Login failed for {username}: {response.status_code}")
            return False
        
        return True
    
    def ensure_logged_in(self):
        """Ensure user is logged in before performing actions"""
        # Check if we can access a protected page
        response = self.client.get("/dashboard", allow_redirects=False)
        if response.status_code == 302:
            # Need to login
            return self.login(self.username, self.password)
        return True


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


class BillerUser(HttpUser):
    """Simulates a biller creating and managing bills"""
    tasks = [BillerBehavior]
    weight = 30  # 30% of users are billers
    wait_time = between(2, 8)


class AdminUser(HttpUser):
    """Simulates an admin monitoring the system"""
    tasks = [AdminBehavior]
    weight = 10  # 10% of users are admins
    wait_time = between(5, 15)


class APIPerfUser(HttpUser):
    """
    Dedicated API performance testing user
    Tests critical API endpoints for performance
    """
    weight = 0  # Not included in normal load tests (use --tags api-perf)
    wait_time = between(0.1, 0.5)  # Rapid-fire API testing
    
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

from locust import HttpUser, task, between
import random
import string
import os

class TraceTrackUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login before starting tasks"""
        # Try to login as admin
        self.client.post("/login", data={
            "username": "admin",
            "password": os.environ.get("ADMIN_PASSWORD", "admin123")
        })
    
    @task(3)
    def view_dashboard(self):
        """View dashboard - most common operation"""
        self.client.get("/dashboard")
    
    @task(2)
    def view_bag_management(self):
        """View bag management page"""
        self.client.get("/bag_management")
    
    @task(2)
    def view_bill_management(self):
        """View bill management page"""
        self.client.get("/bill_management")
    
    @task(1)
    def scan_parent(self):
        """Access parent bag scanning page"""
        self.client.get("/scan_parent")
    
    @task(1)
    def view_reports(self):
        """View reports page"""
        self.client.get("/reports")
    
    @task(1)
    def api_health_check(self):
        """Check API health endpoint"""
        self.client.get("/health")
    
    @task(1)
    def search_bags(self):
        """Search for bags"""
        search_term = f"BAG{random.randint(1, 1000)}"
        self.client.get(f"/bag_management?search={search_term}")

class HeavyLoadUser(HttpUser):
    """Simulate heavy operations like Excel upload and bill creation"""
    wait_time = between(5, 10)
    
    def on_start(self):
        """Login as biller"""
        self.client.post("/login", data={
            "username": "biller",
            "password": os.environ.get("BILLER_PASSWORD", "biller123")
        })
    
    @task(1)
    def create_bill(self):
        """Create a new bill"""
        bill_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        self.client.post("/bill/create", data={
            "bill_id": bill_id,
            "description": f"Load Test Bill {bill_id}"
        })
    
    @task(1)
    def process_parent_scan(self):
        """Process parent bag scan"""
        qr_id = f"PARENT{random.randint(1, 10000)}"
        self.client.post("/process_parent_scan", data={
            "qr_id": qr_id
        })

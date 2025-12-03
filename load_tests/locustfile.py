"""
TraitorTrack Load Testing with Locust
Production-ready load testing for 100+ concurrent users
"""

import random
import string
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner, WorkerRunner
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TraitorTrackUser(HttpUser):
    """Simulates a warehouse user performing typical operations"""
    
    wait_time = between(1, 3)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logged_in = False
        self.csrf_token = None
        self.test_bags = [f"M444-{i:05d}" for i in range(1, 31)]
        
    def on_start(self):
        """Login before starting tasks"""
        self.login()
    
    def login(self):
        """Authenticate and get session"""
        response = self.client.get("/login")
        
        self.csrf_token = self.extract_csrf_token(response.text)
        
        login_data = {
            "username": "superadmin",
            "password": "vidhi2029",
            "csrf_token": self.csrf_token
        }
        
        response = self.client.post("/login", data=login_data, allow_redirects=True)
        
        if response.status_code == 200 and "/dashboard" in response.url:
            self.logged_in = True
            logger.info("Login successful")
        else:
            logger.warning(f"Login may have failed: {response.status_code}")
            self.logged_in = True
    
    def extract_csrf_token(self, html):
        """Extract CSRF token from HTML form"""
        import re
        match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
        if match:
            return match.group(1)
        match = re.search(r'value="([^"]+)"[^>]*name="csrf_token"', html)
        if match:
            return match.group(1)
        return ""
    
    @task(30)
    def view_dashboard(self):
        """View dashboard - 30% of requests"""
        self.client.get("/dashboard", name="/dashboard")
    
    @task(20)
    def search_bag(self):
        """Search for a bag - 20% of requests"""
        bag_qr = random.choice(self.test_bags)
        self.client.get(f"/search?q={bag_qr}", name="/search")
    
    @task(15)
    def view_bills(self):
        """View bills list - 15% of requests"""
        self.client.get("/bills", name="/bills")
    
    @task(10)
    def view_bags(self):
        """View bags list - 10% of requests"""
        self.client.get("/bag_management", name="/bag_management")
    
    @task(10)
    def api_dashboard_stats(self):
        """Get dashboard stats via API - 10% of requests"""
        self.client.get("/api/v2/stats", name="/api/v2/stats")
    
    @task(5)
    def api_bags_list(self):
        """Get bags via API - 5% of requests"""
        self.client.get("/api/v2/bags?page=1&per_page=20", name="/api/v2/bags")
    
    @task(5)
    def api_bills_list(self):
        """Get bills via API - 5% of requests"""
        self.client.get("/api/v2/bills?page=1&per_page=20", name="/api/v2/bills")
    
    @task(3)
    def view_user_management(self):
        """View user management (admin) - 3% of requests"""
        self.client.get("/user_management", name="/user_management")
    
    @task(2)
    def view_pool_dashboard(self):
        """View pool dashboard (admin) - 2% of requests"""
        self.client.get("/admin/pool_dashboard", name="/admin/pool_dashboard")


class ScannerUser(HttpUser):
    """Simulates a warehouse scanner performing rapid scans"""
    
    wait_time = between(0.5, 2)
    weight = 2
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logged_in = False
        self.csrf_token = None
        self.current_bill_id = None
        
    def on_start(self):
        """Login and setup for scanning"""
        self.login()
    
    def login(self):
        """Authenticate"""
        response = self.client.get("/login")
        self.csrf_token = self.extract_csrf_token(response.text)
        
        login_data = {
            "username": "superadmin",
            "password": "vidhi2029",
            "csrf_token": self.csrf_token
        }
        
        self.client.post("/login", data=login_data, allow_redirects=True)
        self.logged_in = True
    
    def extract_csrf_token(self, html):
        """Extract CSRF token from HTML form"""
        import re
        match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
        if match:
            return match.group(1)
        return ""
    
    @task(50)
    def view_scan_interface(self):
        """View scanning interface - 50% of requests"""
        self.client.get("/bills", name="/bills [scanner]")
    
    @task(30)
    def quick_search(self):
        """Quick bag search - 30% of requests"""
        bag_num = random.randint(1, 30)
        self.client.get(f"/search?q=M444-{bag_num:05d}", name="/search [scanner]")
    
    @task(20)
    def dashboard_check(self):
        """Dashboard check - 20% of requests"""
        self.client.get("/dashboard", name="/dashboard [scanner]")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts"""
    if isinstance(environment.runner, MasterRunner):
        logger.info("Load test starting on master")
    elif isinstance(environment.runner, WorkerRunner):
        logger.info(f"Load test starting on worker {environment.runner.client_id}")
    else:
        logger.info("Load test starting (standalone mode)")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops"""
    logger.info("Load test completed")
    
    if environment.stats.total.num_requests > 0:
        logger.info(f"Total requests: {environment.stats.total.num_requests}")
        logger.info(f"Total failures: {environment.stats.total.num_failures}")
        logger.info(f"Avg response time: {environment.stats.total.avg_response_time:.2f}ms")
        
        if environment.stats.total.num_requests > 0:
            failure_rate = (environment.stats.total.num_failures / environment.stats.total.num_requests) * 100
            logger.info(f"Failure rate: {failure_rate:.2f}%")

"""
Locust load test for TraceTrack - 1.5M bags, 50+ concurrent users
Tests scanner endpoints and dashboard with realistic user behavior
"""
from locust import HttpUser, task, between, SequentialTaskSet
import random
import time

class ScannerUserBehavior(SequentialTaskSet):
    """Realistic scanner user workflow"""
    
    def on_start(self):
        """Login before starting"""
        # Login as admin
        response = self.client.post('/login', data={
            'username': 'admin',
            'password': 'admin'
        }, allow_redirects=False)
        
        if response.status_code in [200, 302]:
            print(f"✓ User logged in successfully")
        else:
            print(f"✗ Login failed: {response.status_code}")
    
    @task
    def scan_parent_workflow(self):
        """Complete parent scanning workflow"""
        # Navigate to parent scan page
        self.client.get('/scan_parent', name="/scan_parent [GET]")
        
        # Wait a bit (realistic user behavior)
        time.sleep(random.uniform(0.5, 1.5))
        
        # Scan a random parent bag
        parent_qr = f"SB{random.randint(1, 50000):05d}"
        
        start_time = time.time()
        response = self.client.post('/process_parent_scan', 
            data={
                'qr_code': parent_qr
            },
            name="/process_parent_scan [POST]",
            allow_redirects=False
        )
        
        response_time = (time.time() - start_time) * 1000
        
        if response.status_code in [200, 302]:
            if response_time < 300:
                print(f"✓ Parent scan {parent_qr}: {response_time:.0f}ms")
            else:
                print(f"⚠ Parent scan {parent_qr}: {response_time:.0f}ms (>300ms)")
        else:
            print(f"✗ Parent scan failed: {response.status_code}")
        
        # Small think time
        time.sleep(random.uniform(0.3, 0.8))
    
    @task
    def scan_child_workflow(self):
        """Complete child scanning workflow"""
        # First scan a parent
        parent_qr = f"SB{random.randint(1, 50000):05d}"
        self.client.post('/process_parent_scan', 
            data={'qr_code': parent_qr},
            allow_redirects=False
        )
        
        # Navigate to child scan page
        self.client.get('/scan_child', name="/scan_child [GET]")
        time.sleep(random.uniform(0.3, 0.7))
        
        # Scan 3-5 random child bags
        num_children = random.randint(3, 5)
        for _ in range(num_children):
            child_qr = f"CB{random.randint(1, 1450000):06d}"
            
            start_time = time.time()
            response = self.client.post('/api/fast_child_scan',
                data={'qr_code': child_qr},
                name="/api/fast_child_scan [POST]",
                allow_redirects=False
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                if response_time < 300:
                    print(f"✓ Child scan {child_qr}: {response_time:.0f}ms")
                else:
                    print(f"⚠ Child scan {child_qr}: {response_time:.0f}ms (>300ms)")
            
            # Quick scan interval
            time.sleep(random.uniform(0.2, 0.5))

class DashboardUserBehavior(SequentialTaskSet):
    """Realistic dashboard user workflow"""
    
    def on_start(self):
        """Login before starting"""
        self.client.post('/login', data={
            'username': 'admin',
            'password': 'admin'
        }, allow_redirects=False)
    
    @task
    def view_dashboard(self):
        """View main dashboard with stats"""
        start_time = time.time()
        response = self.client.get('/', name="/ [Dashboard]")
        response_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200 and response_time < 500:
            print(f"✓ Dashboard loaded: {response_time:.0f}ms")
        
        time.sleep(random.uniform(2, 5))
    
    @task
    def view_bag_management(self):
        """View bag management page"""
        start_time = time.time()
        response = self.client.get('/bag_management', name="/bag_management [GET]")
        response_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200 and response_time < 500:
            print(f"✓ Bag management: {response_time:.0f}ms")
        
        time.sleep(random.uniform(3, 7))
    
    @task
    def api_stats(self):
        """Check API stats"""
        start_time = time.time()
        response = self.client.get('/api/stats', name="/api/stats [GET]")
        response_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200 and response_time < 200:
            print(f"✓ API stats: {response_time:.0f}ms")
        
        time.sleep(random.uniform(1, 3))

class ScannerUser(HttpUser):
    """Scanner user - focuses on scanning operations"""
    tasks = [ScannerUserBehavior]
    wait_time = between(1, 3)  # Wait 1-3 seconds between task sets
    weight = 7  # 70% of users are scanners

class DashboardUser(HttpUser):
    """Dashboard user - focuses on viewing data"""
    tasks = [DashboardUserBehavior]
    wait_time = between(3, 8)  # Wait 3-8 seconds between task sets
    weight = 3  # 30% of users are dashboard viewers

# Performance thresholds
class PerformanceMonitor:
    """Monitor and report performance metrics"""
    
    @staticmethod
    def check_response_time(response_time_ms, endpoint, threshold=300):
        """Check if response time meets threshold"""
        if response_time_ms > threshold:
            print(f"⚠ SLOW: {endpoint} took {response_time_ms:.0f}ms (threshold: {threshold}ms)")
            return False
        return True

"""
Ultra-Fast Bill Parent Scan Performance Tests
==============================================

Comprehensive edge case, load, and stress testing for the optimized 
ultra_fast_bill_parent_scan and ultra_fast_remove_bag_from_bill endpoints.

Target: <10ms P95 response time for individual operations

Usage:
    # Run from project root
    python tests/load/ultra_fast_perf_test.py
    
    # Or with locust for load testing
    locust -f tests/load/ultra_fast_perf_test.py --host=http://localhost:5000 --headless -u 100 -r 10 -t 2m
"""

import random
import string
import time
import threading
import statistics
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from locust import HttpUser, task, between, events, tag
from bs4 import BeautifulSoup


class UltraFastScanUser(HttpUser):
    """
    Dedicated performance testing for ultra-fast bill parent scanning.
    Targets <10ms P95 response time.
    """
    wait_time = between(0, 0.1)  # Minimal wait for stress testing
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.csrf_token = None
        self.test_bill_id = None
        self.test_bags = []
        
    def on_start(self):
        """Login and setup test data"""
        self.client.verify = False
        self.login()
        self.setup_test_bill()
        
    def extract_csrf_token(self, response):
        """Extract CSRF token from HTML response"""
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if csrf_meta and csrf_meta.get('content'):
                return csrf_meta['content']
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            if csrf_input and csrf_input.get('value'):
                return csrf_input['value']
            return None
        except Exception:
            return None
    
    def login(self):
        """Login with CSRF handling"""
        response = self.client.get("/login")
        self.csrf_token = self.extract_csrf_token(response)
        
        self.client.post("/login", data={
            "username": "superadmin",
            "password": "vidhi2029",
            "csrf_token": self.csrf_token
        }, allow_redirects=True)
        
        # Refresh CSRF token after login
        dash = self.client.get("/dashboard")
        self.csrf_token = self.extract_csrf_token(dash) or self.csrf_token
    
    def setup_test_bill(self):
        """Create or find a test bill for scanning"""
        response = self.client.get("/bills")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find first bill link
        bill_links = soup.find_all('a', href=lambda x: x and '/bill/' in x)
        if bill_links:
            href = bill_links[0].get('href')
            import re
            match = re.search(r'/bill/(\d+)', href)
            if match:
                self.test_bill_id = int(match.group(1))
                return
        
        # If no bills, use a default
        self.test_bill_id = 1
    
    def generate_parent_qr(self):
        """Generate a realistic parent bag QR code"""
        prefix = random.choice(['SB', 'M444-'])
        suffix = random.randint(10000, 99999)
        return f"{prefix}{suffix}"
    
    @tag('ultra-fast')
    @task(10)
    def test_fast_scan_parent(self):
        """Test ultra-fast parent bag scanning - primary performance metric"""
        if not self.test_bill_id:
            return
            
        qr_code = self.generate_parent_qr()
        
        # Get fresh CSRF token
        scan_page = self.client.get(f"/bill/{self.test_bill_id}/scan_parent_fast", name="GET Scan Page")
        csrf = self.extract_csrf_token(scan_page) or self.csrf_token
        
        start = time.time()
        response = self.client.post(
            "/fast/bill_parent_scan",
            data={
                "bill_id": self.test_bill_id,
                "qr_code": qr_code,
                "csrf_token": csrf
            },
            headers={"X-Requested-With": "XMLHttpRequest"},
            name="POST Ultra-Fast Scan"
        )
        elapsed_ms = (time.time() - start) * 1000
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('success'):
                    self.test_bags.append(qr_code)
            except Exception:
                pass
    
    @tag('ultra-fast')
    @task(5)
    def test_fast_remove_bag(self):
        """Test ultra-fast bag removal - secondary performance metric"""
        if not self.test_bill_id or not self.test_bags:
            return
            
        qr_code = self.test_bags.pop() if self.test_bags else self.generate_parent_qr()
        
        # Get fresh CSRF token
        scan_page = self.client.get(f"/bill/{self.test_bill_id}/scan_parent_fast", name="GET Scan Page (Remove)")
        csrf = self.extract_csrf_token(scan_page) or self.csrf_token
        
        start = time.time()
        response = self.client.post(
            "/remove_bag_from_bill",
            data={
                "bill_id": self.test_bill_id,
                "parent_qr": qr_code,
                "csrf_token": csrf
            },
            headers={"X-Requested-With": "XMLHttpRequest"},
            name="POST Ultra-Fast Remove"
        )
        elapsed_ms = (time.time() - start) * 1000
    
    @tag('edge-case')
    @task(2)
    def test_duplicate_scan(self):
        """Edge case: Scan same bag twice (should be rejected)"""
        if not self.test_bill_id:
            return
            
        qr_code = "SB99999"  # Fixed QR to force duplicates
        
        scan_page = self.client.get(f"/bill/{self.test_bill_id}/scan_parent_fast", name="GET Scan Page (Dup)")
        csrf = self.extract_csrf_token(scan_page) or self.csrf_token
        
        self.client.post(
            "/fast/bill_parent_scan",
            data={
                "bill_id": self.test_bill_id,
                "qr_code": qr_code,
                "csrf_token": csrf
            },
            headers={"X-Requested-With": "XMLHttpRequest"},
            name="POST Duplicate Scan Test"
        )
    
    @tag('edge-case')
    @task(1)
    def test_invalid_qr(self):
        """Edge case: Scan invalid QR code"""
        if not self.test_bill_id:
            return
            
        scan_page = self.client.get(f"/bill/{self.test_bill_id}/scan_parent_fast", name="GET Scan Page (Invalid)")
        csrf = self.extract_csrf_token(scan_page) or self.csrf_token
        
        self.client.post(
            "/fast/bill_parent_scan",
            data={
                "bill_id": self.test_bill_id,
                "qr_code": "INVALID_QR_12345",
                "csrf_token": csrf
            },
            headers={"X-Requested-With": "XMLHttpRequest"},
            name="POST Invalid QR Test"
        )
    
    @tag('edge-case')
    @task(1)
    def test_nonexistent_bill(self):
        """Edge case: Scan to non-existent bill"""
        scan_page = self.client.get("/bills", name="GET Bills (NonExistent)")
        csrf = self.extract_csrf_token(scan_page) or self.csrf_token
        
        self.client.post(
            "/fast/bill_parent_scan",
            data={
                "bill_id": 999999,  # Non-existent bill
                "qr_code": "SB12345",
                "csrf_token": csrf
            },
            headers={"X-Requested-With": "XMLHttpRequest"},
            name="POST NonExistent Bill Test"
        )


class RaceConditionStressUser(HttpUser):
    """
    Tests race conditions under extreme concurrency.
    Multiple users trying to scan/remove same bags simultaneously.
    """
    wait_time = between(0, 0.05)  # Near-zero wait for maximum concurrency
    
    # Shared resources to force race conditions
    SHARED_BAGS = [f"RACE-{i:05d}" for i in range(10)]
    SHARED_BILL_ID = 1
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.csrf_token = None
        
    def on_start(self):
        """Login"""
        self.client.verify = False
        response = self.client.get("/login")
        self.csrf_token = self.extract_csrf_token(response)
        
        self.client.post("/login", data={
            "username": "superadmin",
            "password": "vidhi2029",
            "csrf_token": self.csrf_token
        }, allow_redirects=True)
        
        dash = self.client.get("/dashboard")
        self.csrf_token = self.extract_csrf_token(dash) or self.csrf_token
    
    def extract_csrf_token(self, response):
        """Extract CSRF token from HTML response"""
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if csrf_meta and csrf_meta.get('content'):
                return csrf_meta['content']
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            if csrf_input and csrf_input.get('value'):
                return csrf_input['value']
            return None
        except Exception:
            return None
    
    @tag('race')
    @task(10)
    def race_scan_same_bag(self):
        """Multiple users scanning same bag - tests advisory lock"""
        qr_code = random.choice(self.SHARED_BAGS)
        
        scan_page = self.client.get(f"/bill/{self.SHARED_BILL_ID}/scan_parent_fast", name="GET Scan (Race)")
        csrf = self.extract_csrf_token(scan_page) or self.csrf_token
        
        self.client.post(
            "/fast/bill_parent_scan",
            data={
                "bill_id": self.SHARED_BILL_ID,
                "qr_code": qr_code,
                "csrf_token": csrf
            },
            headers={"X-Requested-With": "XMLHttpRequest"},
            name="POST Race Scan"
        )
    
    @tag('race')
    @task(5)
    def race_scan_remove_same_bag(self):
        """Scan and remove same bag concurrently - tests lock ordering"""
        qr_code = random.choice(self.SHARED_BAGS)
        
        scan_page = self.client.get(f"/bill/{self.SHARED_BILL_ID}/scan_parent_fast", name="GET Scan (Race Remove)")
        csrf = self.extract_csrf_token(scan_page) or self.csrf_token
        
        # Randomly either scan or remove
        if random.random() < 0.5:
            self.client.post(
                "/fast/bill_parent_scan",
                data={
                    "bill_id": self.SHARED_BILL_ID,
                    "qr_code": qr_code,
                    "csrf_token": csrf
                },
                headers={"X-Requested-With": "XMLHttpRequest"},
                name="POST Race Scan/Remove"
            )
        else:
            self.client.post(
                "/remove_bag_from_bill",
                data={
                    "bill_id": self.SHARED_BILL_ID,
                    "parent_qr": qr_code,
                    "csrf_token": csrf
                },
                headers={"X-Requested-With": "XMLHttpRequest"},
                name="POST Race Remove/Scan"
            )


# Event hooks for reporting
@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """Print performance summary when test ends"""
    print("\n" + "="*70)
    print("ULTRA-FAST SCAN PERFORMANCE REPORT")
    print("="*70)
    
    stats = environment.stats
    
    # Get scan-specific stats
    scan_stats = stats.get("POST Ultra-Fast Scan", None)
    remove_stats = stats.get("POST Ultra-Fast Remove", None)
    
    print("\n📊 OVERALL METRICS:")
    print(f"  Total Requests: {stats.total.num_requests}")
    print(f"  Total Failures: {stats.total.num_failures}")
    print(f"  Failure Rate: {(stats.total.num_failures / max(1, stats.total.num_requests)) * 100:.2f}%")
    print(f"  Requests/sec: {stats.total.total_rps:.2f}")
    
    print("\n🎯 PERFORMANCE TARGETS:")
    
    if scan_stats:
        p50 = scan_stats.get_response_time_percentile(0.50)
        p95 = scan_stats.get_response_time_percentile(0.95)
        p99 = scan_stats.get_response_time_percentile(0.99)
        avg = scan_stats.avg_response_time
        
        print(f"\n  Ultra-Fast Scan Endpoint:")
        print(f"    Average: {avg:.2f}ms")
        print(f"    P50: {p50:.2f}ms")
        print(f"    P95: {p95:.2f}ms {'✅' if p95 < 10 else '⚠️' if p95 < 100 else '❌'} (Target: <10ms)")
        print(f"    P99: {p99:.2f}ms")
        print(f"    Max: {scan_stats.max_response_time:.2f}ms")
        print(f"    Requests: {scan_stats.num_requests}")
    
    if remove_stats:
        p50 = remove_stats.get_response_time_percentile(0.50)
        p95 = remove_stats.get_response_time_percentile(0.95)
        p99 = remove_stats.get_response_time_percentile(0.99)
        avg = remove_stats.avg_response_time
        
        print(f"\n  Ultra-Fast Remove Endpoint:")
        print(f"    Average: {avg:.2f}ms")
        print(f"    P50: {p50:.2f}ms")
        print(f"    P95: {p95:.2f}ms {'✅' if p95 < 10 else '⚠️' if p95 < 100 else '❌'} (Target: <10ms)")
        print(f"    P99: {p99:.2f}ms")
        print(f"    Max: {remove_stats.max_response_time:.2f}ms")
        print(f"    Requests: {remove_stats.num_requests}")
    
    print("\n" + "="*70)
    
    # Verdict
    all_p95 = stats.total.get_response_time_percentile(0.95)
    if all_p95 < 10:
        print("🏆 VERDICT: EXCELLENT - P95 < 10ms achieved!")
    elif all_p95 < 50:
        print("✅ VERDICT: GOOD - P95 < 50ms")
    elif all_p95 < 100:
        print("⚠️  VERDICT: ACCEPTABLE - P95 < 100ms")
    else:
        print("❌ VERDICT: NEEDS OPTIMIZATION - P95 > 100ms")
    
    print("="*70)


def run_standalone_test():
    """Run a quick standalone performance test without Locust"""
    import requests
    from bs4 import BeautifulSoup
    
    print("="*70)
    print("STANDALONE ULTRA-FAST SCAN PERFORMANCE TEST")
    print("="*70)
    
    BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")
    
    session = requests.Session()
    session.verify = False
    
    # Login
    print("\n1. Logging in...")
    login_page = session.get(f"{BASE_URL}/login")
    soup = BeautifulSoup(login_page.text, 'html.parser')
    csrf_meta = soup.find('meta', {'name': 'csrf-token'})
    csrf = csrf_meta['content'] if csrf_meta else None
    
    if not csrf:
        csrf_input = soup.find('input', {'name': 'csrf_token'})
        csrf = csrf_input['value'] if csrf_input else None
    
    login_resp = session.post(f"{BASE_URL}/login", data={
        "username": "superadmin",
        "password": "vidhi2029",
        "csrf_token": csrf
    }, allow_redirects=True)
    
    if "dashboard" in login_resp.url or login_resp.status_code == 200:
        print("   ✅ Login successful")
    else:
        print("   ❌ Login failed")
        return
    
    # Get a test bill
    bills_page = session.get(f"{BASE_URL}/bills")
    soup = BeautifulSoup(bills_page.text, 'html.parser')
    bill_links = soup.find_all('a', href=lambda x: x and '/bill/' in x)
    
    import re
    bill_id = 1
    for link in bill_links:
        match = re.search(r'/bill/(\d+)', link.get('href', ''))
        if match:
            bill_id = int(match.group(1))
            break
    
    print(f"   Using bill ID: {bill_id}")
    
    # Run performance tests
    print("\n2. Running scan performance tests...")
    
    scan_times = []
    remove_times = []
    
    # Refresh CSRF
    scan_page = session.get(f"{BASE_URL}/bill/{bill_id}/scan_parent_fast")
    soup = BeautifulSoup(scan_page.text, 'html.parser')
    csrf_meta = soup.find('meta', {'name': 'csrf-token'})
    csrf = csrf_meta['content'] if csrf_meta else csrf
    
    num_tests = 50
    
    for i in range(num_tests):
        qr_code = f"PERF-{random.randint(10000, 99999)}"
        
        # Test scan
        start = time.time()
        resp = session.post(
            f"{BASE_URL}/fast/bill_parent_scan",
            data={
                "bill_id": bill_id,
                "qr_code": qr_code,
                "csrf_token": csrf
            },
            headers={"X-Requested-With": "XMLHttpRequest"}
        )
        elapsed = (time.time() - start) * 1000
        scan_times.append(elapsed)
        
        # Test remove
        start = time.time()
        resp = session.post(
            f"{BASE_URL}/remove_bag_from_bill",
            data={
                "bill_id": bill_id,
                "parent_qr": qr_code,
                "csrf_token": csrf
            },
            headers={"X-Requested-With": "XMLHttpRequest"}
        )
        elapsed = (time.time() - start) * 1000
        remove_times.append(elapsed)
        
        if (i + 1) % 10 == 0:
            print(f"   Completed {i + 1}/{num_tests} tests...")
    
    # Calculate statistics
    def calc_stats(times):
        sorted_times = sorted(times)
        return {
            'avg': statistics.mean(times),
            'min': min(times),
            'max': max(times),
            'p50': sorted_times[int(len(sorted_times) * 0.5)],
            'p95': sorted_times[int(len(sorted_times) * 0.95)],
            'p99': sorted_times[int(len(sorted_times) * 0.99)]
        }
    
    scan_stats = calc_stats(scan_times)
    remove_stats = calc_stats(remove_times)
    
    print("\n" + "="*70)
    print("PERFORMANCE RESULTS")
    print("="*70)
    
    print("\n📊 SCAN ENDPOINT (/fast/bill_parent_scan):")
    print(f"   Average: {scan_stats['avg']:.2f}ms")
    print(f"   Min: {scan_stats['min']:.2f}ms")
    print(f"   Max: {scan_stats['max']:.2f}ms")
    print(f"   P50: {scan_stats['p50']:.2f}ms")
    print(f"   P95: {scan_stats['p95']:.2f}ms {'✅' if scan_stats['p95'] < 10 else '⚠️' if scan_stats['p95'] < 100 else '❌'}")
    print(f"   P99: {scan_stats['p99']:.2f}ms")
    
    print("\n📊 REMOVE ENDPOINT (/remove_bag_from_bill):")
    print(f"   Average: {remove_stats['avg']:.2f}ms")
    print(f"   Min: {remove_stats['min']:.2f}ms")
    print(f"   Max: {remove_stats['max']:.2f}ms")
    print(f"   P50: {remove_stats['p50']:.2f}ms")
    print(f"   P95: {remove_stats['p95']:.2f}ms {'✅' if remove_stats['p95'] < 10 else '⚠️' if remove_stats['p95'] < 100 else '❌'}")
    print(f"   P99: {remove_stats['p99']:.2f}ms")
    
    print("\n" + "="*70)
    avg_p95 = (scan_stats['p95'] + remove_stats['p95']) / 2
    if avg_p95 < 10:
        print("🏆 VERDICT: EXCELLENT - P95 < 10ms achieved!")
    elif avg_p95 < 50:
        print("✅ VERDICT: GOOD - P95 < 50ms")
    elif avg_p95 < 100:
        print("⚠️  VERDICT: ACCEPTABLE - P95 < 100ms")
    else:
        print("❌ VERDICT: NEEDS OPTIMIZATION - P95 > 100ms")
    print("="*70)


if __name__ == "__main__":
    run_standalone_test()

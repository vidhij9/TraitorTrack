"""
Simple Load Testing Script for TraitorTrack
Uses concurrent threads to simulate multiple users
"""

import requests
import time
import threading
import random
import statistics
from dataclasses import dataclass, field
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class RequestResult:
    """Result of a single request"""
    endpoint: str
    status_code: int
    response_time_ms: float
    success: bool
    error: str = ""

@dataclass
class LoadTestStats:
    """Aggregated statistics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    response_times: List[float] = field(default_factory=list)
    errors: Dict[str, int] = field(default_factory=dict)
    
    def add_result(self, result: RequestResult):
        self.total_requests += 1
        self.response_times.append(result.response_time_ms)
        if result.success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            error_key = f"{result.status_code}: {result.error[:50]}"
            self.errors[error_key] = self.errors.get(error_key, 0) + 1
    
    def get_summary(self) -> dict:
        if not self.response_times:
            return {"error": "No data collected"}
        
        sorted_times = sorted(self.response_times)
        p50_idx = int(len(sorted_times) * 0.50)
        p95_idx = int(len(sorted_times) * 0.95)
        p99_idx = int(len(sorted_times) * 0.99)
        
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "failure_rate": f"{(self.failed_requests / max(1, self.total_requests)) * 100:.2f}%",
            "avg_response_time_ms": f"{statistics.mean(self.response_times):.2f}",
            "min_response_time_ms": f"{min(self.response_times):.2f}",
            "max_response_time_ms": f"{max(self.response_times):.2f}",
            "p50_response_time_ms": f"{sorted_times[p50_idx]:.2f}",
            "p95_response_time_ms": f"{sorted_times[p95_idx]:.2f}",
            "p99_response_time_ms": f"{sorted_times[p99_idx]:.2f}",
            "requests_per_second": f"{self.total_requests / max(1, max(self.response_times) / 1000):.2f}",
            "top_errors": dict(sorted(self.errors.items(), key=lambda x: -x[1])[:5])
        }


class LoadTestUser:
    """Simulates a single user making requests"""
    
    def __init__(self, base_url: str, user_id: int):
        self.base_url = base_url.rstrip('/')
        self.user_id = user_id
        self.session = requests.Session()
        self.session.verify = False
        self.logged_in = False
        self.csrf_token = None
        self.test_bags = [f"M444-{i:05d}" for i in range(1, 31)]
        
    def login(self) -> bool:
        """Authenticate with the application"""
        try:
            response = self.session.get(f"{self.base_url}/login", timeout=10)
            
            import re
            match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.text)
            if match:
                self.csrf_token = match.group(1)
            
            login_data = {
                "username": "superadmin",
                "password": "vidhi2029",
                "csrf_token": self.csrf_token or ""
            }
            
            response = self.session.post(
                f"{self.base_url}/login",
                data=login_data,
                allow_redirects=True,
                timeout=10
            )
            
            self.logged_in = response.status_code == 200
            return self.logged_in
            
        except Exception as e:
            logger.error(f"User {self.user_id} login failed: {e}")
            return False
    
    def make_request(self, endpoint: str) -> RequestResult:
        """Make a single request and return result"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            response = self.session.get(url, timeout=30)
            elapsed_ms = (time.time() - start_time) * 1000
            
            return RequestResult(
                endpoint=endpoint,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
                success=200 <= response.status_code < 400
            )
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return RequestResult(
                endpoint=endpoint,
                status_code=0,
                response_time_ms=elapsed_ms,
                success=False,
                error=str(e)
            )
    
    def run_scenario(self, duration_seconds: int, stats: LoadTestStats):
        """Run test scenario for specified duration"""
        if not self.logged_in and not self.login():
            logger.error(f"User {self.user_id} could not login")
            return
        
        endpoints = [
            ("/dashboard", 30),
            (f"/search?q={random.choice(self.test_bags)}", 20),
            ("/bills", 15),
            ("/bag_management", 10),
            ("/api/v2/stats", 10),
            ("/api/v2/bags?page=1&per_page=20", 5),
            ("/api/v2/bills?page=1&per_page=20", 5),
            ("/user_management", 3),
            ("/admin/pool_dashboard", 2)
        ]
        
        weighted_endpoints = []
        for endpoint, weight in endpoints:
            weighted_endpoints.extend([endpoint] * weight)
        
        end_time = time.time() + duration_seconds
        
        while time.time() < end_time:
            endpoint = random.choice(weighted_endpoints)
            if "{bag}" in endpoint:
                endpoint = endpoint.replace("{bag}", random.choice(self.test_bags))
            
            result = self.make_request(endpoint)
            stats.add_result(result)
            
            time.sleep(random.uniform(0.5, 2.0))


def run_load_test(base_url: str, num_users: int, duration_seconds: int) -> LoadTestStats:
    """Run load test with multiple concurrent users"""
    
    logger.info(f"Starting load test: {num_users} users, {duration_seconds}s duration")
    logger.info(f"Target: {base_url}")
    
    stats = LoadTestStats()
    users = [LoadTestUser(base_url, i) for i in range(num_users)]
    
    logger.info("Users logging in...")
    login_start = time.time()
    for user in users:
        user.login()
    login_duration = time.time() - login_start
    logger.info(f"Login completed in {login_duration:.1f}s")
    
    logged_in_count = sum(1 for u in users if u.logged_in)
    logger.info(f"Logged in users: {logged_in_count}/{num_users}")
    
    logger.info("Starting load test...")
    threads = []
    for user in users:
        t = threading.Thread(target=user.run_scenario, args=(duration_seconds, stats))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    return stats


def main():
    import sys
    
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    num_users = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    duration = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    
    print("=" * 60)
    print("TraitorTrack Load Test")
    print("=" * 60)
    print(f"Target URL: {base_url}")
    print(f"Concurrent Users: {num_users}")
    print(f"Duration: {duration} seconds")
    print("=" * 60)
    
    stats = run_load_test(base_url, num_users, duration)
    
    print("\n" + "=" * 60)
    print("LOAD TEST RESULTS")
    print("=" * 60)
    
    summary = stats.get_summary()
    for key, value in summary.items():
        if key != "top_errors":
            print(f"  {key}: {value}")
    
    if summary.get("top_errors"):
        print("\n  Top Errors:")
        for error, count in summary["top_errors"].items():
            print(f"    - {error}: {count}")
    
    print("=" * 60)
    
    failure_rate = float(summary["failure_rate"].rstrip('%'))
    p95 = float(summary["p95_response_time_ms"])
    
    print("\nPERFORMANCE ASSESSMENT:")
    if failure_rate < 0.5:
        print(f"  ✅ Failure rate ({failure_rate:.2f}%) is below 0.5% threshold")
    else:
        print(f"  ❌ Failure rate ({failure_rate:.2f}%) exceeds 0.5% threshold")
    
    if p95 < 350:
        print(f"  ✅ P95 response time ({p95:.0f}ms) is below 350ms threshold")
    else:
        print(f"  ⚠️ P95 response time ({p95:.0f}ms) exceeds 350ms threshold")
    
    return 0 if failure_rate < 1.0 else 1


if __name__ == "__main__":
    exit(main())

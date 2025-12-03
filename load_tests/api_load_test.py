"""
API Load Testing Script for TraitorTrack
Tests API endpoints without login (uses session cookies from a single login)
"""

import requests
import time
import threading
import random
import statistics
from dataclasses import dataclass, field
from typing import List, Dict
import logging
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class RequestResult:
    endpoint: str
    status_code: int
    response_time_ms: float
    success: bool
    error: str = ""

@dataclass
class LoadTestStats:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    response_times: List[float] = field(default_factory=list)
    errors: Dict[str, int] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)
    
    def add_result(self, result: RequestResult):
        with self.lock:
            self.total_requests += 1
            self.response_times.append(result.response_time_ms)
            if result.success:
                self.successful_requests += 1
            else:
                self.failed_requests += 1
                error_key = f"{result.status_code}: {result.error[:30]}"
                self.errors[error_key] = self.errors.get(error_key, 0) + 1
    
    def get_summary(self) -> dict:
        if not self.response_times:
            return {"error": "No data collected"}
        
        sorted_times = sorted(self.response_times)
        p50_idx = int(len(sorted_times) * 0.50)
        p95_idx = min(int(len(sorted_times) * 0.95), len(sorted_times) - 1)
        p99_idx = min(int(len(sorted_times) * 0.99), len(sorted_times) - 1)
        
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
            "top_errors": dict(sorted(self.errors.items(), key=lambda x: -x[1])[:5])
        }


def get_authenticated_session(base_url: str) -> requests.Session:
    """Get a single authenticated session"""
    session = requests.Session()
    session.verify = False
    
    try:
        response = session.get(f"{base_url}/login", timeout=10)
        
        import re
        match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.text)
        csrf_token = match.group(1) if match else ""
        
        login_data = {
            "username": "superadmin",
            "password": "vidhi2029",
            "csrf_token": csrf_token
        }
        
        response = session.post(
            f"{base_url}/login",
            data=login_data,
            allow_redirects=True,
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info("Authentication successful")
            return session
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
    
    return session


def worker(base_url: str, cookies: dict, duration: int, stats: LoadTestStats, worker_id: int):
    """Worker thread making requests"""
    session = requests.Session()
    session.verify = False
    session.cookies.update(cookies)
    
    test_bags = [f"M444-{i:05d}" for i in range(1, 31)]
    
    endpoints = [
        ("/dashboard", 25),
        ("/api/v2/stats", 20),
        ("/search", 15),
        ("/bills", 10),
        ("/bag_management", 10),
        ("/api/v2/bags?page=1&per_page=20", 8),
        ("/api/v2/bills?page=1&per_page=10", 7),
        ("/user_management", 3),
        ("/admin/pool_dashboard", 2),
    ]
    
    weighted_endpoints = []
    for endpoint, weight in endpoints:
        weighted_endpoints.extend([endpoint] * weight)
    
    end_time = time.time() + duration
    request_count = 0
    
    while time.time() < end_time:
        endpoint = random.choice(weighted_endpoints)
        if endpoint == "/search":
            endpoint = f"/search?q={random.choice(test_bags)}"
        
        url = f"{base_url}{endpoint}"
        start_time = time.time()
        
        try:
            response = session.get(url, timeout=30)
            elapsed_ms = (time.time() - start_time) * 1000
            
            result = RequestResult(
                endpoint=endpoint.split('?')[0],
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
                success=200 <= response.status_code < 400
            )
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            result = RequestResult(
                endpoint=endpoint.split('?')[0],
                status_code=0,
                response_time_ms=elapsed_ms,
                success=False,
                error=str(e)[:100]
            )
        
        stats.add_result(result)
        request_count += 1
        
        time.sleep(random.uniform(0.1, 0.5))
    
    logger.debug(f"Worker {worker_id} completed {request_count} requests")


def run_load_test(base_url: str, num_workers: int, duration: int) -> LoadTestStats:
    """Run load test"""
    
    logger.info(f"Starting API load test: {num_workers} workers, {duration}s duration")
    logger.info(f"Target: {base_url}")
    
    logger.info("Authenticating...")
    auth_session = get_authenticated_session(base_url)
    cookies = dict(auth_session.cookies)
    
    stats = LoadTestStats()
    threads = []
    
    logger.info(f"Starting {num_workers} worker threads...")
    start_time = time.time()
    
    for i in range(num_workers):
        t = threading.Thread(target=worker, args=(base_url, cookies, duration, stats, i))
        threads.append(t)
        t.start()
    
    while any(t.is_alive() for t in threads):
        time.sleep(5)
        elapsed = time.time() - start_time
        rps = stats.total_requests / max(1, elapsed)
        logger.info(f"Progress: {stats.total_requests} requests, {rps:.1f} req/s, {elapsed:.0f}s elapsed")
    
    for t in threads:
        t.join()
    
    total_time = time.time() - start_time
    logger.info(f"Test completed in {total_time:.1f}s")
    
    return stats


def main():
    import sys
    
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"
    num_workers = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    duration = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    
    print("=" * 70)
    print("TraitorTrack API Load Test")
    print("=" * 70)
    print(f"Target URL: {base_url}")
    print(f"Concurrent Workers: {num_workers}")
    print(f"Duration: {duration} seconds")
    print("=" * 70)
    
    stats = run_load_test(base_url, num_workers, duration)
    
    print("\n" + "=" * 70)
    print("LOAD TEST RESULTS")
    print("=" * 70)
    
    summary = stats.get_summary()
    
    if "error" in summary:
        print(f"  Error: {summary['error']}")
        return 1
    
    for key, value in summary.items():
        if key != "top_errors":
            print(f"  {key}: {value}")
    
    if summary.get("top_errors"):
        print("\n  Top Errors:")
        for error, count in summary["top_errors"].items():
            print(f"    - {error}: {count}")
    
    print("=" * 70)
    
    failure_rate = float(summary["failure_rate"].rstrip('%'))
    p95 = float(summary["p95_response_time_ms"])
    avg = float(summary["avg_response_time_ms"])
    
    print("\nPERFORMANCE ASSESSMENT:")
    
    if failure_rate < 0.5:
        print(f"  ✅ Failure rate ({failure_rate:.2f}%) is below 0.5% threshold")
    else:
        print(f"  ❌ Failure rate ({failure_rate:.2f}%) exceeds 0.5% threshold")
    
    if p95 < 350:
        print(f"  ✅ P95 response time ({p95:.0f}ms) is below 350ms threshold")
    elif p95 < 500:
        print(f"  ⚠️ P95 response time ({p95:.0f}ms) is between 350-500ms (acceptable)")
    else:
        print(f"  ❌ P95 response time ({p95:.0f}ms) exceeds 500ms threshold")
    
    if avg < 200:
        print(f"  ✅ Average response time ({avg:.0f}ms) is below 200ms target")
    else:
        print(f"  ⚠️ Average response time ({avg:.0f}ms) is above 200ms target")
    
    rps = stats.total_requests / duration
    print(f"  📊 Throughput: {rps:.1f} requests/second")
    
    return 0 if failure_rate < 1.0 else 1


if __name__ == "__main__":
    exit(main())

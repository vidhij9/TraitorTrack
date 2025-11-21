"""
TraitorTrack Stress Testing
============================

Stress tests to find system breaking points and validate extreme scenarios.

Usage:
    locust -f tests/load/stress_test.py --host=http://localhost:5000 --headless -u 200 -r 20 -t 10m
"""

import random
from locust import HttpUser, task, between, events


class StressTestUser(HttpUser):
    """
    Aggressive stress testing user
    Simulates extreme load conditions to find breaking points
    """
    wait_time = between(0.1, 1)  # Minimal wait time for stress
    
    def on_start(self):
        """Login"""
        self.client.post("/login", data={
            "username": "admin",
            "password": "vidhi2029"
        })
    
    @task(20)
    def rapid_scans(self):
        """Rapid-fire scan operations"""
        qr_id = f"STRESS{random.randint(10000, 99999)}"
        self.client.post("/scan", data={"qr_id": qr_id}, name="Stress: Rapid Scan")
    
    @task(10)
    def concurrent_bill_creation(self):
        """Create bills concurrently"""
        bill_id = f"STRESS{random.randint(10000, 99999)}"
        self.client.post("/bill/create", data={
            "bill_id": bill_id,
            "description": "Stress Test"
        }, name="Stress: Create Bill")
    
    @task(15)
    def heavy_search_load(self):
        """Heavy search queries"""
        search_term = f"SB{random.randint(10000, 99999)}"
        self.client.get(f"/bag_management?search={search_term}", name="Stress: Search")
    
    @task(5)
    def api_bag_creation(self):
        """Create bags via API"""
        qr_id = f"STRESSB{random.randint(10000, 99999)}"
        self.client.post("/api/bags", json={
            "qr_id": qr_id,
            "type": "parent",
            "name": f"Stress Test {qr_id}"
        }, name="Stress: Create Bag API")
    
    @task(10)
    def dashboard_load(self):
        """Heavy dashboard loads"""
        self.client.get("/dashboard", name="Stress: Dashboard")


class RaceConditionTester(HttpUser):
    """
    Tests for race conditions under concurrent load
    """
    wait_time = between(0, 0.1)  # Minimal delay to maximize concurrency
    
    def on_start(self):
        """Login"""
        self.client.post("/login", data={
            "username": "admin",
            "password": "vidhi2029"
        })
        # Share a few QR codes across all users to force race conditions
        self.shared_qrs = [f"RACE{i:05d}" for i in range(10)]
    
    @task
    def concurrent_duplicate_scans(self):
        """Try to scan same bag from multiple users"""
        qr_id = random.choice(self.shared_qrs)
        self.client.post("/scan", data={"qr_id": qr_id}, name="Race: Duplicate Scan")
    
    @task
    def concurrent_bill_operations(self):
        """Try to finalize same bill from multiple users"""
        bill_id = random.choice([f"RACE{i:03d}" for i in range(5)])
        self.client.post(f"/bill/{bill_id}/complete", name="Race: Complete Bill")


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """
    Print stress test summary when test ends
    """
    print("\n" + "="*60)
    print("STRESS TEST SUMMARY")
    print("="*60)
    
    stats = environment.stats
    
    # Calculate key metrics
    total_requests = stats.total.num_requests
    total_failures = stats.total.num_failures
    failure_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0
    
    print(f"Total Requests: {total_requests}")
    print(f"Total Failures: {total_failures}")
    print(f"Failure Rate: {failure_rate:.2f}%")
    print(f"Average Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"P95 Response Time: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"P99 Response Time: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"Max Response Time: {stats.total.max_response_time:.2f}ms")
    print(f"Requests/sec: {stats.total.total_rps:.2f}")
    
    print("\n" + "="*60)
    print("PERFORMANCE VERDICT")
    print("="*60)
    
    # Evaluate against targets
    p95 = stats.total.get_response_time_percentile(0.95)
    
    if failure_rate > 1:
        print("❌ FAILED: Failure rate exceeds 1%")
    elif p95 > 500:
        print("⚠️  WARNING: P95 response time exceeds 500ms")
    else:
        print("✅ PASSED: System handles stress load within acceptable limits")
    
    print("="*60)

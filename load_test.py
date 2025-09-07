#!/usr/bin/env python3
"""
TraceTrack Load Testing Script
Simulates multiple concurrent users to test system performance under load
"""

import requests
import time
import random
import threading
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import logging
import statistics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LoadTester:
    def __init__(self, base_url="http://localhost:5000", num_users=50):
        self.base_url = base_url
        self.num_users = num_users
        self.results = {
            "response_times": [],
            "errors": [],
            "success_count": 0,
            "failure_count": 0,
            "endpoint_stats": {}
        }
        self.lock = threading.Lock()
        
    def create_user_session(self, user_id):
        """Create a new session for a user"""
        session = requests.Session()
        
        # Login with different user types
        user_type = user_id % 3
        if user_type == 0:
            username = "admin"
            password = "admin"
        elif user_type == 1:
            username = f"dispatcher{user_id % 5 + 1}"
            password = "password123"
        else:
            username = f"biller{user_id % 3 + 1}"
            password = "password123"
        
        try:
            # Attempt login
            response = session.post(
                f"{self.base_url}/login",
                data={"username": username, "password": password},
                timeout=30
            )
            if response.status_code in [200, 302]:
                return session
        except Exception as e:
            logger.warning(f"Failed to create session for user {user_id}: {e}")
        
        # Return session anyway (will test as anonymous)
        return session
    
    def record_result(self, endpoint, response_time, success, error=None):
        """Thread-safe recording of results"""
        with self.lock:
            self.results["response_times"].append(response_time)
            
            if success:
                self.results["success_count"] += 1
            else:
                self.results["failure_count"] += 1
                if error:
                    self.results["errors"].append(f"{endpoint}: {error}")
            
            # Track endpoint-specific stats
            if endpoint not in self.results["endpoint_stats"]:
                self.results["endpoint_stats"][endpoint] = {
                    "count": 0,
                    "total_time": 0,
                    "errors": 0,
                    "min_time": float('inf'),
                    "max_time": 0
                }
            
            stats = self.results["endpoint_stats"][endpoint]
            stats["count"] += 1
            stats["total_time"] += response_time
            stats["min_time"] = min(stats["min_time"], response_time)
            stats["max_time"] = max(stats["max_time"], response_time)
            if not success:
                stats["errors"] += 1
    
    def simulate_user_behavior(self, user_id):
        """Simulate realistic user behavior"""
        session = self.create_user_session(user_id)
        
        # Define user scenarios with weights
        scenarios = [
            ("dashboard_user", 30),  # 30% chance
            ("scanning_user", 25),    # 25% chance
            ("bill_manager", 20),     # 20% chance
            ("lookup_user", 15),      # 15% chance
            ("admin_user", 10)        # 10% chance
        ]
        
        # Select scenario based on weights
        scenario = random.choices(
            [s[0] for s in scenarios],
            weights=[s[1] for s in scenarios]
        )[0]
        
        logger.info(f"User {user_id} starting scenario: {scenario}")
        
        if scenario == "dashboard_user":
            self.simulate_dashboard_user(session, user_id)
        elif scenario == "scanning_user":
            self.simulate_scanning_user(session, user_id)
        elif scenario == "bill_manager":
            self.simulate_bill_manager(session, user_id)
        elif scenario == "lookup_user":
            self.simulate_lookup_user(session, user_id)
        else:
            self.simulate_admin_user(session, user_id)
    
    def make_request(self, session, endpoint, method="GET", data=None, json_data=None):
        """Make a request and record results"""
        try:
            start_time = time.time()
            
            if method == "GET":
                response = session.get(f"{self.base_url}{endpoint}", timeout=30)
            elif method == "POST":
                if json_data:
                    response = session.post(
                        f"{self.base_url}{endpoint}", 
                        json=json_data, 
                        timeout=30
                    )
                else:
                    response = session.post(
                        f"{self.base_url}{endpoint}", 
                        data=data, 
                        timeout=30
                    )
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            success = response.status_code in [200, 201, 302]
            
            self.record_result(endpoint, response_time, success, 
                             None if success else f"Status: {response.status_code}")
            
            # Simulate think time
            time.sleep(random.uniform(0.5, 2))
            
            return response
            
        except Exception as e:
            response_time = 30000  # Timeout
            self.record_result(endpoint, response_time, False, str(e))
            return None
    
    def simulate_dashboard_user(self, session, user_id):
        """Simulate a user browsing dashboards"""
        # View dashboard
        self.make_request(session, "/dashboard")
        
        # Check analytics
        self.make_request(session, "/api/dashboard/analytics")
        
        # Refresh a few times
        for _ in range(random.randint(2, 5)):
            time.sleep(random.uniform(3, 8))
            self.make_request(session, "/dashboard")
    
    def simulate_scanning_user(self, session, user_id):
        """Simulate a user doing scanning operations"""
        # Navigate to scan page
        self.make_request(session, "/scan/parent")
        
        # Perform parent scans
        for i in range(random.randint(3, 8)):
            parent_id = f"SB{random.randint(100000, 999999)}"
            self.make_request(
                session, 
                "/api/fast_parent_scan", 
                "POST",
                json_data={"qr_id": parent_id}
            )
            
            # Scan children for some parents
            if random.random() > 0.5:
                for j in range(random.randint(5, 15)):
                    child_id = f"CB{random.randint(100000, 999999)}"
                    self.make_request(
                        session,
                        "/process_child_scan_fast",
                        "POST",
                        data={
                            "parent_qr_id": parent_id,
                            "child_qr_id": child_id
                        }
                    )
    
    def simulate_bill_manager(self, session, user_id):
        """Simulate a user managing bills"""
        # View bills
        self.make_request(session, "/bills")
        
        # Create a new bill
        bill_data = {
            "bill_number": f"BILL{random.randint(10000, 99999)}",
            "customer_name": f"Customer {user_id}",
            "address": f"Address {user_id}",
            "phone": f"{random.randint(1000000000, 9999999999)}"
        }
        self.make_request(session, "/bill/create", "POST", data=bill_data)
        
        # View bill details
        self.make_request(session, "/api/bills")
        
        # Check weights
        bill_id = random.randint(1, 100)
        self.make_request(session, f"/api/bill/{bill_id}/weights")
    
    def simulate_lookup_user(self, session, user_id):
        """Simulate a user doing lookups"""
        # Navigate to lookup
        self.make_request(session, "/lookup")
        
        # Perform lookups
        for _ in range(random.randint(3, 7)):
            lookup_data = {
                "qr_id": f"SB{random.randint(100000, 999999)}"
            }
            self.make_request(session, "/lookup", "POST", data=lookup_data)
            time.sleep(random.uniform(1, 3))
        
        # Check bags
        self.make_request(session, "/bags")
    
    def simulate_admin_user(self, session, user_id):
        """Simulate an admin user"""
        # View user management
        self.make_request(session, "/user_management")
        
        # Check system integrity
        self.make_request(session, "/admin/system-integrity")
        
        # View performance dashboard
        self.make_request(session, "/performance/dashboard")
        
        # Check some user profiles
        for _ in range(random.randint(1, 3)):
            user_profile_id = random.randint(1, 20)
            self.make_request(session, f"/admin/users/{user_profile_id}/profile")
    
    def run_load_test(self):
        """Run the load test with multiple concurrent users"""
        logger.info("=" * 70)
        logger.info(f"Starting Load Test with {self.num_users} concurrent users")
        logger.info("=" * 70)
        
        start_time = time.time()
        
        # Use ThreadPoolExecutor for concurrent users
        with ThreadPoolExecutor(max_workers=self.num_users) as executor:
            futures = []
            
            # Submit all user simulations
            for user_id in range(self.num_users):
                future = executor.submit(self.simulate_user_behavior, user_id)
                futures.append(future)
                # Stagger user starts slightly
                time.sleep(random.uniform(0.1, 0.3))
            
            # Wait for all users to complete
            completed = 0
            for future in as_completed(futures):
                completed += 1
                logger.info(f"Completed {completed}/{self.num_users} users")
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"User simulation failed: {e}")
        
        # Calculate statistics
        total_time = time.time() - start_time
        self.print_results(total_time)
    
    def print_results(self, total_time):
        """Print comprehensive load test results"""
        logger.info("\n" + "=" * 70)
        logger.info("LOAD TEST RESULTS")
        logger.info("=" * 70)
        
        # Overall statistics
        total_requests = self.results["success_count"] + self.results["failure_count"]
        success_rate = (self.results["success_count"] / total_requests * 100) if total_requests > 0 else 0
        
        logger.info(f"\n📊 OVERALL STATISTICS:")
        logger.info(f"  Total Requests: {total_requests}")
        logger.info(f"  Successful: {self.results['success_count']} ({success_rate:.1f}%)")
        logger.info(f"  Failed: {self.results['failure_count']} ({100-success_rate:.1f}%)")
        logger.info(f"  Test Duration: {total_time:.2f} seconds")
        logger.info(f"  Requests/Second: {total_requests/total_time:.2f}")
        
        # Response time statistics
        if self.results["response_times"]:
            response_times = self.results["response_times"]
            logger.info(f"\n⏱️  RESPONSE TIME STATISTICS (ms):")
            logger.info(f"  Min: {min(response_times):.2f}")
            logger.info(f"  Max: {max(response_times):.2f}")
            logger.info(f"  Mean: {statistics.mean(response_times):.2f}")
            logger.info(f"  Median: {statistics.median(response_times):.2f}")
            
            # Calculate percentiles
            sorted_times = sorted(response_times)
            p50 = sorted_times[int(len(sorted_times) * 0.50)]
            p90 = sorted_times[int(len(sorted_times) * 0.90)]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]
            
            logger.info(f"  P50: {p50:.2f}")
            logger.info(f"  P90: {p90:.2f}")
            logger.info(f"  P95: {p95:.2f}")
            logger.info(f"  P99: {p99:.2f}")
        
        # Endpoint-specific statistics
        logger.info(f"\n📍 ENDPOINT STATISTICS:")
        for endpoint, stats in sorted(self.results["endpoint_stats"].items()):
            avg_time = stats["total_time"] / stats["count"] if stats["count"] > 0 else 0
            error_rate = (stats["errors"] / stats["count"] * 100) if stats["count"] > 0 else 0
            
            logger.info(f"\n  {endpoint}:")
            logger.info(f"    Requests: {stats['count']}")
            logger.info(f"    Avg Time: {avg_time:.2f}ms")
            logger.info(f"    Min Time: {stats['min_time']:.2f}ms")
            logger.info(f"    Max Time: {stats['max_time']:.2f}ms")
            logger.info(f"    Error Rate: {error_rate:.1f}%")
        
        # Performance assessment
        logger.info(f"\n🎯 PERFORMANCE ASSESSMENT:")
        if p95 < 300:
            logger.info("  ✅ EXCELLENT: P95 < 300ms (Target Met)")
        elif p95 < 500:
            logger.info("  ⚠️  GOOD: P95 < 500ms")
        elif p95 < 1000:
            logger.info("  ⚠️  MODERATE: P95 < 1000ms")
        else:
            logger.info("  ❌ POOR: P95 > 1000ms")
        
        if success_rate > 99:
            logger.info("  ✅ EXCELLENT: Success rate > 99%")
        elif success_rate > 95:
            logger.info("  ⚠️  GOOD: Success rate > 95%")
        else:
            logger.info("  ❌ POOR: Success rate < 95%")
        
        # Error summary
        if self.results["errors"]:
            logger.info(f"\n❌ ERROR SUMMARY (showing first 10):")
            for error in self.results["errors"][:10]:
                logger.info(f"  - {error}")
        
        logger.info("\n" + "=" * 70)
        
        # Save results to file
        with open("load_test_results.json", "w") as f:
            json.dump({
                "test_time": datetime.now().isoformat(),
                "num_users": self.num_users,
                "duration": total_time,
                "total_requests": total_requests,
                "success_rate": success_rate,
                "response_times": {
                    "p50": p50 if self.results["response_times"] else 0,
                    "p90": p90 if self.results["response_times"] else 0,
                    "p95": p95 if self.results["response_times"] else 0,
                    "p99": p99 if self.results["response_times"] else 0,
                },
                "endpoint_stats": self.results["endpoint_stats"]
            }, f, indent=2)
            
        logger.info("Results saved to load_test_results.json")

if __name__ == "__main__":
    import sys
    
    # Get number of users from command line or use default
    num_users = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    
    tester = LoadTester(num_users=num_users)
    tester.run_load_test()
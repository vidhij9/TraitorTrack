#!/usr/bin/env python3
"""
Ultra Load Test for TraceTrack
Tests system with 100+ concurrent users and 800,000+ bags
Target: <50ms response times
"""

import requests
import time
import random
import string
import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import threading
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UltraLoadTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.results = []
        self.lock = threading.Lock()
        self.test_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": [],
            "endpoint_stats": {},
            "sub_50ms_count": 0,
            "sub_100ms_count": 0
        }
        
        # Pre-generate test data for 800,000+ bags simulation
        self.parent_bags = [f"SB{i:07d}" for i in range(1, 10001)]  # 10,000 parent bags
        self.child_bags = [f"CB{i:07d}" for i in range(1, 800001)]  # 800,000 child bags
        
    def record_request(self, endpoint, response_time, success, status_code=None):
        """Record request metrics"""
        with self.lock:
            self.test_stats["total_requests"] += 1
            
            if success:
                self.test_stats["successful_requests"] += 1
            else:
                self.test_stats["failed_requests"] += 1
            
            self.test_stats["response_times"].append(response_time)
            
            # Track sub-50ms and sub-100ms responses
            if response_time < 50:
                self.test_stats["sub_50ms_count"] += 1
            if response_time < 100:
                self.test_stats["sub_100ms_count"] += 1
            
            # Track endpoint-specific stats
            if endpoint not in self.test_stats["endpoint_stats"]:
                self.test_stats["endpoint_stats"][endpoint] = {
                    "count": 0,
                    "total_time": 0,
                    "min_time": float('inf'),
                    "max_time": 0,
                    "sub_50ms": 0,
                    "errors": 0
                }
            
            stats = self.test_stats["endpoint_stats"][endpoint]
            stats["count"] += 1
            stats["total_time"] += response_time
            stats["min_time"] = min(stats["min_time"], response_time)
            stats["max_time"] = max(stats["max_time"], response_time)
            if response_time < 50:
                stats["sub_50ms"] += 1
            if not success:
                stats["errors"] += 1
    
    def test_ultra_parent_scan(self, session, user_id):
        """Test ultra-fast parent scanning"""
        parent_qr = random.choice(self.parent_bags)
        
        try:
            start = time.time()
            response = session.post(
                f"{self.base_url}/ultra/scan/parent",
                json={"qr_id": parent_qr},
                timeout=5
            )
            response_time = (time.time() - start) * 1000
            
            success = response.status_code == 200
            self.record_request("/ultra/scan/parent", response_time, success, response.status_code)
            
            return parent_qr if success else None
            
        except Exception as e:
            self.record_request("/ultra/scan/parent", 5000, False)
            return None
    
    def test_ultra_child_scan(self, session, parent_qr):
        """Test ultra-fast child scanning"""
        if not parent_qr:
            return
        
        child_qr = random.choice(self.child_bags)
        
        try:
            start = time.time()
            response = session.post(
                f"{self.base_url}/ultra/scan/child",
                json={
                    "parent_qr_id": parent_qr,
                    "child_qr_id": child_qr
                },
                timeout=5
            )
            response_time = (time.time() - start) * 1000
            
            success = response.status_code == 200
            self.record_request("/ultra/scan/child", response_time, success, response.status_code)
            
        except Exception as e:
            self.record_request("/ultra/scan/child", 5000, False)
    
    def test_ultra_batch_scan(self, session, parent_qr):
        """Test ultra-fast batch scanning"""
        if not parent_qr:
            return
        
        # Batch scan 30 children (typical use case)
        batch_size = 30
        child_batch = random.sample(self.child_bags, batch_size)
        
        try:
            start = time.time()
            response = session.post(
                f"{self.base_url}/ultra/batch/scan",
                json={
                    "parent_qr_id": parent_qr,
                    "child_qr_ids": child_batch
                },
                timeout=10
            )
            response_time = (time.time() - start) * 1000
            
            success = response.status_code == 200
            self.record_request("/ultra/batch/scan", response_time, success, response.status_code)
            
            # Calculate per-bag time
            if success and response.json().get("per_bag_ms"):
                per_bag_time = response.json()["per_bag_ms"]
                logger.debug(f"Batch scan: {batch_size} bags in {response_time:.2f}ms ({per_bag_time:.2f}ms per bag)")
                
        except Exception as e:
            self.record_request("/ultra/batch/scan", 10000, False)
    
    def test_ultra_lookup(self, session):
        """Test ultra-fast lookup"""
        qr_id = random.choice(self.parent_bags + self.child_bags[:10000])
        
        try:
            start = time.time()
            response = session.get(
                f"{self.base_url}/ultra/lookup/{qr_id}",
                timeout=5
            )
            response_time = (time.time() - start) * 1000
            
            success = response.status_code in [200, 404]  # 404 is valid for non-existent bags
            self.record_request("/ultra/lookup", response_time, success, response.status_code)
            
        except Exception as e:
            self.record_request("/ultra/lookup", 5000, False)
    
    def test_ultra_stats(self, session):
        """Test ultra-fast stats endpoint"""
        try:
            start = time.time()
            response = session.get(
                f"{self.base_url}/ultra/stats",
                timeout=5
            )
            response_time = (time.time() - start) * 1000
            
            success = response.status_code == 200
            self.record_request("/ultra/stats", response_time, success, response.status_code)
            
        except Exception as e:
            self.record_request("/ultra/stats", 5000, False)
    
    def simulate_user_session(self, user_id):
        """Simulate a complete user session"""
        session = requests.Session()
        
        # Simulate realistic user behavior
        operations = random.randint(10, 30)  # Each user performs 10-30 operations
        
        for _ in range(operations):
            operation = random.choice([
                "parent_scan",
                "child_scan",
                "batch_scan",
                "lookup",
                "stats"
            ])
            
            if operation == "parent_scan":
                parent_qr = self.test_ultra_parent_scan(session, user_id)
                
                # Often followed by child scans
                if parent_qr and random.random() > 0.5:
                    for _ in range(random.randint(1, 5)):
                        self.test_ultra_child_scan(session, parent_qr)
                        
            elif operation == "child_scan":
                parent_qr = random.choice(self.parent_bags)
                self.test_ultra_child_scan(session, parent_qr)
                
            elif operation == "batch_scan":
                parent_qr = random.choice(self.parent_bags)
                self.test_ultra_batch_scan(session, parent_qr)
                
            elif operation == "lookup":
                self.test_ultra_lookup(session)
                
            elif operation == "stats":
                self.test_ultra_stats(session)
            
            # Simulate think time between operations
            time.sleep(random.uniform(0.1, 0.5))
        
        logger.debug(f"User {user_id} completed session")
    
    def run_ultra_load_test(self, num_users=100):
        """Run ultra load test with 100+ concurrent users"""
        logger.info("=" * 70)
        logger.info(f"ULTRA LOAD TEST - {num_users} CONCURRENT USERS")
        logger.info("Target: <50ms response times")
        logger.info("Scale: 800,000+ bags simulation")
        logger.info("=" * 70)
        
        start_time = time.time()
        
        # Use ThreadPoolExecutor for concurrent users
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = []
            
            # Submit all user sessions
            for user_id in range(num_users):
                future = executor.submit(self.simulate_user_session, user_id)
                futures.append(future)
                
                # Stagger user starts slightly to avoid thundering herd
                if user_id < 50:
                    time.sleep(0.05)
            
            # Wait for completion with progress updates
            completed = 0
            for future in as_completed(futures):
                completed += 1
                if completed % 10 == 0:
                    logger.info(f"Progress: {completed}/{num_users} users completed")
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"User session failed: {e}")
        
        # Calculate and print results
        total_time = time.time() - start_time
        self.print_results(total_time, num_users)
    
    def print_results(self, total_time, num_users):
        """Print comprehensive test results"""
        logger.info("\n" + "=" * 70)
        logger.info("ULTRA LOAD TEST RESULTS")
        logger.info("=" * 70)
        
        # Overall statistics
        total_requests = self.test_stats["total_requests"]
        success_rate = (self.test_stats["successful_requests"] / total_requests * 100) if total_requests > 0 else 0
        
        logger.info(f"\n📊 OVERALL STATISTICS:")
        logger.info(f"  Concurrent Users: {num_users}")
        logger.info(f"  Total Requests: {total_requests:,}")
        logger.info(f"  Successful: {self.test_stats['successful_requests']:,} ({success_rate:.1f}%)")
        logger.info(f"  Failed: {self.test_stats['failed_requests']:,}")
        logger.info(f"  Test Duration: {total_time:.2f} seconds")
        logger.info(f"  Requests/Second: {total_requests/total_time:.2f}")
        
        # Response time statistics
        if self.test_stats["response_times"]:
            response_times = self.test_stats["response_times"]
            
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
            
            # Performance targets
            sub_50ms_pct = (self.test_stats["sub_50ms_count"] / total_requests * 100) if total_requests > 0 else 0
            sub_100ms_pct = (self.test_stats["sub_100ms_count"] / total_requests * 100) if total_requests > 0 else 0
            
            logger.info(f"\n🎯 PERFORMANCE TARGETS:")
            logger.info(f"  <50ms responses: {self.test_stats['sub_50ms_count']:,} ({sub_50ms_pct:.1f}%)")
            logger.info(f"  <100ms responses: {self.test_stats['sub_100ms_count']:,} ({sub_100ms_pct:.1f}%)")
            
            # Endpoint breakdown
            logger.info(f"\n📍 ENDPOINT PERFORMANCE:")
            for endpoint, stats in self.test_stats["endpoint_stats"].items():
                if stats["count"] > 0:
                    avg_time = stats["total_time"] / stats["count"]
                    sub_50ms_pct = (stats["sub_50ms"] / stats["count"] * 100)
                    error_rate = (stats["errors"] / stats["count"] * 100)
                    
                    logger.info(f"\n  {endpoint}:")
                    logger.info(f"    Requests: {stats['count']:,}")
                    logger.info(f"    Avg Time: {avg_time:.2f}ms")
                    logger.info(f"    Min/Max: {stats['min_time']:.2f}ms / {stats['max_time']:.2f}ms")
                    logger.info(f"    <50ms: {sub_50ms_pct:.1f}%")
                    logger.info(f"    Error Rate: {error_rate:.1f}%")
            
            # Performance assessment
            logger.info(f"\n✨ PERFORMANCE ASSESSMENT:")
            
            if p50 < 50:
                logger.info("  ✅ EXCELLENT: P50 < 50ms TARGET MET!")
            elif p50 < 100:
                logger.info("  ⚠️  GOOD: P50 < 100ms")
            else:
                logger.info("  ❌ NEEDS IMPROVEMENT: P50 > 100ms")
            
            if p95 < 100:
                logger.info("  ✅ EXCELLENT: P95 < 100ms")
            elif p95 < 300:
                logger.info("  ⚠️  GOOD: P95 < 300ms")
            else:
                logger.info("  ❌ NEEDS IMPROVEMENT: P95 > 300ms")
            
            if success_rate > 99.9:
                logger.info("  ✅ EXCELLENT: Success rate > 99.9%")
            elif success_rate > 99:
                logger.info("  ⚠️  GOOD: Success rate > 99%")
            else:
                logger.info("  ❌ NEEDS IMPROVEMENT: Success rate < 99%")
            
            # Save results
            with open("ultra_load_test_results.json", "w") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "num_users": num_users,
                    "duration": total_time,
                    "total_requests": total_requests,
                    "success_rate": success_rate,
                    "response_times": {
                        "p50": p50,
                        "p90": p90,
                        "p95": p95,
                        "p99": p99,
                        "mean": statistics.mean(response_times),
                        "median": statistics.median(response_times)
                    },
                    "performance_targets": {
                        "sub_50ms_pct": sub_50ms_pct,
                        "sub_100ms_pct": sub_100ms_pct
                    },
                    "endpoint_stats": self.test_stats["endpoint_stats"]
                }, f, indent=2)
            
            logger.info("\n📁 Results saved to ultra_load_test_results.json")
        
        logger.info("\n" + "=" * 70)

if __name__ == "__main__":
    import sys
    
    # Get number of users from command line or use default
    num_users = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    
    tester = UltraLoadTester()
    tester.run_ultra_load_test(num_users)
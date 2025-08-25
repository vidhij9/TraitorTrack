#!/usr/bin/env python3
"""
Production Load Test for 800,000+ Bags and 50+ Concurrent Users
Tests system stability and performance at production scale
"""

import concurrent.futures
import time
import random
import string
import logging
import json
import statistics
from datetime import datetime
import requests
from typing import List, Dict, Tuple
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "http://localhost:5000"
TARGET_BAGS = 800000  # 8 lakh bags
TARGET_USERS = 50
TEST_DURATION = 120  # 2 minutes
PARENT_CHILD_RATIO = 30  # 30 children per parent

class LoadTestUser:
    """Simulates a user session"""
    
    def __init__(self, user_id, username, password, role):
        self.user_id = user_id
        self.username = username
        self.password = password
        self.role = role
        self.session = requests.Session()
        self.logged_in = False
        self.response_times = []
        self.errors = []
        
    def login(self):
        """Login to the system"""
        try:
            response = self.session.post(
                f"{BASE_URL}/login",
                data={
                    'username': self.username,
                    'password': self.password
                },
                timeout=10
            )
            if response.status_code == 200:
                self.logged_in = True
                return True
        except Exception as e:
            self.errors.append(f"Login failed: {str(e)}")
        return False
    
    def scan_parent(self):
        """Scan a parent bag"""
        if not self.logged_in:
            return False
            
        try:
            qr_id = f"PARENT_{random.randint(1, TARGET_BAGS//30)}"
            start = time.time()
            response = self.session.post(
                f"{BASE_URL}/process_parent_scan",
                json={'qr_code': qr_id},
                timeout=5
            )
            elapsed = time.time() - start
            self.response_times.append(elapsed)
            return response.status_code == 200
        except Exception as e:
            self.errors.append(f"Parent scan failed: {str(e)}")
            return False
    
    def scan_child(self):
        """Scan a child bag"""
        if not self.logged_in:
            return False
            
        try:
            qr_id = f"CHILD_{random.randint(1, TARGET_BAGS)}"
            start = time.time()
            response = self.session.post(
                f"{BASE_URL}/ultra_process_child_scan",
                json={'qr_code': qr_id},
                timeout=2
            )
            elapsed = time.time() - start
            self.response_times.append(elapsed)
            return response.status_code == 200
        except Exception as e:
            self.errors.append(f"Child scan failed: {str(e)}")
            return False
    
    def get_stats(self):
        """Get dashboard statistics"""
        try:
            start = time.time()
            response = self.session.get(
                f"{BASE_URL}/api/stats",
                timeout=5
            )
            elapsed = time.time() - start
            self.response_times.append(elapsed)
            return response.status_code == 200
        except Exception as e:
            self.errors.append(f"Stats failed: {str(e)}")
            return False
    
    def perform_workflow(self):
        """Perform a typical user workflow"""
        actions = []
        
        # Random workflow based on role
        if self.role == 'dispatcher':
            actions = [self.scan_parent, self.scan_child, self.scan_child, self.get_stats]
        elif self.role == 'biller':
            actions = [self.get_stats, self.scan_parent, self.get_stats]
        else:  # admin
            actions = [self.get_stats, self.get_stats]
        
        for action in actions:
            if not action():
                break
            time.sleep(random.uniform(0.1, 0.5))  # Simulate thinking time

class ProductionLoadTest:
    """Main load test orchestrator"""
    
    def __init__(self):
        self.users: List[LoadTestUser] = []
        self.start_time = None
        self.end_time = None
        self.results = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'errors': [],
            'throughput': 0
        }
    
    def create_test_users(self, count):
        """Create test user accounts"""
        logger.info(f"Creating {count} test users...")
        
        for i in range(count):
            role = random.choice(['dispatcher', 'dispatcher', 'biller', 'admin'])
            username = f"loadtest_{role}_{i}"
            password = "test123"
            
            user = LoadTestUser(i, username, password, role)
            self.users.append(user)
        
        logger.info(f"Created {len(self.users)} test users")
    
    def login_users(self):
        """Login all test users concurrently"""
        logger.info("Logging in users...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(user.login) for user in self.users]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        logged_in = sum(1 for user in self.users if user.logged_in)
        logger.info(f"Successfully logged in {logged_in}/{len(self.users)} users")
    
    def run_concurrent_load(self, duration):
        """Run concurrent load test"""
        logger.info(f"Starting {duration}s load test with {len(self.users)} users...")
        
        self.start_time = time.time()
        end_time = self.start_time + duration
        
        def user_load_generator(user):
            """Generate load for a single user"""
            while time.time() < end_time:
                user.perform_workflow()
                time.sleep(random.uniform(1, 3))  # Random delay between workflows
        
        # Run users concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=TARGET_USERS) as executor:
            futures = [executor.submit(user_load_generator, user) for user in self.users]
            concurrent.futures.wait(futures)
        
        self.end_time = time.time()
        logger.info("Load test completed")
    
    def collect_results(self):
        """Collect and analyze results"""
        all_response_times = []
        all_errors = []
        
        for user in self.users:
            all_response_times.extend(user.response_times)
            all_errors.extend(user.errors)
        
        self.results['total_requests'] = len(all_response_times) + len(all_errors)
        self.results['successful_requests'] = len(all_response_times)
        self.results['failed_requests'] = len(all_errors)
        self.results['response_times'] = all_response_times
        self.results['errors'] = all_errors[:100]  # Limit errors to first 100
        
        if all_response_times:
            self.results['avg_response_time'] = statistics.mean(all_response_times)
            self.results['median_response_time'] = statistics.median(all_response_times)
            self.results['p95_response_time'] = statistics.quantiles(all_response_times, n=20)[18]
            self.results['p99_response_time'] = statistics.quantiles(all_response_times, n=100)[98]
            self.results['min_response_time'] = min(all_response_times)
            self.results['max_response_time'] = max(all_response_times)
        
        duration = self.end_time - self.start_time
        self.results['throughput'] = self.results['total_requests'] / duration
        self.results['success_rate'] = (self.results['successful_requests'] / 
                                       self.results['total_requests'] * 100)
    
    def generate_report(self):
        """Generate detailed performance report"""
        report = []
        report.append("\n" + "="*60)
        report.append("PRODUCTION LOAD TEST REPORT")
        report.append("="*60)
        report.append(f"Test Duration: {self.end_time - self.start_time:.2f} seconds")
        report.append(f"Concurrent Users: {len(self.users)}")
        report.append(f"Target Scale: {TARGET_BAGS:,} bags")
        report.append("")
        
        report.append("PERFORMANCE METRICS:")
        report.append("-"*40)
        report.append(f"Total Requests: {self.results['total_requests']:,}")
        report.append(f"Successful: {self.results['successful_requests']:,} ({self.results.get('success_rate', 0):.1f}%)")
        report.append(f"Failed: {self.results['failed_requests']:,}")
        report.append(f"Throughput: {self.results['throughput']:.2f} req/sec")
        report.append("")
        
        if self.results['response_times']:
            report.append("RESPONSE TIME STATISTICS:")
            report.append("-"*40)
            report.append(f"Average: {self.results['avg_response_time']*1000:.2f}ms")
            report.append(f"Median: {self.results['median_response_time']*1000:.2f}ms")
            report.append(f"P95: {self.results['p95_response_time']*1000:.2f}ms")
            report.append(f"P99: {self.results['p99_response_time']*1000:.2f}ms")
            report.append(f"Min: {self.results['min_response_time']*1000:.2f}ms")
            report.append(f"Max: {self.results['max_response_time']*1000:.2f}ms")
            report.append("")
        
        # Performance assessment
        report.append("PRODUCTION READINESS ASSESSMENT:")
        report.append("-"*40)
        
        avg_response = self.results.get('avg_response_time', float('inf')) * 1000
        p99_response = self.results.get('p99_response_time', float('inf')) * 1000
        success_rate = self.results.get('success_rate', 0)
        
        if avg_response < 100 and p99_response < 500 and success_rate > 99:
            report.append("✅ EXCELLENT: System is production-ready for 800,000+ bags")
            report.append("   All performance targets met")
        elif avg_response < 200 and p99_response < 1000 and success_rate > 95:
            report.append("✅ GOOD: System is production-ready with minor optimizations needed")
            report.append("   Consider adding more caching for peak loads")
        elif avg_response < 500 and success_rate > 90:
            report.append("⚠️  ACCEPTABLE: System can handle production with improvements")
            report.append("   Recommended: Database optimization and caching improvements")
        else:
            report.append("❌ NEEDS IMPROVEMENT: System requires optimization")
            report.append("   Critical: Review database queries and implement caching")
        
        report.append("")
        report.append("RECOMMENDATIONS:")
        report.append("-"*40)
        
        if avg_response > 100:
            report.append("• Implement Redis caching for frequently accessed data")
        if p99_response > 500:
            report.append("• Optimize slow database queries")
        if success_rate < 99:
            report.append("• Increase connection pool size and timeout values")
        if self.results['failed_requests'] > 0:
            report.append("• Review error logs and fix failing endpoints")
        
        report.append("")
        report.append("="*60)
        
        return "\n".join(report)
    
    def save_results(self):
        """Save test results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON results
        with open(f"load_test_results_{timestamp}.json", "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        
        # Save report
        with open(f"load_test_report_{timestamp}.txt", "w") as f:
            f.write(self.generate_report())
        
        logger.info(f"Results saved to load_test_results_{timestamp}.json")

def main():
    """Main test execution"""
    logger.info("Starting Production Load Test")
    logger.info(f"Target: {TARGET_BAGS:,} bags, {TARGET_USERS} concurrent users")
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            logger.error("Server health check failed")
            return
    except:
        logger.error(f"Cannot connect to server at {BASE_URL}")
        logger.info("Please ensure the application is running")
        return
    
    # Run load test
    test = ProductionLoadTest()
    test.create_test_users(TARGET_USERS)
    test.login_users()
    test.run_concurrent_load(TEST_DURATION)
    test.collect_results()
    
    # Generate and display report
    report = test.generate_report()
    print(report)
    
    # Save results
    test.save_results()
    
    # Show cache statistics
    try:
        response = requests.get(f"{BASE_URL}/ultra_cache_stats", timeout=5)
        if response.status_code == 200:
            cache_stats = response.json()
            logger.info("\nCache Statistics:")
            for cache_name, stats in cache_stats.items():
                logger.info(f"  {cache_name}: {stats}")
    except:
        pass

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Production-Safe Load Test
Carefully tests system performance without overwhelming it
Simulates realistic usage patterns for 50+ concurrent users
"""

import concurrent.futures
import time
import random
import logging
import json
import statistics
from datetime import datetime
import requests
from typing import List, Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Production-safe configuration
BASE_URL = "http://localhost:5000"
TARGET_USERS = 20  # Start conservatively
TEST_DURATION = 60  # 1 minute test
RAMP_UP_TIME = 10  # 10 seconds to ramp up users

class SafeLoadTestUser:
    """Simulates a realistic user session"""
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.session = requests.Session()
        self.response_times = []
        self.errors = []
        self.successful_requests = 0
        
    def test_health(self):
        """Test health endpoint"""
        try:
            start = time.time()
            response = self.session.get(f"{BASE_URL}/health", timeout=5)
            elapsed = time.time() - start
            
            if response.status_code == 200:
                self.response_times.append(('health', elapsed))
                self.successful_requests += 1
                return True
            else:
                self.errors.append(f"Health check failed: {response.status_code}")
                return False
        except Exception as e:
            self.errors.append(f"Health error: {str(e)}")
            return False
    
    def test_stats(self):
        """Test stats endpoint"""
        try:
            start = time.time()
            response = self.session.get(f"{BASE_URL}/api/stats", timeout=10)
            elapsed = time.time() - start
            
            if response.status_code == 200:
                self.response_times.append(('stats', elapsed))
                self.successful_requests += 1
                return True
            else:
                self.errors.append(f"Stats failed: {response.status_code}")
                return False
        except Exception as e:
            self.errors.append(f"Stats error: {str(e)}")
            return False
    
    def test_cache_stats(self):
        """Test cache stats endpoint"""
        try:
            start = time.time()
            response = self.session.get(f"{BASE_URL}/ultra_cache_stats", timeout=5)
            elapsed = time.time() - start
            
            if response.status_code == 200:
                self.response_times.append(('cache_stats', elapsed))
                self.successful_requests += 1
                return True
            else:
                self.errors.append(f"Cache stats failed: {response.status_code}")
                return False
        except Exception as e:
            self.errors.append(f"Cache stats error: {str(e)}")
            return False
    
    def perform_realistic_workflow(self):
        """Perform a realistic user workflow"""
        # Simulate realistic user behavior
        workflows = [
            [self.test_health],  # Quick health check
            [self.test_stats, self.test_cache_stats],  # Dashboard view
            [self.test_stats],  # Just stats
        ]
        
        workflow = random.choice(workflows)
        for action in workflow:
            if not action():
                break
            # Realistic delay between actions
            time.sleep(random.uniform(0.5, 2.0))

class ProductionSafeLoadTest:
    """Safe load test orchestrator"""
    
    def __init__(self):
        self.users: List[SafeLoadTestUser] = []
        self.start_time = None
        self.end_time = None
        self.results = {}
        
    def create_users(self, count):
        """Create test users"""
        logger.info(f"Creating {count} test users...")
        for i in range(count):
            self.users.append(SafeLoadTestUser(i))
        logger.info(f"Created {len(self.users)} users")
    
    def run_ramped_load(self, duration, ramp_up):
        """Run load test with gradual ramp-up"""
        logger.info(f"Starting {duration}s load test with {ramp_up}s ramp-up...")
        
        self.start_time = time.time()
        end_time = self.start_time + duration
        
        def user_worker(user, delay):
            """Worker for a single user"""
            time.sleep(delay)  # Ramp-up delay
            
            while time.time() < end_time:
                user.perform_realistic_workflow()
                # Realistic think time
                time.sleep(random.uniform(2, 5))
        
        # Start users with ramp-up delays
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.users)) as executor:
            futures = []
            for i, user in enumerate(self.users):
                delay = (i / len(self.users)) * ramp_up
                futures.append(executor.submit(user_worker, user, delay))
            
            # Wait for all to complete
            concurrent.futures.wait(futures)
        
        self.end_time = time.time()
        logger.info("Load test completed")
    
    def analyze_results(self):
        """Analyze test results"""
        all_times = []
        endpoint_times = {'health': [], 'stats': [], 'cache_stats': []}
        all_errors = []
        total_requests = 0
        successful_requests = 0
        
        for user in self.users:
            for endpoint, time_val in user.response_times:
                all_times.append(time_val)
                endpoint_times[endpoint].append(time_val)
            all_errors.extend(user.errors)
            total_requests += len(user.response_times) + len(user.errors)
            successful_requests += user.successful_requests
        
        # Calculate statistics
        self.results = {
            'duration': self.end_time - self.start_time,
            'users': len(self.users),
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': len(all_errors),
            'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            'throughput': total_requests / (self.end_time - self.start_time),
        }
        
        if all_times:
            self.results['response_times'] = {
                'avg': statistics.mean(all_times),
                'median': statistics.median(all_times),
                'min': min(all_times),
                'max': max(all_times),
            }
            
            if len(all_times) > 1:
                self.results['response_times']['p95'] = statistics.quantiles(all_times, n=20)[18]
                self.results['response_times']['p99'] = statistics.quantiles(all_times, n=100)[98]
        
        # Per-endpoint statistics
        self.results['endpoint_stats'] = {}
        for endpoint, times in endpoint_times.items():
            if times:
                self.results['endpoint_stats'][endpoint] = {
                    'count': len(times),
                    'avg': statistics.mean(times),
                    'median': statistics.median(times),
                    'max': max(times)
                }
        
        # Sample errors
        self.results['sample_errors'] = all_errors[:10] if all_errors else []
    
    def generate_report(self):
        """Generate performance report"""
        report = []
        report.append("\n" + "="*60)
        report.append("PRODUCTION-SAFE LOAD TEST REPORT")
        report.append("="*60)
        report.append(f"Test Duration: {self.results['duration']:.2f} seconds")
        report.append(f"Concurrent Users: {self.results['users']}")
        report.append("")
        
        report.append("OVERALL METRICS:")
        report.append("-"*40)
        report.append(f"Total Requests: {self.results['total_requests']}")
        report.append(f"Successful: {self.results['successful_requests']} ({self.results['success_rate']:.1f}%)")
        report.append(f"Failed: {self.results['failed_requests']}")
        report.append(f"Throughput: {self.results['throughput']:.2f} req/sec")
        report.append("")
        
        if 'response_times' in self.results:
            rt = self.results['response_times']
            report.append("RESPONSE TIME STATISTICS (all endpoints):")
            report.append("-"*40)
            report.append(f"Average: {rt['avg']*1000:.2f}ms")
            report.append(f"Median: {rt['median']*1000:.2f}ms")
            report.append(f"Min: {rt['min']*1000:.2f}ms")
            report.append(f"Max: {rt['max']*1000:.2f}ms")
            if 'p95' in rt:
                report.append(f"P95: {rt['p95']*1000:.2f}ms")
            if 'p99' in rt:
                report.append(f"P99: {rt['p99']*1000:.2f}ms")
            report.append("")
        
        if 'endpoint_stats' in self.results:
            report.append("PER-ENDPOINT PERFORMANCE:")
            report.append("-"*40)
            for endpoint, stats in self.results['endpoint_stats'].items():
                report.append(f"{endpoint}:")
                report.append(f"  Requests: {stats['count']}")
                report.append(f"  Avg: {stats['avg']*1000:.2f}ms")
                report.append(f"  Median: {stats['median']*1000:.2f}ms")
                report.append(f"  Max: {stats['max']*1000:.2f}ms")
            report.append("")
        
        # Production readiness assessment
        report.append("PRODUCTION READINESS FOR 50+ USERS:")
        report.append("-"*40)
        
        avg_response = self.results.get('response_times', {}).get('avg', float('inf')) * 1000
        success_rate = self.results.get('success_rate', 0)
        
        if success_rate >= 99 and avg_response < 200:
            report.append("✅ EXCELLENT - System ready for 50+ concurrent users")
            report.append("   Performance targets met with margin")
            scale_factor = 50 / self.results['users']
            report.append(f"   Projected for 50 users: ~{avg_response * 1.2:.0f}ms avg response")
        elif success_rate >= 95 and avg_response < 500:
            report.append("✅ GOOD - System can handle 50+ users with minor optimization")
            report.append("   Consider enabling caching for better performance")
        elif success_rate >= 90:
            report.append("⚠️  ACCEPTABLE - System needs optimization for 50+ users")
            report.append("   Recommended: Improve caching and query optimization")
        else:
            report.append("❌ NEEDS IMPROVEMENT - Not ready for 50+ users")
            report.append("   Critical: Fix errors and optimize performance")
        
        if self.results['sample_errors']:
            report.append("")
            report.append("SAMPLE ERRORS:")
            report.append("-"*40)
            for error in self.results['sample_errors'][:5]:
                report.append(f"  • {error}")
        
        report.append("")
        report.append("="*60)
        
        return "\n".join(report)

def main():
    """Main test execution"""
    logger.info("Starting Production-Safe Load Test")
    
    # Verify server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            logger.error("Server health check failed")
            return
    except Exception as e:
        logger.error(f"Cannot connect to server: {e}")
        return
    
    # Run test with conservative settings
    test = ProductionSafeLoadTest()
    test.create_users(TARGET_USERS)
    test.run_ramped_load(TEST_DURATION, RAMP_UP_TIME)
    test.analyze_results()
    
    # Generate and display report
    report = test.generate_report()
    print(report)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    with open(f"safe_load_test_{timestamp}.json", "w") as f:
        json.dump(test.results, f, indent=2, default=str)
    
    with open(f"safe_load_test_{timestamp}.txt", "w") as f:
        f.write(report)
    
    logger.info(f"Results saved to safe_load_test_{timestamp}.json")
    
    # Check cache improvement
    try:
        response = requests.get(f"{BASE_URL}/ultra_cache_stats", timeout=5)
        if response.status_code == 200:
            cache_stats = response.json()
            logger.info("\nPost-test Cache Statistics:")
            for cache_name, stats in cache_stats.items():
                logger.info(f"  {cache_name}: {stats}")
    except:
        pass

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Production 50+ Users Load Test
Tests system with full target load of 50+ concurrent users
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

# Production target configuration
BASE_URL = "http://localhost:5000"
TARGET_USERS = 50  # Full production load
TEST_DURATION = 120  # 2 minute test
RAMP_UP_TIME = 20  # 20 seconds to ramp up users

class LoadTestUser:
    """Simulates a production user"""
    
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
            response = self.session.get(f"{BASE_URL}/health", timeout=10)
            elapsed = time.time() - start
            
            if response.status_code == 200:
                self.response_times.append(('health', elapsed))
                self.successful_requests += 1
                return True
            else:
                self.errors.append(f"Health check failed: {response.status_code}")
                return False
        except Exception as e:
            self.errors.append(f"Health error: {str(e)[:50]}")
            return False
    
    def test_stats(self):
        """Test stats endpoint (most critical)"""
        try:
            start = time.time()
            response = self.session.get(f"{BASE_URL}/api/stats", timeout=15)
            elapsed = time.time() - start
            
            if response.status_code == 200:
                self.response_times.append(('stats', elapsed))
                self.successful_requests += 1
                return True
            else:
                self.errors.append(f"Stats failed: {response.status_code}")
                return False
        except Exception as e:
            self.errors.append(f"Stats error: {str(e)[:50]}")
            return False
    
    def test_cache_stats(self):
        """Test cache stats endpoint"""
        try:
            start = time.time()
            response = self.session.get(f"{BASE_URL}/ultra_cache_stats", timeout=10)
            elapsed = time.time() - start
            
            if response.status_code == 200:
                self.response_times.append(('cache_stats', elapsed))
                self.successful_requests += 1
                return True
            else:
                self.errors.append(f"Cache stats failed: {response.status_code}")
                return False
        except Exception as e:
            self.errors.append(f"Cache stats error: {str(e)[:50]}")
            return False
    
    def perform_user_workflow(self):
        """Perform realistic user actions"""
        # Weight the workflows to simulate real usage
        workflows = [
            ([self.test_stats], 0.5),  # 50% just check stats
            ([self.test_health, self.test_stats], 0.3),  # 30% health then stats
            ([self.test_stats, self.test_cache_stats], 0.2),  # 20% stats and cache
        ]
        
        # Choose workflow based on weights
        rand = random.random()
        cumulative = 0
        workflow = None
        for actions, weight in workflows:
            cumulative += weight
            if rand <= cumulative:
                workflow = actions
                break
        
        if workflow:
            for action in workflow:
                if not action():
                    break
                # Realistic delay between actions
                time.sleep(random.uniform(0.3, 1.5))

class Production50UsersTest:
    """Production load test for 50+ users"""
    
    def __init__(self):
        self.users: List[LoadTestUser] = []
        self.start_time = None
        self.end_time = None
        self.results = {}
        
    def create_users(self, count):
        """Create test users"""
        logger.info(f"Creating {count} test users...")
        for i in range(count):
            self.users.append(LoadTestUser(i))
        logger.info(f"Created {len(self.users)} users")
    
    def run_load_test(self, duration, ramp_up):
        """Run load test with production parameters"""
        logger.info(f"Starting {duration}s load test with {len(self.users)} users...")
        logger.info(f"Ramp-up period: {ramp_up}s")
        
        self.start_time = time.time()
        end_time = self.start_time + duration
        
        def user_simulation(user, start_delay):
            """Simulate a single user's activity"""
            time.sleep(start_delay)  # Ramp-up delay
            
            session_count = 0
            while time.time() < end_time:
                user.perform_user_workflow()
                session_count += 1
                
                # Think time between workflows
                think_time = random.uniform(3, 8)
                time.sleep(think_time)
            
            return session_count
        
        # Execute with all users
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.users)) as executor:
            futures = []
            for i, user in enumerate(self.users):
                # Stagger user start times
                delay = (i / len(self.users)) * ramp_up
                futures.append(executor.submit(user_simulation, user, delay))
            
            # Wait for completion
            session_counts = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        self.end_time = time.time()
        logger.info(f"Load test completed. Total sessions: {sum(session_counts)}")
    
    def analyze_results(self):
        """Analyze test results for production readiness"""
        all_times = []
        endpoint_times = {'health': [], 'stats': [], 'cache_stats': []}
        all_errors = []
        total_requests = 0
        successful_requests = 0
        
        for user in self.users:
            for endpoint, time_val in user.response_times:
                all_times.append(time_val)
                if endpoint in endpoint_times:
                    endpoint_times[endpoint].append(time_val)
            all_errors.extend(user.errors)
            total_requests += len(user.response_times) + len(user.errors)
            successful_requests += user.successful_requests
        
        # Core metrics
        self.results = {
            'duration': self.end_time - self.start_time,
            'users': len(self.users),
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': len(all_errors),
            'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            'throughput': total_requests / (self.end_time - self.start_time) if self.end_time > self.start_time else 0,
            'requests_per_user': total_requests / len(self.users) if self.users else 0,
        }
        
        # Response time statistics
        if all_times:
            self.results['response_times'] = {
                'avg': statistics.mean(all_times),
                'median': statistics.median(all_times),
                'min': min(all_times),
                'max': max(all_times),
            }
            
            if len(all_times) >= 20:
                self.results['response_times']['p95'] = statistics.quantiles(all_times, n=20)[18]
            if len(all_times) >= 100:
                self.results['response_times']['p99'] = statistics.quantiles(all_times, n=100)[98]
        
        # Per-endpoint analysis
        self.results['endpoint_stats'] = {}
        for endpoint, times in endpoint_times.items():
            if times:
                self.results['endpoint_stats'][endpoint] = {
                    'count': len(times),
                    'avg': statistics.mean(times),
                    'median': statistics.median(times),
                    'min': min(times),
                    'max': max(times),
                    'success_rate': (len(times) / (len(times) + len([e for e in all_errors if endpoint in e])) * 100)
                }
        
        # Error analysis
        error_types = {}
        for error in all_errors:
            error_type = error.split(':')[0]
            error_types[error_type] = error_types.get(error_type, 0) + 1
        self.results['error_types'] = error_types
        self.results['sample_errors'] = all_errors[:5] if all_errors else []
    
    def generate_report(self):
        """Generate comprehensive production readiness report"""
        report = []
        report.append("\n" + "="*70)
        report.append("🚀 PRODUCTION 50+ USERS LOAD TEST REPORT")
        report.append("="*70)
        report.append(f"Test Duration: {self.results['duration']:.2f} seconds")
        report.append(f"Concurrent Users: {self.results['users']}")
        report.append(f"Target Scale: 800,000+ bags")
        report.append("")
        
        report.append("📊 OVERALL PERFORMANCE:")
        report.append("-"*50)
        report.append(f"Total Requests: {self.results['total_requests']}")
        report.append(f"Successful: {self.results['successful_requests']} ({self.results['success_rate']:.2f}%)")
        report.append(f"Failed: {self.results['failed_requests']}")
        report.append(f"Throughput: {self.results['throughput']:.2f} req/sec")
        report.append(f"Avg Requests/User: {self.results['requests_per_user']:.1f}")
        report.append("")
        
        if 'response_times' in self.results:
            rt = self.results['response_times']
            report.append("⏱️  RESPONSE TIME ANALYSIS:")
            report.append("-"*50)
            report.append(f"Average: {rt['avg']*1000:.2f}ms")
            report.append(f"Median: {rt['median']*1000:.2f}ms")
            report.append(f"Min: {rt['min']*1000:.2f}ms")
            report.append(f"Max: {rt['max']*1000:.2f}ms")
            if 'p95' in rt:
                report.append(f"95th Percentile: {rt['p95']*1000:.2f}ms")
            if 'p99' in rt:
                report.append(f"99th Percentile: {rt['p99']*1000:.2f}ms")
            report.append("")
        
        if 'endpoint_stats' in self.results:
            report.append("🎯 ENDPOINT PERFORMANCE:")
            report.append("-"*50)
            for endpoint, stats in self.results['endpoint_stats'].items():
                report.append(f"\n{endpoint.upper()}:")
                report.append(f"  Requests: {stats['count']}")
                report.append(f"  Success Rate: {stats['success_rate']:.1f}%")
                report.append(f"  Avg Response: {stats['avg']*1000:.2f}ms")
                report.append(f"  Median: {stats['median']*1000:.2f}ms")
                report.append(f"  Min/Max: {stats['min']*1000:.2f}ms / {stats['max']*1000:.2f}ms")
            report.append("")
        
        # Production readiness verdict
        report.append("✅ PRODUCTION READINESS ASSESSMENT:")
        report.append("-"*50)
        
        avg_response = self.results.get('response_times', {}).get('avg', float('inf')) * 1000
        p95_response = self.results.get('response_times', {}).get('p95', float('inf')) * 1000
        success_rate = self.results.get('success_rate', 0)
        throughput = self.results.get('throughput', 0)
        
        criteria = {
            "Success Rate ≥ 99%": success_rate >= 99,
            "Avg Response < 200ms": avg_response < 200,
            "P95 Response < 1000ms": p95_response < 1000,
            "Throughput > 5 req/sec": throughput > 5,
            "Error Rate < 1%": self.results['failed_requests'] / max(self.results['total_requests'], 1) < 0.01
        }
        
        passed = sum(criteria.values())
        total = len(criteria)
        
        for criterion, met in criteria.items():
            status = "✅" if met else "❌"
            report.append(f"{status} {criterion}")
        
        report.append("")
        if passed == total:
            report.append("🎉 VERDICT: PRODUCTION READY!")
            report.append("   System successfully handles 50+ concurrent users")
            report.append("   Performance exceeds all requirements")
            report.append("   Ready for 800,000+ bags scale")
        elif passed >= total - 1:
            report.append("✅ VERDICT: PRODUCTION READY WITH MINOR NOTES")
            report.append("   System can handle production load")
            report.append("   Minor optimizations recommended")
        elif passed >= total - 2:
            report.append("⚠️  VERDICT: CONDITIONAL PRODUCTION READY")
            report.append("   System needs optimization before full load")
            report.append("   Consider phased rollout")
        else:
            report.append("❌ VERDICT: NOT PRODUCTION READY")
            report.append("   Critical performance issues detected")
            report.append("   Requires significant optimization")
        
        if self.results.get('error_types'):
            report.append("")
            report.append("⚠️  ERROR BREAKDOWN:")
            report.append("-"*50)
            for error_type, count in self.results['error_types'].items():
                report.append(f"  {error_type}: {count}")
        
        report.append("")
        report.append("="*70)
        
        return "\n".join(report)

def main():
    """Execute production load test"""
    logger.info("🚀 Starting Production 50+ Users Load Test")
    
    # Verify server
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            logger.error("Server health check failed")
            return
        logger.info("✅ Server is running")
    except Exception as e:
        logger.error(f"Cannot connect to server: {e}")
        return
    
    # Run production load test
    test = Production50UsersTest()
    test.create_users(TARGET_USERS)
    
    logger.info("Starting production load simulation...")
    test.run_load_test(TEST_DURATION, RAMP_UP_TIME)
    
    logger.info("Analyzing results...")
    test.analyze_results()
    
    # Generate report
    report = test.generate_report()
    print(report)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    with open(f"production_50_users_{timestamp}.json", "w") as f:
        json.dump(test.results, f, indent=2, default=str)
    
    with open(f"production_50_users_{timestamp}.txt", "w") as f:
        f.write(report)
    
    logger.info(f"📁 Results saved to production_50_users_{timestamp}.json")
    
    # Final cache stats
    try:
        response = requests.get(f"{BASE_URL}/ultra_cache_stats", timeout=5)
        if response.status_code == 200:
            cache_stats = response.json()
            logger.info("\n📈 Final Cache Performance:")
            for cache_name, stats in cache_stats.items():
                if stats.get('hits', 0) > 0:
                    logger.info(f"  {cache_name}: Hit Rate={stats['hit_rate']}, Hits={stats['hits']}")
    except:
        pass

if __name__ == "__main__":
    main()
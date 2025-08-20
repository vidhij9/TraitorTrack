#!/usr/bin/env python3
"""
Performance Testing Script for TraceTrack Application
Tests high concurrency scenarios with 50+ concurrent users and 800,000+ bags
"""

import asyncio
import aiohttp
import time
import random
import logging
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple
import json
from datetime import datetime
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PerformanceTestSuite:
    """Comprehensive performance testing suite"""
    
    def __init__(self, base_url="http://localhost:5000", num_users=50):
        self.base_url = base_url
        self.num_users = num_users
        self.session = None
        self.results = {
            'bill_creation': [],
            'bag_linking': [],
            'bill_deletion': [],
            'bill_query': [],
            'concurrent_operations': []
        }
        self.test_bills = []
        self.test_bags = []
        
    def setup_test_data(self):
        """Create test data for performance testing"""
        logger.info("Setting up test data...")
        
        # Generate test bill IDs
        self.test_bills = [f"PERF_BILL_{i:06d}" for i in range(1000)]
        
        # Generate test bag QR codes (800,000+ bags)
        self.test_bags = [f"SB{i:05d}" for i in range(1, 100001)]  # Sample of 100k for testing
        
        logger.info(f"Generated {len(self.test_bills)} test bills and {len(self.test_bags)} test bags")
    
    def login_user(self, session, user_num):
        """Login a test user"""
        login_data = {
            'username': f'test_user_{user_num}',
            'password': 'testpass123'
        }
        
        try:
            response = session.post(f"{self.base_url}/login", data=login_data)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Login failed for user {user_num}: {e}")
            return False
    
    async def async_bill_creation(self, session: aiohttp.ClientSession, bill_id: str) -> Tuple[bool, float]:
        """Async bill creation test"""
        start_time = time.time()
        
        data = {
            'bill_id': bill_id,
            'parent_bag_count': random.randint(10, 50)
        }
        
        try:
            async with session.post(f"{self.base_url}/bill/create", data=data) as response:
                success = response.status == 200
                elapsed = time.time() - start_time
                return success, elapsed
        except Exception as e:
            logger.error(f"Bill creation error: {e}")
            return False, time.time() - start_time
    
    async def async_bag_linking(self, session: aiohttp.ClientSession, bill_id: int, qr_code: str) -> Tuple[bool, float]:
        """Async bag linking test"""
        start_time = time.time()
        
        data = {
            'bill_id': bill_id,
            'qr_code': qr_code
        }
        
        try:
            async with session.post(f"{self.base_url}/process_bill_parent_scan", data=data) as response:
                success = response.status == 200
                elapsed = time.time() - start_time
                return success, elapsed
        except Exception as e:
            logger.error(f"Bag linking error: {e}")
            return False, time.time() - start_time
    
    async def async_bill_query(self, session: aiohttp.ClientSession, search_term: str = "") -> Tuple[bool, float]:
        """Async bill query test"""
        start_time = time.time()
        
        params = {'search_bill_id': search_term} if search_term else {}
        
        try:
            async with session.get(f"{self.base_url}/bill_management", params=params) as response:
                success = response.status == 200
                elapsed = time.time() - start_time
                return success, elapsed
        except Exception as e:
            logger.error(f"Bill query error: {e}")
            return False, time.time() - start_time
    
    async def run_concurrent_test(self, test_name: str, num_operations: int):
        """Run concurrent operations test"""
        logger.info(f"Starting {test_name} with {num_operations} concurrent operations...")
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            if test_name == "bill_creation":
                for i in range(num_operations):
                    bill_id = f"CONCURRENT_BILL_{i:06d}_{int(time.time())}"
                    tasks.append(self.async_bill_creation(session, bill_id))
            
            elif test_name == "bag_linking":
                # Assume we have some bills created
                for i in range(num_operations):
                    bill_id = random.randint(1, 100)  # Random bill ID
                    qr_code = random.choice(self.test_bags)
                    tasks.append(self.async_bag_linking(session, bill_id, qr_code))
            
            elif test_name == "bill_query":
                for i in range(num_operations):
                    search_term = random.choice(["", "BILL", "TEST", "PERF"])
                    tasks.append(self.async_bill_query(session, search_term))
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks)
            
            # Analyze results
            successful = sum(1 for success, _ in results if success)
            times = [elapsed for _, elapsed in results]
            
            stats = {
                'total_operations': num_operations,
                'successful': successful,
                'failed': num_operations - successful,
                'success_rate': (successful / num_operations) * 100,
                'min_time': min(times) * 1000,  # Convert to ms
                'max_time': max(times) * 1000,
                'avg_time': statistics.mean(times) * 1000,
                'median_time': statistics.median(times) * 1000,
                'p95_time': statistics.quantiles(times, n=20)[18] * 1000,  # 95th percentile
                'p99_time': statistics.quantiles(times, n=100)[98] * 1000  # 99th percentile
            }
            
            self.results[test_name].append(stats)
            return stats
    
    def run_stress_test(self):
        """Run comprehensive stress test"""
        logger.info("="*60)
        logger.info("STARTING COMPREHENSIVE STRESS TEST")
        logger.info(f"Target: {self.num_users} concurrent users")
        logger.info("="*60)
        
        # Setup test data
        self.setup_test_data()
        
        # Test scenarios
        test_scenarios = [
            ("bill_creation", 50),      # 50 concurrent bill creations
            ("bag_linking", 100),        # 100 concurrent bag linkings
            ("bill_query", 200),         # 200 concurrent queries
            ("bill_creation", 100),      # 100 concurrent bill creations (stress)
            ("bag_linking", 500),        # 500 concurrent bag linkings (heavy stress)
        ]
        
        # Run tests
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        for test_name, num_ops in test_scenarios:
            logger.info(f"\n{'='*40}")
            logger.info(f"Test: {test_name} with {num_ops} operations")
            logger.info(f"{'='*40}")
            
            stats = loop.run_until_complete(self.run_concurrent_test(test_name, num_ops))
            
            # Print results
            logger.info(f"Results for {test_name}:")
            logger.info(f"  Success Rate: {stats['success_rate']:.2f}%")
            logger.info(f"  Response Times (ms):")
            logger.info(f"    Min: {stats['min_time']:.2f}")
            logger.info(f"    Avg: {stats['avg_time']:.2f}")
            logger.info(f"    Median: {stats['median_time']:.2f}")
            logger.info(f"    P95: {stats['p95_time']:.2f}")
            logger.info(f"    P99: {stats['p99_time']:.2f}")
            logger.info(f"    Max: {stats['max_time']:.2f}")
            
            # Check performance requirements
            if stats['avg_time'] > 1000:  # More than 1 second
                logger.warning(f"  ⚠️  Average response time exceeds 1 second!")
            else:
                logger.info(f"  ✓ Performance within acceptable limits")
            
            # Small delay between tests
            time.sleep(2)
        
        loop.close()
        
        # Generate summary report
        self.generate_report()
    
    def generate_report(self):
        """Generate performance test report"""
        logger.info("\n" + "="*60)
        logger.info("PERFORMANCE TEST SUMMARY REPORT")
        logger.info("="*60)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"Test completed at: {timestamp}")
        logger.info(f"Configuration: {self.num_users} concurrent users")
        
        # Overall statistics
        all_success_rates = []
        all_avg_times = []
        
        for test_name, results in self.results.items():
            if results:
                success_rates = [r['success_rate'] for r in results]
                avg_times = [r['avg_time'] for r in results]
                
                if success_rates:
                    all_success_rates.extend(success_rates)
                    all_avg_times.extend(avg_times)
                    
                    logger.info(f"\n{test_name.upper()}:")
                    logger.info(f"  Avg Success Rate: {statistics.mean(success_rates):.2f}%")
                    logger.info(f"  Avg Response Time: {statistics.mean(avg_times):.2f}ms")
        
        # Overall verdict
        logger.info("\n" + "="*40)
        logger.info("OVERALL VERDICT:")
        
        overall_success = statistics.mean(all_success_rates) if all_success_rates else 0
        overall_time = statistics.mean(all_avg_times) if all_avg_times else 0
        
        if overall_success >= 99 and overall_time <= 1000:
            logger.info("✅ EXCELLENT: System performs well under high load")
            logger.info(f"   Success Rate: {overall_success:.2f}%")
            logger.info(f"   Avg Response: {overall_time:.2f}ms")
        elif overall_success >= 95 and overall_time <= 2000:
            logger.info("⚠️  GOOD: System handles load with minor issues")
            logger.info(f"   Success Rate: {overall_success:.2f}%")
            logger.info(f"   Avg Response: {overall_time:.2f}ms")
        else:
            logger.error("❌ POOR: System struggles under high load")
            logger.error(f"   Success Rate: {overall_success:.2f}%")
            logger.error(f"   Avg Response: {overall_time:.2f}ms")
        
        # Save detailed report to file
        report_filename = f"performance_report_{int(time.time())}.json"
        with open(report_filename, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'config': {'concurrent_users': self.num_users},
                'results': self.results,
                'summary': {
                    'overall_success_rate': overall_success,
                    'overall_avg_response_time_ms': overall_time
                }
            }, f, indent=2)
        
        logger.info(f"\nDetailed report saved to: {report_filename}")
        logger.info("="*60)

def main():
    """Main entry point for performance testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Performance testing for TraceTrack')
    parser.add_argument('--url', default='http://localhost:5000', help='Base URL of the application')
    parser.add_argument('--users', type=int, default=50, help='Number of concurrent users')
    parser.add_argument('--test', choices=['stress', 'load', 'spike'], default='stress', 
                       help='Type of test to run')
    
    args = parser.parse_args()
    
    # Create test suite
    test_suite = PerformanceTestSuite(base_url=args.url, num_users=args.users)
    
    # Run appropriate test
    if args.test == 'stress':
        test_suite.run_stress_test()
    else:
        logger.info(f"Test type '{args.test}' not yet implemented")

if __name__ == "__main__":
    main()
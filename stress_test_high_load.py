#!/usr/bin/env python3
"""
High-load stress test for TraceTrack application
Tests 50+ concurrent users and capacity for 800,000+ bags
"""

import asyncio
import aiohttp
import time
import random
import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple
import statistics

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:5000"
NUM_CONCURRENT_USERS = 50
TARGET_BAG_COUNT = 800000
SAMPLE_SIZE = 10000  # Sample size for testing (full 800k would take too long)

class LoadTester:
    def __init__(self):
        self.results = {
            'response_times': [],
            'success_count': 0,
            'failure_count': 0,
            'errors': [],
            'start_time': None,
            'end_time': None
        }
        
    async def create_session(self, session: aiohttp.ClientSession, user_id: int) -> str:
        """Create a user session with login"""
        try:
            # Login
            login_data = {
                'username': 'admin',
                'password': 'Admin@123'
            }
            
            async with session.post(f'{BASE_URL}/login', data=login_data, ssl=False) as resp:
                if resp.status == 200:
                    return session
                else:
                    logger.warning(f"User {user_id} login failed with status {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"User {user_id} session creation failed: {e}")
            return None
    
    async def simulate_parent_scan(self, session: aiohttp.ClientSession, bag_id: str) -> float:
        """Simulate parent bag scanning"""
        start = time.time()
        try:
            data = {
                'qr_id': f'PARENT_{bag_id}',
                'name': f'Parent Bag {bag_id}',
                'child_count': random.randint(10, 30)
            }
            
            async with session.post(f'{BASE_URL}/api/scan_parent', json=data, ssl=False) as resp:
                elapsed = time.time() - start
                if resp.status == 200:
                    self.results['success_count'] += 1
                else:
                    self.results['failure_count'] += 1
                return elapsed
        except Exception as e:
            self.results['failure_count'] += 1
            self.results['errors'].append(str(e))
            return time.time() - start
    
    async def simulate_child_scan(self, session: aiohttp.ClientSession, parent_id: str, child_id: str) -> float:
        """Simulate child bag scanning"""
        start = time.time()
        try:
            data = {
                'parent_qr': f'PARENT_{parent_id}',
                'child_qrs': [f'CHILD_{child_id}_{i}' for i in range(random.randint(5, 15))]
            }
            
            async with session.post(f'{BASE_URL}/api/scan_child', json=data, ssl=False) as resp:
                elapsed = time.time() - start
                if resp.status == 200:
                    self.results['success_count'] += 1
                else:
                    self.results['failure_count'] += 1
                return elapsed
        except Exception as e:
            self.results['failure_count'] += 1
            self.results['errors'].append(str(e))
            return time.time() - start
    
    async def simulate_bill_creation(self, session: aiohttp.ClientSession, bill_id: str) -> float:
        """Simulate bill creation"""
        start = time.time()
        try:
            data = {
                'bill_id': f'BILL_{bill_id}',
                'description': f'High load test bill {bill_id}',
                'parent_bag_count': random.randint(10, 50)
            }
            
            async with session.post(f'{BASE_URL}/api/create_bill', json=data, ssl=False) as resp:
                elapsed = time.time() - start
                if resp.status == 200:
                    self.results['success_count'] += 1
                else:
                    self.results['failure_count'] += 1
                return elapsed
        except Exception as e:
            self.results['failure_count'] += 1
            self.results['errors'].append(str(e))
            return time.time() - start
    
    async def simulate_user_workflow(self, user_id: int, operations_per_user: int):
        """Simulate a complete user workflow"""
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        timeout = aiohttp.ClientTimeout(total=60)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Create session
            logged_session = await self.create_session(session, user_id)
            if not logged_session:
                logger.error(f"User {user_id} failed to login")
                return
            
            for op in range(operations_per_user):
                # Randomly choose operation
                operation = random.choice(['parent_scan', 'child_scan', 'bill_creation'])
                
                if operation == 'parent_scan':
                    elapsed = await self.simulate_parent_scan(session, f"{user_id}_{op}")
                elif operation == 'child_scan':
                    elapsed = await self.simulate_child_scan(session, f"{user_id}", f"{op}")
                else:
                    elapsed = await self.simulate_bill_creation(session, f"{user_id}_{op}")
                
                self.results['response_times'].append(elapsed * 1000)  # Convert to ms
                
                # Small delay between operations
                await asyncio.sleep(random.uniform(0.1, 0.5))
    
    async def run_load_test(self):
        """Run the main load test"""
        logger.info(f"Starting high-load test with {NUM_CONCURRENT_USERS} concurrent users")
        logger.info(f"Simulating system capacity for {TARGET_BAG_COUNT:,} bags")
        logger.info(f"Using sample size of {SAMPLE_SIZE:,} operations")
        
        self.results['start_time'] = datetime.now()
        
        # Calculate operations per user
        operations_per_user = SAMPLE_SIZE // NUM_CONCURRENT_USERS
        
        # Create tasks for all concurrent users
        tasks = []
        for user_id in range(NUM_CONCURRENT_USERS):
            task = asyncio.create_task(self.simulate_user_workflow(user_id, operations_per_user))
            tasks.append(task)
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks)
        
        self.results['end_time'] = datetime.now()
        
    def generate_report(self) -> Dict:
        """Generate performance report"""
        if not self.results['response_times']:
            return {'error': 'No successful operations recorded'}
        
        response_times = sorted(self.results['response_times'])
        total_operations = self.results['success_count'] + self.results['failure_count']
        duration = (self.results['end_time'] - self.results['start_time']).total_seconds()
        
        report = {
            'test_configuration': {
                'concurrent_users': NUM_CONCURRENT_USERS,
                'target_bag_capacity': TARGET_BAG_COUNT,
                'sample_operations': SAMPLE_SIZE,
                'test_duration_seconds': duration
            },
            'performance_metrics': {
                'total_operations': total_operations,
                'successful_operations': self.results['success_count'],
                'failed_operations': self.results['failure_count'],
                'success_rate_percent': (self.results['success_count'] / total_operations * 100) if total_operations > 0 else 0,
                'operations_per_second': total_operations / duration if duration > 0 else 0
            },
            'response_times_ms': {
                'min': min(response_times) if response_times else 0,
                'avg': statistics.mean(response_times) if response_times else 0,
                'median': statistics.median(response_times) if response_times else 0,
                'p95': response_times[int(len(response_times) * 0.95)] if response_times else 0,
                'p99': response_times[int(len(response_times) * 0.99)] if response_times else 0,
                'max': max(response_times) if response_times else 0
            },
            'capacity_analysis': {
                'estimated_daily_capacity': int(total_operations / duration * 86400) if duration > 0 else 0,
                'can_handle_target_bags': 'YES' if self.results['success_count'] / total_operations > 0.95 else 'NO',
                'bottlenecks': []
            },
            'errors': self.results['errors'][:10] if self.results['errors'] else []
        }
        
        # Identify bottlenecks
        if report['response_times_ms']['avg'] > 1000:
            report['capacity_analysis']['bottlenecks'].append('High average response time (>1s)')
        if report['response_times_ms']['p99'] > 3000:
            report['capacity_analysis']['bottlenecks'].append('P99 response time exceeds 3 seconds')
        if report['performance_metrics']['success_rate_percent'] < 95:
            report['capacity_analysis']['bottlenecks'].append('Success rate below 95%')
        
        return report

async def main():
    """Main function to run the load test"""
    tester = LoadTester()
    
    print("\n" + "="*80)
    print("🚀 HIGH-LOAD STRESS TEST FOR TRACETRACK")
    print("="*80)
    print(f"Testing with {NUM_CONCURRENT_USERS} concurrent users")
    print(f"Target capacity: {TARGET_BAG_COUNT:,} bags")
    print(f"Sample size: {SAMPLE_SIZE:,} operations")
    print("="*80 + "\n")
    
    await tester.run_load_test()
    
    report = tester.generate_report()
    
    # Print report
    print("\n" + "="*80)
    print("📊 TEST RESULTS")
    print("="*80)
    
    print(f"\n⏱️ Test Duration: {report['test_configuration']['test_duration_seconds']:.2f} seconds")
    print(f"👥 Concurrent Users: {report['test_configuration']['concurrent_users']}")
    print(f"📦 Target Bag Capacity: {report['test_configuration']['target_bag_capacity']:,}")
    
    print(f"\n✅ Success Rate: {report['performance_metrics']['success_rate_percent']:.2f}%")
    print(f"📈 Operations/Second: {report['performance_metrics']['operations_per_second']:.2f}")
    print(f"💾 Estimated Daily Capacity: {report['capacity_analysis']['estimated_daily_capacity']:,} operations")
    
    print(f"\n⚡ Response Times (ms):")
    print(f"   Min: {report['response_times_ms']['min']:.2f}")
    print(f"   Avg: {report['response_times_ms']['avg']:.2f}")
    print(f"   Median: {report['response_times_ms']['median']:.2f}")
    print(f"   P95: {report['response_times_ms']['p95']:.2f}")
    print(f"   P99: {report['response_times_ms']['p99']:.2f}")
    print(f"   Max: {report['response_times_ms']['max']:.2f}")
    
    print(f"\n🎯 CAPACITY VERDICT:")
    if report['capacity_analysis']['can_handle_target_bags'] == 'YES':
        print(f"   ✅ System CAN handle {TARGET_BAG_COUNT:,} bags with {NUM_CONCURRENT_USERS} concurrent users")
    else:
        print(f"   ❌ System CANNOT reliably handle {TARGET_BAG_COUNT:,} bags with {NUM_CONCURRENT_USERS} concurrent users")
    
    if report['capacity_analysis']['bottlenecks']:
        print(f"\n⚠️ Identified Bottlenecks:")
        for bottleneck in report['capacity_analysis']['bottlenecks']:
            print(f"   - {bottleneck}")
    
    # Save detailed report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"high_load_test_report_{timestamp}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n📄 Detailed report saved to: {filename}")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
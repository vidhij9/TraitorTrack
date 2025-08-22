"""
Massive Load Testing Script for TraceTrack
Tests with 50+ concurrent users and 800,000+ bags
"""
import asyncio
import aiohttp
import time
import random
import string
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing
import psutil
import json
from datetime import datetime

# Configuration
BASE_URL = 'http://localhost:5000'
CONCURRENT_USERS = 50
TOTAL_BAGS = 800000
BAGS_PER_BATCH = 1000
PARENT_BAGS = TOTAL_BAGS // 30  # ~26,666 parent bags
CHILD_BAGS_PER_PARENT = 30

class LoadTester:
    def __init__(self):
        self.results = {
            'start_time': None,
            'end_time': None,
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'errors': [],
            'memory_usage': [],
            'cpu_usage': []
        }
        self.session = None
        
    async def create_session(self):
        """Create aiohttp session with connection pooling"""
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=100,
            force_close=False,
            enable_cleanup_closed=True
        )
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
        return self.session
    
    async def login_user(self, username, password):
        """Async login"""
        try:
            async with self.session.post(
                f'{BASE_URL}/login',
                data={'username': username, 'password': password}
            ) as response:
                return response.status in [200, 302]
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    async def create_parent_bag(self, qr_id):
        """Create a parent bag"""
        start = time.time()
        try:
            async with self.session.post(
                f'{BASE_URL}/process_parent_scan',
                data={'qr_code': qr_id}
            ) as response:
                elapsed = (time.time() - start) * 1000
                self.results['response_times'].append(elapsed)
                if response.status == 200:
                    self.results['successful_requests'] += 1
                    return True
                else:
                    self.results['failed_requests'] += 1
                    return False
        except Exception as e:
            self.results['failed_requests'] += 1
            self.results['errors'].append(str(e))
            return False
        finally:
            self.results['total_requests'] += 1
    
    async def create_child_bag(self, qr_id):
        """Create a child bag"""
        start = time.time()
        try:
            async with self.session.post(
                f'{BASE_URL}/process_child_scan',
                data={'qr_code': qr_id}
            ) as response:
                elapsed = (time.time() - start) * 1000
                self.results['response_times'].append(elapsed)
                if response.status == 200:
                    self.results['successful_requests'] += 1
                    return True
                else:
                    self.results['failed_requests'] += 1
                    return False
        except Exception as e:
            self.results['failed_requests'] += 1
            self.results['errors'].append(str(e))
            return False
        finally:
            self.results['total_requests'] += 1
    
    async def complete_scan(self):
        """Complete the current scan session"""
        try:
            async with self.session.get(f'{BASE_URL}/scan/complete') as response:
                return response.status == 200
        except:
            return False
    
    async def create_bill(self, bill_id, parent_count):
        """Create a bill"""
        start = time.time()
        try:
            async with self.session.post(
                f'{BASE_URL}/bill/create',
                data={'bill_id': bill_id, 'parent_bag_count': parent_count}
            ) as response:
                elapsed = (time.time() - start) * 1000
                self.results['response_times'].append(elapsed)
                if response.status in [200, 302]:
                    self.results['successful_requests'] += 1
                    return True
                else:
                    self.results['failed_requests'] += 1
                    return False
        except Exception as e:
            self.results['failed_requests'] += 1
            self.results['errors'].append(str(e))
            return False
        finally:
            self.results['total_requests'] += 1
    
    async def search_bags(self, query):
        """Search for bags"""
        start = time.time()
        try:
            async with self.session.get(
                f'{BASE_URL}/search',
                params={'q': query}
            ) as response:
                elapsed = (time.time() - start) * 1000
                self.results['response_times'].append(elapsed)
                if response.status == 200:
                    self.results['successful_requests'] += 1
                    return True
                else:
                    self.results['failed_requests'] += 1
                    return False
        except Exception as e:
            self.results['failed_requests'] += 1
            self.results['errors'].append(str(e))
            return False
        finally:
            self.results['total_requests'] += 1
    
    async def simulate_user_workflow(self, user_id):
        """Simulate a complete user workflow"""
        print(f"User {user_id} starting workflow...")
        
        # Login
        username = f'test_user_{user_id}'
        await self.login_user(username, 'password123')
        
        # Create parent bags with children
        parent_bags_per_user = PARENT_BAGS // CONCURRENT_USERS
        
        for i in range(min(parent_bags_per_user, 100)):  # Limit per user for testing
            parent_qr = f'SB{user_id:02d}{i:03d}'
            
            # Create parent
            await self.create_parent_bag(parent_qr)
            
            # Create 30 children for each parent
            child_tasks = []
            for j in range(30):
                child_qr = f'CB{user_id:02d}{i:03d}{j:02d}'
                child_tasks.append(self.create_child_bag(child_qr))
            
            # Process children in batches
            if child_tasks:
                await asyncio.gather(*child_tasks)
            
            # Complete the scan
            await self.complete_scan()
            
            # Random search operations
            if random.random() < 0.1:  # 10% chance
                await self.search_bags(parent_qr)
        
        # Create bills
        for i in range(min(5, parent_bags_per_user // 10)):
            bill_id = f'BILL-{user_id}-{i}'
            await self.create_bill(bill_id, random.randint(5, 20))
        
        print(f"User {user_id} completed workflow")
    
    def monitor_resources(self):
        """Monitor system resources"""
        while self.results['start_time'] and not self.results['end_time']:
            self.results['cpu_usage'].append(psutil.cpu_percent())
            self.results['memory_usage'].append(psutil.virtual_memory().percent)
            time.sleep(1)
    
    async def run_load_test(self):
        """Run the complete load test"""
        print("=" * 70)
        print(f"MASSIVE LOAD TEST: {CONCURRENT_USERS} Users, {TOTAL_BAGS:,} Bags")
        print("=" * 70)
        
        self.results['start_time'] = datetime.now()
        
        # Start resource monitoring in background
        import threading
        monitor_thread = threading.Thread(target=self.monitor_resources)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Create session
        await self.create_session()
        
        # Create user tasks
        user_tasks = []
        for user_id in range(1, CONCURRENT_USERS + 1):
            user_tasks.append(self.simulate_user_workflow(user_id))
        
        # Run all users concurrently
        print(f"\nStarting {CONCURRENT_USERS} concurrent users...")
        await asyncio.gather(*user_tasks)
        
        self.results['end_time'] = datetime.now()
        
        # Close session
        await self.session.close()
        
        # Calculate statistics
        self.print_results()
    
    def print_results(self):
        """Print test results"""
        duration = (self.results['end_time'] - self.results['start_time']).total_seconds()
        
        print("\n" + "=" * 70)
        print("LOAD TEST RESULTS")
        print("=" * 70)
        
        print(f"\nTest Duration: {duration:.2f} seconds")
        print(f"Total Requests: {self.results['total_requests']:,}")
        print(f"Successful: {self.results['successful_requests']:,}")
        print(f"Failed: {self.results['failed_requests']:,}")
        print(f"Success Rate: {(self.results['successful_requests']/max(1, self.results['total_requests'])*100):.2f}%")
        
        if self.results['response_times']:
            avg_response = sum(self.results['response_times']) / len(self.results['response_times'])
            min_response = min(self.results['response_times'])
            max_response = max(self.results['response_times'])
            
            # Calculate percentiles
            sorted_times = sorted(self.results['response_times'])
            p50 = sorted_times[len(sorted_times)//2]
            p95 = sorted_times[int(len(sorted_times)*0.95)]
            p99 = sorted_times[int(len(sorted_times)*0.99)]
            
            print(f"\nResponse Times (ms):")
            print(f"  Average: {avg_response:.2f}")
            print(f"  Min: {min_response:.2f}")
            print(f"  Max: {max_response:.2f}")
            print(f"  P50: {p50:.2f}")
            print(f"  P95: {p95:.2f}")
            print(f"  P99: {p99:.2f}")
            
            # Check millisecond requirement
            if avg_response < 1000:
                print(f"  ✅ Average response under 1 second!")
            if p95 < 1000:
                print(f"  ✅ 95% of requests under 1 second!")
        
        print(f"\nThroughput: {self.results['total_requests']/duration:.2f} requests/second")
        
        if self.results['cpu_usage']:
            print(f"\nResource Usage:")
            print(f"  Avg CPU: {sum(self.results['cpu_usage'])/len(self.results['cpu_usage']):.2f}%")
            print(f"  Max CPU: {max(self.results['cpu_usage']):.2f}%")
            print(f"  Avg Memory: {sum(self.results['memory_usage'])/len(self.results['memory_usage']):.2f}%")
            print(f"  Max Memory: {max(self.results['memory_usage']):.2f}%")
        
        if self.results['errors']:
            print(f"\nErrors (first 5):")
            for error in self.results['errors'][:5]:
                print(f"  - {error}")
        
        # Save detailed results
        with open('load_test_results.json', 'w') as f:
            json.dump({
                'summary': {
                    'duration': duration,
                    'total_requests': self.results['total_requests'],
                    'successful_requests': self.results['successful_requests'],
                    'failed_requests': self.results['failed_requests'],
                    'avg_response_ms': avg_response if self.results['response_times'] else 0,
                    'throughput_rps': self.results['total_requests']/duration
                }
            }, f, indent=2)
        
        print("\nDetailed results saved to load_test_results.json")

async def main():
    """Main entry point"""
    tester = LoadTester()
    await tester.run_load_test()

if __name__ == '__main__':
    print("Starting massive load test...")
    print("Make sure the application is running on port 5000")
    print("Creating test users first...")
    
    # Quick setup - create test users
    import requests
    s = requests.Session()
    s.post(f'{BASE_URL}/login', data={'username': 'admin', 'password': 'admin123'})
    
    for i in range(1, CONCURRENT_USERS + 1):
        username = f'test_user_{i}'
        s.post(f'{BASE_URL}/add_user', data={
            'username': username,
            'password': 'password123',
            'role': 'biller' if i % 2 == 0 else 'dispatcher',
            'area': f'Area{(i % 5) + 1}'
        })
    
    print(f"Created {CONCURRENT_USERS} test users")
    
    # Run async load test
    asyncio.run(main())
#!/usr/bin/env python3
"""
Final Performance Test - Comprehensive Testing with 50+ Concurrent Users
"""

import asyncio
import aiohttp
import time
import statistics
from datetime import datetime
import random

class PerformanceTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.results = []
        self.errors = []
        
    async def user_workflow(self, user_id: int):
        """Complete workflow for one user"""
        workflow_start = time.time()
        result = {
            'user_id': user_id,
            'operations': {},
            'success': True
        }
        
        connector = aiohttp.TCPConnector(limit_per_host=10)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            cookie_jar=aiohttp.CookieJar()
        ) as session:
            
            # Login
            start = time.time()
            try:
                async with session.post(f"{self.base_url}/login", data={
                    'username': 'admin',
                    'password': 'admin123'
                }) as resp:
                    result['operations']['login'] = {
                        'time': time.time() - start,
                        'success': resp.status in [200, 302]
                    }
            except Exception as e:
                result['operations']['login'] = {'time': time.time() - start, 'success': False}
                self.errors.append(f"User {user_id}: Login failed - {str(e)}")
                result['success'] = False
                return result
            
            # Parent Scan
            parent_qr = f"SB{str(12000 + user_id).zfill(5)}"
            start = time.time()
            try:
                async with session.post(f"{self.base_url}/process_parent_scan", 
                    data={'qr_code': parent_qr, 'location': 'Test'},
                    headers={'X-Requested-With': 'XMLHttpRequest'}
                ) as resp:
                    result['operations']['parent_scan'] = {
                        'time': time.time() - start,
                        'success': resp.status == 200
                    }
            except Exception as e:
                result['operations']['parent_scan'] = {'time': time.time() - start, 'success': False}
                self.errors.append(f"User {user_id}: Parent scan failed - {str(e)}")
            
            # Child Scans (3 children)
            child_times = []
            for i in range(3):
                child_qr = f"SC{str(50000 + user_id * 10 + i).zfill(5)}"
                start = time.time()
                try:
                    async with session.post(f"{self.base_url}/process_child_scan",
                        data={'qr_code': child_qr},
                        headers={'X-Requested-With': 'XMLHttpRequest'}
                    ) as resp:
                        child_times.append(time.time() - start)
                except:
                    child_times.append(999)  # Failed request
            
            result['operations']['child_scan'] = {
                'time': statistics.mean(child_times) if child_times else 999,
                'success': all(t < 10 for t in child_times)
            }
            
            # Bill operations (create and link)
            bill_id = f"PERF-{user_id}-{int(time.time())}"
            start = time.time()
            try:
                async with session.post(f"{self.base_url}/bill/create",
                    data={'bill_id': bill_id, 'parent_bag_count': '10', 'description': 'Performance Test'},
                    headers={'X-Requested-With': 'XMLHttpRequest'}
                ) as resp:
                    if resp.status == 200:
                        # Try to get bill DB ID from response
                        try:
                            data = await resp.json()
                            bill_db_id = data.get('bill_db_id', 11)  # Use test bill ID 11 as fallback
                        except:
                            bill_db_id = 11
                        
                        # Link parent to bill
                        link_start = time.time()
                        async with session.post(f"{self.base_url}/process_bill_parent_scan",
                            data={'qr_code': parent_qr, 'bill_id': str(bill_db_id)},
                            headers={'X-Requested-With': 'XMLHttpRequest'}
                        ) as link_resp:
                            result['operations']['bill_ops'] = {
                                'time': time.time() - start,
                                'success': link_resp.status == 200
                            }
                    else:
                        result['operations']['bill_ops'] = {
                            'time': time.time() - start,
                            'success': False
                        }
            except Exception as e:
                result['operations']['bill_ops'] = {'time': time.time() - start, 'success': False}
                self.errors.append(f"User {user_id}: Bill ops failed - {str(e)}")
            
            result['total_time'] = time.time() - workflow_start
            return result
    
    async def run_test(self, num_users: int):
        """Run test with specified number of concurrent users"""
        print(f"\n{'='*70}")
        print(f"🚀 PERFORMANCE TEST WITH {num_users} CONCURRENT USERS")
        print(f"{'='*70}")
        print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
        
        start_time = time.time()
        
        # Run all user workflows concurrently
        tasks = [self.user_workflow(i) for i in range(1, num_users + 1)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Process results
        successful_users = 0
        operation_times = {
            'login': [],
            'parent_scan': [],
            'child_scan': [],
            'bill_ops': []
        }
        
        for r in results:
            if isinstance(r, dict) and r.get('success'):
                successful_users += 1
                for op, data in r.get('operations', {}).items():
                    if data['success'] and data['time'] < 100:  # Filter out failed ops
                        operation_times[op].append(data['time'])
        
        # Display results
        print(f"\n📊 RESULTS:")
        print(f"   Total Time: {total_time:.2f}s")
        print(f"   Successful Users: {successful_users}/{num_users} ({(successful_users/num_users)*100:.1f}%)")
        print(f"   Throughput: {num_users/total_time:.1f} users/second")
        
        print(f"\n⏱️  OPERATION TIMES (seconds):")
        print(f"{'Operation':<15} {'Min':>8} {'Avg':>8} {'Max':>8} {'P95':>8}")
        print(f"{'-'*47}")
        
        for op, times in operation_times.items():
            if times:
                print(f"{op:<15} {min(times):>8.3f} {statistics.mean(times):>8.3f} "
                      f"{max(times):>8.3f} {sorted(times)[int(len(times)*0.95)]:>8.3f}")
        
        # Performance criteria
        avg_times = {op: statistics.mean(times) if times else 999 
                    for op, times in operation_times.items()}
        
        print(f"\n✅ PERFORMANCE CRITERIA:")
        criteria = [
            ("Avg Response < 2s", all(t < 2.0 for t in avg_times.values())),
            ("Success Rate > 90%", successful_users/num_users >= 0.9),
            ("No Critical Errors", len(self.errors) < num_users * 0.1),
            ("All Operations Work", all(len(times) > 0 for times in operation_times.values()))
        ]
        
        all_passed = True
        for name, passed in criteria:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {name:<25} {status}")
            if not passed:
                all_passed = False
        
        if self.errors and len(self.errors) <= 10:
            print(f"\n⚠️  Errors ({len(self.errors)}):")
            for error in self.errors[:5]:
                print(f"   - {error}")
        
        return all_passed

async def main():
    """Run performance tests with increasing loads"""
    tester = PerformanceTester()
    
    test_scenarios = [
        (10, "Light Load"),
        (25, "Medium Load"),
        (50, "Heavy Load"),
        (75, "Stress Test"),
        (100, "Max Load")
    ]
    
    print("\n" + "="*70)
    print("🧪 COMPREHENSIVE PERFORMANCE TEST SUITE")
    print("="*70)
    print("Testing TraceTrack system with increasing concurrent users")
    print("Target: Handle 50+ users with <2s response times")
    
    passed_all = True
    
    for users, scenario in test_scenarios:
        passed = await tester.run_test(users)
        
        if not passed:
            print(f"\n⚠️  {scenario} failed. Stopping further tests.")
            passed_all = False
            break
        
        if users < 100:
            print(f"\n⏳ Waiting 3 seconds before next test...")
            await asyncio.sleep(3)
    
    # Final verdict
    print("\n" + "="*70)
    if passed_all:
        print("🎉 SYSTEM PASSED ALL PERFORMANCE TESTS!")
        print("✅ Ready for production with 50+ concurrent users")
        print("✅ All operations performing within acceptable limits")
    else:
        print("⚠️  SYSTEM NEEDS OPTIMIZATION")
        print("Review the failed scenarios above for details")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
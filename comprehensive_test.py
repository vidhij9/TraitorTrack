#!/usr/bin/env python3

"""
Comprehensive Test Suite for TraceTrack System
Tests all critical functionality with concurrent users and large data volumes
"""

import asyncio
import aiohttp
import time
import random
import json
from concurrent.futures import ThreadPoolExecutor
import threading

class TraceTrackTester:
    def __init__(self, base_url="http://localhost:5000", num_concurrent_users=50):
        self.base_url = base_url
        self.num_concurrent_users = num_concurrent_users
        self.test_results = {
            'login': {'success': 0, 'failed': 0},
            'parent_scan': {'success': 0, 'failed': 0},
            'child_scan': {'success': 0, 'failed': 0},
            'bill_create': {'success': 0, 'failed': 0},
            'bill_parent_link': {'success': 0, 'failed': 0},
            'performance': {'avg_response_time': 0, 'max_response_time': 0}
        }
        self.response_times = []
        self.lock = threading.Lock()
        
    def generate_test_qr_codes(self, count=100):
        """Generate test QR codes for testing"""
        parent_codes = [f"SB{str(i).zfill(5)}" for i in range(10000, 10000 + count)]
        child_codes = [f"SC{str(i).zfill(5)}" for i in range(20000, 20000 + count * 30)]
        return parent_codes, child_codes

    async def login_user(self, session, username, password):
        """Login a test user"""
        start_time = time.time()
        try:
            # Get login page first to get CSRF token
            async with session.get(f"{self.base_url}/login") as resp:
                if resp.status != 200:
                    return False, f"Login page error: {resp.status}"
                
                # Extract CSRF token
                text = await resp.text()
                csrf_token = None
                # Simple CSRF token extraction
                if 'csrf_token' in text:
                    import re
                    match = re.search(r'name="csrf_token".*?value="([^"]*)"', text)
                    if match:
                        csrf_token = match.group(1)
                
                # Login with credentials
                login_data = {
                    'username': username,
                    'password': password
                }
                if csrf_token:
                    login_data['csrf_token'] = csrf_token
                    
                async with session.post(f"{self.base_url}/login", data=login_data) as login_resp:
                    response_time = time.time() - start_time
                    self.response_times.append(response_time)
                    
                    # Check if login successful (should redirect or show dashboard)
                    if login_resp.status in [200, 302] and 'dashboard' in str(login_resp.url):
                        with self.lock:
                            self.test_results['login']['success'] += 1
                        return True, f"Login successful in {response_time:.3f}s"
                    else:
                        with self.lock:
                            self.test_results['login']['failed'] += 1
                        return False, f"Login failed: {login_resp.status}"
                        
        except Exception as e:
            with self.lock:
                self.test_results['login']['failed'] += 1
            return False, f"Login error: {str(e)}"

    async def test_parent_scan(self, session, qr_code):
        """Test parent bag scanning"""
        start_time = time.time()
        try:
            scan_data = {
                'qr_code': qr_code,
                'location': 'Test Location',
                'device_info': 'Test Device'
            }
            
            async with session.post(f"{self.base_url}/scan_parent", json=scan_data) as resp:
                response_time = time.time() - start_time
                self.response_times.append(response_time)
                
                if resp.status == 200:
                    result = await resp.json()
                    if result.get('success'):
                        with self.lock:
                            self.test_results['parent_scan']['success'] += 1
                        return True, f"Parent scan successful in {response_time:.3f}s"
                    else:
                        with self.lock:
                            self.test_results['parent_scan']['failed'] += 1
                        return False, f"Parent scan failed: {result.get('message', 'Unknown error')}"
                else:
                    with self.lock:
                        self.test_results['parent_scan']['failed'] += 1
                    return False, f"Parent scan HTTP error: {resp.status}"
                    
        except Exception as e:
            with self.lock:
                self.test_results['parent_scan']['failed'] += 1
            return False, f"Parent scan error: {str(e)}"

    async def test_child_scan(self, session, parent_qr, child_qr):
        """Test child bag scanning"""
        start_time = time.time()
        try:
            scan_data = {
                'qr_code': child_qr,
                'parent_qr': parent_qr
            }
            
            async with session.post(f"{self.base_url}/process_child_scan", json=scan_data) as resp:
                response_time = time.time() - start_time
                self.response_times.append(response_time)
                
                if resp.status == 200:
                    result = await resp.json()
                    if result.get('success'):
                        with self.lock:
                            self.test_results['child_scan']['success'] += 1
                        return True, f"Child scan successful in {response_time:.3f}s"
                    else:
                        with self.lock:
                            self.test_results['child_scan']['failed'] += 1
                        return False, f"Child scan failed: {result.get('message', 'Unknown error')}"
                else:
                    with self.lock:
                        self.test_results['child_scan']['failed'] += 1
                    return False, f"Child scan HTTP error: {resp.status}"
                    
        except Exception as e:
            with self.lock:
                self.test_results['child_scan']['failed'] += 1
            return False, f"Child scan error: {str(e)}"

    async def test_bill_operations(self, session, parent_qr):
        """Test bill creation and parent linking"""
        try:
            # Create bill
            start_time = time.time()
            bill_data = {
                'bill_id': f'BILL{random.randint(100000, 999999)}',
                'parent_bag_count': 10,
                'description': 'Test Bill'
            }
            
            async with session.post(f"{self.base_url}/bills", json=bill_data) as resp:
                response_time = time.time() - start_time
                self.response_times.append(response_time)
                
                if resp.status == 200:
                    with self.lock:
                        self.test_results['bill_create']['success'] += 1
                    
                    # Now test linking parent to bill
                    start_time = time.time()
                    link_data = {
                        'qr_code': parent_qr,
                        'bill_id': bill_data['bill_id']
                    }
                    
                    async with session.post(f"{self.base_url}/process_bill_parent_scan", json=link_data) as link_resp:
                        response_time = time.time() - start_time
                        self.response_times.append(response_time)
                        
                        if link_resp.status == 200:
                            result = await link_resp.json()
                            if result.get('success'):
                                with self.lock:
                                    self.test_results['bill_parent_link']['success'] += 1
                                return True, f"Bill operations successful"
                            else:
                                with self.lock:
                                    self.test_results['bill_parent_link']['failed'] += 1
                                return False, f"Bill linking failed: {result.get('message', 'Unknown error')}"
                        else:
                            with self.lock:
                                self.test_results['bill_parent_link']['failed'] += 1
                            return False, f"Bill linking HTTP error: {link_resp.status}"
                else:
                    with self.lock:
                        self.test_results['bill_create']['failed'] += 1
                    return False, f"Bill creation failed: {resp.status}"
                    
        except Exception as e:
            with self.lock:
                self.test_results['bill_create']['failed'] += 1
                self.test_results['bill_parent_link']['failed'] += 1
            return False, f"Bill operations error: {str(e)}"

    async def simulate_user_session(self, user_id, parent_codes, child_codes):
        """Simulate a complete user session"""
        connector = aiohttp.TCPConnector(limit_per_host=10)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout, 
                                       cookie_jar=aiohttp.CookieJar()) as session:
            
            print(f"🚀 User {user_id}: Starting session")
            
            # Login
            login_success, login_msg = await self.login_user(session, f"admin", "admin123")
            if not login_success:
                print(f"❌ User {user_id}: {login_msg}")
                return False
                
            print(f"✅ User {user_id}: {login_msg}")
            
            # Test parent scan
            parent_qr = random.choice(parent_codes)
            parent_success, parent_msg = await self.test_parent_scan(session, parent_qr)
            print(f"📱 User {user_id}: Parent scan - {parent_msg}")
            
            if parent_success:
                # Test child scans
                child_qrs = random.choices(child_codes, k=5)  # Scan 5 children
                for child_qr in child_qrs:
                    child_success, child_msg = await self.test_child_scan(session, parent_qr, child_qr)
                    if child_success:
                        print(f"👶 User {user_id}: Child scan - {child_msg}")
                    else:
                        print(f"❌ User {user_id}: Child scan failed - {child_msg}")
                
                # Test bill operations
                bill_success, bill_msg = await self.test_bill_operations(session, parent_qr)
                print(f"🧾 User {user_id}: Bill operations - {bill_msg}")
            
            print(f"✅ User {user_id}: Session completed")
            return True

    async def run_concurrent_test(self):
        """Run concurrent user simulation"""
        print(f"🧪 Starting comprehensive test with {self.num_concurrent_users} concurrent users...")
        
        # Generate test data
        parent_codes, child_codes = self.generate_test_qr_codes(200)
        print(f"📝 Generated {len(parent_codes)} parent codes and {len(child_codes)} child codes")
        
        # Start concurrent user sessions
        start_time = time.time()
        
        tasks = []
        for user_id in range(self.num_concurrent_users):
            task = self.simulate_user_session(user_id, parent_codes, child_codes)
            tasks.append(task)
        
        # Run all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Calculate performance metrics
        if self.response_times:
            avg_response_time = sum(self.response_times) / len(self.response_times)
            max_response_time = max(self.response_times)
            self.test_results['performance']['avg_response_time'] = avg_response_time
            self.test_results['performance']['max_response_time'] = max_response_time
        
        # Print results
        self.print_test_results(total_time)
        
        return self.test_results

    def print_test_results(self, total_time):
        """Print comprehensive test results"""
        print("\n" + "="*80)
        print("🎯 COMPREHENSIVE TEST RESULTS")
        print("="*80)
        
        print(f"⏱️  Total Test Time: {total_time:.2f} seconds")
        print(f"👥 Concurrent Users: {self.num_concurrent_users}")
        print()
        
        for test_name, results in self.test_results.items():
            if test_name == 'performance':
                continue
                
            total = results['success'] + results['failed']
            if total > 0:
                success_rate = (results['success'] / total) * 100
                status_icon = "✅" if success_rate >= 90 else "⚠️" if success_rate >= 70 else "❌"
                print(f"{status_icon} {test_name.upper():<20} Success: {results['success']:>4} Failed: {results['failed']:>4} Rate: {success_rate:>6.1f}%")
        
        print()
        print("📊 PERFORMANCE METRICS:")
        perf = self.test_results['performance']
        print(f"   Average Response Time: {perf['avg_response_time']:.3f}s")
        print(f"   Maximum Response Time: {perf['max_response_time']:.3f}s")
        print(f"   Total API Calls: {len(self.response_times)}")
        
        print("\n🎯 TEST CRITERIA:")
        print("   ✅ Response Time < 2 seconds: ", 
              "PASS" if perf['avg_response_time'] < 2.0 else "FAIL")
        print("   ✅ Success Rate > 90%: ", 
              "PASS" if all((r['success']/(r['success']+r['failed'])) >= 0.9 
                          for r in self.test_results.values() 
                          if isinstance(r, dict) and 'success' in r and (r['success']+r['failed']) > 0) 
              else "FAIL")
        print("   ✅ No Critical Errors: ", 
              "PASS" if self.test_results['login']['failed'] == 0 else "FAIL")
        
        print("="*80)

if __name__ == "__main__":
    # Test with different user loads
    test_loads = [10, 25, 50]  # Start with smaller loads first
    
    for load in test_loads:
        print(f"\n🚀 Testing with {load} concurrent users...")
        tester = TraceTrackTester(num_concurrent_users=load)
        
        try:
            results = asyncio.run(tester.run_concurrent_test())
            
            # Check if system handled the load well
            avg_time = results['performance']['avg_response_time']
            if avg_time < 2.0:  # Target: under 2 seconds
                print(f"✅ System handled {load} users successfully (avg: {avg_time:.3f}s)")
            else:
                print(f"⚠️ System struggled with {load} users (avg: {avg_time:.3f}s)")
                break  # Don't test higher loads if this fails
                
        except KeyboardInterrupt:
            print("\n⏹️ Test interrupted by user")
            break
        except Exception as e:
            print(f"❌ Test failed with error: {str(e)}")
            break
        
        # Wait between tests
        print("⏳ Waiting 10 seconds before next test...")
        time.sleep(10)
    
    print("\n🏁 All tests completed!")
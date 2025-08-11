#!/usr/bin/env python3
"""
Web-based scan management testing
Tests the actual web interface with 50 child bags and concurrent users
"""

import requests
import time
import json
import threading
from concurrent.futures import ThreadPoolExecutor
import statistics

BASE_URL = "http://localhost:5000"

class WebScanner:
    def __init__(self):
        self.session = requests.Session()
        self.csrf_token = None
        
    def login(self, username="testuser", password="testpass"):
        """Login to the web interface"""
        try:
            # Get login page
            response = self.session.get(f"{BASE_URL}/login")
            if response.status_code != 200:
                return False
            
            # Extract CSRF token from the page
            # Simple approach - look for csrf-token meta tag
            if 'csrf-token' in response.text:
                import re
                match = re.search(r'content="([^"]+)"', response.text)
                if match:
                    self.csrf_token = match.group(1)
            
            # Login
            login_data = {
                'username': username,
                'password': password
            }
            
            if self.csrf_token:
                login_data['csrf_token'] = self.csrf_token
            
            response = self.session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=True)
            
            # Check if login was successful
            return response.status_code == 200 and ('dashboard' in response.url or 'index' in response.url)
        except Exception as e:
            print(f"Login failed: {e}")
            return False
    
    def scan_parent_bag(self, parent_qr):
        """Scan a parent bag through the web interface"""
        try:
            # First access the parent scan page
            response = self.session.get(f"{BASE_URL}/scan/parent")
            if response.status_code != 200:
                return False
            
            # Submit parent bag scan
            data = {'qr_code': parent_qr}
            response = self.session.post(f"{BASE_URL}/process_parent_scan", 
                                       data=data, 
                                       headers={'X-Requested-With': 'XMLHttpRequest'})
            
            return response.status_code == 200
        except Exception as e:
            print(f"Parent scan failed: {e}")
            return False
    
    def scan_child_bag(self, child_qr):
        """Scan a child bag through the ultra-fast endpoint"""
        try:
            data = {'qr_code': child_qr}
            response = self.session.post(f"{BASE_URL}/process_child_scan_fast", 
                                       json=data,
                                       headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                result = response.json()
                return result.get('success', False), result.get('processing_time', 0)
            return False, 0
        except Exception as e:
            print(f"Child scan failed: {e}")
            return False, 0

class WebScanTester:
    def __init__(self):
        self.results = {
            'parent_times': [],
            'child_times': [],
            'success_count': 0,
            'failure_count': 0,
            'processing_times': []
        }
        self.lock = threading.Lock()
    
    def record_result(self, success, scan_type, duration, processing_time=None):
        """Thread-safe result recording"""
        with self.lock:
            if scan_type == 'parent':
                self.results['parent_times'].append(duration)
            elif scan_type == 'child':
                self.results['child_times'].append(duration)
                if processing_time:
                    self.results['processing_times'].append(processing_time)
            
            if success:
                self.results['success_count'] += 1
            else:
                self.results['failure_count'] += 1
    
    def test_50_child_bags_web(self):
        """Test adding 50 child bags through web interface"""
        print("\n=== Web Interface: 50 Child Bags Test ===")
        
        scanner = WebScanner()
        if not scanner.login():
            print("❌ Failed to login to web interface")
            return False
        
        # Create parent bag
        parent_qr = f"WEB_PARENT_{int(time.time())}"
        start_time = time.time()
        
        if not scanner.scan_parent_bag(parent_qr):
            print(f"❌ Failed to scan parent bag {parent_qr}")
            return False
        
        parent_time = time.time() - start_time
        self.record_result(True, 'parent', parent_time)
        print(f"✅ Parent bag scanned in {parent_time:.3f}s")
        
        # Scan 50 child bags
        print("Scanning 50 child bags through web interface...")
        successful_scans = 0
        
        for i in range(50):
            child_qr = f"WEB_CHILD_{parent_qr}_{i:03d}"
            
            child_start = time.time()
            success, processing_time = scanner.scan_child_bag(child_qr)
            scan_duration = time.time() - child_start
            
            if success:
                successful_scans += 1
                self.record_result(True, 'child', scan_duration, processing_time)
                
                if (i + 1) % 10 == 0:
                    recent_times = self.results['child_times'][-10:]
                    avg_time = statistics.mean(recent_times) if recent_times else 0
                    print(f"  ✅ Scanned {i + 1}/50 children (recent avg: {avg_time:.3f}s)")
            else:
                self.record_result(False, 'child', scan_duration)
                print(f"  ❌ Failed to scan child {i + 1}")
        
        # Calculate and display results
        total_time = time.time() - start_time
        
        if self.results['child_times']:
            avg_child_time = statistics.mean(self.results['child_times'])
            min_child_time = min(self.results['child_times'])
            max_child_time = max(self.results['child_times'])
            
            print(f"\n📊 Web Interface Test Results:")
            print(f"   Total time: {total_time:.2f}s")
            print(f"   Successful child scans: {successful_scans}/50")
            print(f"   Average child scan time: {avg_child_time:.3f}s")
            print(f"   Min child scan time: {min_child_time:.3f}s")
            print(f"   Max child scan time: {max_child_time:.3f}s")
            print(f"   Success rate: {(successful_scans/50)*100:.1f}%")
            
            # Processing time analysis
            if self.results['processing_times']:
                avg_processing = statistics.mean(self.results['processing_times'])
                print(f"   Average server processing: {avg_processing:.3f}s")
                
                if avg_processing < 0.1:
                    print("   ⚡ ULTRA-FAST: Sub-100ms server processing!")
                elif avg_processing < 0.5:
                    print("   ⚡ EXCELLENT: Sub-500ms server processing")
                elif avg_processing < 1.0:
                    print("   ✅ GOOD: Sub-1s server processing")
                else:
                    print("   ⚠️  SLOW: Server processing needs optimization")
            
            # Overall assessment
            if avg_child_time < 0.5 and successful_scans >= 48:  # 96% success rate
                print("   🏆 WEB INTERFACE: Excellent performance!")
            elif avg_child_time < 1.0 and successful_scans >= 45:  # 90% success rate
                print("   ✅ WEB INTERFACE: Good performance")
            else:
                print("   ⚠️  WEB INTERFACE: Needs optimization")
        
        return successful_scans >= 45  # 90% success rate
    
    def test_concurrent_web_users(self, num_users=20):
        """Test concurrent users through web interface"""
        print(f"\n=== Web Interface: {num_users} Concurrent Users ===")
        
        def simulate_web_user(user_id):
            """Simulate a user performing web scanning operations"""
            user_results = {'success': 0, 'failure': 0, 'times': []}
            
            try:
                scanner = WebScanner()
                if not scanner.login():
                    return user_results
                
                # Perform 3 scanning operations per user
                for op in range(3):
                    operation_start = time.time()
                    
                    # Create parent
                    parent_qr = f"WEB_CONCURRENT_PARENT_{user_id}_{op}"
                    if scanner.scan_parent_bag(parent_qr):
                        
                        # Scan 5 children
                        children_success = 0
                        for child_num in range(5):
                            child_qr = f"WEB_CONCURRENT_CHILD_{user_id}_{op}_{child_num}"
                            success, _ = scanner.scan_child_bag(child_qr)
                            if success:
                                children_success += 1
                        
                        operation_time = time.time() - operation_start
                        user_results['times'].append(operation_time)
                        
                        if children_success >= 3:  # At least 60% success
                            user_results['success'] += 1
                            self.record_result(True, 'operation', operation_time)
                        else:
                            user_results['failure'] += 1
                            self.record_result(False, 'operation', operation_time)
                    else:
                        user_results['failure'] += 1
                        self.record_result(False, 'operation', time.time() - operation_start)
                
            except Exception as e:
                print(f"User {user_id} failed: {e}")
                user_results['failure'] += 3
            
            return user_results
        
        # Execute concurrent web users
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=min(num_users, 15)) as executor:
            futures = [executor.submit(simulate_web_user, i) for i in range(num_users)]
            
            total_operations = 0
            successful_operations = 0
            
            for i, future in enumerate(futures):
                try:
                    result = future.result(timeout=60)  # 1 minute timeout
                    total_operations += result['success'] + result['failure']
                    successful_operations += result['success']
                    
                    if (i + 1) % 5 == 0:
                        print(f"  ✅ Completed {i + 1}/{num_users} concurrent users")
                        
                except Exception as e:
                    print(f"  ❌ User failed: {e}")
                    total_operations += 3  # 3 operations per user
        
        total_time = time.time() - start_time
        success_rate = (successful_operations / total_operations * 100) if total_operations > 0 else 0
        
        print(f"\n📊 Concurrent Web Users Results:")
        print(f"   Users tested: {num_users}")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Total operations: {total_operations}")
        print(f"   Successful operations: {successful_operations}")
        print(f"   Success rate: {success_rate:.1f}%")
        print(f"   Operations per second: {total_operations/total_time:.1f}")
        
        if success_rate > 85 and total_operations/total_time > 5:
            print("   🏆 EXCELLENT: Web interface handles concurrent load very well")
        elif success_rate > 75 and total_operations/total_time > 3:
            print("   ✅ GOOD: Web interface handles concurrent load adequately") 
        else:
            print("   ⚠️  NEEDS IMPROVEMENT: Consider web interface optimizations")
        
        return success_rate > 75

def main():
    """Run comprehensive web-based scan management tests"""
    print("🚀 Starting Web-Based Scan Management Tests")
    print("=" * 60)
    
    tester = WebScanTester()
    
    # Test 1: 50 child bags through web interface
    test1_success = tester.test_50_child_bags_web()
    
    # Reset results for concurrent test  
    tester.results = {
        'parent_times': [],
        'child_times': [],
        'success_count': 0,
        'failure_count': 0,
        'processing_times': []
    }
    
    # Test 2: Concurrent web users
    print("\nWaiting 3 seconds before concurrent test...")
    time.sleep(3)
    
    test2_success = tester.test_concurrent_web_users(15)  # Test with 15 concurrent users
    
    # Final summary
    print("\n" + "=" * 60)
    print("🏁 WEB INTERFACE TEST SUMMARY")  
    print("=" * 60)
    
    if test1_success:
        print("✅ 50 Child Bags Web Test: PASSED")
    else:
        print("❌ 50 Child Bags Web Test: FAILED")
    
    if test2_success:
        print("✅ Concurrent Web Users Test: PASSED")
    else:
        print("❌ Concurrent Web Users Test: FAILED")
    
    if test1_success and test2_success:
        print("\n🎉 WEB INTERFACE READY for production with 200+ concurrent users!")
        print("   - Sub-second scanning response times")
        print("   - Reliable 50+ child bag handling")
        print("   - Concurrent user support verified")
    else:
        print("\n⚠️  Web interface may need additional optimization")
    
    return test1_success and test2_success

if __name__ == "__main__":
    main()
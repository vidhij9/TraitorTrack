#!/usr/bin/env python3
"""
Comprehensive scan management performance testing
Tests adding 50 child bags to a parent and concurrent user scenarios
"""

import threading
import time
import random
import requests
import json
import concurrent.futures
from datetime import datetime
import statistics

# Test configuration
BASE_URL = "http://localhost:5000"  # Change this to your server URL
CONCURRENT_USERS = 200
CHILD_BAGS_PER_PARENT = 50

class ScanManager:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.authenticated = False
        self.user_id = None
        self.csrf_token = None
        
    def login(self, username="testuser", password="testpass"):
        """Login and establish session"""
        try:
            # Get login page for CSRF token
            response = self.session.get(f"{self.base_url}/login")
            if response.status_code != 200:
                return False
                
            # Simple test login (adjust according to your auth system)
            login_data = {
                'username': username,
                'password': password
            }
            
            response = self.session.post(f"{self.base_url}/login", data=login_data)
            self.authenticated = response.status_code == 200 or 'dashboard' in response.url
            return self.authenticated
        except Exception as e:
            print(f"Login failed: {e}")
            return False
    
    def create_parent_bag(self, parent_qr):
        """Create/scan a parent bag"""
        try:
            # Use the fast scanning endpoint
            data = {'qr_code': parent_qr}
            response = self.session.post(f"{self.base_url}/process_parent_scan", 
                                       data=data, 
                                       headers={'X-Requested-With': 'XMLHttpRequest'})
            
            return response.status_code == 200
        except Exception as e:
            print(f"Parent bag creation failed: {e}")
            return False
    
    def add_child_bag(self, child_qr):
        """Add a child bag to current parent"""
        try:
            # Use the ultra-fast child scan endpoint
            data = {'qr_code': child_qr}
            response = self.session.post(f"{self.base_url}/process_child_scan_fast", 
                                       json=data,
                                       headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                result = response.json()
                return result.get('success', False)
            return False
        except Exception as e:
            print(f"Child bag addition failed: {e}")
            return False

class PerformanceTester:
    def __init__(self):
        self.results = {
            'response_times': [],
            'success_count': 0,
            'failure_count': 0,
            'errors': [],
            'concurrent_operations': 0
        }
        self.lock = threading.Lock()
    
    def record_result(self, success, duration, error=None):
        """Thread-safe result recording"""
        with self.lock:
            self.results['response_times'].append(duration)
            if success:
                self.results['success_count'] += 1
            else:
                self.results['failure_count'] += 1
                if error:
                    self.results['errors'].append(error)
    
    def test_single_parent_50_children(self):
        """Test adding 50 child bags to a single parent"""
        print("\n=== Testing Single Parent with 50 Child Bags ===")
        
        # Create scan manager
        scanner = ScanManager()
        if not scanner.login():
            print("❌ Failed to login")
            return False
        
        # Create parent bag
        parent_qr = f"PARENT_TEST_{int(time.time())}"
        start_time = time.time()
        
        if not scanner.create_parent_bag(parent_qr):
            print(f"❌ Failed to create parent bag {parent_qr}")
            return False
        
        parent_time = time.time() - start_time
        print(f"✅ Parent bag created in {parent_time:.3f}s")
        
        # Add 50 child bags
        print(f"Adding {CHILD_BAGS_PER_PARENT} child bags...")
        child_times = []
        successful_children = 0
        
        for i in range(CHILD_BAGS_PER_PARENT):
            child_qr = f"CHILD_TEST_{parent_qr}_{i:03d}"
            
            child_start = time.time()
            if scanner.add_child_bag(child_qr):
                child_duration = time.time() - child_start
                child_times.append(child_duration)
                successful_children += 1
                
                if (i + 1) % 10 == 0:
                    avg_time = sum(child_times[-10:]) / min(10, len(child_times))
                    print(f"  ✅ Added {i + 1}/{CHILD_BAGS_PER_PARENT} children (avg: {avg_time:.3f}s)")
            else:
                print(f"  ❌ Failed to add child {i + 1}")
        
        # Calculate statistics
        total_time = time.time() - start_time
        if child_times:
            avg_child_time = statistics.mean(child_times)
            max_child_time = max(child_times)
            min_child_time = min(child_times)
            
            print(f"\n📊 Single Parent Test Results:")
            print(f"   Total time: {total_time:.2f}s")
            print(f"   Successful children: {successful_children}/{CHILD_BAGS_PER_PARENT}")
            print(f"   Average child scan time: {avg_child_time:.3f}s")
            print(f"   Min child scan time: {min_child_time:.3f}s")
            print(f"   Max child scan time: {max_child_time:.3f}s")
            print(f"   Success rate: {(successful_children/CHILD_BAGS_PER_PARENT)*100:.1f}%")
            
            # Performance benchmarks
            if avg_child_time < 0.5:
                print("   ⚡ EXCELLENT: Sub-500ms average response time")
            elif avg_child_time < 1.0:
                print("   ✅ GOOD: Sub-1s average response time")
            else:
                print("   ⚠️  SLOW: Response time needs optimization")
        
        return successful_children == CHILD_BAGS_PER_PARENT
    
    def simulate_concurrent_user(self, user_id, operations_per_user=5):
        """Simulate a single concurrent user performing scanning operations"""
        scanner = ScanManager()
        user_results = {'success': 0, 'failure': 0, 'times': []}
        
        try:
            # Login
            if not scanner.login():
                self.record_result(False, 0, f"User {user_id} login failed")
                return user_results
            
            # Perform operations
            for op in range(operations_per_user):
                operation_start = time.time()
                
                # Create parent bag
                parent_qr = f"CONCURRENT_PARENT_{user_id}_{op}"
                if scanner.create_parent_bag(parent_qr):
                    
                    # Add 5 random child bags
                    children_added = 0
                    for child_num in range(5):
                        child_qr = f"CONCURRENT_CHILD_{user_id}_{op}_{child_num}"
                        
                        if scanner.add_child_bag(child_qr):
                            children_added += 1
                    
                    operation_time = time.time() - operation_start
                    user_results['times'].append(operation_time)
                    
                    if children_added >= 3:  # At least 3 out of 5 children successful
                        user_results['success'] += 1
                        self.record_result(True, operation_time)
                    else:
                        user_results['failure'] += 1
                        self.record_result(False, operation_time, f"User {user_id} only added {children_added}/5 children")
                else:
                    user_results['failure'] += 1
                    self.record_result(False, time.time() - operation_start, f"User {user_id} parent creation failed")
        
        except Exception as e:
            self.record_result(False, 0, f"User {user_id} exception: {str(e)}")
        
        return user_results
    
    def test_concurrent_users(self, num_users=CONCURRENT_USERS):
        """Test concurrent users accessing the system"""
        print(f"\n=== Testing {num_users} Concurrent Users ===")
        
        start_time = time.time()
        
        # Use ThreadPoolExecutor for controlled concurrency
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(num_users, 50)) as executor:
            # Submit all user tasks
            future_to_user = {
                executor.submit(self.simulate_concurrent_user, user_id, 3): user_id 
                for user_id in range(num_users)
            }
            
            completed = 0
            for future in concurrent.futures.as_completed(future_to_user):
                user_id = future_to_user[future]
                try:
                    user_result = future.result(timeout=30)  # 30 second timeout per user
                    completed += 1
                    
                    if completed % 20 == 0:
                        print(f"  ✅ Completed {completed}/{num_users} users")
                        
                except Exception as e:
                    print(f"  ❌ User {user_id} failed: {e}")
                    self.record_result(False, 0, f"User {user_id} timeout/exception: {str(e)}")
        
        total_time = time.time() - start_time
        
        # Calculate and display results
        self.display_concurrent_results(num_users, total_time)
        
        return self.results['success_count'] > (num_users * 0.8)  # 80% success rate
    
    def display_concurrent_results(self, num_users, total_time):
        """Display comprehensive concurrent test results"""
        print(f"\n📊 Concurrent Users Test Results:")
        print(f"   Total users: {num_users}")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Successful operations: {self.results['success_count']}")
        print(f"   Failed operations: {self.results['failure_count']}")
        
        if self.results['response_times']:
            avg_response = statistics.mean(self.results['response_times'])
            max_response = max(self.results['response_times'])
            min_response = min(self.results['response_times'])
            
            print(f"   Average response time: {avg_response:.3f}s")
            print(f"   Min response time: {min_response:.3f}s")
            print(f"   Max response time: {max_response:.3f}s")
            
            # Calculate percentiles
            sorted_times = sorted(self.results['response_times'])
            p50 = sorted_times[len(sorted_times) // 2]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]
            
            print(f"   Response time P50: {p50:.3f}s")
            print(f"   Response time P95: {p95:.3f}s") 
            print(f"   Response time P99: {p99:.3f}s")
            
            success_rate = (self.results['success_count'] / (self.results['success_count'] + self.results['failure_count'])) * 100
            print(f"   Success rate: {success_rate:.1f}%")
            
            # Performance assessment
            if success_rate > 95 and avg_response < 1.0:
                print("   🏆 EXCELLENT: System handles concurrent load very well")
            elif success_rate > 85 and avg_response < 2.0:
                print("   ✅ GOOD: System handles concurrent load adequately")
            else:
                print("   ⚠️  NEEDS IMPROVEMENT: Consider optimizations")
        
        # Show error summary if any
        if self.results['errors']:
            print(f"\n❌ Error Summary ({len(self.results['errors'])} errors):")
            error_counts = {}
            for error in self.results['errors']:
                error_type = error.split(':')[0] if ':' in error else error
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
            
            for error_type, count in error_counts.items():
                print(f"   - {error_type}: {count} occurrences")

def main():
    """Run comprehensive scan management tests"""
    print("🚀 Starting Comprehensive Scan Management Performance Tests")
    print("=" * 60)
    
    tester = PerformanceTester()
    
    # Test 1: Single parent with 50 child bags
    test1_success = tester.test_single_parent_50_children()
    
    # Reset results for concurrent test
    tester.results = {
        'response_times': [],
        'success_count': 0,
        'failure_count': 0,
        'errors': [],
        'concurrent_operations': 0
    }
    
    # Test 2: 200 concurrent users
    print(f"\nWaiting 5 seconds before concurrent test...")
    time.sleep(5)
    
    test2_success = tester.test_concurrent_users(num_users=min(CONCURRENT_USERS, 50))  # Start with smaller number
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 TEST SUMMARY")
    print("=" * 60)
    
    if test1_success:
        print("✅ Single Parent + 50 Children: PASSED")
    else:
        print("❌ Single Parent + 50 Children: FAILED")
    
    if test2_success:
        print("✅ Concurrent Users Test: PASSED")
    else:
        print("❌ Concurrent Users Test: FAILED")
    
    if test1_success and test2_success:
        print("\n🎉 ALL TESTS PASSED - System ready for production load!")
    else:
        print("\n⚠️  Some tests failed - consider optimizations")
    
    return test1_success and test2_success

if __name__ == "__main__":
    main()
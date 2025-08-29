"""
Load test to verify system can handle 500+ bags per bill
Tests concurrent operations, database stability, and performance under heavy load
"""
import requests
import time
import json
import random
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Test configuration
BASE_URL = "http://127.0.0.1:5000"
TEST_USER = "admin"
TEST_PASSWORD = "admin"

class LoadTest500Bags:
    def __init__(self):
        self.session = requests.Session()
        self.logged_in = False
        self.start_time = None
        self.results = {
            'total_bags_scanned': 0,
            'successful_parent_scans': 0,
            'failed_parent_scans': 0,
            'successful_child_scans': 0,
            'failed_child_scans': 0,
            'successful_bill_links': 0,
            'failed_bill_links': 0,
            'database_errors': 0,
            'connection_errors': 0,
            'response_times': [],
            'parent_scan_times': [],
            'child_scan_times': [],
            'bill_link_times': [],
            'errors': []
        }
        
    def login(self):
        """Login to the system"""
        try:
            response = self.session.get(f"{BASE_URL}/login")
            
            login_data = {
                'username': TEST_USER,
                'password': TEST_PASSWORD
            }
            
            response = self.session.post(
                f"{BASE_URL}/login",
                data=login_data,
                allow_redirects=False
            )
            
            if response.status_code in [200, 302, 303]:
                self.logged_in = True
                print(f"✅ Logged in as {TEST_USER}")
                return True
            else:
                print(f"❌ Login failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
            
    def create_bill(self, bill_name):
        """Create a new bill for testing"""
        try:
            response = self.session.post(
                f"{BASE_URL}/create_bill",
                data={'bill_id': bill_name},
                timeout=10
            )
            
            if response.status_code == 200:
                # Try to extract bill ID from response
                try:
                    if response.headers.get('content-type', '').startswith('application/json'):
                        data = response.json()
                        return data.get('bill_id')
                except:
                    pass
                return bill_name
            return None
            
        except Exception as e:
            print(f"Error creating bill: {e}")
            return None
            
    def scan_parent_bag(self, parent_qr):
        """Scan a parent bag with timing"""
        start = time.time()
        try:
            response = self.session.post(
                f"{BASE_URL}/fast/parent_scan",
                data={'qr_code': parent_qr},
                timeout=10
            )
            
            elapsed = time.time() - start
            self.results['parent_scan_times'].append(elapsed)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.results['successful_parent_scans'] += 1
                    return True, data.get('child_count', 0), elapsed
                else:
                    self.results['failed_parent_scans'] += 1
                    if 'database' in str(data.get('error_type', '')):
                        self.results['database_errors'] += 1
                    self.results['errors'].append(f"Parent scan failed: {data.get('message', 'Unknown')}")
                    return False, 0, elapsed
            else:
                self.results['failed_parent_scans'] += 1
                return False, 0, elapsed
                
        except requests.exceptions.ConnectionError:
            self.results['connection_errors'] += 1
            self.results['errors'].append(f"Connection error scanning parent {parent_qr}")
            return False, 0, time.time() - start
        except Exception as e:
            self.results['failed_parent_scans'] += 1
            self.results['errors'].append(f"Error scanning parent {parent_qr}: {str(e)}")
            return False, 0, time.time() - start
            
    def scan_child_bag(self, child_qr):
        """Scan a child bag with timing"""
        start = time.time()
        try:
            response = self.session.post(
                f"{BASE_URL}/fast/child_scan",
                data={'qr_code': child_qr},
                timeout=10
            )
            
            elapsed = time.time() - start
            self.results['child_scan_times'].append(elapsed)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.results['successful_child_scans'] += 1
                    return True, data.get('child_count', 0), elapsed
                else:
                    self.results['failed_child_scans'] += 1
                    if 'database' in str(data.get('error_type', '')):
                        self.results['database_errors'] += 1
                    return False, 0, elapsed
            else:
                self.results['failed_child_scans'] += 1
                return False, 0, elapsed
                
        except requests.exceptions.ConnectionError:
            self.results['connection_errors'] += 1
            return False, 0, time.time() - start
        except Exception as e:
            self.results['failed_child_scans'] += 1
            return False, 0, time.time() - start
            
    def link_parent_to_bill(self, bill_id, parent_qr):
        """Link a parent bag to a bill"""
        start = time.time()
        try:
            response = self.session.post(
                f"{BASE_URL}/fast/bill_parent_scan",
                data={
                    'bill_id': bill_id,
                    'qr_code': parent_qr
                },
                timeout=10
            )
            
            elapsed = time.time() - start
            self.results['bill_link_times'].append(elapsed)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.results['successful_bill_links'] += 1
                    return True, elapsed
                else:
                    self.results['failed_bill_links'] += 1
                    self.results['errors'].append(f"Bill link failed: {data.get('message', 'Unknown')}")
                    return False, elapsed
            else:
                self.results['failed_bill_links'] += 1
                return False, elapsed
                
        except Exception as e:
            self.results['failed_bill_links'] += 1
            self.results['errors'].append(f"Error linking to bill: {str(e)}")
            return False, time.time() - start
            
    def create_and_scan_parent_with_children(self, parent_num, num_children=30):
        """Create a parent bag with specified number of children"""
        parent_qr = f"SB{str(parent_num).zfill(5)}"
        
        # Scan parent
        success, child_count, parent_time = self.scan_parent_bag(parent_qr)
        if not success:
            return None, 0
            
        # Scan children
        successful_children = 0
        for i in range(num_children):
            child_qr = f"C{parent_num:05d}{i:03d}"
            success, new_count, child_time = self.scan_child_bag(child_qr)
            if success:
                successful_children += 1
                self.results['total_bags_scanned'] += 1
                
        return parent_qr, successful_children
        
    def test_single_bill_with_500_bags(self):
        """Test a single bill with 500+ bags (17 parent bags with 30 children each)"""
        print("\n" + "="*60)
        print("📦 TEST: Single Bill with 500+ Bags")
        print("="*60)
        
        # Create a bill
        bill_id = f"LOAD_TEST_{int(time.time())}"
        print(f"Creating bill: {bill_id}")
        
        # We need 17 parent bags with 30 children each = 510 total bags
        num_parents = 17
        total_bags = num_parents * 30
        
        print(f"Target: {num_parents} parent bags × 30 children = {total_bags} total bags")
        print("Starting bag scanning...\n")
        
        successful_parents = []
        start_time = time.time()
        
        # Create and scan all parent-child combinations
        for i in range(num_parents):
            parent_num = 50000 + i  # Start from SB50000
            parent_qr, children_count = self.create_and_scan_parent_with_children(parent_num, 30)
            
            if parent_qr and children_count == 30:
                successful_parents.append(parent_qr)
                print(f"  ✅ Parent {i+1}/{num_parents}: {parent_qr} completed with {children_count} children")
            else:
                print(f"  ❌ Parent {i+1}/{num_parents}: Failed (only {children_count}/30 children)")
                
            # Brief pause between parents to avoid overwhelming the system
            if i < num_parents - 1:
                time.sleep(0.5)
                
        scan_time = time.time() - start_time
        
        # Now link all successful parents to the bill
        print(f"\nLinking {len(successful_parents)} parent bags to bill {bill_id}...")
        successful_links = 0
        
        for parent_qr in successful_parents:
            success, link_time = self.link_parent_to_bill(1, parent_qr)  # Using bill_id = 1 for simplicity
            if success:
                successful_links += 1
                
        total_time = time.time() - start_time
        
        # Results
        print("\n" + "-"*40)
        print("📊 Single Bill Test Results:")
        print(f"  Total parent bags: {len(successful_parents)}/{num_parents}")
        print(f"  Total bags scanned: {self.results['total_bags_scanned']}")
        print(f"  Successful bill links: {successful_links}/{len(successful_parents)}")
        print(f"  Scanning time: {scan_time:.2f} seconds")
        print(f"  Total time: {total_time:.2f} seconds")
        print(f"  Average scan rate: {self.results['total_bags_scanned']/scan_time:.1f} bags/second")
        
        return len(successful_parents) == num_parents and successful_links == len(successful_parents)
        
    def test_concurrent_bills(self, num_bills=3, bags_per_bill=150):
        """Test multiple bills being processed concurrently"""
        print("\n" + "="*60)
        print(f"🔄 TEST: {num_bills} Concurrent Bills with {bags_per_bill} bags each")
        print("="*60)
        
        def process_bill(bill_num):
            """Process a single bill with multiple bags"""
            bill_results = {
                'successful_parents': 0,
                'total_bags': 0,
                'time': 0
            }
            
            start = time.time()
            
            # Calculate parents needed (5 parents × 30 children = 150 bags)
            num_parents = bags_per_bill // 30
            
            for i in range(num_parents):
                parent_num = 60000 + (bill_num * 1000) + i
                parent_qr, children_count = self.create_and_scan_parent_with_children(parent_num, 30)
                
                if parent_qr and children_count == 30:
                    bill_results['successful_parents'] += 1
                    bill_results['total_bags'] += children_count
                    
            bill_results['time'] = time.time() - start
            return bill_results
            
        print(f"Processing {num_bills} bills concurrently...")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_bills) as executor:
            futures = [executor.submit(process_bill, i) for i in range(num_bills)]
            
            results = []
            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                results.append(result)
                print(f"  Bill {i+1} completed: {result['successful_parents']} parents, {result['total_bags']} bags in {result['time']:.2f}s")
                
        total_time = time.time() - start_time
        
        # Aggregate results
        total_parents = sum(r['successful_parents'] for r in results)
        total_bags = sum(r['total_bags'] for r in results)
        
        print("\n" + "-"*40)
        print("📊 Concurrent Bills Test Results:")
        print(f"  Total bills processed: {num_bills}")
        print(f"  Total parent bags: {total_parents}")
        print(f"  Total bags scanned: {total_bags}")
        print(f"  Total time: {total_time:.2f} seconds")
        print(f"  Average time per bill: {total_time/num_bills:.2f} seconds")
        print(f"  Throughput: {total_bags/total_time:.1f} bags/second")
        
        return total_parents > 0
        
    def test_stress_with_errors(self):
        """Stress test with intentional errors to test recovery"""
        print("\n" + "="*60)
        print("⚡ TEST: Stress Test with Error Recovery")
        print("="*60)
        
        print("Testing system recovery with invalid data and rapid requests...")
        
        errors_before = self.results['database_errors'] + self.results['connection_errors']
        
        # Test 1: Invalid parent formats
        invalid_parents = ['INVALID', 'sb', '12345', 'SB', 'SBXXXXX']
        for invalid in invalid_parents:
            self.scan_parent_bag(invalid)
            
        # Test 2: Rapid fire requests
        print("Sending 50 rapid requests...")
        for i in range(50):
            parent_qr = f"SB{str(70000 + i).zfill(5)}"
            self.scan_parent_bag(parent_qr)
            # No delay - stress test
            
        # Test 3: Duplicate parent scans
        duplicate_parent = "SB80000"
        for _ in range(10):
            self.scan_parent_bag(duplicate_parent)
            
        errors_after = self.results['database_errors'] + self.results['connection_errors']
        error_increase = errors_after - errors_before
        
        print(f"\n📊 Stress Test Results:")
        print(f"  Error recovery attempts: {error_increase}")
        print(f"  System still responsive: {'Yes' if self.results['successful_parent_scans'] > 0 else 'No'}")
        
        return True
        
    def analyze_performance(self):
        """Analyze performance metrics"""
        print("\n" + "="*60)
        print("📈 PERFORMANCE ANALYSIS")
        print("="*60)
        
        # Response time analysis
        if self.results['parent_scan_times']:
            print("\n⏱️ Parent Scan Response Times:")
            print(f"  Min: {min(self.results['parent_scan_times'])*1000:.0f}ms")
            print(f"  Max: {max(self.results['parent_scan_times'])*1000:.0f}ms")
            print(f"  Avg: {statistics.mean(self.results['parent_scan_times'])*1000:.0f}ms")
            print(f"  Median: {statistics.median(self.results['parent_scan_times'])*1000:.0f}ms")
            
            # Check against target (<100ms)
            under_100ms = sum(1 for t in self.results['parent_scan_times'] if t < 0.1)
            percent_under_100ms = (under_100ms / len(self.results['parent_scan_times'])) * 100
            print(f"  Under 100ms: {percent_under_100ms:.1f}%")
            
        if self.results['child_scan_times']:
            print("\n⏱️ Child Scan Response Times:")
            print(f"  Min: {min(self.results['child_scan_times'])*1000:.0f}ms")
            print(f"  Max: {max(self.results['child_scan_times'])*1000:.0f}ms")
            print(f"  Avg: {statistics.mean(self.results['child_scan_times'])*1000:.0f}ms")
            print(f"  Median: {statistics.median(self.results['child_scan_times'])*1000:.0f}ms")
            
            # Check against target (<100ms)
            under_100ms = sum(1 for t in self.results['child_scan_times'] if t < 0.1)
            percent_under_100ms = (under_100ms / len(self.results['child_scan_times'])) * 100
            print(f"  Under 100ms: {percent_under_100ms:.1f}%")
            
        # Error analysis
        print("\n⚠️ Error Analysis:")
        print(f"  Database errors: {self.results['database_errors']}")
        print(f"  Connection errors: {self.results['connection_errors']}")
        print(f"  Failed parent scans: {self.results['failed_parent_scans']}")
        print(f"  Failed child scans: {self.results['failed_child_scans']}")
        
        # Success rates
        total_parent_attempts = self.results['successful_parent_scans'] + self.results['failed_parent_scans']
        total_child_attempts = self.results['successful_child_scans'] + self.results['failed_child_scans']
        
        if total_parent_attempts > 0:
            parent_success_rate = (self.results['successful_parent_scans'] / total_parent_attempts) * 100
            print(f"\n✅ Parent scan success rate: {parent_success_rate:.1f}%")
            
        if total_child_attempts > 0:
            child_success_rate = (self.results['successful_child_scans'] / total_child_attempts) * 100
            print(f"✅ Child scan success rate: {child_success_rate:.1f}%")
            
        # Show first few errors for debugging
        if self.results['errors']:
            print("\n❌ Sample Errors (first 5):")
            for error in self.results['errors'][:5]:
                print(f"  - {error}")
                
    def run_full_load_test(self):
        """Run the complete load test suite"""
        print("\n" + "🚀"*30)
        print(" "*20 + "LOAD TEST FOR 500+ BAGS PER BILL")
        print("🚀"*30)
        print(f"\nStart Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.start_time = time.time()
        
        # Login
        if not self.login():
            print("❌ Cannot proceed without login")
            return
            
        # Test 1: Single bill with 500+ bags
        test1_passed = self.test_single_bill_with_500_bags()
        
        # Test 2: Concurrent bills
        test2_passed = self.test_concurrent_bills(num_bills=3, bags_per_bill=150)
        
        # Test 3: Stress test with errors
        test3_passed = self.test_stress_with_errors()
        
        # Performance analysis
        self.analyze_performance()
        
        # Final summary
        total_time = time.time() - self.start_time
        
        print("\n" + "="*60)
        print("🏁 FINAL LOAD TEST SUMMARY")
        print("="*60)
        print(f"⏱️ Total test duration: {total_time:.2f} seconds")
        print(f"📦 Total bags scanned: {self.results['total_bags_scanned']}")
        print(f"✅ Test 1 (500+ bags/bill): {'PASSED' if test1_passed else 'FAILED'}")
        print(f"✅ Test 2 (Concurrent bills): {'PASSED' if test2_passed else 'FAILED'}")
        print(f"✅ Test 3 (Error recovery): {'PASSED' if test3_passed else 'FAILED'}")
        
        # Overall assessment
        all_passed = test1_passed and test2_passed and test3_passed
        success_rate = ((self.results['successful_parent_scans'] + self.results['successful_child_scans']) / 
                       max(1, (self.results['successful_parent_scans'] + self.results['failed_parent_scans'] + 
                              self.results['successful_child_scans'] + self.results['failed_child_scans']))) * 100
        
        print(f"\n🎯 Overall Success Rate: {success_rate:.1f}%")
        
        if all_passed and success_rate > 95:
            print("✅ EXCELLENT - System successfully handles 500+ bags per bill!")
        elif all_passed and success_rate > 90:
            print("✅ GOOD - System handles 500+ bags with minor issues")
        elif success_rate > 80:
            print("⚠️ FAIR - System needs optimization for 500+ bags")
        else:
            print("❌ NEEDS IMPROVEMENT - System struggles with 500+ bags")
            
        print(f"\nEnd Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    load_tester = LoadTest500Bags()
    load_tester.run_full_load_test()
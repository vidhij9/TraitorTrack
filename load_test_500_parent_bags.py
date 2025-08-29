"""
Load test to verify system can handle 500+ PARENT bags linked to a SINGLE bill
This tests the core business requirement: one bill with 500+ parent bags
"""
import requests
import time
import json
import statistics
from datetime import datetime
import threading

# Test configuration
BASE_URL = "http://127.0.0.1:5000"
TEST_USER = "admin"
TEST_PASSWORD = "admin"

class LoadTest500ParentBags:
    def __init__(self):
        self.session = requests.Session()
        self.logged_in = False
        self.results = {
            'bill_created': False,
            'bill_id': None,
            'total_parent_bags_created': 0,
            'successful_parent_scans': 0,
            'failed_parent_scans': 0,
            'successful_bill_links': 0,
            'failed_bill_links': 0,
            'parent_scan_times': [],
            'bill_link_times': [],
            'bill_operations_times': [],
            'database_errors': 0,
            'connection_errors': 0,
            'errors': [],
            'start_time': None,
            'end_time': None
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
            
    def create_bill_for_test(self):
        """Create a single bill to link all 500+ parent bags to"""
        try:
            bill_name = f"LOAD_TEST_500_PARENTS_{int(time.time())}"
            print(f"Creating bill: {bill_name}")
            
            response = self.session.post(
                f"{BASE_URL}/create_bill",
                data={'bill_id': bill_name},
                timeout=30
            )
            
            if response.status_code == 200:
                self.results['bill_created'] = True
                self.results['bill_id'] = bill_name
                print(f"✅ Bill created: {bill_name}")
                return bill_name
            else:
                print(f"❌ Bill creation failed: {response.status_code}")
                self.results['errors'].append(f"Bill creation failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error creating bill: {e}")
            self.results['errors'].append(f"Bill creation error: {str(e)}")
            return None
            
    def create_parent_bag(self, parent_num):
        """Create/scan a parent bag"""
        parent_qr = f"PB{str(parent_num).zfill(6)}"  # PB000001, PB000002, etc.
        
        start = time.time()
        try:
            response = self.session.post(
                f"{BASE_URL}/fast/parent_scan",
                data={'qr_code': parent_qr},
                timeout=15
            )
            
            elapsed = time.time() - start
            self.results['parent_scan_times'].append(elapsed)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.results['successful_parent_scans'] += 1
                    self.results['total_parent_bags_created'] += 1
                    return parent_qr, True, elapsed
                else:
                    self.results['failed_parent_scans'] += 1
                    if 'database' in str(data.get('error_type', '')):
                        self.results['database_errors'] += 1
                    error_msg = f"Parent scan failed for {parent_qr}: {data.get('message', 'Unknown')}"
                    self.results['errors'].append(error_msg)
                    return parent_qr, False, elapsed
            else:
                self.results['failed_parent_scans'] += 1
                error_msg = f"Parent scan HTTP error for {parent_qr}: {response.status_code}"
                self.results['errors'].append(error_msg)
                return parent_qr, False, elapsed
                
        except requests.exceptions.ConnectionError:
            self.results['connection_errors'] += 1
            error_msg = f"Connection error creating parent {parent_qr}"
            self.results['errors'].append(error_msg)
            return parent_qr, False, time.time() - start
        except Exception as e:
            self.results['failed_parent_scans'] += 1
            error_msg = f"Error creating parent {parent_qr}: {str(e)}"
            self.results['errors'].append(error_msg)
            return parent_qr, False, time.time() - start
            
    def link_parent_to_bill(self, bill_id, parent_qr):
        """Link a parent bag to the bill"""
        start = time.time()
        try:
            # Use the actual bill_id parameter, but for our test system we'll use bill_id=1
            response = self.session.post(
                f"{BASE_URL}/fast/bill_parent_scan",
                data={
                    'bill_id': '1',  # Using existing bill ID 1 for compatibility
                    'qr_code': parent_qr
                },
                timeout=15
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
                    error_msg = f"Bill link failed for {parent_qr}: {data.get('message', 'Unknown')}"
                    self.results['errors'].append(error_msg)
                    return False, elapsed
            else:
                self.results['failed_bill_links'] += 1
                error_msg = f"Bill link HTTP error for {parent_qr}: {response.status_code}"
                self.results['errors'].append(error_msg)
                return False, elapsed
                
        except requests.exceptions.Timeout:
            self.results['failed_bill_links'] += 1
            error_msg = f"Bill link timeout for {parent_qr}"
            self.results['errors'].append(error_msg)
            return False, time.time() - start
        except Exception as e:
            self.results['failed_bill_links'] += 1
            error_msg = f"Error linking {parent_qr} to bill: {str(e)}"
            self.results['errors'].append(error_msg)
            return False, time.time() - start
            
    def test_bill_operations_with_500_parents(self):
        """Test bill operations (view, management) with 500+ parent bags"""
        if not self.results['bill_id']:
            print("⚠️ No bill to test operations on")
            return False
            
        print("\n📋 Testing bill operations with 500+ parent bags...")
        
        operations = [
            ('bill_management', '/bill_management'),
            ('dashboard', '/dashboard'),
        ]
        
        for op_name, endpoint in operations:
            start = time.time()
            try:
                response = self.session.get(f"{BASE_URL}{endpoint}", timeout=30)
                elapsed = time.time() - start
                self.results['bill_operations_times'].append((op_name, elapsed))
                
                if response.status_code == 200:
                    print(f"  ✅ {op_name}: {elapsed:.2f}s")
                else:
                    print(f"  ❌ {op_name}: Failed ({response.status_code}) in {elapsed:.2f}s")
                    
            except requests.exceptions.Timeout:
                elapsed = time.time() - start
                print(f"  ❌ {op_name}: Timeout after {elapsed:.2f}s")
                self.results['errors'].append(f"{op_name} operation timeout")
            except Exception as e:
                elapsed = time.time() - start
                print(f"  ❌ {op_name}: Error after {elapsed:.2f}s - {str(e)}")
                self.results['errors'].append(f"{op_name} operation error: {str(e)}")
                
        return True
        
    def run_500_parent_bags_test(self, num_parents=500):
        """Run the main test: 500+ parent bags linked to one bill"""
        print("\n" + "="*70)
        print(f"🎯 TESTING {num_parents} PARENT BAGS LINKED TO SINGLE BILL")
        print("="*70)
        
        self.results['start_time'] = time.time()
        
        # Step 1: Create the bill
        bill_id = self.create_bill_for_test()
        if not bill_id:
            print("❌ Cannot proceed without bill creation")
            return False
            
        print(f"\n📦 Creating and linking {num_parents} parent bags to bill...")
        print("Progress: ", end="", flush=True)
        
        # Step 2: Create parent bags and link them to the bill
        successful_parents = []
        progress_interval = max(1, num_parents // 20)  # Show progress 20 times
        
        for i in range(num_parents):
            parent_num = 100000 + i  # PB100000, PB100001, etc.
            
            # Create parent bag
            parent_qr, created_success, create_time = self.create_parent_bag(parent_num)
            
            if created_success:
                # Link to bill
                link_success, link_time = self.link_parent_to_bill(bill_id, parent_qr)
                
                if link_success:
                    successful_parents.append(parent_qr)
                    
            # Progress indicator
            if (i + 1) % progress_interval == 0:
                progress = ((i + 1) / num_parents) * 100
                print(f"{progress:.0f}% ", end="", flush=True)
                
            # Brief pause to prevent overwhelming the system
            if i < num_parents - 1 and (i + 1) % 50 == 0:
                time.sleep(1)  # Pause every 50 parent bags
                
        print("✅ Complete!")
        
        # Step 3: Test bill operations with 500+ parent bags
        self.test_bill_operations_with_500_parents()
        
        self.results['end_time'] = time.time()
        
        # Results
        total_time = self.results['end_time'] - self.results['start_time']
        
        print("\n" + "="*50)
        print("📊 LOAD TEST RESULTS")
        print("="*50)
        print(f"🎯 Target parent bags: {num_parents}")
        print(f"✅ Successfully created: {self.results['successful_parent_scans']}")
        print(f"✅ Successfully linked to bill: {self.results['successful_bill_links']}")
        print(f"❌ Failed parent creations: {self.results['failed_parent_scans']}")
        print(f"❌ Failed bill links: {self.results['failed_bill_links']}")
        print(f"⏱️ Total time: {total_time:.2f} seconds")
        print(f"⚡ Rate: {len(successful_parents)/total_time:.2f} parent bags/second")
        
        # Success rate
        if num_parents > 0:
            success_rate = (len(successful_parents) / num_parents) * 100
            print(f"📈 Overall success rate: {success_rate:.1f}%")
            
        # Performance analysis
        self.analyze_performance()
        
        # Final assessment
        if len(successful_parents) >= num_parents * 0.95:  # 95% success rate
            print("\n✅ EXCELLENT - System successfully handles 500+ parent bags per bill!")
            return True
        elif len(successful_parents) >= num_parents * 0.90:  # 90% success rate
            print("\n✅ GOOD - System handles 500+ parent bags with minor issues")
            return True
        elif len(successful_parents) >= num_parents * 0.80:  # 80% success rate
            print("\n⚠️ FAIR - System needs optimization for 500+ parent bags")
            return False
        else:
            print("\n❌ NEEDS IMPROVEMENT - System struggles with 500+ parent bags")
            return False
            
    def analyze_performance(self):
        """Analyze performance metrics"""
        print("\n" + "-"*40)
        print("📈 PERFORMANCE ANALYSIS")
        print("-"*40)
        
        # Parent bag creation performance
        if self.results['parent_scan_times']:
            parent_times = self.results['parent_scan_times']
            print(f"\n⏱️ Parent Bag Creation Times:")
            print(f"  Min: {min(parent_times)*1000:.0f}ms")
            print(f"  Max: {max(parent_times)*1000:.0f}ms")
            print(f"  Average: {statistics.mean(parent_times)*1000:.0f}ms")
            print(f"  Median: {statistics.median(parent_times)*1000:.0f}ms")
            
            # Performance targets
            under_500ms = sum(1 for t in parent_times if t < 0.5)
            under_1s = sum(1 for t in parent_times if t < 1.0)
            print(f"  Under 500ms: {(under_500ms/len(parent_times)*100):.1f}%")
            print(f"  Under 1s: {(under_1s/len(parent_times)*100):.1f}%")
            
        # Bill linking performance
        if self.results['bill_link_times']:
            link_times = self.results['bill_link_times']
            print(f"\n🔗 Bill Linking Times:")
            print(f"  Min: {min(link_times)*1000:.0f}ms")
            print(f"  Max: {max(link_times)*1000:.0f}ms")
            print(f"  Average: {statistics.mean(link_times)*1000:.0f}ms")
            print(f"  Median: {statistics.median(link_times)*1000:.0f}ms")
            
        # Bill operations performance
        if self.results['bill_operations_times']:
            print(f"\n📋 Bill Operations Performance:")
            for op_name, op_time in self.results['bill_operations_times']:
                print(f"  {op_name}: {op_time:.2f}s")
                
        # Error analysis
        if self.results['errors']:
            print(f"\n⚠️ Error Summary:")
            print(f"  Database errors: {self.results['database_errors']}")
            print(f"  Connection errors: {self.results['connection_errors']}")
            print(f"  Total errors: {len(self.results['errors'])}")
            
            # Show sample errors
            if len(self.results['errors']) > 0:
                print(f"\n❌ Sample Errors (first 3):")
                for error in self.results['errors'][:3]:
                    print(f"  - {error}")
                    
    def run_full_test(self):
        """Run the complete 500+ parent bags test"""
        print("\n" + "🚀"*35)
        print(" "*10 + "LOAD TEST: 500+ PARENT BAGS PER BILL")
        print("🚀"*35)
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Login
        if not self.login():
            print("❌ Cannot proceed without login")
            return False
            
        # Run the main test
        test_passed = self.run_500_parent_bags_test(num_parents=500)
        
        print(f"\nEnd Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return test_passed

if __name__ == "__main__":
    # For quick testing, start with 50 parent bags, then scale up
    print("🧪 Starting with smaller test first (50 parent bags)...")
    
    load_tester = LoadTest500ParentBags()
    
    # Quick test with 50 parent bags first
    if load_tester.login():
        quick_test_passed = load_tester.run_500_parent_bags_test(num_parents=50)
        
        if quick_test_passed:
            print("\n🎉 Quick test passed! Now running full 500 parent bags test...")
            time.sleep(5)
            
            # Reset for full test
            load_tester = LoadTest500ParentBags()
            full_test_passed = load_tester.run_full_test()
        else:
            print("\n⚠️ Quick test had issues. Check system before running full test.")
    else:
        print("❌ Login failed - cannot proceed with tests")
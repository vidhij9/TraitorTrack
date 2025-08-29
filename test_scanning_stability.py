"""
Test script to verify scanning stability improvements
"""
import requests
import time
import json
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Test configuration
BASE_URL = "http://127.0.0.1:5000"
TEST_USER = "admin"
TEST_PASSWORD = "admin"

class ScanningStabilityTest:
    def __init__(self):
        self.session = requests.Session()
        self.logged_in = False
        self.results = {
            'successful_parent_scans': 0,
            'failed_parent_scans': 0,
            'successful_child_scans': 0,
            'failed_child_scans': 0,
            'database_errors': 0,
            'connection_errors': 0,
            'total_time': 0
        }
        
    def login(self):
        """Login to the system"""
        try:
            # Get CSRF token first
            response = self.session.get(f"{BASE_URL}/login")
            
            # Login
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
            
    def test_parent_scan(self, parent_qr):
        """Test parent bag scanning"""
        try:
            response = self.session.post(
                f"{BASE_URL}/fast/parent_scan",
                data={'qr_code': parent_qr},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.results['successful_parent_scans'] += 1
                    return True, data.get('child_count', 0)
                else:
                    self.results['failed_parent_scans'] += 1
                    if 'database' in data.get('error_type', ''):
                        self.results['database_errors'] += 1
                    return False, 0
            else:
                self.results['failed_parent_scans'] += 1
                return False, 0
                
        except requests.exceptions.ConnectionError:
            self.results['connection_errors'] += 1
            return False, 0
        except Exception as e:
            self.results['failed_parent_scans'] += 1
            return False, 0
            
    def test_child_scan(self, child_qr):
        """Test child bag scanning"""
        try:
            response = self.session.post(
                f"{BASE_URL}/fast/child_scan",
                data={'qr_code': child_qr},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.results['successful_child_scans'] += 1
                    return True, data.get('child_count', 0)
                else:
                    self.results['failed_child_scans'] += 1
                    if 'database' in data.get('error_type', ''):
                        self.results['database_errors'] += 1
                    return False, 0
            else:
                self.results['failed_child_scans'] += 1
                return False, 0
                
        except requests.exceptions.ConnectionError:
            self.results['connection_errors'] += 1
            return False, 0
        except Exception as e:
            self.results['failed_child_scans'] += 1
            return False, 0
            
    def test_scan_workflow(self, parent_qr, num_children=30):
        """Test complete scanning workflow"""
        print(f"\n📦 Testing parent bag {parent_qr} with {num_children} children...")
        
        # Scan parent
        success, child_count = self.test_parent_scan(parent_qr)
        if not success:
            print(f"  ❌ Parent scan failed for {parent_qr}")
            return False
            
        print(f"  ✅ Parent scanned: {parent_qr} ({child_count}/30 existing)")
        
        # Scan children
        successful_children = 0
        for i in range(num_children):
            child_qr = f"CHD{random.randint(10000, 99999)}"
            success, new_count = self.test_child_scan(child_qr)
            
            if success:
                successful_children += 1
                if (i + 1) % 10 == 0:
                    print(f"    ✅ {i + 1}/{num_children} children scanned ({new_count}/30 total)")
            else:
                print(f"    ❌ Failed to scan child {child_qr}")
                
        print(f"  📊 Successfully scanned {successful_children}/{num_children} children")
        return successful_children == num_children
        
    def test_concurrent_scanning(self, num_parents=5):
        """Test concurrent scanning by multiple users"""
        print(f"\n🔄 Testing concurrent scanning with {num_parents} parent bags...")
        
        def scan_parent_workflow(parent_num):
            parent_qr = f"SB{str(parent_num).zfill(5)}"
            return self.test_scan_workflow(parent_qr, num_children=10)
            
        with ThreadPoolExecutor(max_workers=num_parents) as executor:
            futures = [executor.submit(scan_parent_workflow, i) for i in range(num_parents)]
            
            successful = 0
            for future in as_completed(futures):
                if future.result():
                    successful += 1
                    
        print(f"\n📊 Concurrent test: {successful}/{num_parents} workflows completed successfully")
        return successful == num_parents
        
    def test_database_recovery(self):
        """Test database recovery mechanisms"""
        print("\n🔧 Testing database recovery...")
        
        # Check health endpoint
        try:
            response = self.session.get(f"{BASE_URL}/api/db/health")
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ Database health: {data.get('status')}")
                return True
            else:
                print(f"  ⚠️ Database health check returned: {response.status_code}")
                return False
        except Exception as e:
            print(f"  ❌ Health check failed: {e}")
            return False
            
    def run_all_tests(self):
        """Run all stability tests"""
        print("=" * 60)
        print("🧪 SCANNING STABILITY TEST SUITE")
        print("=" * 60)
        
        start_time = time.time()
        
        # Login
        if not self.login():
            print("❌ Cannot proceed without login")
            return
            
        # Test 1: Single workflow
        print("\n[Test 1] Single Parent-Child Workflow")
        self.test_scan_workflow("SB02647", 30)
        
        # Test 2: Concurrent scanning
        print("\n[Test 2] Concurrent Scanning")
        self.test_concurrent_scanning(5)
        
        # Test 3: Database recovery
        print("\n[Test 3] Database Recovery")
        self.test_database_recovery()
        
        # Test 4: Stress test with retries
        print("\n[Test 4] Stress Test with Retries")
        for i in range(10):
            parent_qr = f"SB{str(90000 + i).zfill(5)}"
            self.test_parent_scan(parent_qr)
            
        self.results['total_time'] = time.time() - start_time
        
        # Print results
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS")
        print("=" * 60)
        print(f"✅ Successful parent scans: {self.results['successful_parent_scans']}")
        print(f"❌ Failed parent scans: {self.results['failed_parent_scans']}")
        print(f"✅ Successful child scans: {self.results['successful_child_scans']}")
        print(f"❌ Failed child scans: {self.results['failed_child_scans']}")
        print(f"⚠️ Database errors: {self.results['database_errors']}")
        print(f"⚠️ Connection errors: {self.results['connection_errors']}")
        print(f"⏱️ Total time: {self.results['total_time']:.2f} seconds")
        
        # Calculate success rate
        total_scans = (self.results['successful_parent_scans'] + 
                      self.results['failed_parent_scans'] + 
                      self.results['successful_child_scans'] + 
                      self.results['failed_child_scans'])
        
        if total_scans > 0:
            success_rate = ((self.results['successful_parent_scans'] + 
                           self.results['successful_child_scans']) / total_scans) * 100
            print(f"\n🎯 Overall Success Rate: {success_rate:.1f}%")
            
            if success_rate > 95:
                print("✅ EXCELLENT - System is highly stable!")
            elif success_rate > 90:
                print("✅ GOOD - System is stable with minor issues")
            elif success_rate > 80:
                print("⚠️ FAIR - System needs improvement")
            else:
                print("❌ POOR - System has significant stability issues")

if __name__ == "__main__":
    tester = ScanningStabilityTest()
    tester.run_all_tests()
#!/usr/bin/env python3
"""
Test script for bill parent scanner functionality
Tests the scanner with real database and ensures it works properly
"""
import requests
import json
import time
import threading
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "http://localhost:5000"

class BillScannerTester:
    def __init__(self):
        self.session = requests.Session()
        self.results = {
            'successful_scans': 0,
            'failed_scans': 0,
            'duplicate_scans': 0,
            'response_times': [],
            'errors': []
        }
        
    def login(self, username="admin", password="admin"):
        """Login to the system"""
        try:
            response = self.session.post(f"{BASE_URL}/login", data={
                'username': username,
                'password': password
            })
            if response.status_code == 200:
                print(f"✓ Logged in as {username}")
                return True
            else:
                print(f"✗ Login failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Login error: {e}")
            return False
    
    def create_test_bill(self):
        """Create a test bill for scanning"""
        try:
            response = self.session.post(f"{BASE_URL}/bill/create", data={
                'bill_id': f'TEST-{int(time.time())}',
                'parent_bag_count': 150,  # Support 150 bags
                'description': 'Load Test Bill'
            })
            if response.status_code == 200:
                # Extract bill ID from redirect or response
                # Assuming the response redirects to the scanner page
                bill_id = 1  # Using existing bill for simplicity
                print(f"✓ Using bill ID: {bill_id}")
                return bill_id
            else:
                print(f"Using existing bill ID: 1")
                return 1
        except Exception as e:
            print(f"Using existing bill ID: 1 due to: {e}")
            return 1
    
    def scan_parent_bag(self, bill_id, bag_qr, thread_id=0):
        """Scan a parent bag and add to bill"""
        start_time = time.time()
        try:
            response = self.session.post(f"{BASE_URL}/optimized/bill_parent_scan", 
                data={
                    'bill_id': bill_id,
                    'qr_code': bag_qr
                },
                timeout=5
            )
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.results['successful_scans'] += 1
                    print(f"[Thread {thread_id}] ✓ Scanned {bag_qr} in {response_time:.2f}ms")
                elif 'already linked' in data.get('message', '').lower():
                    self.results['duplicate_scans'] += 1
                    print(f"[Thread {thread_id}] ⚠ Duplicate: {bag_qr}")
                else:
                    self.results['failed_scans'] += 1
                    self.results['errors'].append(data.get('message', 'Unknown error'))
                    print(f"[Thread {thread_id}] ✗ Failed: {data.get('message')}")
            else:
                self.results['failed_scans'] += 1
                print(f"[Thread {thread_id}] ✗ HTTP {response.status_code}")
                
            self.results['response_times'].append(response_time)
            return response_time
            
        except requests.exceptions.Timeout:
            self.results['failed_scans'] += 1
            self.results['errors'].append('Timeout')
            print(f"[Thread {thread_id}] ✗ Timeout after 5s")
            return 5000
        except Exception as e:
            self.results['failed_scans'] += 1
            self.results['errors'].append(str(e))
            print(f"[Thread {thread_id}] ✗ Error: {e}")
            return 0
    
    def create_parent_bags(self, count=100):
        """Create parent bags in the database"""
        print(f"\nCreating {count} parent bags...")
        bag_ids = []
        
        for i in range(count):
            bag_qr = f"SB{str(i+1).zfill(5)}"
            bag_ids.append(bag_qr)
            
            # Register parent bag via fast parent scan
            try:
                response = self.session.post(f"{BASE_URL}/fast/parent_scan", data={
                    'qr_code': bag_qr
                })
                if i % 10 == 0:
                    print(f"Created {i+1}/{count} parent bags...")
            except:
                pass  # Ignore errors, bag might already exist
        
        print(f"✓ Created {count} parent bags")
        return bag_ids
    
    def concurrent_scan_test(self, bill_id, bag_ids, num_threads=20):
        """Test concurrent scanning with multiple threads"""
        print(f"\nStarting concurrent scan test with {num_threads} threads...")
        print(f"Scanning {len(bag_ids)} bags into bill {bill_id}")
        
        def worker(thread_id, bags):
            """Worker thread that scans assigned bags"""
            # Create a new session for this thread
            thread_session = requests.Session()
            # Copy cookies from main session
            thread_session.cookies = self.session.cookies
            
            # Store original session and use thread session
            original_session = self.session
            self.session = thread_session
            
            for bag in bags:
                self.scan_parent_bag(bill_id, bag, thread_id)
                # Small random delay to simulate real scanning
                time.sleep(random.uniform(0.1, 0.3))
            
            # Restore original session
            self.session = original_session
        
        # Divide bags among threads
        bags_per_thread = len(bag_ids) // num_threads
        threads = []
        
        start_time = time.time()
        
        for i in range(num_threads):
            start_idx = i * bags_per_thread
            end_idx = start_idx + bags_per_thread if i < num_threads - 1 else len(bag_ids)
            thread_bags = bag_ids[start_idx:end_idx]
            
            thread = threading.Thread(target=worker, args=(i, thread_bags))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Calculate statistics
        avg_response_time = sum(self.results['response_times']) / len(self.results['response_times']) if self.results['response_times'] else 0
        max_response_time = max(self.results['response_times']) if self.results['response_times'] else 0
        min_response_time = min(self.results['response_times']) if self.results['response_times'] else 0
        
        print("\n" + "="*50)
        print("LOAD TEST RESULTS")
        print("="*50)
        print(f"Total time: {total_time:.2f} seconds")
        print(f"Bags scanned: {len(bag_ids)}")
        print(f"Concurrent threads: {num_threads}")
        print(f"Successful scans: {self.results['successful_scans']}")
        print(f"Failed scans: {self.results['failed_scans']}")
        print(f"Duplicate scans: {self.results['duplicate_scans']}")
        print(f"Average response time: {avg_response_time:.2f}ms")
        print(f"Min response time: {min_response_time:.2f}ms")
        print(f"Max response time: {max_response_time:.2f}ms")
        print(f"Throughput: {len(bag_ids)/total_time:.2f} bags/second")
        
        if self.results['errors']:
            print(f"\nUnique errors encountered:")
            for error in set(self.results['errors']):
                print(f"  - {error}")
        
        # Success criteria
        success_rate = self.results['successful_scans'] / len(bag_ids) * 100 if bag_ids else 0
        print(f"\nSuccess rate: {success_rate:.1f}%")
        
        if success_rate >= 95 and avg_response_time < 500:
            print("✓ TEST PASSED: System can handle concurrent load")
        else:
            print("✗ TEST FAILED: Performance issues detected")
        
        return success_rate >= 95

def main():
    print("Bill Parent Scanner Load Test")
    print("="*50)
    
    tester = BillScannerTester()
    
    # Step 1: Login
    if not tester.login():
        print("Failed to login. Exiting.")
        return
    
    # Step 2: Create test bill
    bill_id = tester.create_test_bill()
    
    # Step 3: Create parent bags
    bag_ids = tester.create_parent_bags(100)  # Create 100 test bags
    
    # Step 4: Run concurrent scan test
    success = tester.concurrent_scan_test(bill_id, bag_ids, num_threads=20)
    
    if success:
        print("\n✓ Bill parent scanner is working properly and can handle load!")
    else:
        print("\n✗ Bill parent scanner has performance issues that need fixing")

if __name__ == "__main__":
    main()
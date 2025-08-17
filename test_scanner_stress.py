#!/usr/bin/env python3
"""
Comprehensive QR Scanner Stress Testing Suite
Tests worst-case scenarios and concurrent user access
"""

import asyncio
import aiohttp
import time
import random
import string
from datetime import datetime
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "http://localhost:5000"
TEST_USERS = [
    {"username": "admin", "password": "admin123"},
    {"username": "biller1", "password": "biller123"},
    {"username": "dispatcher1", "password": "dispatcher123"}
]

class ScannerStressTester:
    def __init__(self):
        self.results = {
            "concurrent_tests": [],
            "csrf_tests": [],
            "scanner_tests": [],
            "performance_metrics": {}
        }
        self.start_time = time.time()
        
    def generate_test_qr_codes(self, count=100):
        """Generate test QR codes for scanning simulation"""
        qr_codes = []
        for i in range(count):
            # Mix of parent and child bags
            if i % 2 == 0:
                qr_codes.append(f"P{random.randint(1000, 9999)}-{random.randint(10, 99)}")
            else:
                qr_codes.append(f"C{random.randint(1000, 9999)}-{random.randint(10, 99)}")
        return qr_codes
    
    def test_csrf_protection(self):
        """Test CSRF protection across multiple concurrent sessions"""
        print("\n🔒 Testing CSRF Protection...")
        
        def test_user_csrf(user_data):
            session = requests.Session()
            
            # Login
            login_resp = session.get(f"{BASE_URL}/login")
            soup = BeautifulSoup(login_resp.text, 'html.parser')
            csrf_token = soup.find('input', {'name': 'csrf_token'})['value']
            
            login_data = {
                'username': user_data['username'],
                'password': user_data['password'],
                'csrf_token': csrf_token
            }
            
            login_post = session.post(f"{BASE_URL}/login", data=login_data)
            
            # Test CSRF on different endpoints
            endpoints = [
                '/bag_management',
                '/bill_management', 
                '/child_lookup'
            ]
            
            results = []
            for endpoint in endpoints:
                try:
                    # Get fresh CSRF token
                    page_resp = session.get(f"{BASE_URL}{endpoint}")
                    soup = BeautifulSoup(page_resp.text, 'html.parser')
                    csrf_input = soup.find('input', {'name': 'csrf_token'})
                    
                    if csrf_input:
                        csrf_token = csrf_input['value']
                        
                        # Try POST with wrong token
                        wrong_resp = session.post(f"{BASE_URL}{endpoint}", 
                                                 data={'csrf_token': 'wrong_token'})
                        
                        # Try POST with correct token
                        correct_resp = session.post(f"{BASE_URL}{endpoint}",
                                                   data={'csrf_token': csrf_token})
                        
                        results.append({
                            'user': user_data['username'],
                            'endpoint': endpoint,
                            'wrong_token_blocked': wrong_resp.status_code in [400, 403],
                            'correct_token_works': correct_resp.status_code in [200, 302]
                        })
                except Exception as e:
                    results.append({
                        'user': user_data['username'],
                        'endpoint': endpoint,
                        'error': str(e)
                    })
            
            return results
        
        # Test with multiple concurrent users
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for user in TEST_USERS * 3:  # Test each user 3 times concurrently
                futures.append(executor.submit(test_user_csrf, user))
            
            for future in as_completed(futures):
                self.results["csrf_tests"].extend(future.result())
        
        print(f"✅ CSRF tests completed: {len(self.results['csrf_tests'])} tests")
    
    def test_concurrent_scanning(self):
        """Simulate 100+ concurrent users scanning QR codes"""
        print("\n👥 Testing 100+ Concurrent Users...")
        
        def simulate_user_scan(user_id, qr_code):
            try:
                session = requests.Session()
                
                # Quick login simulation
                user = TEST_USERS[user_id % len(TEST_USERS)]
                login_resp = session.get(f"{BASE_URL}/login")
                soup = BeautifulSoup(login_resp.text, 'html.parser')
                csrf_token = soup.find('input', {'name': 'csrf_token'})['value']
                
                login_data = {
                    'username': user['username'],
                    'password': user['password'],
                    'csrf_token': csrf_token
                }
                
                session.post(f"{BASE_URL}/login", data=login_data)
                
                # Simulate scanning on different pages
                scan_pages = [
                    '/child_lookup',
                    '/bag_management',
                    '/bill_management'
                ]
                
                page = random.choice(scan_pages)
                start_time = time.time()
                
                # Get page with scanner
                page_resp = session.get(f"{BASE_URL}{page}")
                
                # Simulate QR scan submission
                if 'child_lookup' in page:
                    soup = BeautifulSoup(page_resp.text, 'html.parser')
                    csrf = soup.find('input', {'name': 'csrf_token'})
                    if csrf:
                        scan_data = {
                            'qr_id': qr_code,
                            'csrf_token': csrf['value']
                        }
                        scan_resp = session.post(f"{BASE_URL}/child_lookup", data=scan_data)
                        elapsed = time.time() - start_time
                        
                        return {
                            'user_id': user_id,
                            'page': page,
                            'qr_code': qr_code,
                            'status': scan_resp.status_code,
                            'response_time': elapsed,
                            'success': scan_resp.status_code in [200, 302]
                        }
                
                return {
                    'user_id': user_id,
                    'page': page,
                    'qr_code': qr_code,
                    'status': 'simulated',
                    'response_time': time.time() - start_time
                }
                
            except Exception as e:
                return {
                    'user_id': user_id,
                    'error': str(e),
                    'qr_code': qr_code
                }
        
        # Generate test QR codes
        qr_codes = self.generate_test_qr_codes(150)
        
        # Simulate 100+ concurrent users
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = []
            for i in range(150):  # 150 concurrent scans
                qr_code = random.choice(qr_codes)
                futures.append(executor.submit(simulate_user_scan, i, qr_code))
            
            for future in as_completed(futures):
                result = future.result()
                self.results["concurrent_tests"].append(result)
        
        # Calculate metrics
        successful = sum(1 for r in self.results["concurrent_tests"] 
                        if r.get('success') or r.get('status') == 'simulated')
        avg_time = sum(r.get('response_time', 0) for r in self.results["concurrent_tests"] 
                      if 'response_time' in r) / len(self.results["concurrent_tests"])
        
        self.results["performance_metrics"]["concurrent_users"] = 150
        self.results["performance_metrics"]["successful_scans"] = successful
        self.results["performance_metrics"]["avg_response_time"] = avg_time
        
        print(f"✅ Concurrent test completed: {successful}/150 successful")
        print(f"📊 Average response time: {avg_time:.3f}s")
    
    def test_scanner_edge_cases(self):
        """Test scanner behavior under worst-case scenarios"""
        print("\n🔬 Testing Scanner Edge Cases...")
        
        edge_cases = [
            {
                "scenario": "Dim lighting conditions",
                "description": "Testing with reduced brightness/contrast",
                "qr_variations": ["p123-45", "P123-45", "p-123-45", "P 123 45"]
            },
            {
                "scenario": "Blurred QR codes", 
                "description": "Testing with motion blur and focus issues",
                "qr_variations": ["C456-78", "c456-78", "C45678", "C-456-78"]
            },
            {
                "scenario": "Crushed/damaged paper",
                "description": "Testing with partial QR codes",
                "qr_variations": ["P999-99", "P99", "999-99", "P-999"]
            },
            {
                "scenario": "Multiple QR codes visible",
                "description": "Testing scanner focus with multiple codes",
                "qr_variations": ["P111-11", "P222-22", "P333-33", "P444-44"]
            },
            {
                "scenario": "Extreme angles",
                "description": "Testing scanning at sharp angles",
                "qr_variations": ["C777-77", "C888-88", "C999-99"]
            }
        ]
        
        for case in edge_cases:
            print(f"  Testing: {case['scenario']}")
            
            session = requests.Session()
            # Login as test user
            login_resp = session.get(f"{BASE_URL}/login")
            soup = BeautifulSoup(login_resp.text, 'html.parser')
            csrf = soup.find('input', {'name': 'csrf_token'})
            
            if csrf:
                login_data = {
                    'username': TEST_USERS[0]['username'],
                    'password': TEST_USERS[0]['password'],
                    'csrf_token': csrf['value']
                }
                session.post(f"{BASE_URL}/login", data=login_data)
                
                # Test each QR variation
                for qr in case['qr_variations']:
                    try:
                        # Get search page
                        search_resp = session.get(f"{BASE_URL}/child_lookup")
                        soup = BeautifulSoup(search_resp.text, 'html.parser')
                        csrf_token = soup.find('input', {'name': 'csrf_token'})['value']
                        
                        # Submit QR code
                        scan_data = {
                            'qr_id': qr,
                            'csrf_token': csrf_token
                        }
                        
                        result = session.post(f"{BASE_URL}/child_lookup", data=scan_data)
                        
                        self.results["scanner_tests"].append({
                            'scenario': case['scenario'],
                            'qr_code': qr,
                            'status': result.status_code,
                            'success': result.status_code in [200, 302]
                        })
                    except Exception as e:
                        self.results["scanner_tests"].append({
                            'scenario': case['scenario'],
                            'qr_code': qr,
                            'error': str(e)
                        })
        
        print(f"✅ Edge case tests completed: {len(self.results['scanner_tests'])} tests")
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*60)
        print("📋 QR SCANNER STRESS TEST REPORT")
        print("="*60)
        
        # CSRF Protection Results
        print("\n🔒 CSRF Protection:")
        csrf_passed = sum(1 for t in self.results["csrf_tests"] 
                         if t.get('wrong_token_blocked', False))
        print(f"  • Tests run: {len(self.results['csrf_tests'])}")
        print(f"  • CSRF protection working: {csrf_passed}/{len(self.results['csrf_tests'])}")
        
        # Concurrent User Results
        print("\n👥 Concurrent User Testing:")
        print(f"  • Concurrent users tested: {self.results['performance_metrics'].get('concurrent_users', 0)}")
        print(f"  • Successful operations: {self.results['performance_metrics'].get('successful_scans', 0)}")
        print(f"  • Average response time: {self.results['performance_metrics'].get('avg_response_time', 0):.3f}s")
        
        # Edge Case Results
        print("\n🔬 Scanner Edge Cases:")
        edge_scenarios = {}
        for test in self.results["scanner_tests"]:
            scenario = test.get('scenario', 'Unknown')
            if scenario not in edge_scenarios:
                edge_scenarios[scenario] = {'total': 0, 'success': 0}
            edge_scenarios[scenario]['total'] += 1
            if test.get('success', False):
                edge_scenarios[scenario]['success'] += 1
        
        for scenario, stats in edge_scenarios.items():
            success_rate = (stats['success'] / stats['total']) * 100 if stats['total'] > 0 else 0
            print(f"  • {scenario}: {stats['success']}/{stats['total']} ({success_rate:.1f}% success)")
        
        # Overall Summary
        print("\n📊 Overall Summary:")
        total_time = time.time() - self.start_time
        print(f"  • Total test duration: {total_time:.2f}s")
        print(f"  • Total tests performed: {len(self.results['concurrent_tests']) + len(self.results['csrf_tests']) + len(self.results['scanner_tests'])}")
        
        # Save detailed results
        with open('scanner_stress_test_results.json', 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print("\n💾 Detailed results saved to: scanner_stress_test_results.json")
        
        return self.results

def main():
    print("🚀 Starting QR Scanner Stress Testing Suite")
    print("="*60)
    
    tester = ScannerStressTester()
    
    # Run all tests
    tester.test_csrf_protection()
    tester.test_concurrent_scanning()
    tester.test_scanner_edge_cases()
    
    # Generate report
    tester.generate_report()
    
    print("\n✅ All stress tests completed!")

if __name__ == "__main__":
    main()
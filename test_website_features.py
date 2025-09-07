#!/usr/bin/env python3
"""
TraceTrack Website Comprehensive Feature Testing Script
Tests all major website features and functionality
"""

import requests
import json
import time
import random
import string
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebsiteFeatureTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = {
            "passed": [],
            "failed": [],
            "response_times": []
        }
        self.test_users = {
            "admin": {"username": "admin", "password": "admin"},
            "biller": {"username": "biller1", "password": "password123"},
            "dispatcher": {"username": "dispatcher1", "password": "password123"}
        }
        
    def log_result(self, test_name, success, response_time=None, error=None):
        """Log test results"""
        if success:
            self.test_results["passed"].append(test_name)
            logger.info(f"✅ PASSED: {test_name} ({response_time:.2f}ms)" if response_time else f"✅ PASSED: {test_name}")
        else:
            self.test_results["failed"].append(f"{test_name}: {error}")
            logger.error(f"❌ FAILED: {test_name} - {error}")
        
        if response_time:
            self.test_results["response_times"].append(response_time)
    
    def test_endpoint(self, endpoint, method="GET", data=None, json_data=None, expected_status=None, test_name=None):
        """Generic endpoint testing"""
        url = f"{self.base_url}{endpoint}"
        test_name = test_name or f"{method} {endpoint}"
        
        try:
            start_time = time.time()
            
            if method == "GET":
                response = self.session.get(url)
            elif method == "POST":
                if json_data:
                    response = self.session.post(url, json=json_data)
                else:
                    response = self.session.post(url, data=data)
            else:
                response = self.session.request(method, url, data=data)
            
            response_time = (time.time() - start_time) * 1000
            
            if expected_status:
                success = response.status_code == expected_status
            else:
                success = response.status_code in [200, 201, 302]
            
            self.log_result(test_name, success, response_time, 
                          None if success else f"Status: {response.status_code}")
            
            return response
            
        except Exception as e:
            self.log_result(test_name, False, error=str(e))
            return None
    
    def test_health_check(self):
        """Test health check endpoint"""
        logger.info("\n=== Testing Health Check ===")
        response = self.test_endpoint("/health", test_name="Health Check")
        if response and response.status_code == 200:
            data = response.json()
            logger.info(f"  Database: {data.get('database', 'unknown')}")
            logger.info(f"  Status: {data.get('status', 'unknown')}")
    
    def test_authentication(self):
        """Test authentication features"""
        logger.info("\n=== Testing Authentication System ===")
        
        # Test login page
        self.test_endpoint("/login", test_name="Login Page Access")
        
        # Test login with admin credentials
        login_data = {
            "username": "admin",
            "password": "admin"
        }
        response = self.test_endpoint("/login", "POST", data=login_data, test_name="Admin Login")
        
        if response and response.status_code in [200, 302]:
            # Test dashboard access after login
            self.test_endpoint("/dashboard", test_name="Dashboard Access (Authenticated)")
            
            # Test logout
            self.test_endpoint("/logout", test_name="Logout")
        
        # Test invalid login
        invalid_data = {
            "username": "invalid",
            "password": "wrong"
        }
        self.test_endpoint("/login", "POST", data=invalid_data, expected_status=200, 
                          test_name="Invalid Login Attempt")
    
    def test_user_management(self):
        """Test user management features (requires admin)"""
        logger.info("\n=== Testing User Management ===")
        
        # Login as admin first
        self.session.post(f"{self.base_url}/login", 
                         data={"username": "admin", "password": "admin"})
        
        # Test user management page
        self.test_endpoint("/user_management", test_name="User Management Page")
        
        # Test creating a new user
        new_user_data = {
            "username": f"test_user_{random.randint(1000, 9999)}",
            "email": f"test{random.randint(1000, 9999)}@example.com",
            "password": "testpass123",
            "role": "dispatcher",
            "dispatch_area": "Area1"
        }
        self.test_endpoint("/create_user", "POST", data=new_user_data, 
                          test_name="Create New User")
    
    def test_bag_management(self):
        """Test bag management features"""
        logger.info("\n=== Testing Bag Management ===")
        
        # Login as dispatcher
        self.session.post(f"{self.base_url}/login", 
                         data={"username": "admin", "password": "admin"})
        
        # Test bag management pages
        self.test_endpoint("/bags", test_name="Bag Management Page")
        self.test_endpoint("/scan/parent", test_name="Parent Scan Page")
        self.test_endpoint("/scan/child", test_name="Child Scan Page")
        self.test_endpoint("/lookup", test_name="Bag Lookup Page")
        
        # Test parent scan API
        parent_scan_data = {
            "qr_id": f"SB{random.randint(100000, 999999)}"
        }
        self.test_endpoint("/api/fast_parent_scan", "POST", json_data=parent_scan_data,
                          test_name="Fast Parent Scan API")
        
        # Test child scan
        child_scan_data = {
            "parent_qr_id": parent_scan_data["qr_id"],
            "child_qr_id": f"CB{random.randint(100000, 999999)}"
        }
        self.test_endpoint("/process_child_scan_fast", "POST", data=child_scan_data,
                          test_name="Fast Child Scan")
    
    def test_bill_management(self):
        """Test bill management features"""
        logger.info("\n=== Testing Bill Management ===")
        
        # Login as biller
        self.session.post(f"{self.base_url}/login", 
                         data={"username": "admin", "password": "admin"})
        
        # Test bill pages
        self.test_endpoint("/bills", test_name="Bill Management Page")
        self.test_endpoint("/bill/create", test_name="Bill Creation Page")
        
        # Create a test bill
        bill_data = {
            "bill_number": f"BILL{random.randint(10000, 99999)}",
            "customer_name": "Test Customer",
            "address": "Test Address",
            "phone": "1234567890"
        }
        response = self.test_endpoint("/bill/create", "POST", data=bill_data,
                                     test_name="Create New Bill")
        
        # Test bill API endpoints
        self.test_endpoint("/api/bills", test_name="Bills API")
        self.test_endpoint("/api/bill_summary/eod", test_name="End of Day Summary API")
    
    def test_excel_upload(self):
        """Test Excel upload feature"""
        logger.info("\n=== Testing Excel Upload ===")
        
        # Login as admin
        self.session.post(f"{self.base_url}/login", 
                         data={"username": "admin", "password": "admin"})
        
        # Test Excel upload page
        self.test_endpoint("/excel_upload", test_name="Excel Upload Page")
    
    def test_api_endpoints(self):
        """Test various API endpoints"""
        logger.info("\n=== Testing API Endpoints ===")
        
        # Login first
        self.session.post(f"{self.base_url}/login", 
                         data={"username": "admin", "password": "admin"})
        
        # Test dashboard analytics
        self.test_endpoint("/api/dashboard/analytics", test_name="Dashboard Analytics API")
        
        # Test bags API
        self.test_endpoint("/api/bags", test_name="Bags API")
        
        # Test performance endpoint
        self.test_endpoint("/api/performance/metrics", test_name="Performance Metrics API")
    
    def test_system_monitoring(self):
        """Test system monitoring endpoints"""
        logger.info("\n=== Testing System Monitoring ===")
        
        # Login as admin
        self.session.post(f"{self.base_url}/login", 
                         data={"username": "admin", "password": "admin"})
        
        # Test monitoring endpoints
        self.test_endpoint("/admin/system-integrity", test_name="System Integrity Check")
        self.test_endpoint("/performance/dashboard", test_name="Performance Dashboard")
    
    def run_all_tests(self):
        """Run all feature tests"""
        logger.info("=" * 60)
        logger.info("Starting TraceTrack Website Feature Testing")
        logger.info("=" * 60)
        
        start_time = time.time()
        
        # Run tests in sequence
        self.test_health_check()
        self.test_authentication()
        self.test_user_management()
        self.test_bag_management()
        self.test_bill_management()
        self.test_excel_upload()
        self.test_api_endpoints()
        self.test_system_monitoring()
        
        # Calculate results
        total_time = time.time() - start_time
        passed = len(self.test_results["passed"])
        failed = len(self.test_results["failed"])
        total = passed + failed
        
        # Calculate average response time
        avg_response_time = (sum(self.test_results["response_times"]) / 
                           len(self.test_results["response_times"]) 
                           if self.test_results["response_times"] else 0)
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {total}")
        logger.info(f"Passed: {passed} ({(passed/total*100):.1f}%)")
        logger.info(f"Failed: {failed} ({(failed/total*100):.1f}%)")
        logger.info(f"Average Response Time: {avg_response_time:.2f}ms")
        logger.info(f"Total Test Time: {total_time:.2f} seconds")
        
        if self.test_results["failed"]:
            logger.info("\n❌ Failed Tests:")
            for failure in self.test_results["failed"]:
                logger.info(f"  - {failure}")
        
        logger.info("\n" + "=" * 60)
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "avg_response_time": avg_response_time,
            "total_time": total_time
        }

if __name__ == "__main__":
    tester = WebsiteFeatureTester()
    results = tester.run_all_tests()
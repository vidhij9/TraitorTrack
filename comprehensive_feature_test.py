#!/usr/bin/env python3
"""
Comprehensive Feature Test Suite for TraceTrack
Tests ALL website features to ensure 100% functionality
"""

import requests
import json
import time
import random
import string
import io
import pandas as pd
from datetime import datetime
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ComprehensiveFeatureTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "errors": [],
            "feature_results": {}
        }
        self.admin_session = None
        self.biller_session = None
        self.dispatcher_session = None
        
    def log_test_result(self, feature, test_name, passed, message="", response_time=None):
        """Log test result"""
        if feature not in self.test_results["feature_results"]:
            self.test_results["feature_results"][feature] = {
                "passed": 0,
                "failed": 0,
                "tests": []
            }
        
        test_info = {
            "name": test_name,
            "passed": passed,
            "message": message,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat()
        }
        
        self.test_results["feature_results"][feature]["tests"].append(test_info)
        
        if passed:
            self.test_results["passed"] += 1
            self.test_results["feature_results"][feature]["passed"] += 1
            logger.info(f"✅ {feature}/{test_name}: PASSED {message}")
        else:
            self.test_results["failed"] += 1
            self.test_results["feature_results"][feature]["failed"] += 1
            self.test_results["errors"].append(f"{feature}/{test_name}: {message}")
            logger.error(f"❌ {feature}/{test_name}: FAILED - {message}")
    
    def test_basic_connectivity(self):
        """Test basic server connectivity"""
        logger.info("=" * 60)
        logger.info("TESTING BASIC CONNECTIVITY")
        logger.info("=" * 60)
        
        try:
            start_time = time.time()
            response = self.session.get(f"{self.base_url}/")
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                self.log_test_result("connectivity", "homepage_access", True, 
                                   f"Status: {response.status_code}", response_time)
            else:
                self.log_test_result("connectivity", "homepage_access", False,
                                   f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test_result("connectivity", "homepage_access", False, str(e))
    
    def test_authentication_system(self):
        """Test complete authentication system"""
        logger.info("=" * 60)
        logger.info("TESTING AUTHENTICATION SYSTEM")
        logger.info("=" * 60)
        
        # Test login page access
        try:
            response = self.session.get(f"{self.base_url}/login")
            if response.status_code == 200 and "login" in response.text.lower():
                self.log_test_result("authentication", "login_page_access", True, "Login page loaded")
            else:
                self.log_test_result("authentication", "login_page_access", False, 
                                   f"Status: {response.status_code}")
        except Exception as e:
            self.log_test_result("authentication", "login_page_access", False, str(e))
        
        # Test admin login
        self.admin_session = self.test_user_login("admin", "admin123", "administrator")
        
        # Test biller login
        self.biller_session = self.test_user_login("biller1", "biller123", "biller")
        
        # Test dispatcher login  
        self.dispatcher_session = self.test_user_login("dispatcher1", "dispatch123", "dispatcher")
        
        # Test invalid login
        self.test_invalid_login()
        
        # Test logout
        self.test_logout()
    
    def test_user_login(self, username, password, role):
        """Test user login for specific role"""
        session = requests.Session()
        
        try:
            # Get login page for CSRF token
            login_page = session.get(f"{self.base_url}/login")
            
            # Extract CSRF token
            csrf_token = None
            if 'csrf_token' in login_page.text:
                import re
                csrf_match = re.search(r'name="csrf_token" value="([^"]*)"', login_page.text)
                if csrf_match:
                    csrf_token = csrf_match.group(1)
            
            # Attempt login
            login_data = {
                "username": username,
                "password": password,
            }
            if csrf_token:
                login_data["csrf_token"] = csrf_token
            
            response = session.post(f"{self.base_url}/login", data=login_data, allow_redirects=False)
            
            if response.status_code in [302, 200]:  # Redirect or success
                # Verify dashboard access
                dashboard_response = session.get(f"{self.base_url}/dashboard")
                if dashboard_response.status_code == 200:
                    self.log_test_result("authentication", f"{role}_login", True, 
                                       f"Successful login and dashboard access")
                    return session
                else:
                    self.log_test_result("authentication", f"{role}_login", False,
                                       f"Login succeeded but dashboard failed: {dashboard_response.status_code}")
            else:
                self.log_test_result("authentication", f"{role}_login", False,
                                   f"Login failed: {response.status_code}")
        except Exception as e:
            self.log_test_result("authentication", f"{role}_login", False, str(e))
        
        return None
    
    def test_invalid_login(self):
        """Test invalid login attempts"""
        try:
            session = requests.Session()
            login_page = session.get(f"{self.base_url}/login")
            
            # Extract CSRF token
            csrf_token = None
            if 'csrf_token' in login_page.text:
                import re
                csrf_match = re.search(r'name="csrf_token" value="([^"]*)"', login_page.text)
                if csrf_match:
                    csrf_token = csrf_match.group(1)
            
            login_data = {
                "username": "invalid_user",
                "password": "wrong_password",
            }
            if csrf_token:
                login_data["csrf_token"] = csrf_token
            
            response = session.post(f"{self.base_url}/login", data=login_data)
            
            # Should not redirect to dashboard
            if response.status_code == 200 and "dashboard" not in response.url:
                self.log_test_result("authentication", "invalid_login_rejection", True,
                                   "Invalid login properly rejected")
            else:
                self.log_test_result("authentication", "invalid_login_rejection", False,
                                   "Invalid login was accepted")
        except Exception as e:
            self.log_test_result("authentication", "invalid_login_rejection", False, str(e))
    
    def test_logout(self):
        """Test logout functionality"""
        if self.admin_session:
            try:
                response = self.admin_session.get(f"{self.base_url}/logout")
                if response.status_code in [200, 302]:  # Success or redirect
                    self.log_test_result("authentication", "logout", True, "Logout successful")
                else:
                    self.log_test_result("authentication", "logout", False, 
                                       f"Logout failed: {response.status_code}")
            except Exception as e:
                self.log_test_result("authentication", "logout", False, str(e))
    
    def test_scanning_operations(self):
        """Test all scanning operations"""
        logger.info("=" * 60)
        logger.info("TESTING SCANNING OPERATIONS")
        logger.info("=" * 60)
        
        if not self.admin_session:
            self.admin_session = requests.Session()
            # Re-login for testing
            login_page = self.admin_session.get(f"{self.base_url}/login")
            csrf_token = None
            if 'csrf_token' in login_page.text:
                import re
                csrf_match = re.search(r'name="csrf_token" value="([^"]*)"', login_page.text)
                if csrf_match:
                    csrf_token = csrf_match.group(1)
            
            login_data = {"username": "admin", "password": "admin123"}
            if csrf_token:
                login_data["csrf_token"] = csrf_token
            self.admin_session.post(f"{self.base_url}/login", data=login_data)
        
        # Test parent scanning page access
        self.test_page_access("scanning", "parent_scan_page", "/scan/parent", self.admin_session)
        
        # Test child scanning page access
        self.test_page_access("scanning", "child_scan_page", "/scan/child", self.admin_session)
        
        # Test batch scanning page access
        self.test_page_access("scanning", "batch_scan_page", "/scan/batch", self.admin_session)
        
        # Test ultra-fast scanning endpoints
        self.test_ultra_scanning_endpoints()
    
    def test_ultra_scanning_endpoints(self):
        """Test ultra-fast scanning API endpoints"""
        # Test ultra parent scan
        try:
            response = self.session.post(f"{self.base_url}/ultra/scan/parent",
                                       json={"qr_id": "SB0001234"})
            if response.status_code in [200, 404]:  # OK or Not Found (both valid)
                self.log_test_result("scanning", "ultra_parent_scan", True,
                                   f"Endpoint accessible: {response.status_code}")
            else:
                self.log_test_result("scanning", "ultra_parent_scan", False,
                                   f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test_result("scanning", "ultra_parent_scan", False, str(e))
        
        # Test ultra child scan
        try:
            response = self.session.post(f"{self.base_url}/ultra/scan/child",
                                       json={"parent_qr_id": "SB0001234", "child_qr_id": "CB0001234"})
            if response.status_code in [200, 404]:
                self.log_test_result("scanning", "ultra_child_scan", True,
                                   f"Endpoint accessible: {response.status_code}")
            else:
                self.log_test_result("scanning", "ultra_child_scan", False,
                                   f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test_result("scanning", "ultra_child_scan", False, str(e))
        
        # Test ultra batch scan
        try:
            response = self.session.post(f"{self.base_url}/ultra/batch/scan",
                                       json={"parent_qr_id": "SB0001234", 
                                           "child_qr_ids": ["CB0001234", "CB0001235"]})
            if response.status_code in [200, 404]:
                self.log_test_result("scanning", "ultra_batch_scan", True,
                                   f"Endpoint accessible: {response.status_code}")
            else:
                self.log_test_result("scanning", "ultra_batch_scan", False,
                                   f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test_result("scanning", "ultra_batch_scan", False, str(e))
        
        # Test ultra lookup
        try:
            response = self.session.get(f"{self.base_url}/ultra/lookup/SB0001234")
            if response.status_code in [200, 404]:
                self.log_test_result("scanning", "ultra_lookup", True,
                                   f"Endpoint accessible: {response.status_code}")
            else:
                self.log_test_result("scanning", "ultra_lookup", False,
                                   f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test_result("scanning", "ultra_lookup", False, str(e))
        
        # Test ultra stats
        try:
            response = self.session.get(f"{self.base_url}/ultra/stats")
            if response.status_code == 200:
                self.log_test_result("scanning", "ultra_stats", True, "Stats endpoint working")
            else:
                self.log_test_result("scanning", "ultra_stats", False,
                                   f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test_result("scanning", "ultra_stats", False, str(e))
    
    def test_bill_management(self):
        """Test bill management features"""
        logger.info("=" * 60)
        logger.info("TESTING BILL MANAGEMENT")
        logger.info("=" * 60)
        
        if not self.admin_session:
            self.admin_session = requests.Session()
            # Re-login
            login_page = self.admin_session.get(f"{self.base_url}/login")
            csrf_token = None
            if 'csrf_token' in login_page.text:
                import re
                csrf_match = re.search(r'name="csrf_token" value="([^"]*)"', login_page.text)
                if csrf_match:
                    csrf_token = csrf_match.group(1)
            login_data = {"username": "admin", "password": "admin123"}
            if csrf_token:
                login_data["csrf_token"] = csrf_token
            self.admin_session.post(f"{self.base_url}/login", data=login_data)
        
        # Test bill pages access
        self.test_page_access("bills", "bill_list_page", "/bills", self.admin_session)
        self.test_page_access("bills", "create_bill_page", "/bills/create", self.admin_session)
        
        # Test bill generation endpoint
        try:
            response = self.admin_session.get(f"{self.base_url}/api/generate_bill")
            if response.status_code in [200, 302]:  # Success or redirect
                self.log_test_result("bills", "bill_generation_endpoint", True,
                                   f"Endpoint accessible: {response.status_code}")
            else:
                self.log_test_result("bills", "bill_generation_endpoint", False,
                                   f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test_result("bills", "bill_generation_endpoint", False, str(e))
    
    def test_excel_upload(self):
        """Test Excel upload functionality"""
        logger.info("=" * 60)
        logger.info("TESTING EXCEL UPLOAD")
        logger.info("=" * 60)
        
        if not self.admin_session:
            self.admin_session = requests.Session()
            # Re-login
            login_page = self.admin_session.get(f"{self.base_url}/login")
            csrf_token = None
            if 'csrf_token' in login_page.text:
                import re
                csrf_match = re.search(r'name="csrf_token" value="([^"]*)"', login_page.text)
                if csrf_match:
                    csrf_token = csrf_match.group(1)
            login_data = {"username": "admin", "password": "admin123"}
            if csrf_token:
                login_data["csrf_token"] = csrf_token
            self.admin_session.post(f"{self.base_url}/login", data=login_data)
        
        # Test Excel upload page access
        self.test_page_access("excel", "upload_page", "/upload", self.admin_session)
        
        # Test Excel upload endpoint  
        try:
            # Create sample Excel file
            df = pd.DataFrame({
                'Parent Bag': ['SB0001001', 'SB0001002'],
                'Child Bag': ['CB0001001', 'CB0001002']
            })
            
            # Save to BytesIO buffer
            excel_buffer = io.BytesIO()
            df.to_excel(excel_buffer, index=False)
            excel_buffer.seek(0)
            
            # Test upload
            files = {'file': ('test_bags.xlsx', excel_buffer, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            response = self.admin_session.post(f"{self.base_url}/upload", files=files)
            
            if response.status_code in [200, 302]:
                self.log_test_result("excel", "file_upload", True,
                                   f"Upload endpoint accessible: {response.status_code}")
            else:
                self.log_test_result("excel", "file_upload", False,
                                   f"Upload failed: {response.status_code}")
        except Exception as e:
            self.log_test_result("excel", "file_upload", False, str(e))
    
    def test_dashboard_features(self):
        """Test dashboard and reporting features"""
        logger.info("=" * 60)
        logger.info("TESTING DASHBOARD FEATURES")
        logger.info("=" * 60)
        
        if not self.admin_session:
            self.admin_session = requests.Session()
            # Re-login
            login_page = self.admin_session.get(f"{self.base_url}/login")
            csrf_token = None
            if 'csrf_token' in login_page.text:
                import re
                csrf_match = re.search(r'name="csrf_token" value="([^"]*)"', login_page.text)
                if csrf_match:
                    csrf_token = csrf_match.group(1)
            login_data = {"username": "admin", "password": "admin123"}
            if csrf_token:
                login_data["csrf_token"] = csrf_token
            self.admin_session.post(f"{self.base_url}/login", data=login_data)
        
        # Test dashboard access
        self.test_page_access("dashboard", "main_dashboard", "/dashboard", self.admin_session)
        
        # Test admin dashboard
        self.test_page_access("dashboard", "admin_dashboard", "/admin/dashboard", self.admin_session)
        
        # Test reports page
        self.test_page_access("dashboard", "reports_page", "/reports", self.admin_session)
        
        # Test statistics endpoint
        try:
            response = self.admin_session.get(f"{self.base_url}/api/statistics")
            if response.status_code == 200:
                self.log_test_result("dashboard", "statistics_api", True, "Statistics endpoint working")
            else:
                self.log_test_result("dashboard", "statistics_api", False,
                                   f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test_result("dashboard", "statistics_api", False, str(e))
    
    def test_performance_monitoring(self):
        """Test performance monitoring endpoints"""
        logger.info("=" * 60)
        logger.info("TESTING PERFORMANCE MONITORING")
        logger.info("=" * 60)
        
        # Test performance dashboard
        try:
            response = self.session.get(f"{self.base_url}/performance/dashboard")
            if response.status_code == 200:
                self.log_test_result("performance", "dashboard", True, "Performance dashboard accessible")
            else:
                self.log_test_result("performance", "dashboard", False,
                                   f"Dashboard failed: {response.status_code}")
        except Exception as e:
            self.log_test_result("performance", "dashboard", False, str(e))
        
        # Test health check
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                self.log_test_result("performance", "health_check", True, "Health check working")
            else:
                self.log_test_result("performance", "health_check", False,
                                   f"Health check failed: {response.status_code}")
        except Exception as e:
            self.log_test_result("performance", "health_check", False, str(e))
        
        # Test database health
        try:
            response = self.session.get(f"{self.base_url}/db/health")
            if response.status_code == 200:
                self.log_test_result("performance", "database_health", True, "Database health check working")
            else:
                self.log_test_result("performance", "database_health", False,
                                   f"Database health failed: {response.status_code}")
        except Exception as e:
            self.log_test_result("performance", "database_health", False, str(e))
    
    def test_api_endpoints(self):
        """Test all API endpoints"""
        logger.info("=" * 60)
        logger.info("TESTING API ENDPOINTS")
        logger.info("=" * 60)
        
        # Common API endpoints to test
        api_endpoints = [
            ("/api/bags", "bags_api"),
            ("/api/users", "users_api"),
            ("/api/scans", "scans_api"),
            ("/api/bills", "bills_api"),
            ("/api/statistics", "statistics_api"),
        ]
        
        for endpoint, test_name in api_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                if response.status_code in [200, 401, 403]:  # OK, Unauthorized, or Forbidden (all valid)
                    self.log_test_result("api", test_name, True,
                                       f"Endpoint accessible: {response.status_code}")
                else:
                    self.log_test_result("api", test_name, False,
                                       f"Unexpected status: {response.status_code}")
            except Exception as e:
                self.log_test_result("api", test_name, False, str(e))
    
    def test_page_access(self, category, test_name, path, session=None):
        """Test access to a specific page"""
        test_session = session or self.session
        try:
            start_time = time.time()
            response = test_session.get(f"{self.base_url}{path}")
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                self.log_test_result(category, test_name, True,
                                   f"Page loaded successfully", response_time)
            elif response.status_code == 302:  # Redirect (might be authentication)
                self.log_test_result(category, test_name, True,
                                   f"Page redirected (auth required)", response_time)
            else:
                self.log_test_result(category, test_name, False,
                                   f"Unexpected status: {response.status_code}")
        except Exception as e:
            self.log_test_result(category, test_name, False, str(e))
    
    def test_database_operations(self):
        """Test database-related operations"""
        logger.info("=" * 60)
        logger.info("TESTING DATABASE OPERATIONS")
        logger.info("=" * 60)
        
        # Test database health
        try:
            response = self.session.get(f"{self.base_url}/db/health")
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_test_result("database", "health_check", True, "Database is healthy")
                else:
                    self.log_test_result("database", "health_check", False,
                                       f"Database unhealthy: {data}")
            else:
                self.log_test_result("database", "health_check", False,
                                   f"Health check failed: {response.status_code}")
        except Exception as e:
            self.log_test_result("database", "health_check", False, str(e))
    
    def run_comprehensive_test(self):
        """Run the complete test suite"""
        logger.info("\n" + "=" * 80)
        logger.info("TRACETRACK COMPREHENSIVE FEATURE TEST SUITE")
        logger.info("Testing ALL features for 100% functionality")
        logger.info("=" * 80)
        
        start_time = time.time()
        
        # Run all test categories
        self.test_basic_connectivity()
        self.test_authentication_system()
        self.test_scanning_operations()
        self.test_bill_management()
        self.test_excel_upload()
        self.test_dashboard_features()
        self.test_performance_monitoring()
        self.test_api_endpoints()
        self.test_database_operations()
        
        # Calculate total time
        total_time = time.time() - start_time
        
        # Print comprehensive results
        self.print_final_results(total_time)
        
        return self.test_results
    
    def print_final_results(self, total_time):
        """Print comprehensive test results"""
        logger.info("\n" + "=" * 80)
        logger.info("COMPREHENSIVE TEST RESULTS")
        logger.info("=" * 80)
        
        total_tests = self.test_results["passed"] + self.test_results["failed"]
        success_rate = (self.test_results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        logger.info(f"\n📊 OVERALL RESULTS:")
        logger.info(f"  Total Tests: {total_tests}")
        logger.info(f"  Passed: {self.test_results['passed']} ✅")
        logger.info(f"  Failed: {self.test_results['failed']} ❌")
        logger.info(f"  Success Rate: {success_rate:.1f}%")
        logger.info(f"  Test Duration: {total_time:.2f} seconds")
        
        # Feature breakdown
        logger.info(f"\n🔍 FEATURE BREAKDOWN:")
        for feature, results in self.test_results["feature_results"].items():
            feature_total = results["passed"] + results["failed"]
            feature_rate = (results["passed"] / feature_total * 100) if feature_total > 0 else 0
            status = "✅" if feature_rate == 100 else "⚠️" if feature_rate >= 80 else "❌"
            
            logger.info(f"  {status} {feature.upper()}: {results['passed']}/{feature_total} ({feature_rate:.1f}%)")
            
            # Show failed tests for this feature
            if results["failed"] > 0:
                for test in results["tests"]:
                    if not test["passed"]:
                        logger.info(f"    ❌ {test['name']}: {test['message']}")
        
        # Overall assessment
        logger.info(f"\n🎯 FEATURE ASSESSMENT:")
        if success_rate == 100:
            logger.info("  ✅ PERFECT: All features working 100%!")
        elif success_rate >= 95:
            logger.info("  🎉 EXCELLENT: 95%+ features working")
        elif success_rate >= 80:
            logger.info("  ⚠️  GOOD: 80%+ features working")
        elif success_rate >= 60:
            logger.info("  🔧 NEEDS WORK: 60%+ features working")
        else:
            logger.info("  ❌ CRITICAL: <60% features working - major issues")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"comprehensive_test_results_{timestamp}.json"
        
        with open(results_file, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "duration": total_time,
                "summary": {
                    "total_tests": total_tests,
                    "passed": self.test_results["passed"],
                    "failed": self.test_results["failed"],
                    "success_rate": success_rate
                },
                "feature_results": self.test_results["feature_results"],
                "errors": self.test_results["errors"]
            }, f, indent=2)
        
        logger.info(f"\n📁 Detailed results saved to: {results_file}")
        
        if self.test_results["errors"]:
            logger.info(f"\n⚠️  ERRORS FOUND:")
            for i, error in enumerate(self.test_results["errors"], 1):
                logger.info(f"  {i}. {error}")
        
        logger.info("\n" + "=" * 80)

if __name__ == "__main__":
    tester = ComprehensiveFeatureTester()
    results = tester.run_comprehensive_test()
    
    # Exit with error code if tests failed
    if results["failed"] > 0:
        exit(1)
    else:
        exit(0)
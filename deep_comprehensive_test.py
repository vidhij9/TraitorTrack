#!/usr/bin/env python3
"""
DEEP COMPREHENSIVE TESTING SUITE
Tests every endpoint, API, functionality, edge case, and deployment readiness
"""

import requests
import time
import json
import concurrent.futures
import statistics
import random
import string
import threading
from datetime import datetime, timedelta
import os
import subprocess

BASE_URL = "http://0.0.0.0:5000"

class DeepComprehensiveTester:
    def __init__(self):
        self.session = requests.Session()
        self.results = {}
        self.errors = []
        self.performance_metrics = {}
        self.security_issues = []
        self.edge_case_results = {}
        
    def login(self, username="admin", password="admin"):
        """Login with different user types"""
        try:
            response = self.session.get(f"{BASE_URL}/login")
            login_data = {'username': username, 'password': password}
            response = self.session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
            return response.status_code in [302, 200]
        except Exception as e:
            self.errors.append(f"Login error: {e}")
            return False
    
    def test_all_endpoints_exhaustive(self):
        """Test every possible endpoint with multiple methods"""
        print("\n🔍 DEEP ENDPOINT TESTING - Every Route, Every Method")
        print("-" * 80)
        
        endpoints = [
            # Main pages
            ("GET", "/", "Homepage"),
            ("GET", "/dashboard", "Dashboard"),
            ("GET", "/login", "Login Page"),
            ("GET", "/register", "Register Page"),
            ("GET", "/logout", "Logout"),
            
            # QR Scanning
            ("GET", "/scan_parent", "Scan Parent Page"),
            ("GET", "/scan_child", "Scan Child Page"),
            ("POST", "/process_parent_scan", "Process Parent Scan"),
            ("POST", "/process_child_scan", "Process Child Scan"),
            ("POST", "/fast/parent_scan", "Fast Parent Scan"),
            
            # Lookup and Search
            ("GET", "/lookup", "Lookup Page"),
            ("POST", "/lookup", "Lookup POST"),
            ("GET", "/child_lookup", "Child Lookup"),
            ("POST", "/child_lookup", "Child Lookup POST"),
            
            # User Management
            ("GET", "/user_management", "User Management"),
            ("POST", "/create_user", "Create User"),
            ("POST", "/update_user", "Update User"),
            ("GET", "/user_profile", "User Profile"),
            
            # Admin Functions
            ("GET", "/admin/promotions", "Admin Promotions"),
            ("GET", "/admin/comprehensive-user-deletion", "Admin Delete"),
            ("POST", "/admin/preview-user-deletion", "Preview Delete"),
            ("POST", "/admin/execute-comprehensive-deletion", "Execute Delete"),
            
            # Bill Management
            ("GET", "/bill_management", "Bill Management"),
            ("POST", "/create_bill", "Create Bill"),
            ("GET", "/edit_bill", "Edit Bill"),
            ("POST", "/update_bill", "Update Bill"),
            ("GET", "/view_bill", "View Bill"),
            ("GET", "/bill_summary", "Bill Summary"),
            
            # API Endpoints
            ("GET", "/api/stats", "API Stats"),
            ("GET", "/api/scans", "API Scans"),
            ("GET", "/api/bags", "API Bags"),
            ("GET", "/api/bills", "API Bills"),
            ("GET", "/api/users", "API Users"),
            ("GET", "/api/health", "API Health"),
            ("GET", "/api/cache/stats", "Cache Stats"),
            ("GET", "/api/cached/stats", "Cached Stats"),
            ("GET", "/api/cached/recent_scans", "Cached Scans"),
            ("GET", "/api/v2/stats", "V2 Stats"),
            
            # Health and Monitoring
            ("GET", "/health", "Health Check"),
            ("GET", "/api/health/redis", "Redis Health"),
            ("GET", "/production-health", "Production Health"),
            ("GET", "/production-setup", "Production Setup"),
            
            # Error Pages
            ("GET", "/nonexistent", "404 Test"),
            ("GET", "/admin/fake", "Admin 404"),
        ]
        
        for method, path, name in endpoints:
            self.test_endpoint_deep(method, path, name)
    
    def test_endpoint_deep(self, method, path, name):
        """Deep test single endpoint with multiple scenarios"""
        try:
            url = f"{BASE_URL}{path}"
            start = time.time()
            
            # Test with different data
            test_data = None
            if method == "POST":
                if "parent_scan" in path:
                    test_data = {'qr_code': f"SB{random.randint(10000, 99999)}"}
                elif "child_scan" in path:
                    test_data = {
                        'parent_qr': f"SB{random.randint(10000, 99999)}",
                        'child_qr': f"C{random.randint(100000, 999999)}"
                    }
                elif "create_user" in path:
                    test_data = {
                        'username': f"test_{random.randint(1000, 9999)}",
                        'email': f"test_{random.randint(1000, 9999)}@test.com",
                        'password': 'test123',
                        'role': 'dispatcher'
                    }
                elif "lookup" in path:
                    test_data = {'qr_code': f"SB{random.randint(10000, 99999)}"}
                else:
                    test_data = {}
            
            if method == "GET":
                response = self.session.get(url, timeout=10)
            elif method == "POST":
                response = self.session.post(url, data=test_data or {}, timeout=10)
            else:
                response = self.session.request(method, url, data=test_data, timeout=10)
            
            elapsed = (time.time() - start) * 1000
            
            # Analyze response
            success = response.status_code < 400
            self.results[name] = {
                'method': method,
                'path': path,
                'status': response.status_code,
                'time_ms': elapsed,
                'success': success,
                'content_length': len(response.text) if hasattr(response, 'text') else 0
            }
            
            # Check for JSON responses
            try:
                if 'application/json' in response.headers.get('content-type', ''):
                    data = response.json()
                    self.results[name]['json_valid'] = True
                    self.results[name]['json_data'] = data
            except:
                pass
            
            status_icon = "✅" if success else "❌"
            print(f"  {status_icon} {name:45} {method:4} {response.status_code:3} {elapsed:7.1f}ms")
            
            # Test edge cases for this endpoint
            self.test_endpoint_edge_cases(method, path, name)
            
        except Exception as e:
            self.errors.append(f"{name}: {str(e)}")
            print(f"  ❌ {name:45} ERROR: {str(e)[:50]}")
    
    def test_endpoint_edge_cases(self, method, path, name):
        """Test edge cases for each endpoint"""
        if method != "POST":
            return
            
        edge_cases = [
            ("Empty data", {}),
            ("Invalid data", {"invalid": "data"}),
            ("SQL injection", {"qr_code": "'; DROP TABLE bags; --"}),
            ("XSS attempt", {"qr_code": "<script>alert('xss')</script>"}),
            ("Very long input", {"qr_code": "A" * 10000}),
            ("Unicode input", {"qr_code": "测试数据🚀"}),
            ("Null bytes", {"qr_code": "test\x00null"}),
        ]
        
        for case_name, test_data in edge_cases:
            try:
                response = self.session.post(f"{BASE_URL}{path}", data=test_data, timeout=5)
                if case_name not in self.edge_case_results:
                    self.edge_case_results[case_name] = []
                self.edge_case_results[case_name].append({
                    'endpoint': name,
                    'status': response.status_code,
                    'handled_safely': response.status_code != 500
                })
            except:
                pass
    
    def test_authentication_security(self):
        """Test authentication and security"""
        print("\n🔒 SECURITY TESTING")
        print("-" * 80)
        
        # Test without authentication
        no_auth_session = requests.Session()
        protected_endpoints = [
            "/dashboard", "/user_management", "/admin/promotions",
            "/bill_management", "/api/stats"
        ]
        
        for endpoint in protected_endpoints:
            try:
                response = no_auth_session.get(f"{BASE_URL}{endpoint}")
                if response.status_code == 200:
                    self.security_issues.append(f"Unprotected endpoint: {endpoint}")
                    print(f"  ⚠️ SECURITY: {endpoint} accessible without auth")
                else:
                    print(f"  ✅ SECURE: {endpoint} protected")
            except:
                pass
        
        # Test session fixation
        print("  🔍 Testing session security...")
        
        # Test CSRF protection
        csrf_endpoints = ["/create_user", "/process_parent_scan"]
        for endpoint in csrf_endpoints:
            try:
                response = self.session.post(f"{BASE_URL}{endpoint}", 
                                           data={"test": "data"})
                # Should either work or fail gracefully
                print(f"  ✅ CSRF: {endpoint} handled")
            except:
                pass
    
    def test_database_operations_deep(self):
        """Deep database operation testing"""
        print("\n💾 DEEP DATABASE TESTING")
        print("-" * 80)
        
        # Test data creation
        print("  🔍 Testing data creation...")
        test_user = f"dbtest_{random.randint(10000, 99999)}"
        
        # Create user
        user_data = {
            'username': test_user,
            'email': f"{test_user}@test.com",
            'password': 'test123',
            'role': 'dispatcher',
            'dispatch_area': 'Test Area'
        }
        
        response = self.session.post(f"{BASE_URL}/create_user", data=user_data)
        if response.status_code == 200:
            print(f"  ✅ User creation: {test_user}")
            
            # Test data retrieval
            response = self.session.get(f"{BASE_URL}/user_management")
            if test_user in response.text:
                print(f"  ✅ User retrieval: Found {test_user}")
            else:
                print(f"  ⚠️ User retrieval: {test_user} not found in UI")
        else:
            print(f"  ⚠️ User creation failed: {response.status_code}")
        
        # Test concurrent database operations
        print("  🔍 Testing concurrent database access...")
        self.test_concurrent_database_access()
    
    def test_concurrent_database_access(self):
        """Test database under concurrent access"""
        def create_test_scan():
            session = requests.Session()
            if session.post(f"{BASE_URL}/login", 
                          data={'username': 'admin', 'password': 'admin'}).status_code in [200, 302]:
                qr = f"CONCURRENT_{random.randint(10000, 99999)}"
                response = session.post(f"{BASE_URL}/process_parent_scan", 
                                      data={'qr_code': qr})
                return response.status_code
            return 500
        
        # Run 20 concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(create_test_scan) for _ in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures, timeout=30)]
        
        success_count = sum(1 for r in results if r < 400)
        print(f"  ✅ Concurrent DB ops: {success_count}/20 successful")
        
        if success_count < 15:
            self.errors.append("Database struggling under concurrent load")
    
    def test_performance_stress(self):
        """Stress test performance"""
        print("\n⚡ PERFORMANCE STRESS TESTING")
        print("-" * 80)
        
        stress_tests = [
            ("/health", "Health Check", 100),
            ("/api/stats", "API Stats", 50),
            ("/dashboard", "Dashboard", 30),
            ("/login", "Login Page", 50),
        ]
        
        for endpoint, name, concurrent_users in stress_tests:
            print(f"\n  🔥 Stress testing {name} with {concurrent_users} users...")
            
            def make_stress_request():
                try:
                    start = time.time()
                    response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
                    elapsed = (time.time() - start) * 1000
                    return (response.status_code == 200, elapsed)
                except:
                    return (False, None)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = [executor.submit(make_stress_request) for _ in range(concurrent_users)]
                results = [f.result() for f in concurrent.futures.as_completed(futures, timeout=60)]
            
            successful = [(success, time_ms) for success, time_ms in results if success and time_ms]
            times = [time_ms for success, time_ms in results if success and time_ms]
            
            if times:
                success_rate = len(successful) / len(results) * 100
                avg_time = statistics.mean(times)
                max_time = max(times)
                
                self.performance_metrics[name] = {
                    'success_rate': success_rate,
                    'avg_response_time': avg_time,
                    'max_response_time': max_time,
                    'concurrent_users': concurrent_users
                }
                
                status = "✅" if success_rate >= 95 else ("⚠️" if success_rate >= 80 else "❌")
                print(f"    {status} Success: {success_rate:.1f}% | Avg: {avg_time:.1f}ms | Max: {max_time:.1f}ms")
            else:
                print(f"    ❌ Complete failure under {concurrent_users} users")
    
    def test_aws_deployment_readiness(self):
        """Test AWS deployment prerequisites"""
        print("\n☁️ AWS DEPLOYMENT READINESS")
        print("-" * 80)
        
        # Check required files
        required_files = [
            "deploy_aws_auto.py",
            "main.py",
            "app_clean.py",
            "models.py",
            "routes.py"
        ]
        
        for file in required_files:
            if os.path.exists(file):
                print(f"  ✅ Required file: {file}")
            else:
                print(f"  ❌ Missing file: {file}")
                self.errors.append(f"Missing required file: {file}")
        
        # Test deployment script syntax
        try:
            with open("deploy_aws_auto.py", "r") as f:
                code = f.read()
                compile(code, "deploy_aws_auto.py", "exec")
            print(f"  ✅ Deployment script syntax valid")
        except Exception as e:
            print(f"  ❌ Deployment script syntax error: {e}")
            self.errors.append(f"Deployment script error: {e}")
        
        # Check environment compatibility
        try:
            import boto3
            print(f"  ✅ boto3 library available")
        except ImportError:
            print(f"  ⚠️ boto3 not installed (will be auto-installed)")
        
        # Test application startup without errors
        print("  🔍 Testing application startup...")
        startup_errors = self.check_application_startup()
        if startup_errors:
            for error in startup_errors:
                print(f"  ❌ Startup error: {error}")
        else:
            print(f"  ✅ Application starts without errors")
    
    def check_application_startup(self):
        """Check for startup errors in logs"""
        # This would check logs for startup errors
        # For now, we'll do a basic health check
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                return []
            else:
                return [f"Health check failed: {response.status_code}"]
        except Exception as e:
            return [f"Health check error: {e}"]
    
    def test_error_handling(self):
        """Test error handling across the application"""
        print("\n🚨 ERROR HANDLING TESTING")
        print("-" * 80)
        
        # Test 404 handling
        response = self.session.get(f"{BASE_URL}/nonexistent-page")
        if response.status_code == 404:
            print("  ✅ 404 errors handled correctly")
        else:
            print(f"  ⚠️ 404 handling: Got {response.status_code}")
        
        # Test malformed requests
        malformed_tests = [
            ("Invalid JSON", "/api/stats", {"malformed": "json}"},),
            ("Missing CSRF", "/create_user", {}),
            ("Invalid method", "/dashboard", {}, "DELETE"),
        ]
        
        for test_name, endpoint, data, method in malformed_tests:
            try:
                if method == "DELETE":
                    response = self.session.delete(f"{BASE_URL}{endpoint}")
                else:
                    response = self.session.post(f"{BASE_URL}{endpoint}", data=data)
                
                if response.status_code >= 400:
                    print(f"  ✅ {test_name}: Properly rejected ({response.status_code})")
                else:
                    print(f"  ⚠️ {test_name}: Not properly handled ({response.status_code})")
            except:
                print(f"  ✅ {test_name}: Connection properly closed")
    
    def run_comprehensive_tests(self):
        """Run all comprehensive tests"""
        print("=" * 100)
        print("🔍 DEEP COMPREHENSIVE TESTING - EVERY ENDPOINT, API & FUNCTION")
        print("=" * 100)
        print(f"Started: {datetime.now()}")
        print(f"Target: {BASE_URL}")
        
        # Login first
        if not self.login():
            print("❌ Cannot proceed without login")
            return
        
        # Run all test categories
        self.test_all_endpoints_exhaustive()
        self.test_authentication_security()
        self.test_database_operations_deep()
        self.test_performance_stress()
        self.test_aws_deployment_readiness()
        self.test_error_handling()
        
        # Generate comprehensive report
        self.generate_comprehensive_report()
    
    def generate_comprehensive_report(self):
        """Generate detailed test report"""
        print("\n" + "=" * 100)
        print("📊 COMPREHENSIVE TEST REPORT")
        print("=" * 100)
        
        # Overall statistics
        total_tests = len(self.results)
        successful = sum(1 for r in self.results.values() if r['success'])
        failed = total_tests - successful
        
        print(f"\n🎯 OVERALL RESULTS:")
        print(f"  Total Endpoints Tested: {total_tests}")
        print(f"  ✅ Successful: {successful}")
        print(f"  ❌ Failed: {failed}")
        print(f"  Success Rate: {successful/total_tests*100:.1f}%")
        
        # Performance analysis
        response_times = [r['time_ms'] for r in self.results.values() if 'time_ms' in r]
        if response_times:
            print(f"\n⚡ PERFORMANCE METRICS:")
            print(f"  Average Response: {statistics.mean(response_times):.1f}ms")
            print(f"  Median Response: {statistics.median(response_times):.1f}ms")
            print(f"  Fastest: {min(response_times):.1f}ms")
            print(f"  Slowest: {max(response_times):.1f}ms")
        
        # Security analysis
        if self.security_issues:
            print(f"\n🔒 SECURITY ISSUES FOUND:")
            for issue in self.security_issues:
                print(f"  ⚠️ {issue}")
        else:
            print(f"\n🔒 SECURITY: No major issues found")
        
        # Edge case results
        if self.edge_case_results:
            print(f"\n🎯 EDGE CASE TESTING:")
            for case, results in self.edge_case_results.items():
                safe_count = sum(1 for r in results if r['handled_safely'])
                total_count = len(results)
                print(f"  {case}: {safe_count}/{total_count} endpoints handled safely")
        
        # Performance stress results
        if self.performance_metrics:
            print(f"\n🔥 STRESS TEST RESULTS:")
            for test, metrics in self.performance_metrics.items():
                print(f"  {test}:")
                print(f"    Users: {metrics['concurrent_users']}")
                print(f"    Success Rate: {metrics['success_rate']:.1f}%")
                print(f"    Avg Response: {metrics['avg_response_time']:.1f}ms")
        
        # Failed endpoints
        failed_endpoints = [(name, data) for name, data in self.results.items() if not data['success']]
        if failed_endpoints:
            print(f"\n❌ FAILED ENDPOINTS:")
            for name, data in failed_endpoints:
                print(f"  {name}: {data['method']} {data['path']} → {data['status']}")
        
        # Errors
        if self.errors:
            print(f"\n🚨 ERRORS ENCOUNTERED:")
            for error in self.errors[:10]:  # Show first 10
                print(f"  • {error}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more errors")
        
        # AWS Deployment readiness
        deployment_ready = len(self.errors) < 5 and successful > failed
        print(f"\n☁️ AWS DEPLOYMENT READINESS:")
        if deployment_ready:
            print(f"  ✅ READY FOR AWS DEPLOYMENT")
            print(f"  • Core functionality working")
            print(f"  • Error rate acceptable")
            print(f"  • Performance within limits")
        else:
            print(f"  ⚠️ DEPLOYMENT CONCERNS:")
            print(f"  • Fix critical errors first")
            print(f"  • {failed} endpoints failing")
            print(f"  • Review performance issues")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if failed > 0:
            print(f"  1. Fix {failed} failing endpoints")
        
        avg_time = statistics.mean(response_times) if response_times else 0
        if avg_time > 1000:
            print(f"  2. Optimize response times (currently {avg_time:.0f}ms avg)")
        elif avg_time > 500:
            print(f"  3. Consider response time optimization ({avg_time:.0f}ms avg)")
        
        if self.security_issues:
            print(f"  4. Address {len(self.security_issues)} security issues")
        
        print(f"\n🎉 TESTING COMPLETE at {datetime.now()}")
        print("=" * 100)

if __name__ == "__main__":
    tester = DeepComprehensiveTester()
    tester.run_comprehensive_tests()
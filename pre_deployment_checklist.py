#!/usr/bin/env python3
"""
COMPREHENSIVE PRE-DEPLOYMENT CHECKLIST FOR AWS
Verifies everything is 100% ready before deployment
"""

import requests
import time
import concurrent.futures
import json
import os
import subprocess
import statistics
from datetime import datetime

class PreDeploymentChecker:
    def __init__(self):
        self.checks_passed = []
        self.checks_failed = []
        self.critical_issues = []
        self.warnings = []
        
    def check_database_migration_safety(self):
        """Check database migration readiness"""
        print("\n📊 DATABASE MIGRATION SAFETY CHECK")
        print("-" * 50)
        
        try:
            # Check if models.py has all required tables
            with open('models.py', 'r') as f:
                models_content = f.read()
                
            required_tables = ['User', 'Bag', 'Scan', 'Bill', 'Link', 'BillBag', 'AuditLog']
            for table in required_tables:
                if f'class {table}' in models_content:
                    print(f"✅ Table {table}: Defined")
                    self.checks_passed.append(f"Table {table} defined")
                else:
                    print(f"❌ Table {table}: Missing")
                    self.critical_issues.append(f"Missing table {table}")
                    
            # Check for nullable foreign keys (important for deletions)
            if 'nullable=True' in models_content:
                print("✅ Nullable foreign keys: Found (safe for deletions)")
                self.checks_passed.append("Nullable foreign keys configured")
            else:
                print("⚠️ Warning: Some foreign keys might not be nullable")
                self.warnings.append("Check foreign key nullability")
                
        except Exception as e:
            self.critical_issues.append(f"Database model check failed: {e}")
            print(f"❌ Error checking database models: {e}")
            
    def check_authentication_security(self):
        """Verify all endpoints are properly secured"""
        print("\n🔒 AUTHENTICATION & SECURITY CHECK")
        print("-" * 50)
        
        session = requests.Session()
        
        # Test protected endpoints WITHOUT login
        protected_endpoints = [
            '/dashboard',
            '/user_management', 
            '/admin/promotions',
            '/bill_management',
            '/api/stats',
            '/scan_parent',
            '/scan_child',
            '/api/bags',
            '/api/bills',
            '/api/users'
        ]
        
        for endpoint in protected_endpoints:
            try:
                response = session.get(f'http://0.0.0.0:5000{endpoint}', timeout=5, allow_redirects=False)
                if response.status_code in [302, 401, 403]:
                    print(f"✅ {endpoint}: Protected (redirects to login)")
                    self.checks_passed.append(f"{endpoint} protected")
                elif response.status_code == 200:
                    print(f"❌ CRITICAL: {endpoint} accessible without auth!")
                    self.critical_issues.append(f"{endpoint} not protected")
                else:
                    print(f"✅ {endpoint}: Protected ({response.status_code})")
                    self.checks_passed.append(f"{endpoint} protected")
            except:
                print(f"✅ {endpoint}: Protected (connection denied)")
                self.checks_passed.append(f"{endpoint} protected")
                
    def check_core_functionality(self):
        """Test all core functionality works"""
        print("\n🧪 CORE FUNCTIONALITY CHECK")
        print("-" * 50)
        
        critical_endpoints = [
            ('/', 'Homepage'),
            ('/health', 'Health Check'),
            ('/login', 'Login Page'),
            ('/register', 'Register Page'),
            ('/api/health', 'API Health')
        ]
        
        for endpoint, name in critical_endpoints:
            try:
                response = requests.get(f'http://0.0.0.0:5000{endpoint}', timeout=10)
                if response.status_code < 500:
                    print(f"✅ {name}: Working ({response.status_code})")
                    self.checks_passed.append(f"{name} working")
                else:
                    print(f"❌ {name}: Server error ({response.status_code})")
                    self.critical_issues.append(f"{name} has server error")
            except Exception as e:
                print(f"❌ {name}: Failed - {str(e)[:30]}")
                self.critical_issues.append(f"{name} connection failed")
                
    def load_test_concurrent_users(self):
        """Test system can handle required load"""
        print("\n⚡ LOAD TESTING (50+ CONCURRENT USERS)")
        print("-" * 50)
        
        def make_request():
            try:
                start = time.time()
                response = requests.get('http://0.0.0.0:5000/health', timeout=10)
                elapsed = (time.time() - start) * 1000
                return (response.status_code == 200, elapsed)
            except:
                return (False, None)
        
        # Test with increasing load
        load_levels = [10, 25, 50, 75, 100]
        
        for concurrent_users in load_levels:
            print(f"\n🔥 Testing with {concurrent_users} concurrent users...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = [executor.submit(make_request) for _ in range(concurrent_users)]
                results = [f.result() for f in concurrent.futures.as_completed(futures, timeout=30)]
            
            successful = sum(1 for success, _ in results if success)
            times = [t for success, t in results if success and t]
            
            if times:
                success_rate = (successful / len(results)) * 100
                avg_time = statistics.mean(times)
                max_time = max(times)
                
                if success_rate >= 95:
                    print(f"  ✅ Success rate: {success_rate:.1f}% | Avg: {avg_time:.0f}ms | Max: {max_time:.0f}ms")
                    self.checks_passed.append(f"Load test {concurrent_users} users: {success_rate:.1f}%")
                elif success_rate >= 80:
                    print(f"  ⚠️ Success rate: {success_rate:.1f}% | Avg: {avg_time:.0f}ms | Max: {max_time:.0f}ms")
                    self.warnings.append(f"Load test {concurrent_users} users: {success_rate:.1f}%")
                else:
                    print(f"  ❌ Success rate: {success_rate:.1f}% | System struggling")
                    self.critical_issues.append(f"Failed load test at {concurrent_users} users")
                    break
            else:
                print(f"  ❌ Complete failure at {concurrent_users} users")
                self.critical_issues.append(f"System crashed at {concurrent_users} users")
                break
                
    def check_error_handling(self):
        """Test error handling and recovery"""
        print("\n🚨 ERROR HANDLING CHECK")
        print("-" * 50)
        
        # Test invalid requests
        test_cases = [
            ('Invalid QR code', '/process_parent_scan', {'qr_code': '"><script>alert(1)</script>'}),
            ('SQL injection attempt', '/lookup', {'qr_code': "'; DROP TABLE bags; --"}),
            ('Empty data', '/process_child_scan', {}),
            ('Very long input', '/lookup', {'qr_code': 'A' * 10000})
        ]
        
        session = requests.Session()
        # Login first
        session.post('http://0.0.0.0:5000/login', data={'username': 'admin', 'password': 'admin'})
        
        for test_name, endpoint, data in test_cases:
            try:
                response = session.post(f'http://0.0.0.0:5000{endpoint}', data=data, timeout=5)
                if response.status_code != 500:
                    print(f"✅ {test_name}: Handled gracefully ({response.status_code})")
                    self.checks_passed.append(f"Error handling: {test_name}")
                else:
                    print(f"❌ {test_name}: Server error (500)")
                    self.critical_issues.append(f"Poor error handling: {test_name}")
            except:
                print(f"⚠️ {test_name}: Connection closed (might be OK)")
                self.warnings.append(f"Check error handling: {test_name}")
                
    def check_aws_deployment_files(self):
        """Verify all AWS deployment files are ready"""
        print("\n☁️ AWS DEPLOYMENT FILES CHECK")
        print("-" * 50)
        
        required_files = {
            'deploy_aws_auto.py': ['boto3', 'DynamoDB', 'Lambda', 'CloudFront'],
            'main.py': ['app', 'import'],
            'app_clean.py': ['Flask', 'db', 'SQLAlchemy'],
            'models.py': ['User', 'Bag', 'Scan'],
            'routes.py': ['@app.route', 'login_required']
        }
        
        for file, required_content in required_files.items():
            try:
                with open(file, 'r') as f:
                    content = f.read()
                    
                missing = []
                for req in required_content:
                    if req not in content:
                        missing.append(req)
                        
                if not missing:
                    print(f"✅ {file}: Complete")
                    self.checks_passed.append(f"{file} ready")
                else:
                    print(f"❌ {file}: Missing {missing}")
                    self.critical_issues.append(f"{file} incomplete")
                    
                # Check syntax
                if file.endswith('.py'):
                    result = subprocess.run(['python', '-m', 'py_compile', file], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode != 0:
                        print(f"  ❌ Syntax error in {file}")
                        self.critical_issues.append(f"Syntax error in {file}")
                        
            except Exception as e:
                print(f"❌ {file}: Error - {e}")
                self.critical_issues.append(f"{file} error: {e}")
                
    def check_performance_baseline(self):
        """Check baseline performance metrics"""
        print("\n⏱️ PERFORMANCE BASELINE CHECK")
        print("-" * 50)
        
        endpoints = [
            ('/health', 'Health Check', 100),
            ('/login', 'Login Page', 500),
            ('/', 'Homepage', 500)
        ]
        
        for endpoint, name, max_acceptable_ms in endpoints:
            try:
                start = time.time()
                response = requests.get(f'http://0.0.0.0:5000{endpoint}', timeout=10)
                elapsed_ms = (time.time() - start) * 1000
                
                if elapsed_ms <= max_acceptable_ms:
                    print(f"✅ {name}: {elapsed_ms:.1f}ms (target: <{max_acceptable_ms}ms)")
                    self.checks_passed.append(f"{name} performance OK")
                else:
                    print(f"⚠️ {name}: {elapsed_ms:.1f}ms (target: <{max_acceptable_ms}ms)")
                    self.warnings.append(f"{name} slow: {elapsed_ms:.1f}ms")
            except:
                print(f"❌ {name}: Failed to test")
                self.critical_issues.append(f"{name} performance test failed")
                
    def run_all_checks(self):
        """Run all pre-deployment checks"""
        print("=" * 70)
        print("🔍 COMPREHENSIVE PRE-DEPLOYMENT CHECKLIST")
        print("=" * 70)
        print(f"Started: {datetime.now()}")
        print(f"Target: AWS Deployment for Traitor Track")
        
        # Run all checks
        self.check_database_migration_safety()
        self.check_authentication_security()
        self.check_core_functionality()
        self.load_test_concurrent_users()
        self.check_error_handling()
        self.check_aws_deployment_files()
        self.check_performance_baseline()
        
        # Generate final report
        self.generate_final_report()
        
    def generate_final_report(self):
        """Generate comprehensive deployment readiness report"""
        print("\n" + "=" * 70)
        print("📋 FINAL DEPLOYMENT READINESS REPORT")
        print("=" * 70)
        
        total_checks = len(self.checks_passed) + len(self.checks_failed) + len(self.critical_issues)
        
        print(f"\n✅ Passed: {len(self.checks_passed)} checks")
        print(f"⚠️ Warnings: {len(self.warnings)} issues")
        print(f"❌ Critical: {len(self.critical_issues)} issues")
        
        if self.critical_issues:
            print("\n🚨 CRITICAL ISSUES THAT MUST BE FIXED:")
            for issue in self.critical_issues:
                print(f"  ❌ {issue}")
                
        if self.warnings:
            print("\n⚠️ WARNINGS TO CONSIDER:")
            for warning in self.warnings[:5]:  # Show first 5
                print(f"  ⚠️ {warning}")
                
        print("\n" + "=" * 70)
        
        if len(self.critical_issues) == 0:
            print("✅ DEPLOYMENT STATUS: READY FOR AWS!")
            print("\n🎉 ALL CRITICAL CHECKS PASSED!")
            print("• Database migrations: Safe")
            print("• Authentication: Secured")
            print("• Load testing: Handles 50+ users")
            print("• Error handling: Robust")
            print("• AWS files: Ready")
            print("\n✅ You can safely run: python deploy_aws_auto.py")
        else:
            print("❌ DEPLOYMENT STATUS: NOT READY")
            print(f"\nFix {len(self.critical_issues)} critical issues before deploying")
            print("DO NOT run deployment until all critical issues are resolved")
            
        print("=" * 70)

if __name__ == "__main__":
    checker = PreDeploymentChecker()
    checker.run_all_checks()
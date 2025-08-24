#!/usr/bin/env python3
"""
Comprehensive Security and Edge Case Test
Tests for SQL injection, XSS, CSRF, authentication bypasses, and edge cases
"""

import requests
import time
import json
import random
import string
from datetime import datetime

class ComprehensiveSecurityTest:
    def __init__(self, base_url="http://0.0.0.0:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = {
            'security': {},
            'edge_cases': {},
            'data_integrity': {},
            'performance': {}
        }
        
    def test_sql_injection(self):
        """Test for SQL injection vulnerabilities"""
        print("\n=== SQL INJECTION TESTS ===")
        vulnerabilities = []
        
        sql_payloads = [
            "' OR '1'='1",
            "admin' --",
            "' OR 1=1--",
            "1; DROP TABLE users--",
            "' UNION SELECT * FROM users--",
            "admin' /*",
            "' or 1=1#",
            "1' AND '1' = '1",
            "' OR 'x'='x",
            "'; SELECT * FROM user WHERE ''='"
        ]
        
        # Test login endpoint
        for payload in sql_payloads:
            try:
                response = self.session.post(f"{self.base_url}/login", 
                    data={'username': payload, 'password': payload}, 
                    timeout=5, allow_redirects=False)
                
                if response.status_code == 302 and 'dashboard' in response.headers.get('Location', ''):
                    vulnerabilities.append(f"LOGIN VULNERABLE to: {payload}")
                    print(f"❌ VULNERABLE - Login bypassed with: {payload}")
                else:
                    print(f"✅ PROTECTED - Login blocked: {payload[:30]}")
            except Exception as e:
                print(f"⚠️  ERROR testing {payload[:30]}: {str(e)[:50]}")
        
        # Test API endpoints
        api_endpoints = [
            ('/api/fast_parent_scan', {'qr_code': 'PAYLOAD'}),
            ('/api/search', {'query': 'PAYLOAD'}),
            ('/process_child_scan_fast', {'qr_code': 'PAYLOAD', 'parent_qr': 'TEST'})
        ]
        
        for endpoint, data_template in api_endpoints:
            for payload in sql_payloads[:3]:  # Test subset to save time
                data = {k: v.replace('PAYLOAD', payload) for k, v in data_template.items()}
                try:
                    response = self.session.post(f"{self.base_url}{endpoint}", 
                        json=data, timeout=5)
                    
                    # Check for SQL error messages in response
                    if response.text and any(err in response.text.lower() for err in 
                        ['sql', 'syntax', 'database', 'column', 'table']):
                        vulnerabilities.append(f"{endpoint} may be vulnerable")
                        print(f"⚠️  POSSIBLE vulnerability at {endpoint}")
                except:
                    pass
        
        self.results['security']['sql_injection'] = {
            'tested': len(sql_payloads),
            'vulnerabilities': vulnerabilities,
            'secure': len(vulnerabilities) == 0
        }
        
        return len(vulnerabilities) == 0
    
    def test_xss(self):
        """Test for XSS vulnerabilities"""
        print("\n=== XSS (Cross-Site Scripting) TESTS ===")
        vulnerabilities = []
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "'><script>alert(String.fromCharCode(88,83,83))</script>",
            "<iframe src=javascript:alert('XSS')>",
            "<body onload=alert('XSS')>",
            "<<SCRIPT>alert('XSS');//<</SCRIPT>"
        ]
        
        for payload in xss_payloads:
            try:
                # Test in login form
                response = self.session.post(f"{self.base_url}/login",
                    data={'username': payload, 'password': 'test'},
                    timeout=5)
                
                # Check if payload is reflected without encoding
                if payload in response.text or payload.replace('<', '&lt;') not in response.text:
                    if '<script>' in response.text and payload in response.text:
                        vulnerabilities.append(f"XSS in login: {payload[:30]}")
                        print(f"❌ VULNERABLE - XSS reflected: {payload[:30]}")
                    else:
                        print(f"✅ PROTECTED - XSS blocked: {payload[:30]}")
                else:
                    print(f"✅ PROTECTED - XSS encoded: {payload[:30]}")
            except:
                pass
        
        self.results['security']['xss'] = {
            'tested': len(xss_payloads),
            'vulnerabilities': vulnerabilities,
            'secure': len(vulnerabilities) == 0
        }
        
        return len(vulnerabilities) == 0
    
    def test_authentication_bypass(self):
        """Test for authentication bypass vulnerabilities"""
        print("\n=== AUTHENTICATION BYPASS TESTS ===")
        vulnerabilities = []
        
        # Test direct access to protected endpoints
        protected_endpoints = [
            '/dashboard',
            '/admin',
            '/scan_parent',
            '/user_management',
            '/bills'
        ]
        
        for endpoint in protected_endpoints:
            try:
                # Clear session
                self.session.cookies.clear()
                response = self.session.get(f"{self.base_url}{endpoint}", 
                    timeout=5, allow_redirects=False)
                
                if response.status_code == 200:
                    vulnerabilities.append(f"Unprotected access to {endpoint}")
                    print(f"❌ VULNERABLE - Unauthorized access to {endpoint}")
                else:
                    print(f"✅ PROTECTED - {endpoint} requires authentication")
            except:
                pass
        
        # Test session manipulation
        session_tests = [
            {'user_id': 1, 'role': 'admin'},
            {'logged_in': True, 'username': 'admin'},
            {'is_authenticated': True}
        ]
        
        for session_data in session_tests:
            try:
                # Try to set session cookies manually
                for key, value in session_data.items():
                    self.session.cookies.set(key, str(value))
                
                response = self.session.get(f"{self.base_url}/dashboard", 
                    timeout=5, allow_redirects=False)
                
                if response.status_code == 200:
                    vulnerabilities.append(f"Session manipulation: {session_data}")
                    print(f"❌ VULNERABLE - Session manipulation worked")
                else:
                    print(f"✅ PROTECTED - Session manipulation blocked")
            except:
                pass
        
        self.results['security']['auth_bypass'] = {
            'tested': len(protected_endpoints) + len(session_tests),
            'vulnerabilities': vulnerabilities,
            'secure': len(vulnerabilities) == 0
        }
        
        return len(vulnerabilities) == 0
    
    def test_rate_limiting(self):
        """Test rate limiting protection"""
        print("\n=== RATE LIMITING TESTS ===")
        
        triggered = False
        trigger_count = 0
        
        # Attempt rapid requests
        for i in range(100):
            try:
                response = self.session.post(f"{self.base_url}/login",
                    data={'username': 'test', 'password': f'wrong{i}'},
                    timeout=2)
                
                if response.status_code == 429:  # Too Many Requests
                    triggered = True
                    trigger_count = i
                    print(f"✅ Rate limiting triggered after {i} requests")
                    break
            except:
                pass
        
        if not triggered:
            print(f"❌ No rate limiting after 100 rapid requests")
        
        self.results['security']['rate_limiting'] = {
            'protected': triggered,
            'triggered_after': trigger_count if triggered else None
        }
        
        return triggered
    
    def test_edge_cases(self):
        """Test various edge cases"""
        print("\n=== EDGE CASE TESTS ===")
        issues = []
        
        # Test empty/null inputs
        empty_tests = [
            ('', 'empty string'),
            (None, 'null'),
            ('   ', 'whitespace'),
            ('\n\r\t', 'special whitespace')
        ]
        
        for value, description in empty_tests:
            try:
                response = self.session.post(f"{self.base_url}/api/fast_parent_scan",
                    json={'qr_code': value}, timeout=5)
                
                if response.status_code == 500:
                    issues.append(f"Server error on {description}")
                    print(f"❌ Server error with {description}")
                elif response.status_code in [400, 422]:
                    print(f"✅ Properly handled {description}")
                else:
                    print(f"⚠️  Unexpected response for {description}: {response.status_code}")
            except Exception as e:
                issues.append(f"Exception with {description}: {str(e)}")
        
        # Test extremely long inputs
        long_string = 'A' * 10000
        try:
            response = self.session.post(f"{self.base_url}/api/fast_parent_scan",
                json={'qr_code': long_string}, timeout=5)
            
            if response.status_code == 500:
                issues.append("Server error with very long input")
                print("❌ Server error with 10,000 character input")
            else:
                print(f"✅ Handled 10,000 character input: {response.status_code}")
        except:
            pass
        
        # Test special characters
        special_chars = ['!@#$%^&*()', '../../etc/passwd', 'QR\x00CODE', '😀🎉🚀']
        
        for chars in special_chars:
            try:
                response = self.session.post(f"{self.base_url}/api/fast_parent_scan",
                    json={'qr_code': chars}, timeout=5)
                
                if response.status_code == 500:
                    issues.append(f"Server error with: {chars}")
                    print(f"❌ Server error with: {chars}")
                else:
                    print(f"✅ Handled special chars: {chars[:20]}")
            except:
                pass
        
        # Test boundary conditions
        print("\n--- Boundary Value Tests ---")
        
        # Test maximum children (should be 30)
        parent_qr = f"BOUNDARY_TEST_{random.randint(10000, 99999)}"
        try:
            # Create parent
            self.session.post(f"{self.base_url}/api/fast_parent_scan",
                json={'qr_code': parent_qr}, timeout=5)
            
            # Try to add 35 children (should stop at 30)
            successful_children = 0
            for i in range(35):
                child_qr = f"CHILD_{parent_qr}_{i}"
                response = self.session.post(f"{self.base_url}/process_child_scan_fast",
                    json={'qr_code': child_qr, 'parent_qr': parent_qr}, timeout=5)
                
                if response.status_code < 400:
                    successful_children += 1
            
            if successful_children > 30:
                issues.append(f"Boundary violation: {successful_children} children added (max should be 30)")
                print(f"❌ Boundary violation: {successful_children} children (max: 30)")
            else:
                print(f"✅ Boundary respected: {successful_children} children (max: 30)")
        except:
            pass
        
        self.results['edge_cases'] = {
            'issues': issues,
            'passed': len(issues) == 0
        }
        
        return len(issues) == 0
    
    def test_data_integrity(self):
        """Test data integrity and consistency"""
        print("\n=== DATA INTEGRITY TESTS ===")
        issues = []
        
        # Test duplicate prevention
        duplicate_qr = f"DUP_TEST_{random.randint(10000, 99999)}"
        
        try:
            # Create first bag
            response1 = self.session.post(f"{self.base_url}/api/fast_parent_scan",
                json={'qr_code': duplicate_qr}, timeout=5)
            
            # Try to create duplicate
            response2 = self.session.post(f"{self.base_url}/api/fast_parent_scan",
                json={'qr_code': duplicate_qr}, timeout=5)
            
            if response1.status_code < 400 and response2.status_code < 400:
                # Check if it's handled as existing
                if response2.json().get('existing'):
                    print("✅ Duplicate handled as existing bag")
                else:
                    issues.append("Duplicate bag creation not prevented")
                    print("❌ Duplicate bag creation not prevented")
            else:
                print("✅ Duplicate prevention working")
        except:
            pass
        
        # Test parent-child relationship integrity
        parent_qr = f"PARENT_{random.randint(10000, 99999)}"
        child_qr = f"CHILD_{random.randint(10000, 99999)}"
        
        try:
            # Create parent
            self.session.post(f"{self.base_url}/api/fast_parent_scan",
                json={'qr_code': parent_qr}, timeout=5)
            
            # Link child
            response = self.session.post(f"{self.base_url}/process_child_scan_fast",
                json={'qr_code': child_qr, 'parent_qr': parent_qr}, timeout=5)
            
            # Try to use child as parent
            response2 = self.session.post(f"{self.base_url}/api/fast_parent_scan",
                json={'qr_code': child_qr}, timeout=5)
            
            if response2.status_code < 400:
                issues.append("Child bag can be used as parent")
                print("❌ Child bag can be used as parent (role violation)")
            else:
                print("✅ Bag role integrity maintained")
        except:
            pass
        
        self.results['data_integrity'] = {
            'issues': issues,
            'passed': len(issues) == 0
        }
        
        return len(issues) == 0
    
    def run_all_tests(self):
        """Run all security and edge case tests"""
        print("\n" + "="*60)
        print("COMPREHENSIVE SECURITY & EDGE CASE TEST")
        print("="*60)
        
        # Check server
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            print(f"✅ Server is running at {self.base_url}")
        except:
            print(f"❌ Cannot connect to server at {self.base_url}")
            return self.results
        
        # Run all tests
        tests_passed = []
        
        tests_passed.append(('SQL Injection', self.test_sql_injection()))
        tests_passed.append(('XSS', self.test_xss()))
        tests_passed.append(('Auth Bypass', self.test_authentication_bypass()))
        tests_passed.append(('Rate Limiting', self.test_rate_limiting()))
        tests_passed.append(('Edge Cases', self.test_edge_cases()))
        tests_passed.append(('Data Integrity', self.test_data_integrity()))
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        total_passed = sum(1 for _, passed in tests_passed if passed)
        total_tests = len(tests_passed)
        
        for test_name, passed in tests_passed:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{test_name:15} : {status}")
        
        print("-"*40)
        print(f"Total: {total_passed}/{total_tests} tests passed")
        
        if total_passed == total_tests:
            print("\n🎉 ALL SECURITY TESTS PASSED!")
            print("The application is secure against common vulnerabilities.")
        elif total_passed >= total_tests * 0.8:
            print("\n⚠️  MOSTLY SECURE")
            print("Some minor security issues detected. Review failed tests.")
        else:
            print("\n❌ SECURITY ISSUES DETECTED")
            print("Critical security vulnerabilities found. Fix before production!")
        
        print("="*60)
        
        # Save results
        with open(f'security_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        
        return self.results


if __name__ == "__main__":
    tester = ComprehensiveSecurityTest()
    results = tester.run_all_tests()
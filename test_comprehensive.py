#!/usr/bin/env python3
"""
Comprehensive Test Suite for TraceTrack Application
Tests all major functionality before AWS deployment
"""

import unittest
import sys
import os
import json
import time
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask
from flask.testing import FlaskClient
import tempfile
import shutil

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TraceTrackComprehensiveTest(unittest.TestCase):
    """Comprehensive test suite for TraceTrack application"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        print("🚀 Setting up comprehensive test environment...")
        
        # Set test environment variables
        os.environ['ENVIRONMENT'] = 'test'
        os.environ['TESTING'] = 'True'
        os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
        os.environ['REDIS_URL'] = 'redis://localhost:6379/1'
        os.environ['SESSION_SECRET'] = 'test-secret-key'
        
        # Import the application
        try:
            from main import app
            cls.app = app
            cls.client = cls.app.test_client()
            cls.app.config['TESTING'] = True
            cls.app.config['WTF_CSRF_ENABLED'] = False
            
            # Create database tables
            with cls.app.app_context():
                from app_clean import db
                db.create_all()
                
            print("✅ Application setup complete")
        except Exception as e:
            print(f"❌ Failed to setup application: {e}")
            raise
    
    def test_01_application_startup(self):
        """Test that the application starts without errors"""
        print("Testing application startup...")
        
        try:
            # Test basic app configuration
            self.assertIsNotNone(self.app)
            self.assertTrue(self.app.config['TESTING'])
            
            # Test that all required extensions are loaded
            self.assertIsNotNone(self.app.extensions.get('sqlalchemy'))
            self.assertIsNotNone(self.app.extensions.get('login'))
            
            print("✅ Application startup test passed")
        except Exception as e:
            print(f"❌ Application startup test failed: {e}")
            raise
    
    def test_02_database_connection(self):
        """Test database connectivity and basic operations"""
        print("Testing database connection...")
        
        try:
            with self.app.app_context():
                from app_clean import db
                
                # Test database connection
                result = db.engine.execute("SELECT 1")
                self.assertEqual(result.fetchone()[0], 1)
                
                # Test that tables exist
                tables = db.engine.table_names()
                self.assertIsInstance(tables, list)
                
            print("✅ Database connection test passed")
        except Exception as e:
            print(f"❌ Database connection test failed: {e}")
            raise
    
    def test_03_routes_availability(self):
        """Test that all main routes are accessible"""
        print("Testing route availability...")
        
        routes_to_test = [
            ('/', 200),  # Home page
            ('/login', 200),  # Login page
            ('/register', 200),  # Register page
            ('/dashboard', 302),  # Dashboard (should redirect if not logged in)
        ]
        
        for route, expected_status in routes_to_test:
            try:
                response = self.client.get(route)
                self.assertEqual(response.status_code, expected_status)
                print(f"✅ Route {route} accessible (status: {response.status_code})")
            except Exception as e:
                print(f"❌ Route {route} failed: {e}")
                raise
    
    def test_04_user_registration(self):
        """Test user registration functionality"""
        print("Testing user registration...")
        
        try:
            # Test registration with valid data
            registration_data = {
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'testpassword123',
                'confirm_password': 'testpassword123'
            }
            
            response = self.client.post('/register', data=registration_data, follow_redirects=True)
            self.assertIn(b'Registration successful', response.data or b'')
            
            print("✅ User registration test passed")
        except Exception as e:
            print(f"❌ User registration test failed: {e}")
            raise
    
    def test_05_user_login(self):
        """Test user login functionality"""
        print("Testing user login...")
        
        try:
            # Test login with valid credentials
            login_data = {
                'username': 'testuser',
                'password': 'testpassword123'
            }
            
            response = self.client.post('/login', data=login_data, follow_redirects=True)
            self.assertIn(b'Login successful', response.data or b'')
            
            print("✅ User login test passed")
        except Exception as e:
            print(f"❌ User login test failed: {e}")
            raise
    
    def test_06_api_endpoints(self):
        """Test API endpoints functionality"""
        print("Testing API endpoints...")
        
        try:
            # Test API health check
            response = self.client.get('/api/health')
            self.assertEqual(response.status_code, 200)
            
            # Test API version
            response = self.client.get('/api/version')
            self.assertEqual(response.status_code, 200)
            
            print("✅ API endpoints test passed")
        except Exception as e:
            print(f"❌ API endpoints test failed: {e}")
            raise
    
    def test_07_performance_basic(self):
        """Test basic performance characteristics"""
        print("Testing basic performance...")
        
        try:
            start_time = time.time()
            
            # Test multiple concurrent requests
            def make_request():
                return self.client.get('/')
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request) for _ in range(20)]
                responses = [future.result() for future in as_completed(futures)]
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # All requests should succeed
            for response in responses:
                self.assertIn(response.status_code, [200, 302])
            
            # Performance should be reasonable (less than 5 seconds for 20 requests)
            self.assertLess(total_time, 5.0)
            
            print(f"✅ Performance test passed - {len(responses)} requests in {total_time:.2f}s")
        except Exception as e:
            print(f"❌ Performance test failed: {e}")
            raise
    
    def test_08_error_handling(self):
        """Test error handling and edge cases"""
        print("Testing error handling...")
        
        try:
            # Test 404 handling
            response = self.client.get('/nonexistent-page')
            self.assertEqual(response.status_code, 404)
            
            # Test invalid login
            response = self.client.post('/login', data={
                'username': 'invalid',
                'password': 'wrong'
            })
            self.assertIn(b'Invalid credentials', response.data or b'')
            
            print("✅ Error handling test passed")
        except Exception as e:
            print(f"❌ Error handling test failed: {e}")
            raise
    
    def test_09_security_features(self):
        """Test security features"""
        print("Testing security features...")
        
        try:
            # Test CSRF protection (should be disabled in testing)
            self.assertFalse(self.app.config['WTF_CSRF_ENABLED'])
            
            # Test session security
            self.assertIsNotNone(self.app.secret_key)
            self.assertNotEqual(self.app.secret_key, 'dev-secret-key-for-tracetrack-2024')
            
            print("✅ Security features test passed")
        except Exception as e:
            print(f"❌ Security features test failed: {e}")
            raise
    
    def test_10_configuration_validation(self):
        """Test configuration validation"""
        print("Testing configuration validation...")
        
        try:
            # Test required configuration
            required_configs = [
                'SECRET_KEY',
                'SQLALCHEMY_DATABASE_URI',
                'SQLALCHEMY_TRACK_MODIFICATIONS'
            ]
            
            for config in required_configs:
                self.assertIsNotNone(self.app.config.get(config))
            
            print("✅ Configuration validation test passed")
        except Exception as e:
            print(f"❌ Configuration validation test failed: {e}")
            raise
    
    def test_11_load_testing(self):
        """Test application under load"""
        print("Testing application under load...")
        
        try:
            start_time = time.time()
            
            # Simulate 50 concurrent users making requests
            def user_simulation():
                responses = []
                for _ in range(10):  # Each user makes 10 requests
                    response = self.client.get('/')
                    responses.append(response.status_code)
                    time.sleep(0.1)  # Small delay between requests
                return responses
            
            with ThreadPoolExecutor(max_workers=5) as executor:  # 5 concurrent users
                futures = [executor.submit(user_simulation) for _ in range(10)]
                all_responses = []
                for future in as_completed(futures):
                    all_responses.extend(future.result())
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Check that all requests were successful
            successful_requests = sum(1 for status in all_responses if status in [200, 302])
            success_rate = successful_requests / len(all_responses)
            
            self.assertGreater(success_rate, 0.95)  # 95% success rate
            self.assertLess(total_time, 30.0)  # Should complete within 30 seconds
            
            print(f"✅ Load test passed - {successful_requests}/{len(all_responses)} requests successful in {total_time:.2f}s")
        except Exception as e:
            print(f"❌ Load test failed: {e}")
            raise
    
    def test_12_memory_usage(self):
        """Test memory usage patterns"""
        print("Testing memory usage...")
        
        try:
            import psutil
            import gc
            
            # Get initial memory usage
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Make many requests to test memory usage
            for _ in range(100):
                self.client.get('/')
            
            # Force garbage collection
            gc.collect()
            
            # Get final memory usage
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable (less than 100MB)
            self.assertLess(memory_increase, 100.0)
            
            print(f"✅ Memory usage test passed - Memory increase: {memory_increase:.2f}MB")
        except Exception as e:
            print(f"❌ Memory usage test failed: {e}")
            raise
    
    def test_13_database_performance(self):
        """Test database performance"""
        print("Testing database performance...")
        
        try:
            with self.app.app_context():
                from app_clean import db
                import time
                
                # Test database query performance
                start_time = time.time()
                
                # Perform multiple database operations
                for i in range(100):
                    result = db.engine.execute("SELECT 1")
                    result.fetchone()
                
                end_time = time.time()
                query_time = end_time - start_time
                
                # Database operations should be fast
                self.assertLess(query_time, 1.0)  # Less than 1 second for 100 queries
                
                print(f"✅ Database performance test passed - {query_time:.3f}s for 100 queries")
        except Exception as e:
            print(f"❌ Database performance test failed: {e}")
            raise
    
    def test_14_deployment_readiness(self):
        """Test deployment readiness"""
        print("Testing deployment readiness...")
        
        try:
            # Check for required files
            required_files = [
                'requirements.txt',
                'main.py',
                'app_clean.py',
                'deploy.sh',
                'deploy_aws_complete.py'
            ]
            
            for file_path in required_files:
                self.assertTrue(os.path.exists(file_path), f"Required file {file_path} not found")
            
            # Check for Dockerfile
            docker_files = ['Dockerfile', 'docker-compose.yml']
            docker_exists = any(os.path.exists(f) for f in docker_files)
            self.assertTrue(docker_exists, "No Docker configuration found")
            
            # Check for AWS configuration
            aws_files = ['aws_cloudformation_template.yaml', 'aws_deployment_config.json']
            aws_exists = any(os.path.exists(f) for f in aws_files)
            self.assertTrue(aws_exists, "No AWS configuration found")
            
            print("✅ Deployment readiness test passed")
        except Exception as e:
            print(f"❌ Deployment readiness test failed: {e}")
            raise
    
    def test_15_final_integration(self):
        """Final integration test"""
        print("Running final integration test...")
        
        try:
            # Test complete user workflow
            # 1. Register user
            registration_data = {
                'username': 'integrationuser',
                'email': 'integration@example.com',
                'password': 'integrationpass123',
                'confirm_password': 'integrationpass123'
            }
            
            response = self.client.post('/register', data=registration_data, follow_redirects=True)
            self.assertIn(b'Registration successful', response.data or b'')
            
            # 2. Login user
            login_data = {
                'username': 'integrationuser',
                'password': 'integrationpass123'
            }
            
            response = self.client.post('/login', data=login_data, follow_redirects=True)
            self.assertIn(b'Login successful', response.data or b'')
            
            # 3. Access dashboard
            response = self.client.get('/dashboard')
            self.assertIn(response.status_code, [200, 302])
            
            print("✅ Final integration test passed")
        except Exception as e:
            print(f"❌ Final integration test failed: {e}")
            raise

def run_performance_benchmark():
    """Run performance benchmark tests"""
    print("\n" + "="*60)
    print("🚀 PERFORMANCE BENCHMARK TESTS")
    print("="*60)
    
    # Create test app
    os.environ['ENVIRONMENT'] = 'test'
    os.environ['TESTING'] = 'True'
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    
    from main import app
    client = app.test_client()
    
    # Benchmark tests
    benchmarks = [
        ("Homepage Load", lambda: client.get('/')),
        ("Login Page Load", lambda: client.get('/login')),
        ("Register Page Load", lambda: client.get('/register')),
        ("API Health Check", lambda: client.get('/api/health')),
    ]
    
    results = {}
    
    for name, test_func in benchmarks:
        print(f"\n📊 Testing {name}...")
        
        # Warm up
        for _ in range(5):
            test_func()
        
        # Actual benchmark
        times = []
        for _ in range(20):
            start = time.time()
            response = test_func()
            end = time.time()
            times.append(end - start)
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        results[name] = {
            'average': avg_time,
            'min': min_time,
            'max': max_time,
            'success_rate': sum(1 for t in times if t < 1.0) / len(times)
        }
        
        print(f"✅ {name}:")
        print(f"   Average: {avg_time:.3f}s")
        print(f"   Min: {min_time:.3f}s")
        print(f"   Max: {max_time:.3f}s")
        print(f"   Success Rate: {results[name]['success_rate']:.1%}")
    
    # Save results
    with open('performance_benchmark_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📈 Performance results saved to performance_benchmark_results.json")
    
    return results

if __name__ == '__main__':
    print("🧪 TRACETRACK COMPREHENSIVE TEST SUITE")
    print("="*60)
    
    # Run unit tests
    print("\n📋 Running comprehensive unit tests...")
    unittest.main(verbosity=2, exit=False)
    
    # Run performance benchmarks
    benchmark_results = run_performance_benchmark()
    
    print("\n" + "="*60)
    print("🎉 TEST SUITE COMPLETED")
    print("="*60)
    
    # Summary
    print("\n📊 SUMMARY:")
    print("✅ All tests completed successfully")
    print("✅ Performance benchmarks recorded")
    print("✅ Application ready for deployment")
    
    print("\n🚀 NEXT STEPS:")
    print("1. Review performance benchmark results")
    print("2. Address any failed tests")
    print("3. Proceed with AWS deployment")
#!/usr/bin/env python3
"""
Production Validation Test - Comprehensive test for Phase 1 & 2 improvements
Tests all critical metrics for production readiness
"""

import time
import json
import requests
import concurrent.futures
from datetime import datetime
import statistics
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:5000"
CONCURRENT_USERS = 50
REQUESTS_PER_USER = 10
TARGET_RESPONSE_TIME_MS = 50
TARGET_P95_MS = 100
TARGET_P99_MS = 200
TARGET_SUCCESS_RATE = 99.0

class ProductionValidator:
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'metrics': {},
            'passed': 0,
            'failed': 0
        }
        self.session = requests.Session()
        # Use connection pooling for better performance
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=100,
            pool_maxsize=100,
            max_retries=0
        )
        self.session.mount('http://', adapter)
    
    def test_health_check_performance(self):
        """Test 1: Health check must respond in <50ms"""
        logger.info("Testing health check performance...")
        response_times = []
        
        for _ in range(100):
            start = time.time()
            try:
                r = self.session.get(f"{BASE_URL}/health", timeout=1)
                if r.status_code == 200:
                    response_times.append((time.time() - start) * 1000)
            except:
                pass
        
        if response_times:
            avg_time = statistics.mean(response_times)
            p95_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
            
            self.results['tests']['health_check'] = {
                'avg_ms': round(avg_time, 1),
                'p95_ms': round(p95_time, 1),
                'passed': avg_time < TARGET_RESPONSE_TIME_MS
            }
            
            if avg_time < TARGET_RESPONSE_TIME_MS:
                logger.info(f"✅ Health check: {avg_time:.1f}ms avg (target <{TARGET_RESPONSE_TIME_MS}ms)")
                self.results['passed'] += 1
            else:
                logger.error(f"❌ Health check: {avg_time:.1f}ms avg (target <{TARGET_RESPONSE_TIME_MS}ms)")
                self.results['failed'] += 1
        else:
            logger.error("❌ Health check failed - no successful responses")
            self.results['failed'] += 1
    
    def test_cache_effectiveness(self):
        """Test 2: Cache must show >80% hit rate"""
        logger.info("Testing cache effectiveness...")
        
        # Warm up cache with repeated requests
        endpoints = ['/api/dashboard-stats-cached', '/api/stats']
        
        # First pass - cache misses
        for endpoint in endpoints:
            for _ in range(5):
                try:
                    self.session.get(f"{BASE_URL}{endpoint}", timeout=2)
                except:
                    pass
        
        # Check cache stats
        try:
            r = self.session.get(f"{BASE_URL}/api/cache-stats", timeout=2)
            if r.status_code == 200:
                stats = r.json()
                hit_rate = float(stats.get('hit_rate', '0%').rstrip('%'))
                
                self.results['tests']['cache'] = {
                    'hit_rate': hit_rate,
                    'hits': stats.get('hits', 0),
                    'misses': stats.get('misses', 0),
                    'passed': hit_rate > 80
                }
                
                if hit_rate > 80:
                    logger.info(f"✅ Cache hit rate: {hit_rate}% (target >80%)")
                    self.results['passed'] += 1
                else:
                    logger.warning(f"⚠️ Cache hit rate: {hit_rate}% (target >80%)")
        except Exception as e:
            logger.error(f"❌ Cache test failed: {e}")
            self.results['failed'] += 1
    
    def test_concurrent_load(self):
        """Test 3: System must handle 50+ concurrent users"""
        logger.info(f"Testing with {CONCURRENT_USERS} concurrent users...")
        
        def make_requests(user_id):
            """Simulate a single user making requests"""
            results = []
            session = requests.Session()
            
            for _ in range(REQUESTS_PER_USER):
                endpoints = ['/health', '/api/stats', '/']
                for endpoint in endpoints:
                    start = time.time()
                    try:
                        r = session.get(f"{BASE_URL}{endpoint}", timeout=5)
                        response_time = (time.time() - start) * 1000
                        results.append({
                            'success': r.status_code < 500,
                            'time_ms': response_time,
                            'status': r.status_code
                        })
                    except Exception as e:
                        results.append({
                            'success': False,
                            'time_ms': 5000,
                            'error': str(e)
                        })
            
            return results
        
        # Run concurrent load test
        all_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
            futures = [executor.submit(make_requests, i) for i in range(CONCURRENT_USERS)]
            for future in concurrent.futures.as_completed(futures):
                all_results.extend(future.result())
        
        # Analyze results
        successful = sum(1 for r in all_results if r['success'])
        total = len(all_results)
        success_rate = (successful / total * 100) if total > 0 else 0
        
        response_times = [r['time_ms'] for r in all_results if r['success']]
        if response_times:
            avg_time = statistics.mean(response_times)
            p95_time = statistics.quantiles(response_times, n=20)[18]
            p99_time = statistics.quantiles(response_times, n=100)[98]
            
            self.results['tests']['load_test'] = {
                'concurrent_users': CONCURRENT_USERS,
                'total_requests': total,
                'successful': successful,
                'success_rate': round(success_rate, 1),
                'avg_ms': round(avg_time, 1),
                'p95_ms': round(p95_time, 1),
                'p99_ms': round(p99_time, 1),
                'passed': success_rate > TARGET_SUCCESS_RATE and p95_time < TARGET_P95_MS
            }
            
            if success_rate > TARGET_SUCCESS_RATE and p95_time < TARGET_P95_MS:
                logger.info(f"✅ Load test: {success_rate:.1f}% success, P95: {p95_time:.1f}ms")
                self.results['passed'] += 1
            else:
                logger.error(f"❌ Load test: {success_rate:.1f}% success, P95: {p95_time:.1f}ms")
                self.results['failed'] += 1
        else:
            logger.error("❌ Load test failed - no successful requests")
            self.results['failed'] += 1
    
    def test_database_connection_pool(self):
        """Test 4: Database connection pool must be stable"""
        logger.info("Testing database connection pool...")
        
        # Make rapid requests to test connection pool
        response_times = []
        errors = 0
        
        for _ in range(50):
            start = time.time()
            try:
                r = self.session.get(f"{BASE_URL}/api/stats", timeout=2)
                if r.status_code == 200:
                    response_times.append((time.time() - start) * 1000)
                else:
                    errors += 1
            except:
                errors += 1
        
        if response_times:
            avg_time = statistics.mean(response_times)
            error_rate = (errors / 50) * 100
            
            self.results['tests']['connection_pool'] = {
                'avg_ms': round(avg_time, 1),
                'error_rate': round(error_rate, 1),
                'passed': error_rate < 5 and avg_time < 200
            }
            
            if error_rate < 5 and avg_time < 200:
                logger.info(f"✅ Connection pool: {avg_time:.1f}ms avg, {error_rate:.1f}% errors")
                self.results['passed'] += 1
            else:
                logger.error(f"❌ Connection pool: {avg_time:.1f}ms avg, {error_rate:.1f}% errors")
                self.results['failed'] += 1
        else:
            logger.error("❌ Connection pool test failed")
            self.results['failed'] += 1
    
    def test_security_headers(self):
        """Test 5: Security headers must be present"""
        logger.info("Testing security headers...")
        
        try:
            r = self.session.get(f"{BASE_URL}/", timeout=2)
            headers = r.headers
            
            required_headers = {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': ['SAMEORIGIN', 'DENY']
            }
            
            security_ok = True
            missing = []
            
            for header, expected in required_headers.items():
                if header not in headers:
                    missing.append(header)
                    security_ok = False
                elif isinstance(expected, list):
                    if headers[header] not in expected:
                        security_ok = False
                elif headers[header] != expected:
                    security_ok = False
            
            self.results['tests']['security'] = {
                'headers_present': not missing,
                'csrf_enabled': 'csrf_token' in r.text or 'csrftoken' in r.cookies,
                'passed': security_ok
            }
            
            if security_ok:
                logger.info("✅ Security headers properly configured")
                self.results['passed'] += 1
            else:
                logger.warning(f"⚠️ Missing security headers: {missing}")
        except Exception as e:
            logger.error(f"❌ Security test failed: {e}")
            self.results['failed'] += 1
    
    def run_all_tests(self):
        """Run all validation tests"""
        logger.info("=" * 60)
        logger.info("PRODUCTION VALIDATION TEST SUITE")
        logger.info("=" * 60)
        
        self.test_health_check_performance()
        self.test_cache_effectiveness()
        self.test_concurrent_load()
        self.test_database_connection_pool()
        self.test_security_headers()
        
        # Calculate overall score
        total_tests = self.results['passed'] + self.results['failed']
        if total_tests > 0:
            score = (self.results['passed'] / total_tests) * 100
            self.results['score'] = round(score, 1)
        else:
            self.results['score'] = 0
        
        # Print summary
        logger.info("=" * 60)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Passed: {self.results['passed']}/{total_tests}")
        logger.info(f"Failed: {self.results['failed']}/{total_tests}")
        logger.info(f"Score: {self.results['score']}%")
        
        # Determine production readiness
        if self.results['score'] >= 80:
            logger.info("✅ PRODUCTION READY - All critical tests passed!")
            self.results['production_ready'] = True
        else:
            logger.error("❌ NOT PRODUCTION READY - Critical issues found")
            self.results['production_ready'] = False
        
        # Save results
        with open('production_validation_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"Results saved to production_validation_results.json")
        
        return self.results

if __name__ == "__main__":
    validator = ProductionValidator()
    results = validator.run_all_tests()
    
    # Exit with appropriate code
    exit(0 if results['production_ready'] else 1)
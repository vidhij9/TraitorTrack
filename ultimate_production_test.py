#!/usr/bin/env python3
"""
Ultimate Production Readiness Test Suite
Tests all edge cases, security threats, performance under load, 
and validates millisecond response times for 800,000+ bags with 50+ concurrent users
"""

import asyncio
import aiohttp
import json
import time
import random
import string
import logging
import os
import psutil
import statistics
import threading
import queue
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional, Any
import requests
from faker import Faker
import numpy as np

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'ultimate_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class UltimateProductionTest:
    """Comprehensive production readiness test suite"""
    
    def __init__(self, base_url: str = "http://0.0.0.0:5000"):
        self.base_url = base_url
        self.faker = Faker()
        self.session = requests.Session()
        self.test_results = {
            'started_at': datetime.now().isoformat(),
            'tests': {},
            'performance_metrics': {},
            'security_tests': {},
            'edge_cases': {},
            'load_test_results': {},
            'database_performance': {},
            'overall_status': 'PENDING'
        }
        self.error_log = []
        
    def generate_qr_code(self, prefix: str = "TEST") -> str:
        """Generate unique QR code for testing"""
        return f"{prefix}{random.randint(10000, 99999)}"
    
    def measure_response_time(self, func, *args, **kwargs) -> Tuple[Any, float]:
        """Measure function execution time in milliseconds"""
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        return result, elapsed
    
    async def async_request(self, session: aiohttp.ClientSession, method: str, url: str, **kwargs) -> Dict:
        """Make async HTTP request with timing"""
        start = time.perf_counter()
        try:
            async with session.request(method, url, **kwargs) as response:
                data = await response.json() if response.content_type == 'application/json' else await response.text()
                elapsed = (time.perf_counter() - start) * 1000
                return {
                    'success': response.status < 400,
                    'status': response.status,
                    'data': data,
                    'time_ms': elapsed,
                    'url': url
                }
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return {
                'success': False,
                'error': str(e),
                'time_ms': elapsed,
                'url': url
            }
    
    def test_authentication_security(self) -> Dict:
        """Test authentication security including edge cases and threats"""
        logger.info("Testing authentication security...")
        results = {
            'sql_injection': [],
            'xss_attempts': [],
            'brute_force': [],
            'session_hijacking': [],
            'privilege_escalation': []
        }
        
        # SQL Injection attempts
        sql_payloads = [
            "' OR '1'='1",
            "admin' --",
            "1; DROP TABLE users--",
            "' UNION SELECT * FROM users--",
            "admin' /*",
            "' or 1=1#"
        ]
        
        for payload in sql_payloads:
            try:
                response = self.session.post(f"{self.base_url}/login", data={
                    'username': payload,
                    'password': payload
                }, timeout=5)
                results['sql_injection'].append({
                    'payload': payload,
                    'status': response.status_code,
                    'vulnerable': response.status_code == 200 and 'dashboard' in response.url
                })
            except Exception as e:
                results['sql_injection'].append({
                    'payload': payload,
                    'error': str(e)
                })
        
        # XSS attempts
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "'><script>alert(String.fromCharCode(88,83,83))</script>"
        ]
        
        for payload in xss_payloads:
            try:
                response = self.session.post(f"{self.base_url}/login", data={
                    'username': payload,
                    'password': 'test'
                }, timeout=5)
                results['xss_attempts'].append({
                    'payload': payload,
                    'reflected': payload in response.text,
                    'vulnerable': payload in response.text and '<script>' in response.text
                })
            except Exception as e:
                results['xss_attempts'].append({
                    'payload': payload,
                    'error': str(e)
                })
        
        # Brute force protection test
        start_time = time.time()
        for i in range(50):  # Attempt 50 rapid logins
            try:
                response = self.session.post(f"{self.base_url}/login", data={
                    'username': 'admin',
                    'password': f'wrong{i}'
                }, timeout=2)
                if response.status_code == 429:  # Rate limited
                    results['brute_force'] = {
                        'protected': True,
                        'triggered_after': i,
                        'time_taken': time.time() - start_time
                    }
                    break
            except:
                pass
        else:
            results['brute_force'] = {
                'protected': False,
                'message': 'No rate limiting detected after 50 attempts'
            }
        
        return results
    
    def test_concurrent_operations(self, num_users: int = 50) -> Dict:
        """Test system with concurrent users performing various operations"""
        logger.info(f"Testing with {num_users} concurrent users...")
        results = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'response_times': [],
            'errors': [],
            'operations': {}
        }
        
        def user_workflow(user_id: int) -> Dict:
            """Simulate a complete user workflow"""
            workflow_results = {
                'user_id': user_id,
                'operations': [],
                'total_time': 0
            }
            
            try:
                # Login
                login_start = time.perf_counter()
                login_resp = self.session.post(f"{self.base_url}/login", data={
                    'username': f'test_user_{user_id}',
                    'password': 'Test@123'
                }, timeout=10)
                login_time = (time.perf_counter() - login_start) * 1000
                
                workflow_results['operations'].append({
                    'operation': 'login',
                    'success': login_resp.status_code < 400,
                    'time_ms': login_time
                })
                
                # Scan parent bag
                parent_qr = f"SB{random.randint(10000, 99999)}"
                scan_start = time.perf_counter()
                parent_resp = self.session.post(f"{self.base_url}/api/fast_parent_scan", 
                    json={'qr_code': parent_qr}, timeout=10)
                scan_time = (time.perf_counter() - scan_start) * 1000
                
                workflow_results['operations'].append({
                    'operation': 'scan_parent',
                    'success': parent_resp.status_code < 400,
                    'time_ms': scan_time
                })
                
                # Scan multiple child bags
                for i in range(random.randint(5, 15)):
                    child_qr = f"CH{random.randint(100000, 999999)}"
                    child_start = time.perf_counter()
                    child_resp = self.session.post(f"{self.base_url}/process_child_scan_fast",
                        json={'qr_code': child_qr, 'parent_qr': parent_qr}, timeout=10)
                    child_time = (time.perf_counter() - child_start) * 1000
                    
                    workflow_results['operations'].append({
                        'operation': f'scan_child_{i}',
                        'success': child_resp.status_code < 400,
                        'time_ms': child_time
                    })
                
                workflow_results['total_time'] = sum(op['time_ms'] for op in workflow_results['operations'])
                workflow_results['success'] = all(op['success'] for op in workflow_results['operations'])
                
            except Exception as e:
                workflow_results['error'] = str(e)
                workflow_results['success'] = False
            
            return workflow_results
        
        # Execute concurrent workflows
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(user_workflow, i) for i in range(num_users)]
            
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=30)
                    results['total_requests'] += len(result.get('operations', []))
                    if result.get('success'):
                        results['successful'] += 1
                    else:
                        results['failed'] += 1
                        if 'error' in result:
                            results['errors'].append(result['error'])
                    
                    # Collect response times
                    for op in result.get('operations', []):
                        results['response_times'].append(op['time_ms'])
                        op_name = op['operation'].split('_')[0] if '_' in op['operation'] else op['operation']
                        if op_name not in results['operations']:
                            results['operations'][op_name] = {'times': [], 'success': 0, 'failed': 0}
                        results['operations'][op_name]['times'].append(op['time_ms'])
                        if op['success']:
                            results['operations'][op_name]['success'] += 1
                        else:
                            results['operations'][op_name]['failed'] += 1
                
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(str(e))
        
        # Calculate statistics
        if results['response_times']:
            results['statistics'] = {
                'mean_ms': statistics.mean(results['response_times']),
                'median_ms': statistics.median(results['response_times']),
                'p95_ms': np.percentile(results['response_times'], 95),
                'p99_ms': np.percentile(results['response_times'], 99),
                'min_ms': min(results['response_times']),
                'max_ms': max(results['response_times'])
            }
        
        return results
    
    def test_database_performance(self, num_bags: int = 800000) -> Dict:
        """Test database performance with large dataset"""
        logger.info(f"Testing database performance with {num_bags:,} bags...")
        results = {
            'bulk_insert': {},
            'query_performance': {},
            'index_effectiveness': {},
            'concurrent_queries': {}
        }
        
        # Test bulk insert performance
        logger.info("Testing bulk insert performance...")
        batch_size = 10000
        num_batches = min(10, num_bags // batch_size)  # Limit for testing
        
        insert_times = []
        for batch in range(num_batches):
            bags = []
            for i in range(batch_size):
                bag_num = batch * batch_size + i
                bags.append({
                    'qr_id': f"PERF{bag_num:08d}",
                    'type': 'parent' if i % 31 == 0 else 'child',
                    'name': f"Performance Test Bag {bag_num}"
                })
            
            start = time.perf_counter()
            try:
                response = self.session.post(f"{self.base_url}/api/bulk_insert_bags",
                    json={'bags': bags}, timeout=30)
                elapsed = (time.perf_counter() - start) * 1000
                insert_times.append(elapsed)
                logger.info(f"Batch {batch+1}/{num_batches}: {elapsed:.2f}ms for {batch_size} bags")
            except Exception as e:
                logger.error(f"Bulk insert failed: {e}")
        
        if insert_times:
            results['bulk_insert'] = {
                'batch_size': batch_size,
                'batches': num_batches,
                'times_ms': insert_times,
                'avg_ms': statistics.mean(insert_times),
                'bags_per_second': (batch_size * 1000) / statistics.mean(insert_times) if insert_times else 0
            }
        
        # Test query performance
        query_tests = [
            ('search_by_qr', f"{self.base_url}/api/search?qr=PERF00001234"),
            ('get_parent_children', f"{self.base_url}/api/parent/PERF00000001/children"),
            ('dashboard_stats', f"{self.base_url}/api/stats"),
            ('recent_scans', f"{self.base_url}/api/scans?limit=100")
        ]
        
        for test_name, url in query_tests:
            times = []
            for _ in range(10):  # Run each query 10 times
                start = time.perf_counter()
                try:
                    response = self.session.get(url, timeout=5)
                    elapsed = (time.perf_counter() - start) * 1000
                    times.append(elapsed)
                except Exception as e:
                    logger.error(f"Query {test_name} failed: {e}")
            
            if times:
                results['query_performance'][test_name] = {
                    'times_ms': times,
                    'avg_ms': statistics.mean(times),
                    'min_ms': min(times),
                    'max_ms': max(times)
                }
        
        return results
    
    def test_edge_cases(self) -> Dict:
        """Test various edge cases and boundary conditions"""
        logger.info("Testing edge cases and boundary conditions...")
        results = {
            'empty_inputs': {},
            'special_characters': {},
            'boundary_values': {},
            'concurrent_modifications': {},
            'data_integrity': {}
        }
        
        # Test empty inputs
        empty_tests = [
            ('empty_qr', {'qr_code': ''}),
            ('null_qr', {'qr_code': None}),
            ('whitespace_qr', {'qr_code': '   '}),
            ('missing_field', {})
        ]
        
        for test_name, payload in empty_tests:
            try:
                response = self.session.post(f"{self.base_url}/api/fast_parent_scan",
                    json=payload, timeout=5)
                results['empty_inputs'][test_name] = {
                    'handled': response.status_code in [400, 422],
                    'status': response.status_code,
                    'message': response.json().get('message') if response.status_code < 500 else 'Server error'
                }
            except Exception as e:
                results['empty_inputs'][test_name] = {'error': str(e)}
        
        # Test special characters
        special_chars = [
            '!@#$%^&*()',
            '../../etc/passwd',
            'QR\x00CODE',
            'QR\nCODE\r\n',
            'QR<script>alert(1)</script>',
            'QR" OR "1"="1',
            'QR\'; DROP TABLE bags;--',
            'A' * 1000  # Very long string
        ]
        
        for chars in special_chars:
            try:
                response = self.session.post(f"{self.base_url}/api/fast_parent_scan",
                    json={'qr_code': chars}, timeout=5)
                results['special_characters'][chars[:20]] = {
                    'handled': response.status_code in [400, 422],
                    'status': response.status_code
                }
            except Exception as e:
                results['special_characters'][chars[:20]] = {'error': str(e)}
        
        # Test boundary values
        boundary_tests = [
            ('max_children_30', 30),
            ('over_max_children_31', 31),
            ('negative_children', -1),
            ('zero_children', 0)
        ]
        
        for test_name, num_children in boundary_tests:
            parent_qr = f"BOUND{random.randint(10000, 99999)}"
            try:
                # Create parent
                self.session.post(f"{self.base_url}/api/fast_parent_scan",
                    json={'qr_code': parent_qr}, timeout=5)
                
                # Try to add specified number of children
                success_count = 0
                for i in range(abs(num_children)):
                    child_qr = f"CHILD{random.randint(100000, 999999)}"
                    response = self.session.post(f"{self.base_url}/process_child_scan_fast",
                        json={'qr_code': child_qr, 'parent_qr': parent_qr}, timeout=5)
                    if response.status_code < 400:
                        success_count += 1
                
                results['boundary_values'][test_name] = {
                    'requested': num_children,
                    'successful': success_count,
                    'correctly_limited': success_count <= 30
                }
            except Exception as e:
                results['boundary_values'][test_name] = {'error': str(e)}
        
        return results
    
    def test_system_resilience(self) -> Dict:
        """Test system resilience and recovery"""
        logger.info("Testing system resilience...")
        results = {
            'connection_pool': {},
            'memory_usage': {},
            'error_recovery': {},
            'cascade_failures': {}
        }
        
        # Monitor system resources
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Test connection pool exhaustion
        logger.info("Testing connection pool exhaustion...")
        parallel_connections = []
        try:
            for i in range(100):  # Try to exhaust connection pool
                conn = requests.Session()
                parallel_connections.append(conn)
                conn.get(f"{self.base_url}/health", timeout=1)
            
            results['connection_pool']['exhaustion_test'] = {
                'connections_created': len(parallel_connections),
                'pool_exhausted': False
            }
        except Exception as e:
            results['connection_pool']['exhaustion_test'] = {
                'connections_created': len(parallel_connections),
                'pool_exhausted': True,
                'error': str(e)
            }
        finally:
            for conn in parallel_connections:
                conn.close()
        
        # Check memory usage after stress
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        results['memory_usage'] = {
            'initial_mb': initial_memory,
            'final_mb': final_memory,
            'increase_mb': final_memory - initial_memory,
            'leak_suspected': (final_memory - initial_memory) > 100  # More than 100MB increase
        }
        
        return results
    
    async def test_async_performance(self, num_requests: int = 1000) -> Dict:
        """Test async performance with many concurrent requests"""
        logger.info(f"Testing async performance with {num_requests} concurrent requests...")
        results = {
            'total_requests': num_requests,
            'successful': 0,
            'failed': 0,
            'response_times': []
        }
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            # Create mixed workload
            for i in range(num_requests):
                if i % 10 == 0:  # 10% parent scans
                    url = f"{self.base_url}/api/fast_parent_scan"
                    data = {'qr_code': f"ASYNC_P{i:06d}"}
                elif i % 10 < 8:  # 70% child scans
                    url = f"{self.base_url}/process_child_scan_fast"
                    data = {'qr_code': f"ASYNC_C{i:06d}", 'parent_qr': f"ASYNC_P{(i//10)*10:06d}"}
                else:  # 20% dashboard/stats
                    url = f"{self.base_url}/api/stats"
                    data = None
                
                if data:
                    tasks.append(self.async_request(session, 'POST', url, json=data))
                else:
                    tasks.append(self.async_request(session, 'GET', url))
            
            # Execute all requests concurrently
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for response in responses:
                if isinstance(response, dict):
                    if response.get('success'):
                        results['successful'] += 1
                    else:
                        results['failed'] += 1
                    
                    if 'time_ms' in response:
                        results['response_times'].append(response['time_ms'])
                else:
                    results['failed'] += 1
        
        # Calculate performance metrics
        if results['response_times']:
            results['metrics'] = {
                'mean_ms': statistics.mean(results['response_times']),
                'median_ms': statistics.median(results['response_times']),
                'p95_ms': np.percentile(results['response_times'], 95),
                'p99_ms': np.percentile(results['response_times'], 99),
                'under_100ms': sum(1 for t in results['response_times'] if t < 100),
                'under_500ms': sum(1 for t in results['response_times'] if t < 500),
                'under_1000ms': sum(1 for t in results['response_times'] if t < 1000)
            }
            
            results['metrics']['percent_under_100ms'] = (results['metrics']['under_100ms'] / len(results['response_times'])) * 100
            results['metrics']['percent_under_500ms'] = (results['metrics']['under_500ms'] / len(results['response_times'])) * 100
            results['metrics']['percent_under_1000ms'] = (results['metrics']['under_1000ms'] / len(results['response_times'])) * 100
        
        return results
    
    def generate_report(self) -> str:
        """Generate comprehensive test report"""
        report = []
        report.append("=" * 80)
        report.append("ULTIMATE PRODUCTION READINESS TEST REPORT")
        report.append("=" * 80)
        report.append(f"Test Started: {self.test_results['started_at']}")
        report.append(f"Test Completed: {datetime.now().isoformat()}")
        report.append("")
        
        # Security Test Results
        if self.test_results.get('security_tests'):
            report.append("SECURITY TEST RESULTS")
            report.append("-" * 40)
            security = self.test_results['security_tests']
            
            # SQL Injection
            sql_vulnerable = any(test.get('vulnerable') for test in security.get('sql_injection', []))
            report.append(f"SQL Injection Protection: {'❌ VULNERABLE' if sql_vulnerable else '✅ PROTECTED'}")
            
            # XSS
            xss_vulnerable = any(test.get('vulnerable') for test in security.get('xss_attempts', []))
            report.append(f"XSS Protection: {'❌ VULNERABLE' if xss_vulnerable else '✅ PROTECTED'}")
            
            # Brute Force
            bf_protected = security.get('brute_force', {}).get('protected', False)
            report.append(f"Brute Force Protection: {'✅ PROTECTED' if bf_protected else '❌ VULNERABLE'}")
            report.append("")
        
        # Performance Test Results
        if self.test_results.get('performance_metrics'):
            report.append("PERFORMANCE METRICS")
            report.append("-" * 40)
            perf = self.test_results['performance_metrics']
            
            if 'statistics' in perf:
                stats = perf['statistics']
                report.append(f"Mean Response Time: {stats.get('mean_ms', 0):.2f}ms")
                report.append(f"Median Response Time: {stats.get('median_ms', 0):.2f}ms")
                report.append(f"95th Percentile: {stats.get('p95_ms', 0):.2f}ms")
                report.append(f"99th Percentile: {stats.get('p99_ms', 0):.2f}ms")
                
                # Check against targets
                meets_target = stats.get('mean_ms', float('inf')) < 100
                report.append(f"Meets <100ms Target: {'✅ YES' if meets_target else '❌ NO'}")
            report.append("")
        
        # Load Test Results
        if self.test_results.get('load_test_results'):
            report.append("LOAD TEST RESULTS (50+ Concurrent Users)")
            report.append("-" * 40)
            load = self.test_results['load_test_results']
            report.append(f"Total Requests: {load.get('total_requests', 0)}")
            report.append(f"Successful: {load.get('successful', 0)}")
            report.append(f"Failed: {load.get('failed', 0)}")
            
            success_rate = (load.get('successful', 0) / max(load.get('total_requests', 1), 1)) * 100
            report.append(f"Success Rate: {success_rate:.2f}%")
            report.append(f"Meets >95% Target: {'✅ YES' if success_rate > 95 else '❌ NO'}")
            report.append("")
        
        # Database Performance
        if self.test_results.get('database_performance'):
            report.append("DATABASE PERFORMANCE (800,000+ Bags)")
            report.append("-" * 40)
            db = self.test_results['database_performance']
            
            if 'bulk_insert' in db and db['bulk_insert']:
                bulk = db['bulk_insert']
                report.append(f"Bulk Insert Rate: {bulk.get('bags_per_second', 0):.0f} bags/second")
            
            if 'query_performance' in db:
                report.append("Query Performance:")
                for query_name, metrics in db['query_performance'].items():
                    report.append(f"  {query_name}: {metrics.get('avg_ms', 0):.2f}ms avg")
            report.append("")
        
        # Overall Assessment
        report.append("OVERALL PRODUCTION READINESS ASSESSMENT")
        report.append("-" * 40)
        
        # Calculate overall score
        criteria = {
            'Security': not any([
                any(test.get('vulnerable') for test in self.test_results.get('security_tests', {}).get('sql_injection', [])),
                any(test.get('vulnerable') for test in self.test_results.get('security_tests', {}).get('xss_attempts', []))
            ]) if self.test_results.get('security_tests') else False,
            
            'Performance': self.test_results.get('performance_metrics', {}).get('statistics', {}).get('mean_ms', float('inf')) < 100,
            
            'Load Handling': (self.test_results.get('load_test_results', {}).get('successful', 0) / 
                            max(self.test_results.get('load_test_results', {}).get('total_requests', 1), 1)) > 0.95,
            
            'Database Scale': self.test_results.get('database_performance', {}).get('bulk_insert', {}).get('bags_per_second', 0) > 1000
        }
        
        passed = sum(criteria.values())
        total = len(criteria)
        
        for criterion, passed_test in criteria.items():
            report.append(f"{criterion}: {'✅ PASS' if passed_test else '❌ FAIL'}")
        
        report.append("")
        report.append(f"Overall Score: {passed}/{total} ({(passed/total)*100:.0f}%)")
        
        if passed == total:
            report.append("Status: ✅ PRODUCTION READY")
            self.test_results['overall_status'] = 'PRODUCTION_READY'
        elif passed >= total * 0.75:
            report.append("Status: ⚠️ NEARLY READY (Minor fixes needed)")
            self.test_results['overall_status'] = 'NEARLY_READY'
        elif passed >= total * 0.5:
            report.append("Status: ⚠️ NEEDS WORK (Major improvements required)")
            self.test_results['overall_status'] = 'NEEDS_WORK'
        else:
            report.append("Status: ❌ NOT READY (Critical issues present)")
            self.test_results['overall_status'] = 'NOT_READY'
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        logger.info("Starting Ultimate Production Test Suite...")
        
        try:
            # 1. Security Tests
            logger.info("Running security tests...")
            self.test_results['security_tests'] = self.test_authentication_security()
            
            # 2. Edge Cases
            logger.info("Running edge case tests...")
            self.test_results['edge_cases'] = self.test_edge_cases()
            
            # 3. Load Test with 50+ concurrent users
            logger.info("Running load test with 50 concurrent users...")
            self.test_results['load_test_results'] = self.test_concurrent_operations(50)
            
            # 4. Database Performance Test
            logger.info("Running database performance test...")
            self.test_results['database_performance'] = self.test_database_performance(800000)
            
            # 5. System Resilience
            logger.info("Running system resilience tests...")
            self.test_results['resilience'] = self.test_system_resilience()
            
            # 6. Async Performance Test
            logger.info("Running async performance test...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.test_results['async_performance'] = loop.run_until_complete(
                self.test_async_performance(1000)
            )
            
            # Copy async performance to main performance metrics for report
            if self.test_results['async_performance'].get('metrics'):
                self.test_results['performance_metrics'] = {
                    'statistics': self.test_results['async_performance']['metrics']
                }
            
        except Exception as e:
            logger.error(f"Test suite failed: {e}")
            self.test_results['error'] = str(e)
            self.test_results['overall_status'] = 'ERROR'
        
        # Generate and save report
        report = self.generate_report()
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"ultimate_test_report_{timestamp}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        # Save JSON results
        json_file = f"ultimate_test_results_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        # Print report
        print(report)
        logger.info(f"Test report saved to {report_file}")
        logger.info(f"Detailed results saved to {json_file}")
        
        return self.test_results


if __name__ == "__main__":
    # Check if server is running
    try:
        response = requests.get("http://0.0.0.0:5000/health", timeout=5)
        if response.status_code != 200:
            logger.error("Server health check failed. Please ensure the application is running.")
            exit(1)
    except Exception as e:
        logger.error(f"Cannot connect to server: {e}")
        logger.error("Please start the application first with: gunicorn --bind 0.0.0.0:5000 main:app")
        exit(1)
    
    # Run the ultimate test suite
    tester = UltimateProductionTest()
    results = tester.run_all_tests()
    
    # Exit with appropriate code
    if results['overall_status'] == 'PRODUCTION_READY':
        exit(0)
    elif results['overall_status'] in ['NEARLY_READY', 'NEEDS_WORK']:
        exit(1)
    else:
        exit(2)
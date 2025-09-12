#!/usr/bin/env python3
"""
AWS Performance Testing Script
Tests AWS infrastructure performance and validates migration success
"""

import asyncio
import aiohttp
import time
import statistics
import json
import logging
from datetime import datetime
from typing import Dict, List, Any
import concurrent.futures
import psycopg2
import redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AWSPerformanceTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'base_url': base_url,
            'tests': {}
        }
    
    async def test_endpoint(self, session: aiohttp.ClientSession, endpoint: str, 
                           method: str = 'GET', data: dict = None, 
                           expected_status: int = 200) -> Dict[str, Any]:
        """Test a single endpoint"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            async with session.request(method, url, json=data) as response:
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                content = await response.text()
                
                return {
                    'endpoint': endpoint,
                    'method': method,
                    'status_code': response.status,
                    'response_time_ms': response_time,
                    'success': response.status == expected_status,
                    'content_length': len(content),
                    'headers': dict(response.headers)
                }
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return {
                'endpoint': endpoint,
                'method': method,
                'status_code': 0,
                'response_time_ms': response_time,
                'success': False,
                'error': str(e)
            }
    
    async def load_test_endpoint(self, endpoint: str, concurrent_users: int = 50, 
                                requests_per_user: int = 10) -> Dict[str, Any]:
        """Load test a single endpoint"""
        logger.info(f"Load testing {endpoint} with {concurrent_users} users, {requests_per_user} requests each")
        
        connector = aiohttp.TCPConnector(limit=100)
        timeout = aiohttp.ClientTimeout(total=60)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []
            
            # Create tasks for concurrent requests
            for user in range(concurrent_users):
                for request in range(requests_per_user):
                    task = self.test_endpoint(session, endpoint)
                    tasks.append(task)
            
            # Execute all tasks concurrently
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Process results
            successful_results = [r for r in results if isinstance(r, dict) and r.get('success')]
            failed_results = [r for r in results if isinstance(r, dict) and not r.get('success')]
            exceptions = [r for r in results if isinstance(r, Exception)]
            
            response_times = [r['response_time_ms'] for r in successful_results]
            
            return {
                'endpoint': endpoint,
                'total_requests': len(tasks),
                'successful_requests': len(successful_results),
                'failed_requests': len(failed_results),
                'exceptions': len(exceptions),
                'success_rate': len(successful_results) / len(tasks) * 100,
                'total_time_seconds': total_time,
                'requests_per_second': len(tasks) / total_time,
                'response_times': {
                    'min_ms': min(response_times) if response_times else 0,
                    'max_ms': max(response_times) if response_times else 0,
                    'avg_ms': statistics.mean(response_times) if response_times else 0,
                    'median_ms': statistics.median(response_times) if response_times else 0,
                    'p95_ms': self.percentile(response_times, 0.95) if response_times else 0,
                    'p99_ms': self.percentile(response_times, 0.99) if response_times else 0
                }
            }
    
    def percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    async def test_health_endpoints(self) -> Dict[str, Any]:
        """Test health check endpoints"""
        logger.info("Testing health endpoints...")
        
        endpoints = ['/health', '/ready', '/live']
        timeout = aiohttp.ClientTimeout(total=10)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            tasks = [self.test_endpoint(session, endpoint) for endpoint in endpoints]
            results = await asyncio.gather(*tasks)
            
            return {
                'test_type': 'health_checks',
                'results': results,
                'all_healthy': all(r.get('success', False) for r in results)
            }
    
    async def test_critical_endpoints(self) -> Dict[str, Any]:
        """Test critical application endpoints"""
        logger.info("Testing critical endpoints...")
        
        endpoints = [
            ('/', 'GET'),
            ('/api/stats', 'GET'),
            ('/api/health', 'GET'),
            ('/login', 'GET'),
        ]
        
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            tasks = []
            for endpoint, method in endpoints:
                task = self.test_endpoint(session, endpoint, method)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            response_times = [r['response_time_ms'] for r in results if r.get('success')]
            
            return {
                'test_type': 'critical_endpoints',
                'results': results,
                'avg_response_time_ms': statistics.mean(response_times) if response_times else 0,
                'max_response_time_ms': max(response_times) if response_times else 0,
                'success_rate': sum(1 for r in results if r.get('success')) / len(results) * 100
            }
    
    async def run_load_tests(self) -> Dict[str, Any]:
        """Run load tests on key endpoints"""
        logger.info("Running load tests...")
        
        endpoints_to_test = [
            '/health',
            '/',
            '/api/stats'
        ]
        
        load_test_results = {}
        
        for endpoint in endpoints_to_test:
            try:
                result = await self.load_test_endpoint(endpoint, concurrent_users=50, requests_per_user=10)
                load_test_results[endpoint] = result
                
                # Log results
                logger.info(f"Load test {endpoint}:")
                logger.info(f"  Success rate: {result['success_rate']:.1f}%")
                logger.info(f"  Avg response time: {result['response_times']['avg_ms']:.1f}ms")
                logger.info(f"  P95 response time: {result['response_times']['p95_ms']:.1f}ms")
                logger.info(f"  Requests/sec: {result['requests_per_second']:.1f}")
                
            except Exception as e:
                logger.error(f"Load test failed for {endpoint}: {e}")
                load_test_results[endpoint] = {'error': str(e)}
        
        return {
            'test_type': 'load_tests',
            'results': load_test_results
        }
    
    def test_database_performance(self, database_url: str) -> Dict[str, Any]:
        """Test database performance"""
        logger.info("Testing database performance...")
        
        try:
            # Test connection time
            start_time = time.time()
            conn = psycopg2.connect(database_url)
            connection_time = (time.time() - start_time) * 1000
            
            cursor = conn.cursor()
            
            # Test simple query
            start_time = time.time()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            simple_query_time = (time.time() - start_time) * 1000
            
            # Test table count query
            start_time = time.time()
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
            table_count = cursor.fetchone()[0]
            count_query_time = (time.time() - start_time) * 1000
            
            # Test more complex query if tables exist
            complex_query_time = 0
            if table_count > 0:
                try:
                    start_time = time.time()
                    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' LIMIT 5")
                    cursor.fetchall()
                    complex_query_time = (time.time() - start_time) * 1000
                except:
                    pass
            
            conn.close()
            
            return {
                'test_type': 'database_performance',
                'connection_time_ms': connection_time,
                'simple_query_time_ms': simple_query_time,
                'count_query_time_ms': count_query_time,
                'complex_query_time_ms': complex_query_time,
                'table_count': table_count,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Database performance test failed: {e}")
            return {
                'test_type': 'database_performance',
                'success': False,
                'error': str(e)
            }
    
    def test_redis_performance(self, redis_url: str) -> Dict[str, Any]:
        """Test Redis cache performance"""
        logger.info("Testing Redis performance...")
        
        try:
            r = redis.from_url(redis_url, decode_responses=True)
            
            # Test connection
            start_time = time.time()
            r.ping()
            ping_time = (time.time() - start_time) * 1000
            
            # Test set operation
            start_time = time.time()
            r.set("test_key", "test_value", ex=60)
            set_time = (time.time() - start_time) * 1000
            
            # Test get operation
            start_time = time.time()
            value = r.get("test_key")
            get_time = (time.time() - start_time) * 1000
            
            # Test delete operation
            start_time = time.time()
            r.delete("test_key")
            delete_time = (time.time() - start_time) * 1000
            
            # Get Redis info
            info = r.info()
            
            return {
                'test_type': 'redis_performance',
                'ping_time_ms': ping_time,
                'set_time_ms': set_time,
                'get_time_ms': get_time,
                'delete_time_ms': delete_time,
                'redis_version': info.get('redis_version'),
                'connected_clients': info.get('connected_clients'),
                'used_memory': info.get('used_memory'),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Redis performance test failed: {e}")
            return {
                'test_type': 'redis_performance',
                'success': False,
                'error': str(e)
            }
    
    async def run_comprehensive_test(self, database_url: str = None, redis_url: str = None) -> Dict[str, Any]:
        """Run comprehensive performance test suite"""
        logger.info("🚀 Starting comprehensive AWS performance tests...")
        
        # Run web application tests
        health_results = await self.test_health_endpoints()
        critical_results = await self.test_critical_endpoints()
        load_results = await self.run_load_tests()
        
        self.results['tests']['health_checks'] = health_results
        self.results['tests']['critical_endpoints'] = critical_results
        self.results['tests']['load_tests'] = load_results
        
        # Run database tests if URL provided
        if database_url:
            db_results = self.test_database_performance(database_url)
            self.results['tests']['database'] = db_results
        
        # Run Redis tests if URL provided
        if redis_url:
            redis_results = self.test_redis_performance(redis_url)
            self.results['tests']['redis'] = redis_results
        
        # Calculate overall performance metrics
        self.calculate_summary_metrics()
        
        return self.results
    
    def calculate_summary_metrics(self):
        """Calculate summary performance metrics"""
        summary = {
            'overall_health': True,
            'avg_response_time_ms': 0,
            'max_response_time_ms': 0,
            'success_rate_percent': 100,
            'performance_grade': 'A',
            'recommendations': []
        }
        
        # Analyze health checks
        health_test = self.results['tests'].get('health_checks', {})
        if not health_test.get('all_healthy', False):
            summary['overall_health'] = False
            summary['recommendations'].append('Health check endpoints are failing')
        
        # Analyze critical endpoints
        critical_test = self.results['tests'].get('critical_endpoints', {})
        if critical_test:
            summary['avg_response_time_ms'] = critical_test.get('avg_response_time_ms', 0)
            summary['max_response_time_ms'] = critical_test.get('max_response_time_ms', 0)
            
            if summary['avg_response_time_ms'] > 100:
                summary['performance_grade'] = 'B'
                summary['recommendations'].append('Average response time exceeds 100ms')
            
            if summary['max_response_time_ms'] > 500:
                summary['performance_grade'] = 'C'
                summary['recommendations'].append('Maximum response time exceeds 500ms')
        
        # Analyze load tests
        load_test = self.results['tests'].get('load_tests', {}).get('results', {})
        if load_test:
            success_rates = [test.get('success_rate', 0) for test in load_test.values() if isinstance(test, dict)]
            if success_rates:
                summary['success_rate_percent'] = statistics.mean(success_rates)
                
                if summary['success_rate_percent'] < 95:
                    summary['performance_grade'] = 'C'
                    summary['recommendations'].append('Load test success rate below 95%')
        
        # Set overall grade
        if not summary['overall_health']:
            summary['performance_grade'] = 'F'
        
        if not summary['recommendations']:
            summary['recommendations'].append('All performance metrics within acceptable ranges')
        
        self.results['summary'] = summary
    
    def generate_report(self, filename: str = None) -> str:
        """Generate performance test report"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'aws_performance_report_{timestamp}.json'
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"Performance report generated: {filename}")
        
        # Print summary
        summary = self.results.get('summary', {})
        logger.info("\n" + "="*50)
        logger.info("PERFORMANCE TEST SUMMARY")
        logger.info("="*50)
        logger.info(f"Overall Health: {'✅ PASS' if summary.get('overall_health') else '❌ FAIL'}")
        logger.info(f"Performance Grade: {summary.get('performance_grade', 'N/A')}")
        logger.info(f"Average Response Time: {summary.get('avg_response_time_ms', 0):.1f}ms")
        logger.info(f"Success Rate: {summary.get('success_rate_percent', 0):.1f}%")
        
        recommendations = summary.get('recommendations', [])
        logger.info(f"\nRecommendations ({len(recommendations)}):")
        for i, rec in enumerate(recommendations, 1):
            logger.info(f"  {i}. {rec}")
        logger.info("="*50)
        
        return filename

async def main():
    """Main testing function"""
    import os
    
    # Get configuration from environment
    base_url = os.environ.get('AWS_APP_URL', 'http://localhost:5000')
    database_url = os.environ.get('DATABASE_URL')
    redis_url = os.environ.get('REDIS_URL')
    
    logger.info(f"Testing AWS infrastructure at: {base_url}")
    
    # Create tester and run tests
    tester = AWSPerformanceTester(base_url)
    results = await tester.run_comprehensive_test(database_url, redis_url)
    
    # Generate report
    report_file = tester.generate_report()
    
    # Determine exit code based on results
    summary = results.get('summary', {})
    success = summary.get('overall_health', False) and summary.get('performance_grade') in ['A', 'B']
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
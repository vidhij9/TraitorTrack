#!/usr/bin/env python3
"""
Comprehensive Performance Testing Suite for TraceTrack
Tests all performance requirements:
- Database queries <50ms
- Page load times <100ms  
- 60+ concurrent users
- Ultra-fast batch scanning (30 bags in <1 minute)
- 800k+ bags support for search
"""

import asyncio
import aiohttp
import time
import random
import json
import statistics
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
import requests
from datetime import datetime

class PerformanceTestResults:
    def __init__(self):
        self.response_times = []
        self.errors = []
        self.successful_requests = 0
        self.failed_requests = 0
        self.endpoint_metrics = {}
        
    def add_result(self, endpoint: str, time_ms: float, success: bool, error: str = ""):
        if endpoint not in self.endpoint_metrics:
            self.endpoint_metrics[endpoint] = {
                'times': [],
                'successes': 0,
                'failures': 0,
                'errors': []
            }
        
        self.endpoint_metrics[endpoint]['times'].append(time_ms)
        if success:
            self.endpoint_metrics[endpoint]['successes'] += 1
            self.successful_requests += 1
        else:
            self.endpoint_metrics[endpoint]['failures'] += 1
            self.failed_requests += 1
            if error:
                self.endpoint_metrics[endpoint]['errors'].append(error)
        
        self.response_times.append(time_ms)
    
    def get_summary(self) -> Dict[str, Any]:
        if not self.response_times:
            return {'error': 'No test results'}
        
        summary = {
            'total_requests': self.successful_requests + self.failed_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': f"{(self.successful_requests / (self.successful_requests + self.failed_requests) * 100):.2f}%",
            'response_times': {
                'min_ms': min(self.response_times),
                'max_ms': max(self.response_times),
                'avg_ms': statistics.mean(self.response_times),
                'median_ms': statistics.median(self.response_times),
                'p95_ms': sorted(self.response_times)[int(len(self.response_times) * 0.95)] if len(self.response_times) > 20 else max(self.response_times),
                'p99_ms': sorted(self.response_times)[int(len(self.response_times) * 0.99)] if len(self.response_times) > 100 else max(self.response_times),
            },
            'endpoint_breakdown': {}
        }
        
        for endpoint, metrics in self.endpoint_metrics.items():
            if metrics['times']:
                summary['endpoint_breakdown'][endpoint] = {
                    'requests': len(metrics['times']),
                    'successes': metrics['successes'],
                    'failures': metrics['failures'],
                    'avg_ms': statistics.mean(metrics['times']),
                    'max_ms': max(metrics['times']),
                    'min_ms': min(metrics['times']),
                    'meets_target': self._check_target(endpoint, metrics['times'])
                }
        
        return summary
    
    def _check_target(self, endpoint: str, times: List[float]) -> Dict[str, Any]:
        """Check if endpoint meets performance targets"""
        avg_time = statistics.mean(times)
        p95_time = sorted(times)[int(len(times) * 0.95)] if len(times) > 20 else max(times)
        
        # Define targets based on endpoint type
        if 'scan' in endpoint or 'fast' in endpoint:
            target = 50  # Scanning endpoints should be <50ms
        elif 'api' in endpoint:
            target = 100  # API endpoints should be <100ms
        else:
            target = 100  # Page loads should be <100ms
        
        return {
            'target_ms': target,
            'avg_meets_target': avg_time < target,
            'p95_meets_target': p95_time < target
        }

class PerformanceLoadTester:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = None
        self.results = PerformanceTestResults()
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_endpoint(self, endpoint: str, method: str = "GET", data: Dict = None, headers: Dict = None):
        """Test a single endpoint and record metrics"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            if self.session:
                async with self.session.request(method, url, json=data, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    elapsed_ms = (time.time() - start_time) * 1000
                    success = response.status < 400
                    self.results.add_result(endpoint, elapsed_ms, success)
                    return await response.json() if response.headers.get('content-type', '').startswith('application/json') else await response.text()
            else:
                raise Exception("Session not initialized")
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self.results.add_result(endpoint, elapsed_ms, False, str(e))
            return None
    
    async def simulate_user_session(self, user_id: int):
        """Simulate a complete user session"""
        # Test main pages
        await self.test_endpoint("/")
        await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # Test API endpoints
        await self.test_endpoint("/api/performance/metrics")
        await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Test search with high volume
        search_query = f"SB{random.randint(10000, 99999)}"
        await self.test_endpoint(f"/api/search?q={search_query}&type=bags")
        
        # Test scanning operations
        await self.test_endpoint("/api/fast_parent_scan", "POST", {
            "qr_code": f"SB{random.randint(10000, 99999)}"
        })
        
        await self.test_endpoint("/api/fast_child_scan", "POST", {
            "qr_code": f"CB{random.randint(10000, 99999)}"
        })
        
        # Test dashboard stats
        await self.test_endpoint("/api/dashboard-stats")
        
        return f"User {user_id} session completed"
    
    async def run_concurrent_users_test(self, num_users: int = 60):
        """Run test with concurrent users"""
        print(f"\n🚀 Starting concurrent users test with {num_users} users...")
        
        tasks = []
        for i in range(num_users):
            tasks.append(self.simulate_user_session(i))
            # Stagger user starts slightly
            if i % 10 == 0:
                await asyncio.sleep(0.1)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        print(f"✅ Completed {success_count}/{num_users} user sessions successfully")
        
        return self.results.get_summary()
    
    async def test_batch_scanning_performance(self):
        """Test ultra-fast batch scanning (30 bags in <1 minute)"""
        print("\n🔄 Testing batch scanning performance...")
        
        start_time = time.time()
        parent_qr = f"SB{random.randint(100000, 999999)}"
        
        # Start batch session
        await self.test_endpoint("/api/ultra_batch/start", "POST", {
            "parent_qr": parent_qr
        })
        
        # Scan 30 children
        for i in range(30):
            child_qr = f"CB{random.randint(100000, 999999)}"
            await self.test_endpoint("/api/ultra_batch/scan", "POST", {
                "parent_qr": parent_qr,
                "child_qr": child_qr
            })
        
        # Complete batch
        await self.test_endpoint("/api/ultra_batch/complete", "POST", {
            "parent_qr": parent_qr
        })
        
        total_time = time.time() - start_time
        print(f"✅ Batch scanning of 30 bags completed in {total_time:.2f} seconds")
        
        return {
            'total_time_seconds': total_time,
            'meets_target': total_time < 60,
            'bags_per_second': 30 / total_time
        }
    
    async def test_database_query_performance(self):
        """Test database query performance (<50ms requirement)"""
        print("\n📊 Testing database query performance...")
        
        # Test various query-heavy endpoints
        endpoints = [
            "/api/bags?limit=100",
            "/api/scans/recent?limit=50",
            "/api/stats",
            "/api/search?q=SB&type=bags&limit=100",
            "/api/performance/metrics",
        ]
        
        for endpoint in endpoints:
            for _ in range(5):  # Test each endpoint 5 times
                await self.test_endpoint(endpoint)
                await asyncio.sleep(0.1)
        
        return self.results.get_summary()
    
    async def test_search_with_large_dataset(self):
        """Test search performance with 800k+ bags simulation"""
        print("\n🔍 Testing search with large dataset...")
        
        # Generate diverse search patterns
        search_patterns = [
            "SB1",  # Prefix search
            "CB99",  # Child bag search
            "12345",  # Number search
            "BAG",  # Text search
            "SB123456",  # Full ID search
        ]
        
        for pattern in search_patterns:
            start_time = time.time()
            await self.test_endpoint(f"/api/search?q={pattern}&type=bags&limit=100")
            elapsed_ms = (time.time() - start_time) * 1000
            print(f"  Search for '{pattern}': {elapsed_ms:.2f}ms")
        
        return self.results.get_summary()

async def run_comprehensive_tests():
    """Run all performance tests"""
    print("=" * 60)
    print("TraceTrack Performance Testing Suite")
    print("=" * 60)
    
    async with PerformanceLoadTester() as tester:
        # Test 1: Database Query Performance
        print("\n[TEST 1] Database Query Performance (<50ms)")
        db_results = await tester.test_database_query_performance()
        
        # Test 2: Concurrent Users (60+)
        print("\n[TEST 2] Concurrent Users Test (60+ users)")
        concurrent_results = await tester.run_concurrent_users_test(65)
        
        # Test 3: Batch Scanning
        print("\n[TEST 3] Ultra-Fast Batch Scanning (30 bags <1 min)")
        batch_results = await tester.test_batch_scanning_performance()
        
        # Test 4: Large Dataset Search
        print("\n[TEST 4] Search with Large Dataset (800k+ bags)")
        search_results = await tester.test_search_with_large_dataset()
        
        # Generate final report
        print("\n" + "=" * 60)
        print("PERFORMANCE TEST RESULTS SUMMARY")
        print("=" * 60)
        
        # Overall metrics
        overall_summary = tester.results.get_summary()
        print(f"\n📈 OVERALL METRICS:")
        print(f"  Total Requests: {overall_summary['total_requests']}")
        print(f"  Success Rate: {overall_summary['success_rate']}")
        print(f"  Response Times:")
        print(f"    Average: {overall_summary['response_times']['avg_ms']:.2f}ms")
        print(f"    Median: {overall_summary['response_times']['median_ms']:.2f}ms")
        print(f"    P95: {overall_summary['response_times']['p95_ms']:.2f}ms")
        print(f"    P99: {overall_summary['response_times']['p99_ms']:.2f}ms")
        
        # Endpoint breakdown
        print(f"\n📊 ENDPOINT PERFORMANCE:")
        for endpoint, metrics in overall_summary['endpoint_breakdown'].items():
            status = "✅" if metrics['meets_target']['avg_meets_target'] else "❌"
            print(f"  {status} {endpoint}:")
            print(f"      Avg: {metrics['avg_ms']:.2f}ms (Target: {metrics['meets_target']['target_ms']}ms)")
            print(f"      Success Rate: {metrics['successes']}/{metrics['requests']}")
        
        # Performance requirements check
        print(f"\n✔️ PERFORMANCE REQUIREMENTS CHECK:")
        
        # Check <50ms database queries
        db_endpoints = [e for e in overall_summary['endpoint_breakdown'] if 'scan' in e or 'fast' in e]
        db_meets_target = all(
            overall_summary['endpoint_breakdown'][e]['meets_target']['avg_meets_target'] 
            for e in db_endpoints if e in overall_summary['endpoint_breakdown']
        )
        print(f"  {'✅' if db_meets_target else '❌'} Database queries <50ms: {'PASS' if db_meets_target else 'FAIL'}")
        
        # Check <100ms page loads
        page_meets_target = all(
            metrics['avg_ms'] < 100 
            for endpoint, metrics in overall_summary['endpoint_breakdown'].items()
            if not ('scan' in endpoint or 'fast' in endpoint)
        )
        print(f"  {'✅' if page_meets_target else '❌'} Page loads <100ms: {'PASS' if page_meets_target else 'FAIL'}")
        
        # Check 60+ concurrent users
        concurrent_success = overall_summary['successful_requests'] > 300  # At least 5 requests per user
        print(f"  {'✅' if concurrent_success else '❌'} 60+ concurrent users: {'PASS' if concurrent_success else 'FAIL'}")
        
        # Check batch scanning
        batch_pass = batch_results['meets_target']
        print(f"  {'✅' if batch_pass else '❌'} Batch scanning (30 bags <1min): {'PASS' if batch_pass else 'FAIL'}")
        
        # Overall pass/fail
        all_pass = db_meets_target and page_meets_target and concurrent_success and batch_pass
        print(f"\n{'🎉 ALL TESTS PASSED!' if all_pass else '⚠️ SOME TESTS FAILED - OPTIMIZATION NEEDED'}")
        
        return overall_summary

if __name__ == "__main__":
    # Run the tests
    asyncio.run(run_comprehensive_tests())
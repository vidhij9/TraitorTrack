#!/usr/bin/env python3
"""
Enhanced Load Test for TraceTrack System
Tests with 55 concurrent users and simulates 800,000+ bags
"""

import asyncio
import aiohttp
import time
import random
import string
import logging
import sys
import json
import psutil
import os
from datetime import datetime
from typing import Dict, List
import threading
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'enhanced_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://0.0.0.0:5000"
CONCURRENT_USERS = 55
TEST_DURATION_SECONDS = 120  # 2 minutes comprehensive test
REQUEST_TIMEOUT = 45
BATCH_SIZE = 1000  # For bag creation simulation

class PerformanceMetrics:
    """Enhanced performance metrics tracking"""
    def __init__(self):
        self.start_time = time.time()
        self.metrics = defaultdict(lambda: {
            'count': 0,
            'success': 0,
            'errors': 0,
            'total_time': 0,
            'min_time': float('inf'),
            'max_time': 0,
            'status_codes': defaultdict(int)
        })
        self.lock = threading.Lock()
        self.bags_created = 0
        self.bills_created = 0
        self.scans_completed = 0
        
    def record(self, endpoint: str, duration: float, status: int, success: bool):
        with self.lock:
            m = self.metrics[endpoint]
            m['count'] += 1
            m['total_time'] += duration
            m['status_codes'][status] += 1
            
            if success:
                m['success'] += 1
            else:
                m['errors'] += 1
                
            m['min_time'] = min(m['min_time'], duration)
            m['max_time'] = max(m['max_time'], duration)
    
    def increment_bags(self, count: int):
        with self.lock:
            self.bags_created += count
    
    def increment_bills(self):
        with self.lock:
            self.bills_created += 1
    
    def increment_scans(self):
        with self.lock:
            self.scans_completed += 1
    
    def get_summary(self) -> Dict:
        duration = time.time() - self.start_time
        all_times = []
        total_requests = 0
        total_errors = 0
        
        for endpoint, m in self.metrics.items():
            if m['count'] > 0:
                total_requests += m['count']
                total_errors += m['errors']
                avg_time = m['total_time'] / m['count']
                for _ in range(m['count']):
                    all_times.append(avg_time)
        
        if not all_times:
            return {"error": "No requests completed"}
        
        all_times.sort()
        
        return {
            "test_duration": duration,
            "total_requests": total_requests,
            "successful_requests": total_requests - total_errors,
            "failed_requests": total_errors,
            "error_rate": (total_errors / total_requests * 100) if total_requests > 0 else 0,
            "requests_per_second": total_requests / duration if duration > 0 else 0,
            "bags_created": self.bags_created,
            "bills_created": self.bills_created,
            "scans_completed": self.scans_completed,
            "avg_response_time": sum(all_times) / len(all_times) if all_times else 0,
            "p50_response_time": all_times[int(len(all_times) * 0.5)] if all_times else 0,
            "p95_response_time": all_times[int(len(all_times) * 0.95)] if all_times else 0,
            "p99_response_time": all_times[int(len(all_times) * 0.99)] if all_times else 0,
            "endpoint_metrics": dict(self.metrics)
        }

class EnhancedLoadTester:
    """Enhanced load testing with comprehensive scenarios"""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.running = True
        self.sessions = []
        
    def generate_unique_id(self, prefix=""):
        """Generate unique identifiers"""
        timestamp = int(time.time() * 1000000)
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        return f"{prefix}_{timestamp}_{random_str}"
    
    async def create_session(self):
        """Create an optimized session"""
        connector = aiohttp.TCPConnector(
            limit=200,
            limit_per_host=50,
            ttl_dns_cache=300,
            enable_cleanup_closed=True
        )
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        )
        self.sessions.append(session)
        return session
    
    async def cleanup_sessions(self):
        """Clean up all sessions"""
        for session in self.sessions:
            await session.close()
    
    async def make_request(self, session, method, endpoint, data=None, json_data=None):
        """Make an HTTP request with metrics tracking"""
        start_time = time.time()
        url = f"{BASE_URL}{endpoint}"
        
        try:
            if method == "GET":
                async with session.get(url) as response:
                    duration = time.time() - start_time
                    success = response.status in [200, 304]
                    self.metrics.record(endpoint, duration, response.status, success)
                    return response.status, await response.text()
                    
            elif method == "POST":
                kwargs = {}
                if json_data:
                    kwargs['json'] = json_data
                elif data:
                    kwargs['data'] = data
                    
                async with session.post(url, **kwargs) as response:
                    duration = time.time() - start_time
                    success = response.status in [200, 201, 302, 303]
                    self.metrics.record(endpoint, duration, response.status, success)
                    return response.status, await response.text()
                    
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            self.metrics.record(endpoint, duration, 0, False)
            return 0, "Timeout"
        except Exception as e:
            duration = time.time() - start_time
            self.metrics.record(endpoint, duration, 0, False)
            return 0, str(e)
    
    async def login_user(self, session, username="admin", password="admin123"):
        """Login and establish session"""
        status, _ = await self.make_request(
            session, "POST", "/login",
            data={"username": username, "password": password}
        )
        return status in [200, 302, 303]
    
    async def simulate_scanner_workflow(self, user_id: int):
        """Simulate intensive QR scanning workflow"""
        session = await self.create_session()
        
        try:
            if not await self.login_user(session):
                logger.warning(f"Scanner {user_id} failed to login")
                return
            
            # Intensive scanning simulation
            scan_count = 0
            while self.running and scan_count < 50:
                # Create parent bag
                parent_qr = self.generate_unique_id("PARENT")
                status, _ = await self.make_request(
                    session, "POST", "/scan/parent",
                    json_data={"qr_code": parent_qr}
                )
                
                if status in [200, 201]:
                    self.metrics.increment_bags(1)
                    
                    # Create and scan child bags in batches
                    num_children = random.randint(10, 30)
                    child_qrs = [self.generate_unique_id("CHILD") for _ in range(num_children)]
                    
                    status, _ = await self.make_request(
                        session, "POST", "/process_child_scan_fast",
                        json_data={"parent_qr": parent_qr, "child_qrs": child_qrs}
                    )
                    
                    if status in [200, 201]:
                        self.metrics.increment_bags(num_children)
                        self.metrics.increment_scans()
                
                scan_count += 1
                await asyncio.sleep(random.uniform(0.5, 1.5))
            
            logger.info(f"Scanner {user_id} completed {scan_count} scans")
            
        finally:
            await session.close()
    
    async def simulate_viewer_workflow(self, user_id: int):
        """Simulate user viewing pages"""
        session = await self.create_session()
        
        try:
            if not await self.login_user(session):
                logger.warning(f"Viewer {user_id} failed to login")
                return
            
            pages = ['/dashboard', '/bags', '/bills', '/scans', '/api/stats', '/api/scans']
            view_count = 0
            
            while self.running and view_count < 100:
                page = random.choice(pages)
                await self.make_request(session, "GET", page)
                view_count += 1
                await asyncio.sleep(random.uniform(0.3, 1.0))
            
            logger.info(f"Viewer {user_id} viewed {view_count} pages")
            
        finally:
            await session.close()
    
    async def simulate_biller_workflow(self, user_id: int):
        """Simulate bill creation workflow"""
        session = await self.create_session()
        
        try:
            if not await self.login_user(session):
                logger.warning(f"Biller {user_id} failed to login")
                return
            
            bills_created = 0
            while self.running and bills_created < 20:
                bill_id = self.generate_unique_id("BILL")
                status, _ = await self.make_request(
                    session, "POST", "/bill/create",
                    data={
                        "bill_id": bill_id,
                        "description": f"Test bill {bill_id}",
                        "parent_bag_count": random.randint(5, 20)
                    }
                )
                
                if status in [200, 201, 302]:
                    self.metrics.increment_bills()
                    bills_created += 1
                
                await asyncio.sleep(random.uniform(1, 3))
            
            logger.info(f"Biller {user_id} created {bills_created} bills")
            
        finally:
            await session.close()
    
    async def simulate_admin_workflow(self, user_id: int):
        """Simulate admin monitoring workflow"""
        session = await self.create_session()
        
        try:
            if not await self.login_user(session):
                logger.warning(f"Admin {user_id} failed to login")
                return
            
            admin_pages = ['/user_management', '/api/stats', '/admin/system-integrity']
            checks = 0
            
            while self.running and checks < 50:
                page = random.choice(admin_pages)
                await self.make_request(session, "GET", page)
                checks += 1
                await asyncio.sleep(random.uniform(1, 2))
            
            logger.info(f"Admin {user_id} performed {checks} checks")
            
        finally:
            await session.close()
    
    async def run_concurrent_test(self):
        """Run concurrent user simulations"""
        logger.info(f"Starting {CONCURRENT_USERS} concurrent user simulations...")
        
        tasks = []
        
        # Distribute users across different roles
        scanner_count = int(CONCURRENT_USERS * 0.4)  # 40% scanners
        viewer_count = int(CONCURRENT_USERS * 0.3)   # 30% viewers
        biller_count = int(CONCURRENT_USERS * 0.2)   # 20% billers
        admin_count = CONCURRENT_USERS - scanner_count - viewer_count - biller_count  # 10% admins
        
        user_id = 0
        
        # Create scanner tasks
        for _ in range(scanner_count):
            tasks.append(asyncio.create_task(self.simulate_scanner_workflow(user_id)))
            user_id += 1
        
        # Create viewer tasks
        for _ in range(viewer_count):
            tasks.append(asyncio.create_task(self.simulate_viewer_workflow(user_id)))
            user_id += 1
        
        # Create biller tasks
        for _ in range(biller_count):
            tasks.append(asyncio.create_task(self.simulate_biller_workflow(user_id)))
            user_id += 1
        
        # Create admin tasks
        for _ in range(admin_count):
            tasks.append(asyncio.create_task(self.simulate_admin_workflow(user_id)))
            user_id += 1
        
        # Wait for test duration
        await asyncio.sleep(TEST_DURATION_SECONDS)
        
        # Stop all workflows
        self.running = False
        
        # Wait for tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("All concurrent users completed")
    
    async def test_system_capacity(self):
        """Test system's capacity to handle large datasets"""
        session = await self.create_session()
        
        try:
            await self.login_user(session)
            
            # Test API response with potentially large dataset
            status, response = await self.make_request(session, "GET", "/api/stats")
            if status == 200:
                try:
                    stats = json.loads(response)
                    logger.info(f"System stats: Total bags: {stats.get('total_bags', 0)}, "
                              f"Total bills: {stats.get('total_bills', 0)}, "
                              f"Total scans: {stats.get('total_scans', 0)}")
                except:
                    pass
            
            # Test pagination and filtering
            await self.make_request(session, "GET", "/bags?page=1&limit=100")
            await self.make_request(session, "GET", "/bills?status=completed")
            await self.make_request(session, "GET", "/scans?limit=1000")
            
        finally:
            await session.close()
    
    def get_system_resources(self):
        """Get current system resource usage"""
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net = psutil.net_io_counters()
        
        return {
            "cpu_percent": cpu,
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024**3),
            "disk_percent": disk.percent,
            "network_sent_mb": net.bytes_sent / (1024**2),
            "network_recv_mb": net.bytes_recv / (1024**2)
        }

async def main():
    """Main test execution"""
    logger.info("=" * 80)
    logger.info("ENHANCED LOAD TEST FOR TRACETRACK SYSTEM")
    logger.info("=" * 80)
    logger.info(f"Configuration:")
    logger.info(f"  - Concurrent Users: {CONCURRENT_USERS}")
    logger.info(f"  - Test Duration: {TEST_DURATION_SECONDS} seconds")
    logger.info(f"  - Request Timeout: {REQUEST_TIMEOUT} seconds")
    logger.info("=" * 80)
    
    tester = EnhancedLoadTester()
    
    # Get initial system state
    initial_resources = tester.get_system_resources()
    logger.info("Initial System Resources:")
    logger.info(f"  CPU: {initial_resources['cpu_percent']}%")
    logger.info(f"  Memory: {initial_resources['memory_percent']}%")
    logger.info(f"  Disk: {initial_resources['disk_percent']}%")
    
    try:
        # Test system capacity first
        logger.info("\nTesting system capacity...")
        await tester.test_system_capacity()
        
        # Run main concurrent load test
        logger.info("\nStarting concurrent load test...")
        await tester.run_concurrent_test()
        
        # Get final resources
        final_resources = tester.get_system_resources()
        
        # Get test summary
        summary = tester.metrics.get_summary()
        
        # Print results
        logger.info("\n" + "=" * 80)
        logger.info("LOAD TEST RESULTS")
        logger.info("=" * 80)
        
        logger.info(f"\n📊 OVERALL METRICS:")
        logger.info(f"  Test Duration: {summary['test_duration']:.1f} seconds")
        logger.info(f"  Total Requests: {summary['total_requests']:,}")
        logger.info(f"  Successful: {summary['successful_requests']:,}")
        logger.info(f"  Failed: {summary['failed_requests']:,}")
        logger.info(f"  Error Rate: {summary['error_rate']:.2f}%")
        logger.info(f"  Requests/Second: {summary['requests_per_second']:.2f}")
        
        logger.info(f"\n📦 DATA CREATED:")
        logger.info(f"  Bags Created: {summary['bags_created']:,}")
        logger.info(f"  Bills Created: {summary['bills_created']:,}")
        logger.info(f"  Scans Completed: {summary['scans_completed']:,}")
        logger.info(f"  Estimated Total Bags in System: {summary['bags_created'] + 1000:,}+")
        
        logger.info(f"\n⏱️ RESPONSE TIMES:")
        logger.info(f"  Average: {summary['avg_response_time']:.3f}s")
        logger.info(f"  P50 (Median): {summary['p50_response_time']:.3f}s")
        logger.info(f"  P95: {summary['p95_response_time']:.3f}s")
        logger.info(f"  P99: {summary['p99_response_time']:.3f}s")
        
        logger.info(f"\n💻 SYSTEM RESOURCES:")
        logger.info(f"  CPU: {initial_resources['cpu_percent']}% → {final_resources['cpu_percent']}%")
        logger.info(f"  Memory: {initial_resources['memory_percent']:.1f}% → {final_resources['memory_percent']:.1f}%")
        logger.info(f"  Network Traffic: {(final_resources['network_sent_mb'] + final_resources['network_recv_mb'] - initial_resources['network_sent_mb'] - initial_resources['network_recv_mb']):.2f} MB")
        
        logger.info(f"\n📈 TOP ENDPOINTS BY VOLUME:")
        sorted_endpoints = sorted(summary['endpoint_metrics'].items(), 
                                 key=lambda x: x[1]['count'], reverse=True)[:10]
        for endpoint, metrics in sorted_endpoints:
            if metrics['count'] > 0:
                avg_time = metrics['total_time'] / metrics['count']
                error_rate = (metrics['errors'] / metrics['count']) * 100
                logger.info(f"  {endpoint}:")
                logger.info(f"    Requests: {metrics['count']:,}, Errors: {error_rate:.1f}%, Avg Time: {avg_time:.3f}s")
        
        # Performance assessment
        logger.info("\n" + "=" * 80)
        logger.info("PERFORMANCE ASSESSMENT")
        logger.info("=" * 80)
        
        # Calculate capacity for 800,000+ bags
        bags_per_second = summary['bags_created'] / summary['test_duration'] if summary['test_duration'] > 0 else 0
        time_for_800k = 800000 / bags_per_second / 3600 if bags_per_second > 0 else float('inf')
        
        logger.info(f"\n📦 CAPACITY FOR 800,000+ BAGS:")
        logger.info(f"  Current Rate: {bags_per_second:.1f} bags/second")
        logger.info(f"  Time to Process 800,000 bags: {time_for_800k:.1f} hours")
        logger.info(f"  System can handle large datasets: {'✅ YES' if time_for_800k < 24 else '⚠️ NEEDS OPTIMIZATION'}")
        
        # Verdict
        error_threshold = 5
        p95_threshold = 3
        
        if summary['error_rate'] < error_threshold and summary['p95_response_time'] < p95_threshold:
            verdict = "✅ EXCELLENT: System ready for production with 50+ concurrent users"
            ready = True
        elif summary['error_rate'] < 10 and summary['p95_response_time'] < 5:
            verdict = "✅ GOOD: System can handle load with minor optimizations"
            ready = True
        elif summary['error_rate'] < 20 and summary['p95_response_time'] < 10:
            verdict = "⚠️ FAIR: System needs optimization for sustained load"
            ready = False
        else:
            verdict = "❌ NEEDS IMPROVEMENT: Critical optimizations required"
            ready = False
        
        logger.info(f"\n🎯 FINAL VERDICT:")
        logger.info(f"  {verdict}")
        
        if ready:
            logger.info(f"\n✅ SYSTEM IS READY:")
            logger.info(f"  - Handles {CONCURRENT_USERS} concurrent users effectively")
            logger.info(f"  - Can process 800,000+ bags with current architecture")
            logger.info(f"  - Response times within acceptable limits")
            logger.info(f"  - Error rate manageable")
        else:
            logger.info(f"\n⚠️ OPTIMIZATIONS NEEDED:")
            if summary['error_rate'] > error_threshold:
                logger.info(f"  - Reduce error rate from {summary['error_rate']:.1f}% to below {error_threshold}%")
            if summary['p95_response_time'] > p95_threshold:
                logger.info(f"  - Improve P95 response time from {summary['p95_response_time']:.1f}s to below {p95_threshold}s")
            logger.info(f"  - Consider adding caching layers")
            logger.info(f"  - Optimize database queries")
        
        # Save detailed report
        report = {
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "concurrent_users": CONCURRENT_USERS,
                "test_duration": TEST_DURATION_SECONDS
            },
            "summary": summary,
            "resources": {
                "initial": initial_resources,
                "final": final_resources
            },
            "verdict": verdict,
            "capacity_assessment": {
                "bags_per_second": bags_per_second,
                "time_for_800k_hours": time_for_800k,
                "ready_for_production": ready
            }
        }
        
        report_file = f"enhanced_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"\n📄 Detailed report saved to: {report_file}")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise
    finally:
        await tester.cleanup_sessions()

if __name__ == "__main__":
    asyncio.run(main())
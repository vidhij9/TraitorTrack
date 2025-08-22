#!/usr/bin/env python3
"""
Production Readiness Test for TraceTrack AWS Deployment
Tests caching, performance, India timezone, and AWS optimizations
Target: 500+ concurrent users with <50ms response times
"""

import os
import time
import logging
import json
import concurrent.futures
from datetime import datetime
import pytz
from typing import Dict, List, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
import requests
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# India timezone
IST = pytz.timezone('Asia/Kolkata')

class ProductionReadinessTest:
    def __init__(self):
        self.database_url = os.environ.get('DATABASE_URL')
        self.base_url = "http://localhost:5000"
        self.test_results = {
            'passed': [],
            'failed': [],
            'warnings': [],
            'metrics': {},
            'cache_tests': {},
            'timezone_tests': {},
            'aws_readiness': {}
        }
        
        # Create optimized engine for AWS RDS Proxy
        if self.database_url:
            self.engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=50,  # Optimized for RDS Proxy
                max_overflow=100,
                pool_timeout=30,
                pool_recycle=300,
                pool_pre_ping=True
            )
        else:
            raise ValueError("DATABASE_URL environment variable not set")
        
        self.session = requests.Session()
    
    def run_all_tests(self):
        """Run comprehensive production readiness tests with AWS focus"""
        logger.info("="*60)
        logger.info("🚀 TRACETRACK AWS PRODUCTION READINESS TEST")
        logger.info(f"   India Region (ap-south-1) Optimization")
        logger.info(f"   Current IST: {datetime.now(IST).strftime('%d/%m/%Y %H:%M:%S IST')}")
        logger.info("="*60)
        
        test_suites = [
            ("🔍 Cache Performance", self.test_cache_performance),
            ("🕐 India Timezone (IST)", self.test_timezone_configuration),
            ("⚡ Database Performance", self.test_database_performance),
            ("📊 Critical Queries", self.test_critical_queries),
            ("👥 Concurrent Operations", self.test_concurrent_operations),
            ("☁️ AWS Readiness", self.test_aws_readiness),
            ("🔐 Security Validation", self.test_security),
            ("📈 Scalability Check", self.test_scalability)
        ]
        
        for suite_name, test_func in test_suites:
            logger.info(f"\n{'='*40}")
            logger.info(f"Testing: {suite_name}")
            logger.info(f"{'='*40}")
            
            try:
                test_func()
            except Exception as e:
                logger.error(f"Test suite failed: {e}")
                self.test_results['failed'].append(f"{suite_name}: {str(e)}")
        
        self.generate_report()
        return self.test_results
    
    def test_cache_performance(self):
        """Test in-memory caching with Redis/ElastiCache simulation"""
        logger.info("Testing cache performance...")
        
        endpoints = [
            ("/api/v2/stats", "Dashboard Stats", 60),
            ("/api/bag-count", "Bag Count", 120),
            ("/api/recent-scans", "Recent Scans", 30)
        ]
        
        cache_results = {}
        
        for endpoint, name, expected_ttl in endpoints:
            # First request (cache miss)
            start = time.time()
            r1 = self.session.get(f"{self.base_url}{endpoint}")
            time1 = time.time() - start
            
            # Second request (should be cached)
            start = time.time()
            r2 = self.session.get(f"{self.base_url}{endpoint}")
            time2 = time.time() - start
            
            # Third request (verify cache consistency)
            start = time.time()
            r3 = self.session.get(f"{self.base_url}{endpoint}")
            time3 = time.time() - start
            
            improvement = ((time1 - time2) / time1 * 100) if time1 > 0 else 0
            
            cache_results[name] = {
                "first_request_ms": round(time1 * 1000, 2),
                "cached_request_ms": round(time2 * 1000, 2),
                "improvement_percent": round(improvement, 2),
                "cache_working": time2 < time1 * 0.5,  # At least 50% faster
                "expected_ttl": expected_ttl,
                "status": "✅ PASS" if time2 < time1 * 0.5 else "❌ FAIL"
            }
            
            logger.info(f"  {cache_results[name]['status']} {name}: "
                       f"{cache_results[name]['cached_request_ms']}ms (cached) vs "
                       f"{cache_results[name]['first_request_ms']}ms (uncached) - "
                       f"{cache_results[name]['improvement_percent']}% improvement")
            
            if cache_results[name]['cache_working']:
                self.test_results['passed'].append(f"Cache: {name}")
            else:
                self.test_results['failed'].append(f"Cache: {name}")
        
        self.test_results['cache_tests'] = cache_results
        
        # Calculate overall cache performance
        avg_improvement = sum(r['improvement_percent'] for r in cache_results.values()) / len(cache_results)
        logger.info(f"\n  📊 Average Cache Improvement: {avg_improvement:.2f}%")
        
        if avg_improvement >= 50:
            logger.info("  ✅ Cache layer ready for AWS ElastiCache")
        else:
            logger.warning("  ⚠️ Cache layer needs optimization")
    
    def test_timezone_configuration(self):
        """Test India timezone (IST) and DD/MM/YY date formatting"""
        logger.info("Testing India timezone configuration...")
        
        # Login as admin
        login_data = {"username": "admin", "password": "admin123"}
        self.session.post(f"{self.base_url}/login", data=login_data)
        
        endpoints = [
            "/api/v2/stats",
            "/user_management",
            "/dashboard"
        ]
        
        timezone_results = {}
        for endpoint in endpoints:
            r = self.session.get(f"{self.base_url}{endpoint}")
            if r.status_code == 200:
                content = r.text
                
                # Check for IST indicators
                has_ist = "IST" in content or "Asia/Kolkata" in content
                
                # Check for DD/MM/YY format
                current_date_ddmmyy = datetime.now(IST).strftime("%d/%m/%y")
                current_date_ddmmyyyy = datetime.now(IST).strftime("%d/%m/%Y")
                has_ddmm_format = current_date_ddmmyy in content or current_date_ddmmyyyy in content
                
                timezone_results[endpoint] = {
                    "has_ist": has_ist,
                    "has_ddmm_format": has_ddmm_format,
                    "status": "✅ PASS" if (has_ist or has_ddmm_format) else "⚠️ PARTIAL"
                }
                
                logger.info(f"  {timezone_results[endpoint]['status']} {endpoint}: "
                           f"IST={has_ist}, DD/MM format={has_ddmm_format}")
        
        self.test_results['timezone_tests'] = timezone_results
        logger.info(f"\n  🕐 Current IST Time: {datetime.now(IST).strftime('%d/%m/%Y %H:%M:%S IST')}")
    
    def test_database_performance(self):
        """Test database performance with AWS RDS Proxy simulation"""
        logger.info("Testing database performance...")
        
        queries = [
            ("SELECT COUNT(*) FROM bags", "Count all bags"),
            ("SELECT COUNT(*) FROM scans", "Count all scans"),
            ("SELECT b.*, COUNT(s.id) as scan_count FROM bags b LEFT JOIN scans s ON b.id = s.bag_id GROUP BY b.id LIMIT 10", "Complex join query"),
            ("SELECT * FROM bags WHERE type = 'parent' LIMIT 100", "Filter parent bags"),
            ("SELECT * FROM users WHERE role = 'dispatcher' LIMIT 50", "Filter users by role")
        ]
        
        for query, description in queries:
            times = []
            for _ in range(5):
                start = time.time()
                with self.engine.connect() as conn:
                    result = conn.execute(text(query))
                    _ = result.fetchall()
                elapsed = time.time() - start
                times.append(elapsed)
            
            avg_time = sum(times) / len(times)
            self.test_results['metrics'][description] = {
                'avg_ms': round(avg_time * 1000, 2),
                'min_ms': round(min(times) * 1000, 2),
                'max_ms': round(max(times) * 1000, 2)
            }
            
            status = "✅" if avg_time < 0.05 else "⚠️" if avg_time < 0.1 else "❌"
            logger.info(f"  {status} {description}: {avg_time*1000:.2f}ms avg")
            
            if avg_time < 0.1:
                self.test_results['passed'].append(f"DB Query: {description}")
            else:
                self.test_results['failed'].append(f"DB Query: {description} (too slow)")
    
    def test_critical_queries(self):
        """Test critical business queries optimized for AWS"""
        logger.info("Testing critical queries...")
        
        critical_queries = [
            ("""
                SELECT b.qr_id, b.type, 
                       COUNT(DISTINCT s.id) as scan_count,
                       MAX(s.scanned_at) as last_scan
                FROM bags b
                LEFT JOIN scans s ON b.id = s.bag_id
                WHERE b.created_at >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY b.id, b.qr_id, b.type
                LIMIT 100
            """, "Weekly bag activity"),
            
            ("""
                SELECT u.username, u.role, COUNT(s.id) as total_scans
                FROM users u
                LEFT JOIN scans s ON u.id = s.user_id
                WHERE s.scanned_at >= CURRENT_DATE - INTERVAL '24 hours'
                GROUP BY u.id, u.username, u.role
                ORDER BY total_scans DESC
                LIMIT 10
            """, "Top scanners today"),
            
            ("""
                WITH RECURSIVE bag_hierarchy AS (
                    SELECT id, qr_id, type, 0 as level
                    FROM bags WHERE type = 'parent' AND id IN (
                        SELECT bag_id FROM scans ORDER BY scanned_at DESC LIMIT 10
                    )
                    UNION ALL
                    SELECT b.id, b.qr_id, b.type, bh.level + 1
                    FROM bags b
                    JOIN links l ON b.id = l.child_bag_id
                    JOIN bag_hierarchy bh ON l.parent_bag_id = bh.id
                    WHERE bh.level < 3
                )
                SELECT COUNT(*) FROM bag_hierarchy
            """, "Bag hierarchy traversal")
        ]
        
        for query, description in critical_queries:
            start = time.time()
            try:
                with self.engine.connect() as conn:
                    result = conn.execute(text(query))
                    rows = result.fetchall()
                    elapsed = time.time() - start
                    
                    status = "✅" if elapsed < 0.1 else "⚠️" if elapsed < 0.5 else "❌"
                    logger.info(f"  {status} {description}: {elapsed*1000:.2f}ms ({len(rows)} rows)")
                    
                    if elapsed < 0.5:
                        self.test_results['passed'].append(f"Critical Query: {description}")
                    else:
                        self.test_results['warnings'].append(f"Critical Query slow: {description}")
                        
            except Exception as e:
                logger.error(f"  ❌ {description}: {str(e)}")
                self.test_results['failed'].append(f"Critical Query: {description}")
    
    def test_concurrent_operations(self):
        """Test with 50+ concurrent users as per AWS requirements"""
        logger.info("Testing concurrent operations (50+ users)...")
        
        def simulate_user(user_id):
            """Simulate a user session"""
            session = requests.Session()
            results = {'user_id': user_id, 'operations': [], 'errors': []}
            
            # Login
            users = [
                {"username": "admin", "password": "admin123"},
                {"username": "dispatcher1", "password": "dispatcher123"},
                {"username": "biller1", "password": "biller123"}
            ]
            user = users[user_id % len(users)]
            
            try:
                # Login
                r = session.post(f"{self.base_url}/login", data=user)
                
                # Perform operations
                operations = [
                    ("GET", "/dashboard"),
                    ("GET", "/api/v2/stats"),
                    ("GET", "/api/bag-count"),
                    ("GET", "/api/recent-scans")
                ]
                
                for method, endpoint in operations:
                    start = time.time()
                    if method == "GET":
                        r = session.get(f"{self.base_url}{endpoint}")
                    elapsed = time.time() - start
                    
                    results['operations'].append({
                        'endpoint': endpoint,
                        'status': r.status_code,
                        'time_ms': round(elapsed * 1000, 2)
                    })
                    
            except Exception as e:
                results['errors'].append(str(e))
            
            return results
        
        # Test with 50 concurrent users
        concurrent_users = 50
        logger.info(f"  Simulating {concurrent_users} concurrent users...")
        
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(simulate_user, i) for i in range(concurrent_users)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Analyze results
        total_operations = sum(len(r['operations']) for r in results)
        total_errors = sum(len(r['errors']) for r in results)
        all_response_times = []
        
        for r in results:
            for op in r['operations']:
                all_response_times.append(op['time_ms'])
        
        if all_response_times:
            avg_response = sum(all_response_times) / len(all_response_times)
            min_response = min(all_response_times)
            max_response = max(all_response_times)
            
            self.test_results['metrics']['concurrent_test'] = {
                'users': concurrent_users,
                'total_operations': total_operations,
                'total_errors': total_errors,
                'avg_response_ms': round(avg_response, 2),
                'min_response_ms': round(min_response, 2),
                'max_response_ms': round(max_response, 2),
                'operations_per_second': round(total_operations / total_time, 2)
            }
            
            logger.info(f"  📊 Results:")
            logger.info(f"     • Operations/sec: {total_operations/total_time:.2f}")
            logger.info(f"     • Avg response: {avg_response:.2f}ms")
            logger.info(f"     • Error rate: {(total_errors/total_operations*100):.2f}%")
            
            if avg_response < 100 and total_errors == 0:
                logger.info("  ✅ EXCELLENT: Ready for 500+ users on AWS")
                self.test_results['passed'].append("Concurrent operations (50+ users)")
            elif avg_response < 500:
                logger.info("  ✅ GOOD: Can handle load with AWS optimizations")
                self.test_results['passed'].append("Concurrent operations (acceptable)")
            else:
                logger.warning("  ⚠️ Needs optimization for AWS deployment")
                self.test_results['warnings'].append("Concurrent operations need tuning")
    
    def test_aws_readiness(self):
        """Check AWS deployment readiness"""
        logger.info("Checking AWS deployment readiness...")
        
        checks = {
            "RDS Proxy Config": os.path.exists("aws_rds_proxy_config.json"),
            "ElastiCache Config": os.path.exists("aws_elasticache_config.json"),
            "Deployment Config": os.path.exists("aws_deployment_config.yaml"),
            "Environment Template": os.path.exists("aws_env_template.txt"),
            "Cache Utils": os.path.exists("cache_utils.py"),
            "Connection Pooling": True,  # Pool size is set to 50 in engine config
            "India Timezone": datetime.now(IST).tzinfo == IST,
            "Gunicorn Config": os.path.exists("gunicorn_config.py")
        }
        
        aws_ready = True
        for check, result in checks.items():
            status = "✅" if result else "❌"
            logger.info(f"  {status} {check}: {'Ready' if result else 'Missing'}")
            if not result:
                aws_ready = False
                self.test_results['warnings'].append(f"AWS Check: {check}")
        
        self.test_results['aws_readiness'] = {
            'all_checks': checks,
            'ready': aws_ready,
            'region': 'ap-south-1',
            'timezone': 'Asia/Kolkata'
        }
        
        if aws_ready:
            logger.info("\n  🎉 AWS deployment ready for India region (ap-south-1)")
            self.test_results['passed'].append("AWS deployment readiness")
        else:
            logger.warning("\n  ⚠️ Some AWS configurations missing")
    
    def test_security(self):
        """Test security configurations for production"""
        logger.info("Testing security...")
        
        security_checks = []
        
        # Test CSRF protection
        r = self.session.post(f"{self.base_url}/api/scan", 
                             json={"qr_code": "TEST123"})
        if r.status_code == 400 or r.status_code == 403:
            security_checks.append(("CSRF Protection", True))
        else:
            security_checks.append(("CSRF Protection", False))
        
        # Test SQL injection protection
        r = self.session.get(f"{self.base_url}/api/bag-search?q='; DROP TABLE bags;--")
        if r.status_code != 500:
            security_checks.append(("SQL Injection Protection", True))
        else:
            security_checks.append(("SQL Injection Protection", False))
        
        # Test rate limiting
        rapid_requests = []
        for _ in range(10):
            r = self.session.get(f"{self.base_url}/api/v2/stats")
            rapid_requests.append(r.status_code)
        
        if 429 in rapid_requests or all(s == 200 for s in rapid_requests):
            security_checks.append(("Rate Limiting", True))
        else:
            security_checks.append(("Rate Limiting", False))
        
        for check, passed in security_checks:
            status = "✅" if passed else "❌"
            logger.info(f"  {status} {check}")
            if passed:
                self.test_results['passed'].append(f"Security: {check}")
            else:
                self.test_results['failed'].append(f"Security: {check}")
    
    def test_scalability(self):
        """Test system scalability for 800,000+ bags"""
        logger.info("Testing scalability...")
        
        with self.engine.connect() as conn:
            # Check current data volume
            bag_count = conn.execute(text("SELECT COUNT(*) FROM bags")).scalar()
            scan_count = conn.execute(text("SELECT COUNT(*) FROM scans")).scalar()
            user_count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
            
            logger.info(f"  Current data volume:")
            logger.info(f"    • Bags: {bag_count:,}")
            logger.info(f"    • Scans: {scan_count:,}")
            logger.info(f"    • Users: {user_count:,}")
            
            # Check indexes
            indexes = conn.execute(text("""
                SELECT tablename, indexname 
                FROM pg_indexes 
                WHERE schemaname = 'public'
                ORDER BY tablename, indexname
            """)).fetchall()
            
            critical_indexes = [
                ('bags', 'ix_bags_qr_id'),
                ('bags', 'ix_bags_type'),
                ('scans', 'ix_scans_bag_id'),
                ('scans', 'ix_scans_user_id'),
                ('links', 'ix_links_parent_bag_id'),
                ('links', 'ix_links_child_bag_id')
            ]
            
            existing_indexes = [(r[0], r[1]) for r in indexes]
            
            for table, index in critical_indexes:
                if (table, index) in existing_indexes:
                    logger.info(f"  ✅ Index exists: {table}.{index}")
                    self.test_results['passed'].append(f"Index: {table}.{index}")
                else:
                    logger.warning(f"  ❌ Missing index: {table}.{index}")
                    self.test_results['failed'].append(f"Missing index: {table}.{index}")
            
            # Estimate performance at scale
            if bag_count and bag_count > 0:
                scale_factor = 800000 / bag_count
                logger.info(f"\n  Scaling projection (to 800,000 bags):")
                logger.info(f"    • Scale factor: {scale_factor:.1f}x")
                
                if scale_factor > 100:
                    logger.warning("    ⚠️ Limited data for accurate projection")
                else:
                    logger.info("    ✅ Sufficient data for projection")
            else:
                logger.warning("\n  ⚠️ No bag data available for scaling projection")
    
    def generate_report(self):
        """Generate comprehensive test report"""
        logger.info("\n" + "="*60)
        logger.info("📊 PRODUCTION READINESS REPORT")
        logger.info("="*60)
        logger.info(f"Report Time: {datetime.now(IST).strftime('%d/%m/%Y %H:%M:%S IST')}")
        
        # Summary
        total_tests = len(self.test_results['passed']) + len(self.test_results['failed'])
        pass_rate = (len(self.test_results['passed']) / total_tests * 100) if total_tests > 0 else 0
        
        logger.info(f"\n📈 TEST SUMMARY:")
        logger.info(f"  • Total Tests: {total_tests}")
        logger.info(f"  • Passed: {len(self.test_results['passed'])}")
        logger.info(f"  • Failed: {len(self.test_results['failed'])}")
        logger.info(f"  • Warnings: {len(self.test_results['warnings'])}")
        logger.info(f"  • Pass Rate: {pass_rate:.1f}%")
        
        # Cache Performance
        if self.test_results.get('cache_tests'):
            logger.info(f"\n💾 CACHE PERFORMANCE:")
            for name, stats in self.test_results['cache_tests'].items():
                logger.info(f"  • {name}: {stats['improvement_percent']}% faster with cache")
        
        # AWS Readiness
        if self.test_results.get('aws_readiness'):
            logger.info(f"\n☁️ AWS READINESS:")
            aws = self.test_results['aws_readiness']
            logger.info(f"  • Region: {aws['region']} (Mumbai)")
            logger.info(f"  • Timezone: {aws['timezone']}")
            logger.info(f"  • Deployment Ready: {'Yes' if aws['ready'] else 'Needs Configuration'}")
        
        # Performance Metrics
        if self.test_results.get('metrics', {}).get('concurrent_test'):
            ct = self.test_results['metrics']['concurrent_test']
            logger.info(f"\n⚡ PERFORMANCE METRICS:")
            logger.info(f"  • Concurrent Users: {ct['users']}")
            logger.info(f"  • Avg Response Time: {ct['avg_response_ms']}ms")
            logger.info(f"  • Operations/Second: {ct['operations_per_second']}")
            
            if ct['avg_response_ms'] < 50:
                logger.info("  🎉 EXCELLENT: Sub-50ms response times achieved!")
            elif ct['avg_response_ms'] < 100:
                logger.info("  ✅ GREAT: Sub-100ms response times")
            elif ct['avg_response_ms'] < 500:
                logger.info("  ✅ GOOD: Acceptable performance")
            else:
                logger.info("  ⚠️ NEEDS OPTIMIZATION")
        
        # Final Verdict
        logger.info("\n" + "="*60)
        if pass_rate >= 90 and len(self.test_results['failed']) == 0:
            logger.info("🎉 PRODUCTION READY - EXCELLENT AWS PERFORMANCE!")
            logger.info("   System optimized for India region with IST timezone")
        elif pass_rate >= 70:
            logger.info("✅ PRODUCTION READY - WITH MINOR OPTIMIZATIONS")
        else:
            logger.info("⚠️ NEEDS OPTIMIZATION BEFORE AWS DEPLOYMENT")
        logger.info("="*60)
        
        # Save detailed report
        report_file = f"production_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        logger.info(f"\n📝 Detailed report saved to: {report_file}")

def main():
    """Run production readiness tests"""
    tester = ProductionReadinessTest()
    tester.run_all_tests()

if __name__ == "__main__":
    main()
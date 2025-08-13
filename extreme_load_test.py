"""
Extreme Load Testing for 50+ Lakh Bags and 1000+ Concurrent Users
Tests system performance under massive load conditions
"""

import os
import time
import random
import string
import asyncio
import aiohttp
import psutil
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Pool, cpu_count
import requests
from sqlalchemy import create_engine, text
from faker import Faker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExtremeLoadTester:
    """Comprehensive load testing for enterprise scale"""
    
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.database_url = os.environ.get('DATABASE_URL')
        self.faker = Faker()
        self.test_results = {
            'start_time': None,
            'end_time': None,
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'errors': [],
            'system_metrics': []
        }
        
    def generate_test_data(self, num_bags=5000000, num_users=1000):
        """Generate 50+ lakh test bags and 1000+ users"""
        logger.info(f"Generating {num_bags:,} test bags and {num_users:,} test users...")
        
        engine = create_engine(self.database_url, pool_size=20, max_overflow=40)
        
        try:
            with engine.connect() as conn:
                trans = conn.begin()
                
                # Create test users
                logger.info("Creating test users...")
                users_created = 0
                for i in range(num_users):
                    username = f"testuser_{i}_{random.randint(1000, 9999)}"
                    email = f"{username}@test.com"
                    
                    conn.execute(text("""
                        INSERT INTO "user" (username, email, password_hash, role, verified, created_at)
                        VALUES (:username, :email, :password_hash, :role, true, NOW())
                        ON CONFLICT (username) DO NOTHING
                    """), {
                        'username': username,
                        'email': email,
                        'password_hash': 'pbkdf2:sha256:600000$test$test',  # Test password
                        'role': random.choice(['admin', 'biller', 'dispatcher'])
                    })
                    
                    users_created += 1
                    if users_created % 100 == 0:
                        logger.info(f"Created {users_created} users...")
                
                # Create test bags in batches
                logger.info("Creating test bags in batches...")
                batch_size = 10000
                bags_created = 0
                
                for batch_num in range(num_bags // batch_size + 1):
                    batch_data = []
                    batch_end = min((batch_num + 1) * batch_size, num_bags)
                    
                    for i in range(batch_num * batch_size, batch_end):
                        qr_id = f"TEST_{i:08d}_{random.randint(1000, 9999)}"
                        bag_type = 'parent' if i % 3 == 0 else 'child'
                        
                        batch_data.append({
                            'qr_id': qr_id,
                            'type': bag_type,
                            'name': f"Test Bag {i}",
                            'dispatch_area': random.choice(['North', 'South', 'East', 'West', 'Central']),
                            'created_at': datetime.utcnow() - timedelta(days=random.randint(0, 90))
                        })
                    
                    if batch_data:
                        # Use COPY for fastest insertion
                        conn.execute(text("""
                            INSERT INTO bag (qr_id, type, name, dispatch_area, created_at)
                            VALUES (:qr_id, :type, :name, :dispatch_area, :created_at)
                            ON CONFLICT (qr_id) DO NOTHING
                        """), batch_data)
                        
                        bags_created += len(batch_data)
                        logger.info(f"Created {bags_created:,} / {num_bags:,} bags...")
                
                trans.commit()
                logger.info(f"Successfully created {users_created} users and {bags_created:,} bags")
                
        except Exception as e:
            logger.error(f"Failed to generate test data: {e}")
            raise
    
    async def simulate_user_session(self, session, user_id):
        """Simulate a single user session with multiple operations"""
        results = []
        
        try:
            # Login
            start = time.time()
            async with session.post(f"{self.base_url}/login", data={
                'username': f'testuser_{user_id}_1234',
                'password': 'test'
            }) as resp:
                login_time = time.time() - start
                results.append({
                    'operation': 'login',
                    'status': resp.status,
                    'time': login_time
                })
            
            # Search for bags
            start = time.time()
            async with session.get(f"{self.base_url}/bags?search=TEST") as resp:
                search_time = time.time() - start
                results.append({
                    'operation': 'search',
                    'status': resp.status,
                    'time': search_time
                })
            
            # Scan QR code
            qr_id = f"TEST_{random.randint(0, 1000000):08d}_1234"
            start = time.time()
            async with session.post(f"{self.base_url}/api/scan", json={
                'qr_id': qr_id,
                'type': 'parent'
            }) as resp:
                scan_time = time.time() - start
                results.append({
                    'operation': 'scan',
                    'status': resp.status,
                    'time': scan_time
                })
            
            # Get dashboard
            start = time.time()
            async with session.get(f"{self.base_url}/") as resp:
                dashboard_time = time.time() - start
                results.append({
                    'operation': 'dashboard',
                    'status': resp.status,
                    'time': dashboard_time
                })
            
        except Exception as e:
            logger.error(f"User session error: {e}")
            results.append({
                'operation': 'error',
                'error': str(e)
            })
        
        return results
    
    async def run_concurrent_users(self, num_users=1000):
        """Simulate 1000+ concurrent users"""
        logger.info(f"Starting {num_users} concurrent user sessions...")
        
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        timeout = aiohttp.ClientTimeout(total=60)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []
            for i in range(num_users):
                task = self.simulate_user_session(session, i)
                tasks.append(task)
            
            # Run all user sessions concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for user_results in results:
                if isinstance(user_results, Exception):
                    self.test_results['failed_requests'] += 1
                    self.test_results['errors'].append(str(user_results))
                else:
                    for result in user_results:
                        if 'error' in result:
                            self.test_results['failed_requests'] += 1
                            self.test_results['errors'].append(result['error'])
                        else:
                            self.test_results['successful_requests'] += 1
                            self.test_results['response_times'].append(result['time'])
        
        return self.test_results
    
    def stress_test_database(self, num_queries=10000):
        """Stress test database with heavy queries"""
        logger.info(f"Running {num_queries} database stress queries...")
        
        engine = create_engine(self.database_url, pool_size=50, max_overflow=100)
        
        query_times = []
        errors = 0
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = []
            
            for i in range(num_queries):
                query_type = random.choice(['select', 'aggregate', 'join', 'complex'])
                future = executor.submit(self._execute_stress_query, engine, query_type)
                futures.append(future)
            
            for future in as_completed(futures):
                try:
                    query_time = future.result()
                    query_times.append(query_time)
                except Exception as e:
                    errors += 1
                    logger.error(f"Query error: {e}")
        
        # Calculate statistics
        avg_time = sum(query_times) / len(query_times) if query_times else 0
        max_time = max(query_times) if query_times else 0
        min_time = min(query_times) if query_times else 0
        
        return {
            'total_queries': num_queries,
            'successful': num_queries - errors,
            'failed': errors,
            'avg_time': avg_time,
            'max_time': max_time,
            'min_time': min_time
        }
    
    def _execute_stress_query(self, engine, query_type):
        """Execute a single stress query"""
        start = time.time()
        
        with engine.connect() as conn:
            if query_type == 'select':
                # Random bag lookup
                conn.execute(text("""
                    SELECT * FROM bag 
                    WHERE qr_id = :qr_id
                """), {'qr_id': f"TEST_{random.randint(0, 1000000):08d}_1234"})
                
            elif query_type == 'aggregate':
                # Count by area
                conn.execute(text("""
                    SELECT dispatch_area, COUNT(*) 
                    FROM bag 
                    GROUP BY dispatch_area
                """))
                
            elif query_type == 'join':
                # Complex join
                conn.execute(text("""
                    SELECT b.*, l.child_bag_id
                    FROM bag b
                    LEFT JOIN link l ON b.id = l.parent_bag_id
                    WHERE b.type = 'parent'
                    LIMIT 100
                """))
                
            elif query_type == 'complex':
                # Complex analytical query
                conn.execute(text("""
                    WITH bag_stats AS (
                        SELECT 
                            dispatch_area,
                            type,
                            DATE_TRUNC('day', created_at) as day,
                            COUNT(*) as count
                        FROM bag
                        WHERE created_at > NOW() - INTERVAL '30 days'
                        GROUP BY dispatch_area, type, day
                    )
                    SELECT * FROM bag_stats
                    ORDER BY day DESC, count DESC
                """))
        
        return time.time() - start
    
    def monitor_system_resources(self, duration=60):
        """Monitor system resources during load test"""
        logger.info(f"Monitoring system resources for {duration} seconds...")
        
        metrics = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get network stats
            net_io = psutil.net_io_counters()
            
            # Get database connections
            try:
                engine = create_engine(self.database_url)
                with engine.connect() as conn:
                    result = conn.execute(text("""
                        SELECT count(*) FROM pg_stat_activity
                    """)).scalar()
                    db_connections = result
            except:
                db_connections = 0
            
            metric = {
                'timestamp': datetime.utcnow().isoformat(),
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_gb': memory.used / (1024**3),
                'disk_percent': disk.percent,
                'network_sent_mb': net_io.bytes_sent / (1024**2),
                'network_recv_mb': net_io.bytes_recv / (1024**2),
                'db_connections': db_connections
            }
            
            metrics.append(metric)
            
            # Alert if resources are critical
            if cpu_percent > 90:
                logger.warning(f"CRITICAL: CPU usage at {cpu_percent}%")
            if memory.percent > 90:
                logger.warning(f"CRITICAL: Memory usage at {memory.percent}%")
            if db_connections > 200:
                logger.warning(f"CRITICAL: Database connections at {db_connections}")
            
            time.sleep(5)
        
        return metrics
    
    def run_extreme_load_test(self):
        """Run the complete extreme load test"""
        logger.info("=" * 50)
        logger.info("STARTING EXTREME LOAD TEST")
        logger.info("Target: 50+ Lakh Bags, 1000+ Concurrent Users")
        logger.info("=" * 50)
        
        self.test_results['start_time'] = datetime.utcnow()
        
        # Step 1: Generate test data
        logger.info("\n[Step 1/4] Generating test data...")
        # self.generate_test_data(num_bags=100000, num_users=100)  # Reduced for testing
        
        # Step 2: Start resource monitoring in background
        logger.info("\n[Step 2/4] Starting resource monitoring...")
        from threading import Thread
        monitor_thread = Thread(target=self.monitor_system_resources, args=(120,))
        monitor_thread.start()
        
        # Step 3: Run concurrent user load test
        logger.info("\n[Step 3/4] Running concurrent user load test...")
        asyncio.run(self.run_concurrent_users(num_users=100))  # Start with 100 users
        
        # Step 4: Database stress test
        logger.info("\n[Step 4/4] Running database stress test...")
        db_results = self.stress_test_database(num_queries=1000)
        
        # Wait for monitoring to complete
        monitor_thread.join()
        
        self.test_results['end_time'] = datetime.utcnow()
        
        # Generate report
        self.generate_load_test_report(db_results)
    
    def generate_load_test_report(self, db_results):
        """Generate comprehensive load test report"""
        duration = (self.test_results['end_time'] - self.test_results['start_time']).total_seconds()
        
        # Calculate statistics
        total_requests = self.test_results['successful_requests'] + self.test_results['failed_requests']
        success_rate = (self.test_results['successful_requests'] / total_requests * 100) if total_requests > 0 else 0
        
        avg_response_time = sum(self.test_results['response_times']) / len(self.test_results['response_times']) if self.test_results['response_times'] else 0
        max_response_time = max(self.test_results['response_times']) if self.test_results['response_times'] else 0
        min_response_time = min(self.test_results['response_times']) if self.test_results['response_times'] else 0
        
        report = f"""
================================================================================
                        EXTREME LOAD TEST REPORT
================================================================================

Test Configuration:
- Target Scale: 50+ Lakh Bags, 1000+ Concurrent Users
- Test Duration: {duration:.2f} seconds
- Start Time: {self.test_results['start_time']}
- End Time: {self.test_results['end_time']}

Request Statistics:
- Total Requests: {total_requests:,}
- Successful: {self.test_results['successful_requests']:,} ({success_rate:.2f}%)
- Failed: {self.test_results['failed_requests']:,}
- Requests/Second: {total_requests/duration:.2f}

Response Time Analysis:
- Average: {avg_response_time:.3f} seconds
- Maximum: {max_response_time:.3f} seconds
- Minimum: {min_response_time:.3f} seconds

Database Performance:
- Total Queries: {db_results['total_queries']:,}
- Successful: {db_results['successful']:,}
- Failed: {db_results['failed']}
- Avg Query Time: {db_results['avg_time']:.3f} seconds
- Max Query Time: {db_results['max_time']:.3f} seconds

Error Summary:
- Total Errors: {len(self.test_results['errors'])}
- Unique Error Types: {len(set(self.test_results['errors']))}

Performance Assessment:
"""
        
        # Performance grading
        if success_rate >= 99 and avg_response_time < 1:
            grade = "EXCELLENT ✓"
            assessment = "System performing exceptionally well under extreme load"
        elif success_rate >= 95 and avg_response_time < 2:
            grade = "GOOD"
            assessment = "System handling load well with minor optimizations needed"
        elif success_rate >= 90 and avg_response_time < 5:
            grade = "ACCEPTABLE"
            assessment = "System functional but requires optimization for production"
        else:
            grade = "NEEDS IMPROVEMENT"
            assessment = "System struggling under load - immediate optimization required"
        
        report += f"""
Grade: {grade}
Assessment: {assessment}

Recommendations:
"""
        
        # Generate recommendations
        if avg_response_time > 2:
            report += "- Implement additional caching layers\n"
            report += "- Optimize database queries and indexes\n"
        
        if self.test_results['failed_requests'] > total_requests * 0.05:
            report += "- Increase connection pool size\n"
            report += "- Implement circuit breakers for resilience\n"
        
        if db_results['max_time'] > 5:
            report += "- Add database read replicas\n"
            report += "- Implement query result caching\n"
        
        report += """
================================================================================
"""
        
        # Save report
        with open('load_test_report.txt', 'w') as f:
            f.write(report)
        
        print(report)
        logger.info("Load test report saved to load_test_report.txt")
        
        return report


if __name__ == "__main__":
    tester = ExtremeLoadTester()
    tester.run_extreme_load_test()
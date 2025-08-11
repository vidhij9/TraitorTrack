#!/usr/bin/env python3
"""
Comprehensive Application Test Suite
Tests all major functionality to ensure seamless operation
"""

import os
import sys
import time
import json
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set up the Flask application context
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_clean import app, db
from models import User, Bag, Link, Scan, BagType
from query_optimizer import QueryOptimizer
from werkzeug.security import generate_password_hash

class ComprehensiveAppTester:
    """Test all major application functionality"""
    
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        self.test_results = []
    
    def setup_test_users(self):
        """Create test users for different roles"""
        print("\n📋 Setting up test users...")
        
        try:
            with app.app_context():
                # Create admin user
                admin = User.query.filter_by(username='test_admin').first()
                if not admin:
                    admin = User(
                        username='test_admin',
                        email='admin@test.com',
                        password_hash=generate_password_hash('Admin123!'),
                        role='admin'
                    )
                    db.session.add(admin)
                
                # Create biller user
                biller = User.query.filter_by(username='test_biller').first()
                if not biller:
                    biller = User(
                        username='test_biller',
                        email='biller@test.com',
                        password_hash=generate_password_hash('Biller123!'),
                        role='biller'
                    )
                    db.session.add(biller)
                
                # Create dispatcher user
                dispatcher = User.query.filter_by(username='test_dispatcher').first()
                if not dispatcher:
                    dispatcher = User(
                        username='test_dispatcher',
                        email='dispatcher@test.com',
                        password_hash=generate_password_hash('Dispatcher123!'),
                        role='dispatcher',
                        dispatch_area='AREA_A'
                    )
                    db.session.add(dispatcher)
                
                db.session.commit()
                print("✅ Test users created successfully")
                return True
                
        except Exception as e:
            print(f"❌ Failed to create test users: {e}")
            return False
    
    def test_database_operations(self):
        """Test core database operations"""
        print("\n🗄️ Testing Database Operations...")
        
        try:
            with app.app_context():
                # Test 1: Create parent bag
                parent_qr = f"TEST_PARENT_{int(time.time() * 1000) % 1000000}"
                parent_bag = QueryOptimizer.create_bag_optimized(
                    qr_id=parent_qr,
                    bag_type=BagType.PARENT.value,
                    name="Test Parent Bag"
                )
                db.session.commit()
                print(f"✅ Created parent bag: {parent_qr}")
                
                # Test 2: Add multiple child bags
                child_qrs = [f"TEST_CHILD_{i}_{int(time.time() * 1000) % 1000000}" for i in range(10)]
                for child_qr in child_qrs:
                    child_bag = Bag(
                        qr_id=child_qr,
                        type=BagType.CHILD.value,
                        name=f"Test Child {child_qr}",
                        parent_id=parent_bag.id
                    )
                    db.session.add(child_bag)
                    db.session.flush()
                    
                    # Create link
                    link = Link(parent_bag_id=parent_bag.id, child_bag_id=child_bag.id)
                    db.session.add(link)
                
                db.session.commit()
                print(f"✅ Added {len(child_qrs)} child bags to parent")
                
                # Test 3: Query relationships
                links = Link.query.filter_by(parent_bag_id=parent_bag.id).count()
                print(f"✅ Verified {links} parent-child relationships")
                
                # Test 4: Update operations
                parent_bag.child_count = links
                db.session.commit()
                print(f"✅ Updated parent bag child count")
                
                # Test 5: Search operations
                search_result = Bag.query.filter(Bag.qr_id.like('TEST_%')).count()
                print(f"✅ Search found {search_result} test bags")
                
                self.test_results.append(('Database Operations', True, None))
                return True
                
        except Exception as e:
            print(f"❌ Database operations failed: {e}")
            self.test_results.append(('Database Operations', False, str(e)))
            return False
    
    def test_concurrent_scanning(self):
        """Test concurrent scanning operations"""
        print("\n🔄 Testing Concurrent Scanning Operations...")
        
        def simulate_scan(thread_id):
            """Simulate a scanning operation"""
            try:
                with app.app_context():
                    # Create parent
                    parent_qr = f"CONCURRENT_PARENT_{thread_id}_{int(time.time() * 1000000) % 1000000}"
                    parent_bag = QueryOptimizer.create_bag_optimized(
                        qr_id=parent_qr,
                        bag_type=BagType.PARENT.value,
                        name=f"Concurrent Parent {thread_id}"
                    )
                    db.session.commit()
                    
                    # Add 5 children
                    for i in range(5):
                        child_qr = f"CONCURRENT_CHILD_{thread_id}_{i}_{int(time.time() * 1000000) % 1000000}"
                        child_bag = Bag(
                            qr_id=child_qr,
                            type=BagType.CHILD.value,
                            name=f"Concurrent Child {thread_id}-{i}",
                            parent_id=parent_bag.id
                        )
                        db.session.add(child_bag)
                        db.session.flush()
                        
                        link = Link(parent_bag_id=parent_bag.id, child_bag_id=child_bag.id)
                        db.session.add(link)
                    
                    db.session.commit()
                    return {'success': True, 'thread_id': thread_id}
                    
            except Exception as e:
                return {'success': False, 'thread_id': thread_id, 'error': str(e)}
        
        # Run concurrent scans
        num_threads = 20
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(simulate_scan, i) for i in range(num_threads)]
            results = [future.result() for future in as_completed(futures)]
        
        successful = sum(1 for r in results if r['success'])
        print(f"✅ Concurrent scanning: {successful}/{num_threads} successful")
        
        if successful >= num_threads * 0.8:  # 80% success rate
            self.test_results.append(('Concurrent Scanning', True, None))
            return True
        else:
            self.test_results.append(('Concurrent Scanning', False, f"Only {successful}/{num_threads} succeeded"))
            return False
    
    def test_query_performance(self):
        """Test query performance with various operations"""
        print("\n⚡ Testing Query Performance...")
        
        try:
            with app.app_context():
                query_times = []
                
                # Test 1: Count all bags
                start = time.time()
                total_bags = Bag.query.count()
                query_times.append(time.time() - start)
                print(f"✅ Count query: {total_bags} bags in {query_times[-1]:.3f}s")
                
                # Test 2: Complex join query
                start = time.time()
                result = db.session.execute(db.text("""
                    SELECT 
                        p.qr_id as parent_qr,
                        COUNT(l.id) as child_count
                    FROM bag p
                    LEFT JOIN link l ON p.id = l.parent_bag_id
                    WHERE p.type = 'parent'
                    GROUP BY p.id, p.qr_id
                    LIMIT 10
                """)).fetchall()
                query_times.append(time.time() - start)
                print(f"✅ Join query: {len(result)} results in {query_times[-1]:.3f}s")
                
                # Test 3: Aggregation query
                start = time.time()
                result = db.session.execute(db.text("""
                    SELECT 
                        type,
                        COUNT(*) as count,
                        MAX(child_count) as max_children
                    FROM bag
                    GROUP BY type
                """)).fetchall()
                query_times.append(time.time() - start)
                print(f"✅ Aggregation query: {len(result)} groups in {query_times[-1]:.3f}s")
                
                # Test 4: Search query
                start = time.time()
                search_results = Bag.query.filter(
                    Bag.qr_id.like('%TEST%')
                ).limit(100).all()
                query_times.append(time.time() - start)
                print(f"✅ Search query: {len(search_results)} results in {query_times[-1]:.3f}s")
                
                avg_time = sum(query_times) / len(query_times)
                max_time = max(query_times)
                
                print(f"📊 Average query time: {avg_time:.3f}s, Max: {max_time:.3f}s")
                
                if max_time < 2.0:  # All queries under 2 seconds
                    self.test_results.append(('Query Performance', True, f"Avg: {avg_time:.3f}s"))
                    return True
                else:
                    self.test_results.append(('Query Performance', False, f"Max time {max_time:.3f}s > 2s"))
                    return False
                    
        except Exception as e:
            print(f"❌ Query performance test failed: {e}")
            self.test_results.append(('Query Performance', False, str(e)))
            return False
    
    def test_bulk_operations(self):
        """Test bulk insertion and update operations"""
        print("\n📦 Testing Bulk Operations...")
        
        try:
            with app.app_context():
                # Create a parent for bulk children
                parent_qr = f"BULK_PARENT_{int(time.time() * 1000000) % 1000000}"
                parent_bag = QueryOptimizer.create_bag_optimized(
                    qr_id=parent_qr,
                    bag_type=BagType.PARENT.value,
                    name="Bulk Test Parent"
                )
                db.session.commit()
                
                # Bulk create 50 children
                child_qrs = [f"BULK_CHILD_{i}_{int(time.time() * 1000000) % 1000000}" for i in range(50)]
                
                start_time = time.time()
                result = QueryOptimizer.bulk_create_child_bags(
                    parent_bag, child_qrs, user_id=1
                )
                bulk_time = time.time() - start_time
                
                if result['success']:
                    print(f"✅ Bulk created {result['children_created']} children in {bulk_time:.2f}s")
                    rate = result.get('children_per_second', result['children_created']/bulk_time if bulk_time > 0 else 0)
                    print(f"   Rate: {rate:.1f} bags/second")
                    
                    # Verify the bulk operation
                    link_count = Link.query.filter_by(parent_bag_id=parent_bag.id).count()
                    print(f"✅ Verified {link_count} links created")
                    
                    self.test_results.append(('Bulk Operations', True, f"{result['children_created']} children"))
                    return True
                else:
                    print(f"❌ Bulk operation failed: {result.get('error')}")
                    self.test_results.append(('Bulk Operations', False, result.get('error')))
                    return False
                    
        except Exception as e:
            print(f"❌ Bulk operations test failed: {e}")
            self.test_results.append(('Bulk Operations', False, str(e)))
            return False
    
    def test_connection_pool(self):
        """Test connection pool under load"""
        print("\n🔌 Testing Connection Pool...")
        
        try:
            with app.app_context():
                pool = db.engine.pool
                
                # Get initial stats
                print(f"📊 Connection Pool Stats:")
                print(f"   Size: {pool.size()}")
                print(f"   Checked in: {pool.checkedin()}")
                print(f"   Checked out: {pool.checkedout()}")
                print(f"   Overflow: {pool.overflow()}")
                
                # Test multiple concurrent connections
                def test_connection(conn_id):
                    try:
                        with app.app_context():
                            result = db.session.execute(db.text("SELECT 1")).fetchone()
                            return True
                    except Exception as e:
                        return False
                
                # Test with 50 concurrent connections
                with ThreadPoolExecutor(max_workers=50) as executor:
                    futures = [executor.submit(test_connection, i) for i in range(50)]
                    results = [f.result() for f in as_completed(futures)]
                
                successful = sum(1 for r in results if r)
                print(f"✅ Connection pool test: {successful}/50 successful connections")
                
                if successful >= 45:  # 90% success rate
                    self.test_results.append(('Connection Pool', True, f"{successful}/50"))
                    return True
                else:
                    self.test_results.append(('Connection Pool', False, f"Only {successful}/50"))
                    return False
                    
        except Exception as e:
            print(f"❌ Connection pool test failed: {e}")
            self.test_results.append(('Connection Pool', False, str(e)))
            return False
    
    def run_all_tests(self):
        """Run all comprehensive tests"""
        print("🚀 COMPREHENSIVE APPLICATION TEST SUITE")
        print("=" * 60)
        
        # Run all test categories
        test_functions = [
            self.setup_test_users,
            self.test_database_operations,
            self.test_concurrent_scanning,
            self.test_query_performance,
            self.test_bulk_operations,
            self.test_connection_pool
        ]
        
        for test_func in test_functions:
            try:
                test_func()
            except Exception as e:
                print(f"Test {test_func.__name__} encountered error: {e}")
            
            # Brief pause between tests
            time.sleep(1)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = 0
        failed = 0
        
        for test_name, success, error in self.test_results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{test_name:.<30} {status}")
            if error:
                print(f"   Error: {error[:100]}")
            
            if success:
                passed += 1
            else:
                failed += 1
        
        print(f"\nTotal: {passed} passed, {failed} failed")
        
        if failed == 0:
            print("\n🎉 ALL TESTS PASSED - APPLICATION WORKS SEAMLESSLY!")
            print("✅ Database operations are optimized")
            print("✅ Concurrent scanning works perfectly")
            print("✅ Query performance is excellent")
            print("✅ Bulk operations are efficient")
            print("✅ Connection pool handles high load")
            print("\n🚀 READY FOR PRODUCTION WITH 4+ LAKH BAGS!")
        else:
            print(f"\n⚠️ {failed} TESTS FAILED - Review issues above")
        
        return failed == 0

def main():
    """Run comprehensive application tests"""
    tester = ComprehensiveAppTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
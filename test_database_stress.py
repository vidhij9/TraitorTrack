#!/usr/bin/env python3
"""
Database stress testing for scan management performance
Tests database performance with high concurrent load
"""

import os
import sys
import time
import threading
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set up the Flask application context
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_clean import app, db
from models import User, Bag, Link, Scan, BagType
from query_optimizer import QueryOptimizer
import statistics

class DatabaseStressTester:
    def __init__(self):
        self.results = {
            'insert_times': [],
            'query_times': [],
            'link_times': [],
            'errors': [],
            'successful_operations': 0,
            'failed_operations': 0
        }
        self.lock = threading.Lock()
    
    def record_result(self, operation, duration, success=True, error=None):
        """Thread-safe result recording"""
        with self.lock:
            if operation == 'insert':
                self.results['insert_times'].append(duration)
            elif operation == 'query':
                self.results['query_times'].append(duration)
            elif operation == 'link':
                self.results['link_times'].append(duration)
            
            if success:
                self.results['successful_operations'] += 1
            else:
                self.results['failed_operations'] += 1
                if error:
                    self.results['errors'].append(f"{operation}: {error}")
    
    def setup_test_user(self):
        """Create a test user for operations"""
        try:
            with app.app_context():
                # Check if test user exists
                test_user = User.query.filter_by(username='stress_test_user').first()
                if not test_user:
                    test_user = User(
                        username='stress_test_user',
                        email='stress@test.com',
                        password_hash='test_hash',
                        role='dispatcher'
                    )
                    db.session.add(test_user)
                    db.session.commit()
                return test_user.id
        except Exception as e:
            print(f"Failed to setup test user: {e}")
            return None
    
    def create_parent_bag_batch(self, batch_id, batch_size=10):
        """Create a batch of parent bags"""
        try:
            with app.app_context():
                start_time = time.time()
                
                parent_bags = []
                for i in range(batch_size):
                    parent_qr = f"STRESS_PARENT_{batch_id}_{i:04d}"
                    
                    # Check if bag already exists
                    existing = Bag.query.filter_by(qr_id=parent_qr).first()
                    if not existing:
                        parent_bag = Bag(
                            qr_id=parent_qr,
                            type=BagType.PARENT.value,
                            name=f"Stress Test Parent {batch_id}-{i}",
                            child_count=0
                        )
                        parent_bags.append(parent_bag)
                
                if parent_bags:
                    db.session.add_all(parent_bags)
                    db.session.commit()
                
                duration = time.time() - start_time
                self.record_result('insert', duration, True)
                
                return len(parent_bags)
        except Exception as e:
            self.record_result('insert', 0, False, str(e))
            return 0
    
    def create_child_bags_for_parent(self, parent_qr, child_count=50):
        """Create multiple child bags for a parent (stress test scenario)"""
        try:
            with app.app_context():
                start_time = time.time()
                
                # Get parent bag
                parent_bag = Bag.query.filter_by(qr_id=parent_qr, type=BagType.PARENT.value).first()
                if not parent_bag:
                    raise Exception(f"Parent bag {parent_qr} not found")
                
                child_bags = []
                links = []
                
                for i in range(child_count):
                    child_qr = f"{parent_qr}_CHILD_{i:03d}"
                    
                    # Check if child already exists
                    existing_child = Bag.query.filter_by(qr_id=child_qr).first()
                    if not existing_child:
                        child_bag = Bag(
                            qr_id=child_qr,
                            type=BagType.CHILD.value,
                            name=f"Child {i} of {parent_qr}",
                            parent_id=parent_bag.id
                        )
                        child_bags.append(child_bag)
                    else:
                        child_bag = existing_child
                    
                    # Check if link already exists
                    existing_link = Link.query.filter_by(
                        parent_bag_id=parent_bag.id,
                        child_bag_id=child_bag.id if existing_child else None
                    ).first()
                    
                    if not existing_link:
                        # We'll create the link after inserting the child bag
                        if not existing_child:
                            links.append((parent_bag.id, len(child_bags) - 1))  # Store index for later
                        else:
                            link = Link(parent_bag_id=parent_bag.id, child_bag_id=child_bag.id)
                            db.session.add(link)
                
                # Bulk insert child bags
                if child_bags:
                    db.session.add_all(child_bags)
                    db.session.flush()  # Get IDs for links
                
                # Create links for new child bags
                for parent_id, child_index in links:
                    link = Link(parent_bag_id=parent_id, child_bag_id=child_bags[child_index].id)
                    db.session.add(link)
                
                # Update parent bag child count
                total_children = Link.query.filter_by(parent_bag_id=parent_bag.id).count() + len(links)
                parent_bag.child_count = total_children
                
                db.session.commit()
                
                duration = time.time() - start_time
                self.record_result('link', duration, True)
                
                return len(child_bags)
        except Exception as e:
            db.session.rollback()
            self.record_result('link', 0, False, str(e))
            return 0
    
    def query_performance_test(self, iterations=100):
        """Test various query performance scenarios"""
        try:
            with app.app_context():
                query_times = []
                
                for i in range(iterations):
                    start_time = time.time()
                    
                    # Random query type
                    query_type = random.choice(['parent_lookup', 'child_lookup', 'link_count', 'recent_scans'])
                    
                    if query_type == 'parent_lookup':
                        # Query random parent bag
                        parent_bags = Bag.query.filter_by(type=BagType.PARENT.value).limit(10).all()
                        if parent_bags:
                            random_parent = random.choice(parent_bags)
                            children = QueryOptimizer.get_child_bags_for_parent(random_parent.id)
                    
                    elif query_type == 'child_lookup':
                        # Query random child bag
                        child_bags = Bag.query.filter_by(type=BagType.CHILD.value).limit(10).all()
                        if child_bags:
                            random_child = random.choice(child_bags)
                            parent_link = Link.query.filter_by(child_bag_id=random_child.id).first()
                    
                    elif query_type == 'link_count':
                        # Count links for random parent
                        parent_bags = Bag.query.filter_by(type=BagType.PARENT.value).limit(5).all()
                        if parent_bags:
                            random_parent = random.choice(parent_bags)
                            count = Link.query.filter_by(parent_bag_id=random_parent.id).count()
                    
                    elif query_type == 'recent_scans':
                        # Query recent scans
                        recent_scans = QueryOptimizer.get_recent_scans(limit=20)
                    
                    duration = time.time() - start_time
                    query_times.append(duration)
                    self.record_result('query', duration, True)
                
                return query_times
        except Exception as e:
            self.record_result('query', 0, False, str(e))
            return []
    
    def concurrent_operations_test(self, num_threads=20, operations_per_thread=10):
        """Test concurrent database operations"""
        print(f"Testing {num_threads} concurrent threads with {operations_per_thread} operations each...")
        
        def worker_thread(thread_id):
            """Worker thread for concurrent operations"""
            thread_results = {'success': 0, 'failure': 0}
            
            try:
                with app.app_context():
                    for op in range(operations_per_thread):
                        try:
                            # Create parent bag
                            parent_qr = f"CONCURRENT_PARENT_{thread_id}_{op}"
                            parent_bag = Bag(
                                qr_id=parent_qr,
                                type=BagType.PARENT.value,
                                name=f"Concurrent Parent {thread_id}-{op}",
                                child_count=0
                            )
                            db.session.add(parent_bag)
                            db.session.flush()
                            
                            # Add 5 child bags
                            for child_num in range(5):
                                child_qr = f"CONCURRENT_CHILD_{thread_id}_{op}_{child_num}"
                                child_bag = Bag(
                                    qr_id=child_qr,
                                    type=BagType.CHILD.value,
                                    name=f"Concurrent Child {thread_id}-{op}-{child_num}",
                                    parent_id=parent_bag.id
                                )
                                db.session.add(child_bag)
                                db.session.flush()
                                
                                # Create link
                                link = Link(parent_bag_id=parent_bag.id, child_bag_id=child_bag.id)
                                db.session.add(link)
                            
                            # Update parent child count
                            parent_bag.child_count = 5
                            db.session.commit()
                            
                            thread_results['success'] += 1
                        except Exception as e:
                            db.session.rollback()
                            thread_results['failure'] += 1
                            self.record_result('concurrent', 0, False, f"Thread {thread_id}: {str(e)}")
            except Exception as e:
                thread_results['failure'] += operations_per_thread
                self.record_result('concurrent', 0, False, f"Thread {thread_id} fatal: {str(e)}")
            
            return thread_results
        
        # Execute concurrent threads
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_thread, i) for i in range(num_threads)]
            
            total_success = 0
            total_failure = 0
            
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=30)
                    total_success += result['success']
                    total_failure += result['failure']
                except Exception as e:
                    print(f"Thread execution failed: {e}")
                    total_failure += operations_per_thread
        
        total_time = time.time() - start_time
        total_operations = num_threads * operations_per_thread
        
        print(f"Concurrent test completed in {total_time:.2f}s")
        print(f"Total operations: {total_operations}")
        print(f"Successful: {total_success}")
        print(f"Failed: {total_failure}")
        print(f"Success rate: {(total_success/total_operations)*100:.1f}%")
        print(f"Operations per second: {total_operations/total_time:.1f}")
        
        return total_success >= (total_operations * 0.8)  # 80% success rate
    
    def test_50_child_bags_scenario(self):
        """Test the specific scenario: adding 50 child bags to a parent"""
        print("\n=== Testing 50 Child Bags per Parent Scenario ===")
        
        try:
            with app.app_context():
                # Create a test parent bag
                test_parent_qr = f"TEST_50_PARENT_{int(time.time())}"
                start_time = time.time()
                
                parent_bag = Bag(
                    qr_id=test_parent_qr,
                    type=BagType.PARENT.value,
                    name="Test Parent for 50 Children",
                    child_count=0
                )
                db.session.add(parent_bag)
                db.session.commit()
                
                parent_creation_time = time.time() - start_time
                print(f"✅ Parent bag created in {parent_creation_time:.3f}s")
                
                # Add 50 child bags
                children_added = self.create_child_bags_for_parent(test_parent_qr, 50)
                
                # Verify the results
                final_parent = Bag.query.filter_by(qr_id=test_parent_qr).first()
                link_count = Link.query.filter_by(parent_bag_id=final_parent.id).count()
                child_count = Bag.query.filter_by(type=BagType.CHILD.value).filter(
                    Bag.qr_id.like(f"{test_parent_qr}_CHILD_%")
                ).count()
                
                print(f"✅ Created {children_added} child bags")
                print(f"✅ Database shows {link_count} links")
                print(f"✅ Database shows {child_count} child bags")
                
                # Performance verification
                if self.results['link_times']:
                    avg_link_time = statistics.mean(self.results['link_times'])
                    print(f"✅ Average linking time: {avg_link_time:.3f}s")
                    
                    if avg_link_time < 2.0:
                        print("⚡ EXCELLENT: Fast bulk child bag creation")
                    elif avg_link_time < 5.0:
                        print("✅ GOOD: Acceptable bulk child bag creation")
                    else:
                        print("⚠️  SLOW: Consider optimization for bulk operations")
                
                return link_count == 50 and child_count == 50
        except Exception as e:
            print(f"❌ 50-child test failed: {e}")
            return False
    
    def display_comprehensive_results(self):
        """Display comprehensive test results"""
        print("\n📊 DATABASE STRESS TEST RESULTS")
        print("=" * 50)
        
        print(f"Total successful operations: {self.results['successful_operations']}")
        print(f"Total failed operations: {self.results['failed_operations']}")
        
        if self.results['successful_operations'] > 0:
            success_rate = (self.results['successful_operations'] / 
                          (self.results['successful_operations'] + self.results['failed_operations'])) * 100
            print(f"Overall success rate: {success_rate:.1f}%")
        
        # Insert performance
        if self.results['insert_times']:
            avg_insert = statistics.mean(self.results['insert_times'])
            max_insert = max(self.results['insert_times'])
            print(f"\nInsert Performance:")
            print(f"  Average time: {avg_insert:.3f}s")
            print(f"  Max time: {max_insert:.3f}s")
        
        # Query performance
        if self.results['query_times']:
            avg_query = statistics.mean(self.results['query_times'])
            max_query = max(self.results['query_times'])
            print(f"\nQuery Performance:")
            print(f"  Average time: {avg_query:.3f}s")
            print(f"  Max time: {max_query:.3f}s")
        
        # Link performance
        if self.results['link_times']:
            avg_link = statistics.mean(self.results['link_times'])
            max_link = max(self.results['link_times'])
            print(f"\nLinking Performance (Bulk 50 children):")
            print(f"  Average time: {avg_link:.3f}s")
            print(f"  Max time: {max_link:.3f}s")
        
        # Error summary
        if self.results['errors']:
            print(f"\nErrors ({len(self.results['errors'])}):")
            for error in self.results['errors'][:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(self.results['errors']) > 10:
                print(f"  ... and {len(self.results['errors']) - 10} more errors")

def main():
    """Run comprehensive database stress tests"""
    print("🚀 Starting Database Stress Tests for Scan Management")
    print("=" * 60)
    
    tester = DatabaseStressTester()
    
    # Setup test environment
    user_id = tester.setup_test_user()
    if not user_id:
        print("❌ Failed to setup test environment")
        return False
    
    # Test 1: 50 child bags scenario
    test1_success = tester.test_50_child_bags_scenario()
    
    # Test 2: Query performance
    print("\n=== Testing Query Performance ===")
    query_times = tester.query_performance_test(50)
    if query_times:
        avg_query_time = statistics.mean(query_times)
        print(f"✅ Completed 50 queries, average time: {avg_query_time:.3f}s")
    
    # Test 3: Concurrent operations
    print("\n=== Testing Concurrent Database Operations ===")
    test3_success = tester.concurrent_operations_test(10, 5)  # 10 threads, 5 operations each
    
    # Display comprehensive results
    tester.display_comprehensive_results()
    
    # Final assessment
    print("\n" + "=" * 60)
    print("🏁 DATABASE STRESS TEST SUMMARY")
    print("=" * 60)
    
    if test1_success:
        print("✅ 50 Child Bags Test: PASSED")
    else:
        print("❌ 50 Child Bags Test: FAILED")
    
    if test3_success:
        print("✅ Concurrent Operations Test: PASSED")
    else:
        print("❌ Concurrent Operations Test: FAILED")
    
    overall_success = test1_success and test3_success
    
    if overall_success:
        print("\n🎉 DATABASE READY for high concurrent load!")
    else:
        print("\n⚠️  Database may need optimization for concurrent load")
    
    return overall_success

if __name__ == "__main__":
    main()
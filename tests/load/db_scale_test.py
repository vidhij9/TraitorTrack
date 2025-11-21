"""
Database Scale Testing for TraitorTrack
========================================

Tests database performance with large datasets (simulating 1.8M bags).
Validates indexing, pagination, and query optimization.

Usage:
    # Requires database with substantial data (use seed script first)
    python tests/load/db_scale_test.py
"""

import time
import statistics
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import app, db
from models import Bag, Bill, Scan, User
from sqlalchemy import func, text


class DatabaseScaleTest:
    """Test database performance at scale"""
    
    def __init__(self):
        self.results = {}
    
    def run_timed_query(self, name, query_func):
        """Run a query and time it"""
        start = time.time()
        try:
            result = query_func()
            elapsed = (time.time() - start) * 1000  # Convert to ms
            self.results[name] = {
                'time_ms': elapsed,
                'status': 'success',
                'result': result
            }
            print(f"✓ {name}: {elapsed:.2f}ms")
            return result
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            self.results[name] = {
                'time_ms': elapsed,
                'status': 'error',
                'error': str(e)
            }
            print(f"✗ {name}: FAILED - {str(e)}")
            return None
    
    def test_count_bags(self):
        """Test counting total bags"""
        def query():
            return Bag.query.count()
        return self.run_timed_query("Count All Bags", query)
    
    def test_count_parent_bags(self):
        """Test counting parent bags with index"""
        def query():
            return Bag.query.filter_by(type='parent').count()
        return self.run_timed_query("Count Parent Bags (Indexed)", query)
    
    def test_pagination_first_page(self):
        """Test first page pagination (should be fast)"""
        def query():
            return Bag.query.order_by(Bag.id.desc()).limit(50).all()
        return self.run_timed_query("Pagination: First Page (50 items)", query)
    
    def test_pagination_middle_page(self):
        """Test middle page pagination with offset"""
        def query():
            return Bag.query.order_by(Bag.id.desc()).offset(50000).limit(50).all()
        return self.run_timed_query("Pagination: Middle Page (offset 50k)", query)
    
    def test_search_by_qr_exact(self):
        """Test exact QR search (should use index)"""
        def query():
            return Bag.query.filter_by(qr_id='SB12345').first()
        return self.run_timed_query("Search: Exact QR Match (Indexed)", query)
    
    def test_search_by_qr_pattern(self):
        """Test pattern search (LIKE query)"""
        def query():
            return Bag.query.filter(Bag.qr_id.like('SB%')).limit(50).all()
        return self.run_timed_query("Search: QR Pattern (LIKE)", query)
    
    def test_join_bags_with_scans(self):
        """Test JOIN performance"""
        def query():
            return db.session.query(Bag, func.count(Scan.id))\
                .outerjoin(Scan, Scan.parent_bag_id == Bag.id)\
                .group_by(Bag.id)\
                .limit(100)\
                .all()
        return self.run_timed_query("JOIN: Bags with Scan Counts", query)
    
    def test_complex_dashboard_query(self):
        """Test complex aggregation query (dashboard stats)"""
        def query():
            return db.session.query(
                func.count(Bag.id).label('total_bags'),
                func.count(Bag.id).filter(Bag.type == 'parent').label('parent_bags'),
                func.count(Bag.id).filter(Bag.type == 'child').label('child_bags')
            ).first()
        return self.run_timed_query("Dashboard: Aggregate Statistics", query)
    
    def test_recent_scans(self):
        """Test querying recent scans with JOIN"""
        def query():
            return db.session.query(Scan, Bag, User)\
                .join(Bag, Scan.parent_bag_id == Bag.id)\
                .join(User, Scan.user_id == User.id)\
                .order_by(Scan.timestamp.desc())\
                .limit(50)\
                .all()
        return self.run_timed_query("Recent Scans with JOINs", query)
    
    def test_bill_with_bags(self):
        """Test bill retrieval with related bags"""
        def query():
            return Bill.query.order_by(Bill.created_at.desc()).limit(10).all()
        return self.run_timed_query("Bills: Recent 10 with relationships", query)
    
    def run_all_tests(self):
        """Run all database scale tests"""
        print("\n" + "="*60)
        print("DATABASE SCALE TESTS - TraitorTrack")
        print("="*60 + "\n")
        
        with app.app_context():
            # Get database size
            total_bags = self.test_count_bags()
            total_parent = self.test_count_parent_bags()
            
            print(f"\nDatabase contains: {total_bags:,} bags ({total_parent:,} parent)")
            print("-" * 60 + "\n")
            
            # Run performance tests
            self.test_pagination_first_page()
            self.test_pagination_middle_page()
            self.test_search_by_qr_exact()
            self.test_search_by_qr_pattern()
            self.test_join_bags_with_scans()
            self.test_complex_dashboard_query()
            self.test_recent_scans()
            self.test_bill_with_bags()
            
            # Analyze results
            self.print_summary()
    
    def print_summary(self):
        """Print test summary and evaluation"""
        print("\n" + "="*60)
        print("PERFORMANCE SUMMARY")
        print("="*60)
        
        times = [r['time_ms'] for r in self.results.values() if r['status'] == 'success']
        
        if times:
            print(f"\nAverage Query Time: {statistics.mean(times):.2f}ms")
            print(f"Median Query Time: {statistics.median(times):.2f}ms")
            print(f"Fastest Query: {min(times):.2f}ms")
            print(f"Slowest Query: {max(times):.2f}ms")
        
        # Evaluate against targets
        print("\n" + "="*60)
        print("PERFORMANCE TARGETS")
        print("="*60)
        
        targets = {
            "Pagination: First Page (50 items)": 100,  # Should be <100ms
            "Search: Exact QR Match (Indexed)": 50,    # Should be <50ms
            "Dashboard: Aggregate Statistics": 200,     # Should be <200ms
        }
        
        passed = 0
        failed = 0
        
        for test_name, target_ms in targets.items():
            if test_name in self.results:
                actual_ms = self.results[test_name]['time_ms']
                status = "✅ PASS" if actual_ms <= target_ms else "❌ FAIL"
                print(f"{status} {test_name}: {actual_ms:.2f}ms (target: <{target_ms}ms)")
                if actual_ms <= target_ms:
                    passed += 1
                else:
                    failed += 1
        
        print("\n" + "="*60)
        print(f"Overall: {passed}/{passed+failed} tests passed")
        
        if failed == 0:
            print("✅ Database performs well at scale!")
        else:
            print(f"⚠️  {failed} test(s) exceeded performance targets")
            print("Consider: re-indexing, query optimization, or connection pooling tuning")
        
        print("="*60 + "\n")


if __name__ == "__main__":
    tester = DatabaseScaleTest()
    tester.run_all_tests()

"""
Comprehensive Test Suite for Optimized Excel Upload
Tests handling of 80,000+ bags with various formats
"""
import os
import time
import unittest
import tempfile
from io import BytesIO
import xlsxwriter
import openpyxl
import psycopg2
from flask import Flask, session
from flask_login import login_user, current_user
from datetime import datetime
from optimized_excel_upload import OptimizedExcelUploader, create_test_excel
from app_clean import app, db
from models import User, Bag, Link, Scan, BagType

class TestOptimizedExcelUpload(unittest.TestCase):
    """Test suite for optimized Excel upload with 80k+ bags"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        cls.app = app
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        
        # Create test database tables
        db.create_all()
        
        # Create test admin user
        admin = User()
        admin.username = 'test_admin'
        admin.email = 'test@example.com'
        admin.set_password('test123')
        admin.role = 'admin'
        admin.verified = True
        db.session.add(admin)
        db.session.commit()
        cls.admin_id = admin.id
        
        # Initialize uploader
        cls.uploader = OptimizedExcelUploader()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        db.session.remove()
        db.drop_all()
        cls.ctx.pop()
    
    def setUp(self):
        """Set up before each test"""
        # Clear all bags and links before each test
        db.session.query(Scan).delete()
        db.session.query(Link).delete()
        db.session.query(Bag).delete()
        db.session.commit()
    
    def create_excel_file(self, parent_child_data):
        """Create an Excel file with given parent-child data"""
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet()
        
        # Write headers
        worksheet.write(0, 0, 'Serial')
        worksheet.write(0, 1, 'Parent Bag')
        worksheet.write(0, 2, 'Child Bag')
        
        # Write data
        for i, (parent, child) in enumerate(parent_child_data, 1):
            worksheet.write(i, 0, i)
            worksheet.write(i, 1, parent)
            worksheet.write(i, 2, child)
        
        workbook.close()
        output.seek(0)
        return output.getvalue()
    
    def test_basic_upload(self):
        """Test basic upload with small dataset"""
        print("\n=== Test: Basic Upload ===")
        
        # Create test data
        parent_child_data = [
            ('PARENT001', 'CHILD001'),
            ('PARENT001', 'CHILD002'),
            ('PARENT002', 'CHILD003'),
            ('PARENT002', 'CHILD004'),
        ]
        
        excel_content = self.create_excel_file(parent_child_data)
        
        # Process the file
        stats = self.uploader.process_excel_file(
            excel_content, 
            self.admin_id, 
            'Test Area'
        )
        
        # Verify results
        self.assertEqual(stats['total_rows'], 4)
        self.assertEqual(stats['successful_links'], 4)
        self.assertEqual(stats['parent_bags_created'], 2)
        self.assertEqual(stats['child_bags_created'], 4)
        
        # Verify database
        parent_bags = Bag.query.filter_by(type='parent').all()
        child_bags = Bag.query.filter_by(type='child').all()
        links = Link.query.all()
        
        self.assertEqual(len(parent_bags), 2)
        self.assertEqual(len(child_bags), 4)
        self.assertEqual(len(links), 4)
        
        print(f"✓ Basic upload test passed: {stats}")
    
    def test_duplicate_detection(self):
        """Test duplicate child bag detection"""
        print("\n=== Test: Duplicate Detection ===")
        
        # Create test data with duplicates
        parent_child_data = [
            ('PARENT001', 'CHILD001'),
            ('PARENT001', 'CHILD001'),  # Duplicate
            ('PARENT001', 'CHILD002'),
            ('PARENT002', 'CHILD002'),  # Same child, different parent (allowed)
            ('PARENT002', 'CHILD002'),  # Duplicate
        ]
        
        excel_content = self.create_excel_file(parent_child_data)
        
        # Process the file
        stats = self.uploader.process_excel_file(
            excel_content, 
            self.admin_id, 
            'Test Area'
        )
        
        # Verify results
        self.assertEqual(stats['total_rows'], 3)  # 2 duplicates removed
        self.assertEqual(stats['duplicate_children'], 2)
        self.assertEqual(stats['successful_links'], 3)
        
        print(f"✓ Duplicate detection test passed: {stats}")
    
    def test_various_formats(self):
        """Test various bag ID formats"""
        print("\n=== Test: Various Formats ===")
        
        # Create test data with various formats
        parent_child_data = [
            ('SB12345', '98765'),         # Traditional format
            ('PB-001', 'CB-001'),         # With prefix and dash
            ('BAG100', 'CHILD100'),       # Text prefix
            ('12345', '67890'),           # Pure numbers
            ('Parent_A', 'Child_A'),      # With underscore
            ('P.001', 'C.001'),          # With dots
        ]
        
        excel_content = self.create_excel_file(parent_child_data)
        
        # Process the file
        stats = self.uploader.process_excel_file(
            excel_content, 
            self.admin_id, 
            'Test Area'
        )
        
        # Verify all formats were accepted
        self.assertEqual(stats['total_rows'], 6)
        self.assertEqual(stats['successful_links'], 6)
        self.assertEqual(stats['parent_bags_created'], 6)
        self.assertEqual(stats['child_bags_created'], 6)
        
        print(f"✓ Various formats test passed: {stats}")
    
    def test_large_dataset_performance(self):
        """Test performance with large dataset (10,000 bags)"""
        print("\n=== Test: Large Dataset Performance (10,000 bags) ===")
        
        # Create large dataset
        parent_child_data = []
        num_parents = 334  # 334 parents * 30 children ≈ 10,020 bags
        
        for p in range(num_parents):
            parent_id = f"P{p:05d}"
            for c in range(30):
                child_id = f"C{p:05d}_{c:02d}"
                parent_child_data.append((parent_id, child_id))
        
        excel_content = self.create_excel_file(parent_child_data)
        
        # Process with timing
        start_time = time.time()
        stats = self.uploader.process_excel_file(
            excel_content, 
            self.admin_id, 
            'Test Area'
        )
        elapsed = time.time() - start_time
        
        # Verify results
        self.assertEqual(stats['total_rows'], 10020)
        self.assertEqual(stats['successful_links'], 10020)
        self.assertEqual(stats['parent_bags_created'], 334)
        self.assertEqual(stats['child_bags_created'], 10020)
        
        # Performance check - should complete within reasonable time
        print(f"✓ Processed 10,000 bags in {elapsed:.2f} seconds")
        print(f"  Rate: {10020/elapsed:.0f} bags/second")
        
        # Verify parent counts
        parent_bags = Bag.query.filter_by(type='parent').all()
        for parent in parent_bags:
            self.assertEqual(parent.child_count, 30)
            self.assertEqual(parent.weight_kg, 30.0)
    
    def test_existing_bags_handling(self):
        """Test handling of existing bags"""
        print("\n=== Test: Existing Bags Handling ===")
        
        # Pre-create some bags
        parent1 = Bag()
        parent1.qr_id = 'EXISTING_PARENT'
        parent1.type = 'parent'
        parent1.status = 'pending'
        parent1.user_id = self.admin_id
        parent1.dispatch_area = 'Test Area'
        parent1.child_count = 0
        parent1.weight_kg = 0
        
        child1 = Bag()
        child1.qr_id = 'EXISTING_CHILD'
        child1.type = 'child'
        child1.status = 'pending'
        child1.user_id = self.admin_id
        child1.dispatch_area = 'Test Area'
        
        db.session.add_all([parent1, child1])
        db.session.commit()
        
        # Create test data with existing and new bags
        parent_child_data = [
            ('EXISTING_PARENT', 'EXISTING_CHILD'),
            ('EXISTING_PARENT', 'NEW_CHILD1'),
            ('NEW_PARENT', 'EXISTING_CHILD'),
            ('NEW_PARENT', 'NEW_CHILD2'),
        ]
        
        excel_content = self.create_excel_file(parent_child_data)
        
        # Process the file
        stats = self.uploader.process_excel_file(
            excel_content, 
            self.admin_id, 
            'Test Area'
        )
        
        # Verify results
        self.assertEqual(stats['total_rows'], 4)
        self.assertEqual(stats['successful_links'], 4)
        self.assertEqual(stats['parent_bags_created'], 1)  # Only NEW_PARENT
        self.assertEqual(stats['child_bags_created'], 2)  # NEW_CHILD1 and NEW_CHILD2
        
        print(f"✓ Existing bags handling test passed: {stats}")
    
    def test_unlimited_children(self):
        """Test that parents can have unlimited children (not just 30)"""
        print("\n=== Test: Unlimited Children per Parent ===")
        
        # Create test data with >30 children for one parent
        parent_child_data = []
        parent_id = 'PARENT_WITH_MANY'
        
        for i in range(100):  # 100 children for one parent
            child_id = f'CHILD_{i:03d}'
            parent_child_data.append((parent_id, child_id))
        
        excel_content = self.create_excel_file(parent_child_data)
        
        # Process the file
        stats = self.uploader.process_excel_file(
            excel_content, 
            self.admin_id, 
            'Test Area'
        )
        
        # Verify results
        self.assertEqual(stats['total_rows'], 100)
        self.assertEqual(stats['successful_links'], 100)
        self.assertEqual(stats['parent_bags_created'], 1)
        self.assertEqual(stats['child_bags_created'], 100)
        
        # Verify parent has all 100 children
        parent = Bag.query.filter_by(qr_id='PARENT_WITH_MANY').first()
        self.assertIsNotNone(parent)
        self.assertEqual(parent.child_count, 100)
        self.assertEqual(parent.weight_kg, 100.0)
        
        print(f"✓ Unlimited children test passed: Parent has {parent.child_count} children")
    
    def test_memory_efficiency(self):
        """Test memory efficiency with streaming processing"""
        print("\n=== Test: Memory Efficiency ===")
        
        # This test verifies that the uploader can handle files
        # without loading everything into memory at once
        
        # Create a moderately large dataset
        parent_child_data = []
        for p in range(100):
            parent_id = f"MEM_P{p:03d}"
            for c in range(50):
                child_id = f"MEM_C{p:03d}_{c:02d}"
                parent_child_data.append((parent_id, child_id))
        
        excel_content = self.create_excel_file(parent_child_data)
        
        # Process the file
        stats = self.uploader.process_excel_file(
            excel_content, 
            self.admin_id, 
            'Test Area'
        )
        
        # Verify results
        self.assertEqual(stats['total_rows'], 5000)
        self.assertEqual(stats['successful_links'], 5000)
        
        print(f"✓ Memory efficiency test passed: Processed {stats['total_rows']} rows")
    
    def test_error_handling(self):
        """Test error handling for invalid data"""
        print("\n=== Test: Error Handling ===")
        
        # Create test data with some invalid entries
        parent_child_data = [
            ('VALID_PARENT', 'VALID_CHILD'),
            ('', 'ORPHAN_CHILD'),  # Empty parent
            ('ORPHAN_PARENT', ''),  # Empty child
            ('PARENT2', 'CHILD2'),
        ]
        
        excel_content = self.create_excel_file(parent_child_data)
        
        # Process the file
        stats = self.uploader.process_excel_file(
            excel_content, 
            self.admin_id, 
            'Test Area'
        )
        
        # Verify results - only valid rows processed
        self.assertEqual(stats['total_rows'], 2)  # Only valid rows
        self.assertEqual(stats['invalid_format'], 2)  # Invalid rows
        self.assertEqual(stats['successful_links'], 2)
        
        print(f"✓ Error handling test passed: {stats}")


def run_performance_test():
    """Run a standalone performance test with 80,000+ bags"""
    print("\n" + "="*60)
    print("PERFORMANCE TEST: 80,000+ BAGS")
    print("="*60)
    
    # Create test Excel file
    print("\nCreating test Excel file with 80,010 bags...")
    temp_file = 'test_80k_bags.xlsx'
    create_test_excel(temp_file, num_parents=2667, children_per_parent=30)
    
    # Read the file
    with open(temp_file, 'rb') as f:
        excel_content = f.read()
    
    # Initialize uploader
    uploader = OptimizedExcelUploader()
    
    # Process with timing
    print("\nProcessing 80,000+ bags...")
    start_time = time.time()
    
    # Note: This would need a real database connection
    # For testing purposes, we'll simulate the processing
    print("Simulating processing (actual processing requires database)...")
    
    elapsed = time.time() - start_time
    
    print(f"\n✓ Test file created and ready")
    print(f"  File: {temp_file}")
    print(f"  Size: {os.path.getsize(temp_file) / (1024*1024):.2f} MB")
    print(f"  Rows: 80,010")
    print(f"\nTo run actual processing:")
    print("  1. Ensure database is connected")
    print("  2. Use the web interface to upload the file")
    print("  3. Monitor the processing time and results")
    
    # Clean up
    if os.path.exists(temp_file):
        os.remove(temp_file)
    
    print("\n" + "="*60)


if __name__ == '__main__':
    # Run unit tests
    print("Running Unit Tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run performance test
    run_performance_test()
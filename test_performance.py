#!/usr/bin/env python3
"""
Performance test script for large-scale Excel import.
Simulates importing 100,000+ bag records to identify bottlenecks.
"""

import os
import sys
import time
import tempfile
import tracemalloc
import gc
from datetime import datetime

# Ensure we can import from the project
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_large_test_excel(num_parents: int = 1000, children_per_parent: int = 15):
    """
    Create a large Excel file with the expected format.
    Total rows = num_parents * (children_per_parent + 1)
    
    For 100k bags: 6667 parents × 15 children = 100,005 child rows
    """
    from openpyxl import Workbook
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Test Data"
    
    # Add headers
    ws.append(["Sr. No.", "QR Code"])
    
    row_count = 1
    start_label = 1000000  # Start from a high number to avoid conflicts
    
    print(f"Generating {num_parents} parent bags with {children_per_parent} children each...")
    print(f"Total rows to generate: {num_parents * (children_per_parent + 1):,}")
    
    for parent_idx in range(num_parents):
        # Add child rows
        for child_idx in range(children_per_parent):
            label_num = start_label + (parent_idx * children_per_parent) + child_idx
            sr_no = child_idx + 1
            qr_code = f"LABEL NO.{label_num:07d} LOT NO.:TEST{parent_idx:05d}, D.O.T.:01/01/2025"
            ws.append([sr_no, qr_code])
            row_count += 1
        
        # Add parent row
        parent_code = f"PERF-TEST-{parent_idx:06d}"
        ws.append(["Parent Code", parent_code])
        row_count += 1
        
        if (parent_idx + 1) % 500 == 0:
            print(f"  Generated {parent_idx + 1:,} parents ({row_count:,} rows)")
    
    # Save to temp file
    temp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    wb.save(temp_file.name)
    wb.close()
    
    file_size_mb = os.path.getsize(temp_file.name) / (1024 * 1024)
    print(f"Created test file: {temp_file.name} ({file_size_mb:.2f} MB)")
    print(f"Total rows: {row_count:,}")
    
    return temp_file.name


def run_performance_test(test_file: str, user_id: int = 1):
    """Run the import and measure performance."""
    from app import app, db
    from import_utils import LargeScaleChildParentImporter
    from werkzeug.datastructures import FileStorage
    from io import BytesIO
    
    with app.app_context():
        # Start memory tracking
        tracemalloc.start()
        gc.collect()
        
        start_time = time.time()
        start_memory = tracemalloc.get_traced_memory()[0]
        
        print("\n" + "="*60)
        print("STARTING PERFORMANCE TEST")
        print("="*60)
        
        last_progress_time = time.time()
        last_progress_rows = 0
        
        def progress_callback(current, total):
            nonlocal last_progress_time, last_progress_rows
            now = time.time()
            elapsed = now - last_progress_time
            if elapsed > 0:
                rows_per_sec = (current - last_progress_rows) / elapsed
                print(f"  Progress: {current:,}/{total:,} ({100*current/total:.1f}%) - {rows_per_sec:.0f} rows/sec")
            last_progress_time = now
            last_progress_rows = current
        
        try:
            with open(test_file, 'rb') as f:
                file_data = f.read()
            
            file_storage = FileStorage(
                stream=BytesIO(file_data),
                filename=os.path.basename(test_file),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            stats, results = LargeScaleChildParentImporter.process_file_streaming(
                file_storage=file_storage,
                user_id=user_id,
                dispatch_area="PERF-TEST",
                auto_create_parents=True,
                progress_callback=progress_callback
            )
            
            end_time = time.time()
            current_memory, peak_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            duration = end_time - start_time
            
            print("\n" + "="*60)
            print("PERFORMANCE RESULTS")
            print("="*60)
            print(f"Duration: {duration:.2f} seconds")
            print(f"Peak memory: {peak_memory / (1024*1024):.2f} MB")
            print(f"Final memory: {current_memory / (1024*1024):.2f} MB")
            
            total_bags = stats.get('children_created', 0) + stats.get('children_existing', 0)
            if duration > 0:
                print(f"Throughput: {total_bags/duration:.0f} bags/second")
                print(f"Time per 10k bags: {(duration/total_bags)*10000:.2f} seconds")
            
            print(f"\nStats: {stats}")
            
            # Count errors
            error_count = sum(1 for r in results if r.status == 'error')
            print(f"Total errors: {error_count:,}")
            
            return {
                'duration': duration,
                'peak_memory_mb': peak_memory / (1024*1024),
                'total_bags': total_bags,
                'bags_per_second': total_bags/duration if duration > 0 else 0,
                'stats': stats,
                'error_count': error_count
            }
            
        except Exception as e:
            print(f"ERROR: {e}")
            traceback = __import__('traceback')
            traceback.print_exc()
            return None


def cleanup_test_data():
    """Remove test data from database."""
    from app import app, db
    from models import Bag, Link
    
    with app.app_context():
        print("\nCleaning up test data...")
        
        # Find all test parent bags
        test_parents = Bag.query.filter(Bag.qr_id.like('PERF-TEST-%')).all()
        parent_ids = [p.id for p in test_parents]
        
        if parent_ids:
            # Delete links first
            Link.query.filter(Link.parent_bag_id.in_(parent_ids)).delete(synchronize_session=False)
            
            # Find child bags linked to test parents
            child_ids = db.session.query(Link.child_bag_id).filter(
                Link.parent_bag_id.in_(parent_ids)
            ).all()
            child_ids = [c[0] for c in child_ids]
            
            # Delete child bags
            if child_ids:
                Bag.query.filter(Bag.id.in_(child_ids)).delete(synchronize_session=False)
            
            # Delete parent bags
            Bag.query.filter(Bag.id.in_(parent_ids)).delete(synchronize_session=False)
            
            db.session.commit()
            print(f"Deleted {len(test_parents)} parent bags and associated data")
        else:
            print("No test data found to clean up")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Performance test for bag import')
    parser.add_argument('--parents', type=int, default=500, 
                        help='Number of parent bags (default: 500)')
    parser.add_argument('--children', type=int, default=15,
                        help='Children per parent (default: 15)')
    parser.add_argument('--cleanup', action='store_true',
                        help='Clean up test data after running')
    parser.add_argument('--cleanup-only', action='store_true',
                        help='Only clean up existing test data')
    
    args = parser.parse_args()
    
    if args.cleanup_only:
        cleanup_test_data()
        return
    
    total_bags = args.parents * args.children
    print(f"\n{'='*60}")
    print(f"PERFORMANCE TEST: {total_bags:,} bags ({args.parents} parents × {args.children} children)")
    print(f"{'='*60}\n")
    
    # Create test file
    test_file = create_large_test_excel(args.parents, args.children)
    
    try:
        # Run test
        results = run_performance_test(test_file)
        
        if results:
            print("\n" + "="*60)
            print("SUMMARY")
            print("="*60)
            print(f"Total bags processed: {results['total_bags']:,}")
            print(f"Duration: {results['duration']:.2f} seconds")
            print(f"Throughput: {results['bags_per_second']:.0f} bags/second")
            print(f"Peak memory: {results['peak_memory_mb']:.2f} MB")
            
            # Estimate for 1 lakh (100,000) bags
            if results['bags_per_second'] > 0:
                time_for_100k = 100000 / results['bags_per_second']
                print(f"\nEstimated time for 1 lakh (100,000) bags: {time_for_100k:.1f} seconds ({time_for_100k/60:.1f} minutes)")
    
    finally:
        # Cleanup temp file
        if os.path.exists(test_file):
            os.unlink(test_file)
            print(f"\nDeleted temp file: {test_file}")
        
        if args.cleanup:
            cleanup_test_data()


if __name__ == '__main__':
    main()

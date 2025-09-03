#!/usr/bin/env python
"""
Create Test Excel Files for Upload Testing
Generates Excel files with various sizes for testing the optimized upload feature
"""
import xlsxwriter
import random
import time

def create_test_excel_file(filename, num_parents=100, children_per_parent=30, format_variety=True):
    """
    Create a test Excel file with specified parameters
    
    Args:
        filename: Output Excel file name
        num_parents: Number of parent bags
        children_per_parent: Number of children per parent
        format_variety: Use various formats for bag IDs
    """
    print(f"\nCreating test Excel file: {filename}")
    print(f"  Parents: {num_parents:,}")
    print(f"  Children per parent: {children_per_parent}")
    print(f"  Total rows: {num_parents * children_per_parent:,}")
    
    start_time = time.time()
    
    workbook = xlsxwriter.Workbook(filename, {'constant_memory': True})
    worksheet = workbook.add_worksheet()
    
    # Write headers
    worksheet.write(0, 0, 'Serial')
    worksheet.write(0, 1, 'Parent Bag')
    worksheet.write(0, 2, 'Child Bag')
    
    row = 1
    serial = 1
    
    # Progress tracking
    total_rows = num_parents * children_per_parent
    progress_interval = max(1, total_rows // 10)  # Show 10 progress updates
    
    for parent_num in range(num_parents):
        # Generate parent QR with various formats if requested
        if format_variety:
            format_choice = parent_num % 5
            if format_choice == 0:
                parent_qr = f"SB{parent_num:05d}"
            elif format_choice == 1:
                parent_qr = f"PB{parent_num:06d}"
            elif format_choice == 2:
                parent_qr = f"BAG{parent_num:04d}"
            elif format_choice == 3:
                parent_qr = f"P-{parent_num:05d}"
            else:
                parent_qr = f"PARENT_{parent_num}"
        else:
            # Simple format
            parent_qr = f"P{parent_num:06d}"
        
        for child_num in range(children_per_parent):
            # Generate child QR with various formats if requested
            child_id = parent_num * children_per_parent + child_num
            
            if format_variety:
                format_choice = child_num % 4
                if format_choice == 0:
                    child_qr = f"{child_id:06d}"
                elif format_choice == 1:
                    child_qr = f"CB{child_id:05d}"
                elif format_choice == 2:
                    child_qr = f"C-{child_id}"
                else:
                    child_qr = f"CHILD{child_id}"
            else:
                # Simple format
                child_qr = f"C{child_id:07d}"
            
            # Write row
            worksheet.write(row, 0, serial)
            worksheet.write(row, 1, parent_qr)
            worksheet.write(row, 2, child_qr)
            
            row += 1
            serial += 1
            
            # Show progress
            if row % progress_interval == 0:
                progress = (row / total_rows) * 100
                print(f"  Progress: {progress:.0f}% ({row:,} / {total_rows:,} rows)")
    
    workbook.close()
    
    elapsed = time.time() - start_time
    file_size_mb = 0
    
    try:
        import os
        file_size_mb = os.path.getsize(filename) / (1024 * 1024)
    except:
        pass
    
    print(f"\n✓ Test Excel file created successfully!")
    print(f"  File: {filename}")
    print(f"  Size: {file_size_mb:.2f} MB")
    print(f"  Total rows: {row - 1:,}")
    print(f"  Time taken: {elapsed:.2f} seconds")
    print(f"  Rate: {(row - 1) / elapsed:,.0f} rows/second")
    
    return filename

def create_duplicate_test_file(filename, num_unique=100, duplicate_factor=2):
    """
    Create a test file with intentional duplicates
    """
    print(f"\nCreating test file with duplicates: {filename}")
    print(f"  Unique pairs: {num_unique}")
    print(f"  Duplicate factor: {duplicate_factor}x")
    
    workbook = xlsxwriter.Workbook(filename)
    worksheet = workbook.add_worksheet()
    
    # Write headers
    worksheet.write(0, 0, 'Serial')
    worksheet.write(0, 1, 'Parent Bag')
    worksheet.write(0, 2, 'Child Bag')
    
    # Generate unique pairs
    unique_pairs = []
    for i in range(num_unique):
        parent = f"DUP_P{i:04d}"
        child = f"DUP_C{i:04d}"
        unique_pairs.append((parent, child))
    
    # Write pairs with duplicates
    row = 1
    serial = 1
    
    for _ in range(duplicate_factor):
        # Shuffle to distribute duplicates
        random.shuffle(unique_pairs)
        for parent, child in unique_pairs:
            worksheet.write(row, 0, serial)
            worksheet.write(row, 1, parent)
            worksheet.write(row, 2, child)
            row += 1
            serial += 1
    
    workbook.close()
    
    print(f"✓ Duplicate test file created: {row - 1} total rows ({num_unique} unique)")
    return filename

def create_edge_case_test_file(filename):
    """
    Create a test file with edge cases
    """
    print(f"\nCreating edge case test file: {filename}")
    
    workbook = xlsxwriter.Workbook(filename)
    worksheet = workbook.add_worksheet()
    
    # Write headers
    worksheet.write(0, 0, 'Serial')
    worksheet.write(0, 1, 'Parent Bag')
    worksheet.write(0, 2, 'Child Bag')
    
    # Edge cases
    edge_cases = [
        # Normal cases
        ("NORMAL_P1", "NORMAL_C1"),
        
        # Special characters (should be handled)
        ("P-123", "C-456"),
        ("P.789", "C.012"),
        ("P_345", "C_678"),
        
        # Long IDs
        ("P" * 50, "C" * 50),
        
        # Unicode (if supported)
        ("PARENT_001", "CHILD_001"),
        
        # Numbers only
        ("123456", "789012"),
        
        # Mixed case (should be normalized to uppercase)
        ("parent_lower", "child_lower"),
        ("Parent_Mixed", "Child_Mixed"),
        
        # Spaces (should be trimmed)
        ("  P_SPACE  ", "  C_SPACE  "),
        
        # One parent with many children
        *[("PARENT_MANY", f"CHILD_{i:03d}") for i in range(50)],
        
        # Many parents with same child (allowed)
        *[(f"PARENT_{i:02d}", "SHARED_CHILD") for i in range(10)],
    ]
    
    row = 1
    for i, (parent, child) in enumerate(edge_cases, 1):
        worksheet.write(row, 0, i)
        worksheet.write(row, 1, parent)
        worksheet.write(row, 2, child)
        row += 1
    
    workbook.close()
    
    print(f"✓ Edge case test file created: {row - 1} rows")
    return filename

def main():
    """Generate various test Excel files"""
    
    print("=" * 60)
    print("Excel Test File Generator")
    print("=" * 60)
    
    # 1. Small test file (for quick testing)
    create_test_excel_file(
        "test_small.xlsx",
        num_parents=10,
        children_per_parent=5,
        format_variety=True
    )
    
    # 2. Medium test file (1,000 bags)
    create_test_excel_file(
        "test_medium.xlsx",
        num_parents=34,
        children_per_parent=30,
        format_variety=True
    )
    
    # 3. Large test file (10,000 bags)
    create_test_excel_file(
        "test_large_10k.xlsx",
        num_parents=334,
        children_per_parent=30,
        format_variety=False  # Simple format for speed
    )
    
    # 4. Extra large test file (80,000+ bags)
    print("\n" + "=" * 60)
    print("Creating EXTRA LARGE test file (80,000+ bags)")
    print("This may take a minute...")
    print("=" * 60)
    
    create_test_excel_file(
        "test_extra_large_80k.xlsx",
        num_parents=2667,
        children_per_parent=30,
        format_variety=False  # Simple format for speed
    )
    
    # 5. Duplicate test file
    create_duplicate_test_file(
        "test_duplicates.xlsx",
        num_unique=100,
        duplicate_factor=3
    )
    
    # 6. Edge cases test file
    create_edge_case_test_file("test_edge_cases.xlsx")
    
    print("\n" + "=" * 60)
    print("All test files created successfully!")
    print("=" * 60)
    print("\nTest files ready for upload:")
    print("  - test_small.xlsx (50 rows) - Quick functionality test")
    print("  - test_medium.xlsx (1,020 rows) - Standard test")
    print("  - test_large_10k.xlsx (10,020 rows) - Performance test")
    print("  - test_extra_large_80k.xlsx (80,010 rows) - Stress test")
    print("  - test_duplicates.xlsx (300 rows, 100 unique) - Duplicate handling")
    print("  - test_edge_cases.xlsx - Special cases and edge conditions")
    print("\nUpload these files through the web interface to test the feature.")

if __name__ == "__main__":
    main()
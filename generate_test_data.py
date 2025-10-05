"""
Generate 1.5 million test bags for performance testing
Creates CSV files for bulk COPY into PostgreSQL
"""
import csv
import random
from datetime import datetime, timedelta
import os

# Configuration
TOTAL_BAGS = 1_500_000
PARENT_BAGS = 50_000  # 50K parent bags
CHILDREN_PER_PARENT = 30  # Average 30 children per parent
DISPATCH_AREAS = ['Area_A', 'Area_B', 'Area_C', 'Area_D', 'Area_E']

def generate_parent_bags():
    """Generate parent bag CSV"""
    print(f"Generating {PARENT_BAGS} parent bags...")
    
    with open('/tmp/parent_bags.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write parent bags
        for i in range(1, PARENT_BAGS + 1):
            qr_id = f"SB{i:05d}"  # SB00001 to SB50000
            bag_type = 'parent'
            user_id = 1  # Admin user
            dispatch_area = random.choice(DISPATCH_AREAS)
            created_at = datetime.now() - timedelta(days=random.randint(0, 30))
            
            writer.writerow([
                qr_id,
                bag_type,
                user_id,
                dispatch_area,
                created_at.isoformat()
            ])
    
    print(f"✓ Generated /tmp/parent_bags.csv")

def generate_child_bags():
    """Generate child bag CSV"""
    print(f"Generating {TOTAL_BAGS - PARENT_BAGS} child bags...")
    
    with open('/tmp/child_bags.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Generate children for each parent
        child_counter = 1
        for parent_id in range(1, PARENT_BAGS + 1):
            # Random number of children (20-35)
            num_children = random.randint(25, 35)
            
            for _ in range(num_children):
                qr_id = f"CB{child_counter:06d}"  # CB000001, CB000002, etc.
                bag_type = 'child'
                user_id = 1
                dispatch_area = random.choice(DISPATCH_AREAS)
                created_at = datetime.now() - timedelta(days=random.randint(0, 30))
                
                writer.writerow([
                    qr_id,
                    bag_type,
                    user_id,
                    dispatch_area,
                    created_at.isoformat()
                ])
                
                child_counter += 1
                
                if child_counter > (TOTAL_BAGS - PARENT_BAGS):
                    break
            
            if child_counter > (TOTAL_BAGS - PARENT_BAGS):
                break
            
            # Progress update every 10K parent bags
            if parent_id % 10000 == 0:
                print(f"  Progress: {parent_id}/{PARENT_BAGS} parents, {child_counter} children")
    
    print(f"✓ Generated /tmp/child_bags.csv with {child_counter} children")

def generate_links():
    """Generate parent-child link CSV"""
    print(f"Generating parent-child links...")
    
    with open('/tmp/bag_links.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Link children to parents
        child_counter = 1
        for parent_id in range(1, PARENT_BAGS + 1):
            num_children = random.randint(25, 35)
            
            for _ in range(num_children):
                # Assuming sequential IDs: parent bags are 1-50000, children start at 50001
                parent_bag_id = parent_id
                child_bag_id = PARENT_BAGS + child_counter
                created_at = datetime.now() - timedelta(days=random.randint(0, 30))
                
                writer.writerow([
                    parent_bag_id,
                    child_bag_id,
                    created_at.isoformat()
                ])
                
                child_counter += 1
                
                if child_counter > (TOTAL_BAGS - PARENT_BAGS):
                    break
            
            if child_counter > (TOTAL_BAGS - PARENT_BAGS):
                break
    
    print(f"✓ Generated /tmp/bag_links.csv")

def main():
    print("=" * 60)
    print("PERFORMANCE TEST DATA GENERATION")
    print(f"Target: {TOTAL_BAGS:,} total bags")
    print(f"Parents: {PARENT_BAGS:,}")
    print(f"Children: {TOTAL_BAGS - PARENT_BAGS:,}")
    print("=" * 60)
    print()
    
    # Generate all CSVs
    generate_parent_bags()
    generate_child_bags()
    generate_links()
    
    print()
    print("=" * 60)
    print("✓ DATA GENERATION COMPLETE!")
    print()
    print("Next steps:")
    print("1. Run: python load_test_data.py")
    print("2. Run: locust -f locustfile.py")
    print("=" * 60)

if __name__ == '__main__':
    main()

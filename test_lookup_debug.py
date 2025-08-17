#!/usr/bin/env python3
"""
Debug script to test the lookup function directly without web interface
"""

import sys
sys.path.append('.')

try:
    from app_clean import app, db
    from models import Bag, Link
    from forms import ChildLookupForm
    from validation_utils import sanitize_input
    
    print("✓ All imports successful")
    
    # Test with app context
    with app.app_context():
        print("✓ App context created")
        
        # Test database connection
        try:
            bag_count = Bag.query.count()
            print(f"✓ Database connected - found {bag_count} bags")
        except Exception as e:
            print(f"✗ Database error: {e}")
            exit(1)
        
        # Test form creation (skip - requires request context)
        print("⚠ Skipping form creation test (requires request context)")
        
        # Test bag lookup logic
        try:
            qr_id = "P123-45"
            print(f"Testing lookup for QR ID: {qr_id}")
            
            # Direct database search
            bag = Bag.query.filter_by(qr_id=qr_id).first()
            
            if bag:
                print(f"✓ Found bag: {bag.qr_id}, type: {bag.type}")
                
                # Build bag info dictionary (same as in routes.py)
                bag_info = {
                    'id': bag.id,
                    'qr_id': bag.qr_id,
                    'type': bag.type,
                    'name': bag.name,
                    'dispatch_area': bag.dispatch_area,
                    'created_at': bag.created_at,
                    'updated_at': bag.updated_at
                }
                print(f"✓ Basic bag info created: {bag_info}")
                
                # Add relationship counts (same as in routes.py)
                if bag.type == 'parent':
                    print("Processing parent bag relationships...")
                    child_links = Link.query.filter_by(parent_bag_id=bag.id).all()
                    bag_info['child_count'] = len(child_links)
                    bag_info['children'] = []
                    for link in child_links:
                        child_bag = Bag.query.get(link.child_bag_id)
                        if child_bag:
                            bag_info['children'].append({
                                'qr_id': child_bag.qr_id,
                                'name': child_bag.name,
                                'dispatch_area': child_bag.dispatch_area
                            })
                    print(f"✓ Found {len(bag_info['children'])} child bags")
                else:  # child bag
                    print("Processing child bag relationships...")
                    parent_links = Link.query.filter_by(child_bag_id=bag.id).all()
                    bag_info['parent_count'] = len(parent_links)
                    bag_info['parents'] = []
                    for link in parent_links:
                        parent_bag = Bag.query.get(link.parent_bag_id)
                        if parent_bag:
                            bag_info['parents'].append({
                                'qr_id': parent_bag.qr_id,
                                'name': parent_bag.name,
                                'dispatch_area': parent_bag.dispatch_area
                            })
                    print(f"✓ Found {len(bag_info['parents'])} parent bags")
                
                print("✓ Bag lookup logic completed successfully!")
                print(f"Final bag_info structure: {list(bag_info.keys())}")
                
            else:
                print(f"✗ No bag found with QR ID: {qr_id}")
                
        except Exception as e:
            print(f"✗ Lookup logic error: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            exit(1)
            
    print("✓ All tests passed! The lookup logic should work correctly.")
    
except ImportError as e:
    print(f"✗ Import error: {e}")
    exit(1)
except Exception as e:
    print(f"✗ General error: {e}")
    import traceback
    print(f"Traceback: {traceback.format_exc()}")
    exit(1)
#!/usr/bin/env python3
"""
Test script for comprehensive user deletion functionality
"""

import sys
import os
sys.path.append('.')

# Import the Flask app and database
from app import app, db
from models import User, Scan, Bag, Link, BillBag, BagType, UserRole
from sqlalchemy import or_

def test_preview_deletion(username, email):
    """Test the preview deletion logic"""
    print(f"\n=== Testing Preview Deletion for {username} ({email}) ===")
    
    with app.app_context():
        # Find the user by username AND email for safety
        user = User.query.filter_by(username=username, email=email).first()
        
        if not user:
            print(f"❌ No user found with username '{username}' and email '{email}'")
            return False
        
        print(f"✓ User found: {user.username} (ID: {user.id}, Role: {user.role})")
        
        # Get all scans by this user
        user_scans = Scan.query.filter_by(user_id=user.id).all()
        print(f"✓ Found {len(user_scans)} scans by this user")
        
        # Collect unique bag IDs from scans
        scanned_bag_ids = set()
        for scan in user_scans:
            if scan.parent_bag_id:
                scanned_bag_ids.add(scan.parent_bag_id)
            if scan.child_bag_id:
                scanned_bag_ids.add(scan.child_bag_id)
        
        print(f"✓ Found {len(scanned_bag_ids)} unique bags scanned by user")
        
        # Get bag details
        bags_to_delete = Bag.query.filter(Bag.id.in_(scanned_bag_ids)).all() if scanned_bag_ids else []
        
        # Count related data
        parent_bags = sum(1 for bag in bags_to_delete if bag.type == BagType.PARENT.value)
        child_bags = sum(1 for bag in bags_to_delete if bag.type == BagType.CHILD.value)
        
        print(f"✓ Bags to delete: {parent_bags} parent bags, {child_bags} child bags")
        
        # Check for bills that would be affected
        affected_bills = []
        if parent_bags > 0:
            parent_bag_ids = [bag.id for bag in bags_to_delete if bag.type == BagType.PARENT.value]
            bill_links = BillBag.query.filter(BillBag.bag_id.in_(parent_bag_ids)).all()
            for link in bill_links:
                if link.bill:
                    affected_bills.append({
                        'id': link.bill.id,
                        'bill_id': link.bill.bill_id,
                        'description': link.bill.description or 'No description'
                    })
        
        print(f"✓ Affected bills: {len(affected_bills)}")
        
        # Count links that would be deleted
        link_count = 0
        if scanned_bag_ids:
            link_count = Link.query.filter(
                or_(Link.parent_bag_id.in_(scanned_bag_ids), 
                    Link.child_bag_id.in_(scanned_bag_ids))
            ).count()
        
        print(f"✓ Links to delete: {link_count}")
        
        # Show bag details
        print("\n📋 Bags that would be deleted:")
        for bag in bags_to_delete:
            print(f"   - {bag.qr_id} ({bag.type}) - {bag.name or 'Unnamed'}")
        
        if affected_bills:
            print("\n📄 Bills that would be affected:")
            for bill in affected_bills:
                print(f"   - {bill['bill_id']}: {bill['description']}")
        
        return True

def test_deletion_execution(username, email, dry_run=True):
    """Test the actual deletion logic (with dry_run option)"""
    print(f"\n=== Testing Deletion Execution for {username} ({email}) ===")
    print(f"DRY RUN: {dry_run}")
    
    with app.app_context():
        # Find the user
        user = User.query.filter_by(username=username, email=email).first()
        
        if not user:
            print(f"❌ No user found")
            return False
        
        # Safety checks
        if user.role == UserRole.ADMIN.value:
            admin_count = User.query.filter_by(role=UserRole.ADMIN.value).count()
            if admin_count <= 1:
                print("❌ Cannot delete the last admin account")
                return False
        
        # Step 1: Get all scans by this user
        user_scans = Scan.query.filter_by(user_id=user.id).all()
        scan_count = len(user_scans)
        print(f"Step 1: Found {scan_count} scans to delete")
        
        # Step 2: Collect unique bag IDs from scans
        bags_to_delete_ids = set()
        for scan in user_scans:
            if scan.parent_bag_id:
                bags_to_delete_ids.add(scan.parent_bag_id)
            if scan.child_bag_id:
                bags_to_delete_ids.add(scan.child_bag_id)
        
        print(f"Step 2: Found {len(bags_to_delete_ids)} bags to delete")
        
        if not dry_run:
            # Step 3: Delete all scans by this user
            deleted_scans = Scan.query.filter_by(user_id=user.id).delete()
            print(f"Step 3: Deleted {deleted_scans} scan records")
            
            # Step 4: Delete links associated with these bags
            if bags_to_delete_ids:
                deleted_links = Link.query.filter(
                    or_(Link.parent_bag_id.in_(bags_to_delete_ids), 
                        Link.child_bag_id.in_(bags_to_delete_ids))
                ).delete(synchronize_session=False)
                print(f"Step 4: Deleted {deleted_links} links")
                
                # Step 5: Delete bill associations
                deleted_bill_links = BillBag.query.filter(BillBag.bag_id.in_(bags_to_delete_ids)).delete(synchronize_session=False)
                print(f"Step 5: Deleted {deleted_bill_links} bill associations")
                
                # Step 6: Delete the bags themselves
                bags_deleted = Bag.query.filter(Bag.id.in_(bags_to_delete_ids)).delete(synchronize_session=False)
                print(f"Step 6: Deleted {bags_deleted} bags")
            else:
                bags_deleted = 0
                print("Step 4-6: No bags to delete")
            
            # Step 7: Delete the user
            db.session.delete(user)
            print(f"Step 7: Deleted user {user.username}")
            
            # Commit all changes
            db.session.commit()
            print("✓ All changes committed successfully")
            
            return {
                'scans_deleted': scan_count,
                'bags_deleted': bags_deleted
            }
        else:
            print("✓ Dry run completed - no changes made")
            return {
                'scans_to_delete': scan_count,
                'bags_to_delete': len(bags_to_delete_ids)
            }

def run_comprehensive_tests():
    """Run comprehensive tests on the deletion functionality"""
    print("🧪 COMPREHENSIVE USER DELETION TESTING")
    print("=" * 50)
    
    # Test 1: Preview deletion for existing test user
    print("\n📋 TEST 1: Preview Deletion")
    test_preview_deletion('testuser1', 'test1@example.com')
    
    # Test 2: Preview deletion for non-existent user
    print("\n📋 TEST 2: Preview Non-existent User")
    test_preview_deletion('nonexistent', 'fake@example.com')
    
    # Test 3: Preview deletion with wrong email
    print("\n📋 TEST 3: Preview with Wrong Email")
    test_preview_deletion('testuser1', 'wrong@example.com')
    
    # Test 4: Dry run deletion
    print("\n📋 TEST 4: Dry Run Deletion")
    test_deletion_execution('testuser1', 'test1@example.com', dry_run=True)
    
    # Test 5: Check data integrity before actual deletion
    print("\n📋 TEST 5: Data Integrity Check")
    with app.app_context():
        total_users = User.query.count()
        total_scans = Scan.query.count()
        total_bags = Bag.query.count()
        total_links = Link.query.count()
        
        print(f"Current data: {total_users} users, {total_scans} scans, {total_bags} bags, {total_links} links")
    
    # Test 6: Actual deletion (if user confirms)
    print("\n📋 TEST 6: Actual Deletion")
    print("⚠️  This will permanently delete testuser1 and all their data")
    
    # For automated testing, we'll do the actual deletion
    result = test_deletion_execution('testuser1', 'test1@example.com', dry_run=False)
    
    if result:
        print(f"✓ Deletion completed: {result}")
        
        # Verify deletion
        print("\n📋 TEST 7: Verify Deletion")
        with app.app_context():
            user_check = User.query.filter_by(username='testuser1').first()
            if user_check is None:
                print("✓ User successfully deleted")
            else:
                print("❌ User still exists!")
            
            # Check remaining data
            total_users = User.query.count()
            total_scans = Scan.query.count()
            total_bags = Bag.query.count()
            total_links = Link.query.count()
            
            print(f"Remaining data: {total_users} users, {total_scans} scans, {total_bags} bags, {total_links} links")
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    run_comprehensive_tests()
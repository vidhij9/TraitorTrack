#!/usr/bin/env python3
"""
Migration script to update existing parent bags with their owners.
Associates parent bags with users based on scan history.
"""

from app_clean import app, db
from models import Bag, Scan, BagType, User
from sqlalchemy import func

def migrate_parent_bag_owners():
    """Update existing parent bags with their owners based on scan history"""
    
    with app.app_context():
        try:
            # First, get all parent bags without owners
            parent_bags_without_owners = Bag.query.filter(
                Bag.type == BagType.PARENT.value,
                Bag.user_id == None
            ).all()
            
            print(f"Found {len(parent_bags_without_owners)} parent bags without owners")
            
            updated_count = 0
            
            for parent_bag in parent_bags_without_owners:
                # Find the first scan for this parent bag
                first_scan = Scan.query.filter_by(
                    parent_bag_id=parent_bag.id
                ).order_by(Scan.timestamp.asc()).first()
                
                if first_scan and first_scan.user_id:
                    # Update the parent bag with the user who first scanned it
                    parent_bag.user_id = first_scan.user_id
                    updated_count += 1
                    
                    # Get user info for logging
                    user = User.query.get(first_scan.user_id)
                    if user:
                        print(f"Updated parent bag {parent_bag.qr_id} - owner: {user.username}")
            
            # Commit all changes
            db.session.commit()
            
            print(f"\n✅ Migration completed successfully!")
            print(f"Updated {updated_count} parent bags with their owners")
            
            # Verify the update
            parent_bags_with_owners = Bag.query.filter(
                Bag.type == BagType.PARENT.value,
                Bag.user_id != None
            ).count()
            
            parent_bags_total = Bag.query.filter(
                Bag.type == BagType.PARENT.value
            ).count()
            
            print(f"Total parent bags: {parent_bags_total}")
            print(f"Parent bags with owners: {parent_bags_with_owners}")
            print(f"Parent bags without owners: {parent_bags_total - parent_bags_with_owners}")
            
            # Also update child bags without owners based on scan history
            print("\n--- Updating child bags ---")
            
            child_bags_without_owners = Bag.query.filter(
                Bag.type == BagType.CHILD.value,
                Bag.user_id == None
            ).all()
            
            print(f"Found {len(child_bags_without_owners)} child bags without owners")
            
            child_updated_count = 0
            
            for child_bag in child_bags_without_owners:
                # Find the first scan for this child bag
                first_scan = Scan.query.filter_by(
                    child_bag_id=child_bag.id
                ).order_by(Scan.timestamp.asc()).first()
                
                if first_scan and first_scan.user_id:
                    # Update the child bag with the user who first scanned it
                    child_bag.user_id = first_scan.user_id
                    child_updated_count += 1
                    
                    # Get user info for logging
                    user = User.query.get(first_scan.user_id)
                    if user:
                        print(f"Updated child bag {child_bag.qr_id} - owner: {user.username}")
            
            # Commit child bag updates
            db.session.commit()
            
            print(f"\nUpdated {child_updated_count} child bags with their owners")
            
            # Final statistics
            child_bags_with_owners = Bag.query.filter(
                Bag.type == BagType.CHILD.value,
                Bag.user_id != None
            ).count()
            
            child_bags_total = Bag.query.filter(
                Bag.type == BagType.CHILD.value
            ).count()
            
            print(f"Total child bags: {child_bags_total}")
            print(f"Child bags with owners: {child_bags_with_owners}")
            print(f"Child bags without owners: {child_bags_total - child_bags_with_owners}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {str(e)}")
            raise

if __name__ == "__main__":
    migrate_parent_bag_owners()
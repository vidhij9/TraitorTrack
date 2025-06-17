#!/usr/bin/env python3
"""
Database Integrity Monitor - Automated cleanup and prevention system
This script can be run periodically to maintain database integrity.
"""

import sys
import os
from datetime import datetime

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_clean import db, app
from models import Bag, Link, Scan

def cleanup_unlinked_children():
    """Remove any unlinked child bags and their scan records."""
    with app.app_context():
        # Find unlinked child bags
        unlinked_children = db.session.query(Bag).filter(
            Bag.type == 'child',
            ~Bag.id.in_(db.session.query(Link.child_bag_id).distinct())
        ).all()
        
        if not unlinked_children:
            print(f"[{datetime.now()}] No unlinked child bags found - database is clean")
            return 0
        
        print(f"[{datetime.now()}] Found {len(unlinked_children)} unlinked child bags to clean up:")
        
        deleted_count = 0
        for child in unlinked_children:
            print(f"  Removing: {child.qr_id} (ID: {child.id})")
            
            # Delete all scans for this child bag
            child_scans = Scan.query.filter_by(child_bag_id=child.id).all()
            for scan in child_scans:
                db.session.delete(scan)
            
            # Delete the child bag itself
            db.session.delete(child)
            deleted_count += 1
        
        # Commit all changes
        db.session.commit()
        print(f"[{datetime.now()}] Successfully deleted {deleted_count} unlinked child bags")
        return deleted_count

def validate_database_integrity():
    """Validate overall database integrity."""
    with app.app_context():
        # Count all bags and links
        total_bags = Bag.query.count()
        parent_bags = Bag.query.filter_by(type='parent').count()
        child_bags = Bag.query.filter_by(type='child').count()
        total_links = Link.query.count()
        linked_children = db.session.query(Link.child_bag_id).distinct().count()
        
        # Check for orphaned scans
        orphaned_scans = db.session.query(Scan).filter(
            ~Scan.child_bag_id.in_(db.session.query(Bag.id).filter_by(type='child'))
        ).count()
        
        print(f"[{datetime.now()}] Database Integrity Report:")
        print(f"  Total bags: {total_bags} (Parents: {parent_bags}, Children: {child_bags})")
        print(f"  Active links: {total_links}")
        print(f"  Linked children: {linked_children}")
        print(f"  Orphaned scans: {orphaned_scans}")
        
        # Check integrity
        unlinked_children = child_bags - linked_children
        if unlinked_children == 0 and orphaned_scans == 0:
            print(f"  Status: ✓ Database integrity is excellent")
            return True
        else:
            print(f"  Status: ⚠ Found {unlinked_children} unlinked children and {orphaned_scans} orphaned scans")
            return False

if __name__ == "__main__":
    print("=== Database Integrity Monitor ===")
    
    # First validate current state
    is_clean = validate_database_integrity()
    
    # Clean up if needed
    if not is_clean:
        deleted = cleanup_unlinked_children()
        if deleted > 0:
            print("Re-validating after cleanup...")
            validate_database_integrity()
    
    print("=== Monitor Complete ===")

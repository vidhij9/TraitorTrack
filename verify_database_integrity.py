#!/usr/bin/env python3
"""
Database integrity verification script for TraceTrack application.
This script checks for unlinked child bags and provides a health report.
"""

import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_clean import db, app
from models import Bag, Link, Scan

def verify_database_integrity():
    """Verify database integrity and report any issues."""
    with app.app_context():
        print("=== Database Integrity Check ===")
        
        # Count all bags
        total_bags = Bag.query.count()
        parent_bags = Bag.query.filter_by(type='parent').count()
        child_bags = Bag.query.filter_by(type='child').count()
        
        print(f"Total bags: {total_bags}")
        print(f"Parent bags: {parent_bags}")
        print(f"Child bags: {child_bags}")
        
        # Count links
        total_links = Link.query.count()
        linked_children = db.session.query(Link.child_bag_id).distinct().count()
        
        print(f"Active links: {total_links}")
        print(f"Linked child bags: {linked_children}")
        
        # Find unlinked child bags
        unlinked_children = db.session.query(Bag).filter(
            Bag.type == 'child',
            ~Bag.id.in_(db.session.query(Link.child_bag_id).distinct())
        ).all()
        
        if unlinked_children:
            print(f"\n⚠️  WARNING: Found {len(unlinked_children)} unlinked child bags:")
            for child in unlinked_children:
                print(f"  - {child.qr_id} (ID: {child.id})")
            return False
        else:
            print("\n✓ All child bags are properly linked to parent bags")
        
        # Check for orphaned scans
        orphaned_scans = db.session.query(Scan).filter(
            ~Scan.child_bag_id.in_(db.session.query(Bag.id).filter_by(type='child'))
        ).count()
        
        if orphaned_scans > 0:
            print(f"⚠️  WARNING: Found {orphaned_scans} orphaned scan records")
            return False
        else:
            print("✓ All scan records reference valid bags")
        
        print("\n✓ Database integrity check passed - all data is properly linked")
        return True

if __name__ == "__main__":
    print("Running database integrity verification...")
    is_healthy = verify_database_integrity()
    
    if is_healthy:
        print("\n🎉 Database is healthy and properly maintained!")
        sys.exit(0)
    else:
        print("\n❌ Database has integrity issues that need attention")
        sys.exit(1)
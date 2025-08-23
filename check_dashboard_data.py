import sys
sys.path.insert(0, '/home/runner/workspace')

from app_clean import app, db
from models import Bag, Scan, Bill
from sqlalchemy import text

with app.app_context():
    # Check actual database counts
    print("📊 DATABASE INVESTIGATION:")
    print("="*40)
    
    # Count parent bags
    parent_count = Bag.query.filter_by(type='parent').count()
    print(f"Parent bags in DB: {parent_count}")
    
    # Count child bags 
    child_count = Bag.query.filter_by(type='child').count()
    print(f"Child bags in DB: {child_count}")
    
    # Count scans
    scan_count = Scan.query.count()
    print(f"Scans in DB: {scan_count}")
    
    # Count bills
    bill_count = Bill.query.count()
    print(f"Bills in DB: {bill_count}")
    
    # Show some actual bags if they exist
    if parent_count > 0:
        print("\nSample parent bags:")
        parents = Bag.query.filter_by(type='parent').limit(3).all()
        for p in parents:
            print(f"  - {p.qr_id} (id: {p.id})")
    
    # Test the exact SQL query used by /api/stats
    print("\n📊 TESTING API SQL QUERY:")
    print("="*40)
    
    result = db.session.execute(text("""
        SELECT 
            (SELECT COUNT(*) FROM bag WHERE type = 'parent')::int as parent_count,
            (SELECT COUNT(*) FROM bag WHERE type = 'child')::int as child_count,
            (SELECT COUNT(*) FROM scan)::int as scan_count,
            (SELECT COUNT(*) FROM bill)::int as bill_count
    """)).fetchone()
    
    print(f"SQL Query Results:")
    print(f"  parent_count: {result.parent_count}")
    print(f"  child_count: {result.child_count}")
    print(f"  scan_count: {result.scan_count}")
    print(f"  bill_count: {result.bill_count}")

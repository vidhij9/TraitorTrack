#!/usr/bin/env python3
"""
Database Optimization Script
Run this script to apply database optimizations
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def apply_database_optimizations():
    """Apply database optimizations"""
    print("🗄️ Applying database optimizations...")
    
    try:
        # Import Flask app
        from app_clean import app, db
        from sqlalchemy import text
        
        with app.app_context():
            # Create performance indexes
            indexes = [
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_created_by_status ON bill (created_by_id, status)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_created_at_status ON bill (created_at, status)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_weight ON bill (total_weight_kg)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_type_status_weight ON bag (type, status, weight_kg)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_user_type_status ON bag (user_id, type, status)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_user_timestamp_type ON scan (user_id, timestamp DESC, parent_bag_id, child_bag_id)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_parent_child_created ON link (parent_bag_id, child_bag_id, created_at)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_billbag_bill_bag_created ON bill_bag (bill_id, bag_id, created_at)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_role_verified ON "user" (role, verified)",
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_user_action_timestamp ON audit_log (user_id, action, timestamp DESC)"
            ]
            
            for i, index_query in enumerate(indexes, 1):
                try:
                    print(f"Creating index {i}/{len(indexes)}...")
                    db.session.execute(text(index_query))
                    db.session.commit()
                    print(f"✅ Index {i} created successfully")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        print(f"ℹ️ Index {i} already exists")
                    else:
                        print(f"⚠️ Failed to create index {i}: {e}")
                    db.session.rollback()
            
            # Update database statistics
            print("Updating database statistics...")
            db.session.execute(text("ANALYZE"))
            db.session.commit()
            print("✅ Database statistics updated")
            
            print("✅ Database optimizations completed successfully!")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure Flask and database dependencies are installed")
    except Exception as e:
        print(f"❌ Database optimization failed: {e}")

if __name__ == "__main__":
    apply_database_optimizations()

#!/usr/bin/env python3
"""
Ultra-Scale Database Optimization Script
Optimizes database for 600,000+ bags and 100+ concurrent users
"""

import os
import sys
import time

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def optimize_database_ultra_scale():
    """Optimize database for ultra-scale performance"""
    print("🚀 Optimizing database for ultra-scale performance...")
    
    try:
        # Import Flask app
        from app_clean import app, db
        from sqlalchemy import text
        
        with app.app_context():
            # Ultra-performance indexes for 600k+ bags
            ultra_indexes = [
                # Bill ultra-performance indexes
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_ultra_performance ON bill (created_by_id, status, created_at DESC)", "bill_ultra_performance"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_weight_status ON bill (total_weight_kg, status)", "bill_weight_status"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_created_at_partition ON bill (DATE(created_at), status)", "bill_date_partition"),
                
                # Bag ultra-performance indexes for 600k+ bags
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_ultra_performance ON bag (type, status, dispatch_area, created_at DESC)", "bag_ultra_performance"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_qr_ultra ON bag (qr_id) WHERE qr_id IS NOT NULL", "bag_qr_ultra"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_user_type_ultra ON bag (user_id, type, status)", "bag_user_type_ultra"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_parent_child_ultra ON bag (parent_id, type, status)", "bag_parent_child_ultra"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_dispatch_type_ultra ON bag (dispatch_area, type, status)", "bag_dispatch_type_ultra"),
                
                # Scan ultra-performance indexes
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_ultra_performance ON scan (user_id, timestamp DESC, parent_bag_id, child_bag_id)", "scan_ultra_performance"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_date_hour_ultra ON scan (DATE(timestamp), EXTRACT(hour FROM timestamp), user_id)", "scan_date_hour_ultra"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_parent_child_ultra ON scan (parent_bag_id, child_bag_id, timestamp DESC)", "scan_parent_child_ultra"),
                
                # Link ultra-performance indexes
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_ultra_performance ON link (parent_bag_id, child_bag_id, created_at DESC)", "link_ultra_performance"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_parent_ultra ON link (parent_bag_id, created_at DESC)", "link_parent_ultra"),
                
                # BillBag ultra-performance indexes
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_billbag_ultra_performance ON bill_bag (bill_id, bag_id, created_at DESC)", "billbag_ultra_performance"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_billbag_bill_ultra ON bill_bag (bill_id, created_at DESC)", "billbag_bill_ultra"),
                
                # User ultra-performance indexes
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_ultra_performance ON "user" (role, verified, dispatch_area)", "user_ultra_performance"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_username_ultra ON "user" (username) WHERE username IS NOT NULL", "user_username_ultra"),
                
                # Audit log ultra-performance indexes
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_ultra_performance ON audit_log (user_id, action, timestamp DESC)", "audit_ultra_performance"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_entity_ultra ON audit_log (entity_type, entity_id, timestamp DESC)", "audit_entity_ultra"),
                
                # Composite indexes for complex queries
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_composite_ultra ON bag (type, status, dispatch_area, user_id, created_at DESC)", "bag_composite_ultra"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bill_composite_ultra ON bill (status, created_by_id, created_at DESC)", "bill_composite_ultra"),
                ("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scan_composite_ultra ON scan (user_id, parent_bag_id, timestamp DESC)", "scan_composite_ultra"),
            ]
            
            for i, (query, index_name) in enumerate(ultra_indexes, 1):
                try:
                    print(f"Creating ultra-performance index {i}/{len(ultra_indexes)}: {index_name}")
                    db.session.execute(text(query))
                    db.session.commit()
                    print(f"✅ Ultra-performance index created: {index_name}")
                except Exception as e:
                    db.session.rollback()
                    if "already exists" in str(e).lower():
                        print(f"ℹ️ Ultra-performance index already exists: {index_name}")
                    else:
                        print(f"⚠️ Failed to create ultra-performance index {index_name}: {e}")
            
            # Create materialized views for ultra-fast queries
            materialized_views = [
                """
                CREATE MATERIALIZED VIEW IF NOT EXISTS bill_summary_ultra AS
                SELECT 
                    b.id as bill_id,
                    b.bill_id as bill_number,
                    b.created_at,
                    b.status,
                    b.total_weight_kg,
                    b.total_child_bags,
                    u.username as creator_username,
                    u.role as creator_role,
                    u.dispatch_area as creator_dispatch_area,
                    COUNT(bb.bag_id) as linked_parent_bags,
                    CASE 
                        WHEN b.parent_bag_count > 0 THEN 
                            (COUNT(bb.bag_id) * 100 / b.parent_bag_count)
                        ELSE 0 
                    END as completion_percentage,
                    AVG(pb.weight_kg) as avg_parent_weight
                FROM bill b
                LEFT JOIN "user" u ON b.created_by_id = u.id
                LEFT JOIN bill_bag bb ON b.id = bb.bill_id
                LEFT JOIN bag pb ON bb.bag_id = pb.id
                GROUP BY b.id, b.bill_id, b.created_at, b.status, b.total_weight_kg, 
                         b.total_child_bags, u.username, u.role, u.dispatch_area, b.parent_bag_count
                """,
                
                """
                CREATE MATERIALIZED VIEW IF NOT EXISTS bag_summary_ultra AS
                SELECT 
                    b.id,
                    b.qr_id,
                    b.type,
                    b.status,
                    b.weight_kg,
                    b.dispatch_area,
                    b.created_at,
                    u.username as owner_username,
                    u.role as owner_role,
                    COUNT(l.child_bag_id) as child_count,
                    COUNT(s.id) as scan_count,
                    MAX(s.timestamp) as last_scan
                FROM bag b
                LEFT JOIN "user" u ON b.user_id = u.id
                LEFT JOIN link l ON b.id = l.parent_bag_id
                LEFT JOIN scan s ON b.id = s.parent_bag_id OR b.id = s.child_bag_id
                GROUP BY b.id, b.qr_id, b.type, b.status, b.weight_kg, 
                         b.dispatch_area, b.created_at, u.username, u.role
                """,
                
                """
                CREATE MATERIALIZED VIEW IF NOT EXISTS user_activity_ultra AS
                SELECT 
                    u.id,
                    u.username,
                    u.role,
                    u.dispatch_area,
                    COUNT(s.id) as total_scans,
                    COUNT(DISTINCT DATE(s.timestamp)) as active_days,
                    MAX(s.timestamp) as last_activity,
                    COUNT(DISTINCT b.id) as bills_created,
                    COUNT(DISTINCT bag.id) as bags_owned
                FROM "user" u
                LEFT JOIN scan s ON u.id = s.user_id
                LEFT JOIN bill b ON u.id = b.created_by_id
                LEFT JOIN bag ON u.id = bag.user_id
                GROUP BY u.id, u.username, u.role, u.dispatch_area
                """
            ]
            
            for i, view_sql in enumerate(materialized_views, 1):
                try:
                    print(f"Creating materialized view {i}/{len(materialized_views)}...")
                    db.session.execute(text(view_sql))
                    db.session.commit()
                    print(f"✅ Materialized view {i} created successfully")
                except Exception as e:
                    db.session.rollback()
                    print(f"❌ Failed to create materialized view {i}: {e}")
            
            # Update database statistics for ultra-scale
            print("Updating database statistics for ultra-scale...")
            db.session.execute(text("ANALYZE"))
            db.session.commit()
            
            # Optimize connection pool for 100+ concurrent users
            engine = db.engine
            engine.pool.size = 50  # Increased for high concurrency
            engine.pool.max_overflow = 100  # Allow overflow for peak loads
            engine.pool.pool_timeout = 30
            engine.pool.pool_recycle = 1800  # 30 minutes
            engine.pool.pool_pre_ping = True
            
            print(f"✅ Ultra-scale database optimization completed")
            print(f"   Connection pool: {engine.pool.size} + {engine.pool.max_overflow} overflow")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure Flask and database dependencies are installed")
    except Exception as e:
        print(f"❌ Database optimization failed: {e}")

if __name__ == "__main__":
    optimize_database_ultra_scale()

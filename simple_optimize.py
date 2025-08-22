"""
Simple Database Optimization for TraceTrack
"""
import os
import psycopg2
from psycopg2 import sql

DATABASE_URL = os.environ.get('DATABASE_URL')

def create_indexes():
    """Create essential indexes for performance"""
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_bag_qr_id ON bag(qr_id)",
        "CREATE INDEX IF NOT EXISTS idx_bag_type ON bag(type)",
        "CREATE INDEX IF NOT EXISTS idx_bag_status ON bag(status)",
        "CREATE INDEX IF NOT EXISTS idx_bag_parent_id ON bag(parent_bag_id)",
        "CREATE INDEX IF NOT EXISTS idx_bill_bill_id ON bill(bill_id)",
        "CREATE INDEX IF NOT EXISTS idx_bill_completed ON bill(is_completed)",
        "CREATE INDEX IF NOT EXISTS idx_bill_created_by ON bill(created_by_id)",
        "CREATE INDEX IF NOT EXISTS idx_billbag_bill_id ON bill_bag(bill_id)",
        "CREATE INDEX IF NOT EXISTS idx_billbag_bag_id ON bill_bag(bag_id)",
        "CREATE INDEX IF NOT EXISTS idx_scan_user_id ON scan(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_scan_timestamp ON scan(timestamp DESC)",
        "CREATE INDEX IF NOT EXISTS idx_user_username ON \"user\"(username)",
        "CREATE INDEX IF NOT EXISTS idx_user_role ON \"user\"(role)"
    ]
    
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True  # Required for CREATE INDEX
    cur = conn.cursor()
    
    print("Creating performance indexes...")
    for idx_sql in indexes:
        try:
            cur.execute(idx_sql)
            print(f"✅ Created: {idx_sql.split('idx_')[1].split(' ')[0]}")
        except Exception as e:
            if "already exists" in str(e):
                print(f"⚠️  Already exists: {idx_sql.split('idx_')[1].split(' ')[0]}")
            else:
                print(f"❌ Error: {e}")
    
    # Analyze tables
    tables = ['bag', 'bill', 'bill_bag', 'scan', '"user"']
    print("\nAnalyzing tables...")
    for table in tables:
        try:
            cur.execute(f"ANALYZE {table}")
            print(f"✅ Analyzed {table}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    cur.close()
    conn.close()
    print("\n✅ Optimization complete!")

if __name__ == '__main__':
    create_indexes()
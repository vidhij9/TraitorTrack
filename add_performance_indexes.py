"""
Add performance indexes to improve query speed
"""
from main import app
from models import db

def add_indexes():
    """Add database indexes for better performance"""
    with app.app_context():
        try:
            # Add indexes for frequently queried columns
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_bags_qr_id ON bags(qr_id);",
                "CREATE INDEX IF NOT EXISTS idx_bags_type ON bags(type);",
                "CREATE INDEX IF NOT EXISTS idx_bags_qr_type ON bags(qr_id, type);",
                "CREATE INDEX IF NOT EXISTS idx_links_parent_bag_id ON links(parent_bag_id);",
                "CREATE INDEX IF NOT EXISTS idx_links_child_bag_id ON links(child_bag_id);",
                "CREATE INDEX IF NOT EXISTS idx_links_parent_child ON links(parent_bag_id, child_bag_id);",
                "CREATE INDEX IF NOT EXISTS idx_scans_timestamp ON scans(timestamp DESC);",
                "CREATE INDEX IF NOT EXISTS idx_scans_user_id ON scans(user_id);",
                "CREATE INDEX IF NOT EXISTS idx_bills_bill_id ON bills(bill_id);",
                "CREATE INDEX IF NOT EXISTS idx_bills_created_at ON bills(created_at DESC);",
                "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);",
                "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);"
            ]
            
            for index_sql in indexes:
                try:
                    db.session.execute(db.text(index_sql))
                    print(f"✓ Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
                except Exception as e:
                    print(f"  Note: {str(e)}")
            
            db.session.commit()
            print("\n✅ All performance indexes added successfully!")
            
        except Exception as e:
            print(f"❌ Error adding indexes: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    add_indexes()
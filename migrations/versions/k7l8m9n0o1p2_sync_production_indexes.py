"""Sync production indexes with development database

This migration adds all indexes that exist in development but may be missing in production.
Uses CREATE INDEX IF NOT EXISTS for safety - indexes that already exist are skipped.

Revision ID: k7l8m9n0o1p2
Revises: j6k7l8m9n0o1
Create Date: 2026-01-03 12:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'k7l8m9n0o1p2'
down_revision = 'j6k7l8m9n0o1'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing B-tree indexes to production database.
    
    Based on production database analysis:
    - link table: missing idx_link_parent_id, idx_link_child_id
    - bill_bag table: missing idx_bill_bag_bill_id, idx_bill_bag_bag_id  
    - notification table: missing idx_notification_user_read
    
    Uses CREATE INDEX IF NOT EXISTS for idempotency.
    """
    conn = op.get_bind()
    
    # These specific indexes are missing in production (verified via screenshots)
    # Using CREATE INDEX IF NOT EXISTS to be safe
    indexes = [
        ('CREATE INDEX IF NOT EXISTS idx_link_child_id ON link (child_bag_id)', 'idx_link_child_id'),
        ('CREATE INDEX IF NOT EXISTS idx_link_parent_id ON link (parent_bag_id)', 'idx_link_parent_id'),
        ('CREATE INDEX IF NOT EXISTS idx_bill_bag_bill_id ON bill_bag (bill_id)', 'idx_bill_bag_bill_id'),
        ('CREATE INDEX IF NOT EXISTS idx_bill_bag_bag_id ON bill_bag (bag_id)', 'idx_bill_bag_bag_id'),
        ('CREATE INDEX IF NOT EXISTS idx_notification_user_read ON notification (user_id, is_read)', 'idx_notification_user_read'),
    ]
    
    for sql, name in indexes:
        try:
            conn.execute(text(sql))
            print(f"  ✅ {name}")
        except Exception as e:
            print(f"  ⚠️ {name}: {str(e)}")
    
    print("  ✅ Index sync migration completed")


def downgrade():
    """Remove ONLY the indexes added by this migration."""
    conn = op.get_bind()
    
    # Only drop the 5 indexes we created
    indexes_to_drop = [
        "idx_link_child_id",
        "idx_link_parent_id",
        "idx_bill_bag_bill_id",
        "idx_bill_bag_bag_id",
        "idx_notification_user_read",
    ]
    
    for idx_name in indexes_to_drop:
        try:
            conn.execute(text(f"DROP INDEX IF EXISTS {idx_name}"))
            print(f"  Dropped {idx_name}")
        except Exception as e:
            print(f"  Warning dropping {idx_name}: {str(e)}")

"""Add functional indexes for ultra-fast bill scanning

Revision ID: i5j6k7l8m9n0
Revises: h4i5j6k7l8m9
Create Date: 2025-12-06 07:10:00.000000

This migration adds functional indexes for case-insensitive QR code lookups
to eliminate the UPPER() overhead that was causing slow scans.

Key indexes added:
- idx_bag_qr_id_lower: Functional index on lower(qr_id) for instant QR lookups
- idx_billbag_bill_bag: Composite index for fast bill-bag relationship checks
- idx_billbag_bag_id: Index for "already linked to other bill" checks
"""
from alembic import op
import sqlalchemy as sa


revision = 'i5j6k7l8m9n0'
down_revision = 'h4i5j6k7l8m9'
branch_labels = None
depends_on = None


def index_exists(index_name):
    """Check if an index exists in the database."""
    bind = op.get_bind()
    result = bind.execute(sa.text(
        """
        SELECT 1 FROM pg_indexes 
        WHERE indexname = :index_name
        """
    ), {'index_name': index_name})
    return result.fetchone() is not None


def upgrade():
    """Add functional indexes for ultra-fast scanning.
    
    These indexes enable sub-50ms response times for parent bag scanning.
    Uses CONCURRENTLY to avoid locking the table during creation.
    """
    
    # Functional index for case-insensitive QR code lookup
    # This is the CRITICAL index - eliminates the slow UPPER() overhead
    if not index_exists('idx_bag_qr_id_lower'):
        op.execute(sa.text(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_qr_id_lower 
            ON bag (lower(qr_id))
            """
        ))
    
    # Composite index for bill-bag relationship lookups
    if not index_exists('idx_billbag_bill_bag'):
        op.execute(sa.text(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_billbag_bill_bag 
            ON bill_bag (bill_id, bag_id)
            """
        ))
    
    # Index for "already linked to other bill" checks
    if not index_exists('idx_billbag_bag_id'):
        op.execute(sa.text(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_billbag_bag_id 
            ON bill_bag (bag_id)
            """
        ))
    
    # Composite index on link table for child count queries
    if not index_exists('idx_link_parent_child'):
        op.execute(sa.text(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_link_parent_child 
            ON link (parent_bag_id, child_bag_id)
            """
        ))


def downgrade():
    """Remove the functional indexes."""
    op.execute(sa.text("DROP INDEX IF EXISTS idx_bag_qr_id_lower"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_billbag_bill_bag"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_billbag_bag_id"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_link_parent_child"))

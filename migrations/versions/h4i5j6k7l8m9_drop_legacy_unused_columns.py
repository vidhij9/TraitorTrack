"""Drop legacy unused columns from scan and bag tables

Revision ID: h4i5j6k7l8m9
Revises: g3h4i5j6k7l8
Create Date: 2025-12-02 16:15:00.000000

SAFE MIGRATION: Only drops columns, does NOT delete any rows.
All existing row data in other columns is fully preserved.

Drops unused legacy columns that exist in production but not in code:

scan table (8 columns):
- bag_id: Redundant - we use parent_bag_id and child_bag_id instead
- scan_type: The relationship already defines scan type
- scan_location: Location tracking removed from system
- device_info: Not used in current workflow
- scan_duration_ms: Performance metric not utilized
- dispatch_area: Can be looked up via bag/user relationships
- location: Duplicate of scan_location
- duration_seconds: Duplicate of scan_duration_ms

bag table (4 columns):
- created_by: Redundant with user_id column
- current_location: Location tracking removed
- qr_code: Duplicate of qr_id column
- bag_type: Duplicate of type column
"""
from alembic import op
import sqlalchemy as sa


revision = 'h4i5j6k7l8m9'
down_revision = 'g3h4i5j6k7l8'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    """Check if a column exists in the specified table."""
    bind = op.get_bind()
    result = bind.execute(sa.text(
        """
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = :table AND column_name = :column
        """
    ), {'table': table_name, 'column': column_name})
    return result.fetchone() is not None


def upgrade():
    """Drop unused legacy columns from scan and bag tables.
    
    SAFE: Only removes columns, all row data in other columns is preserved.
    Each column is checked for existence before dropping (idempotent).
    """
    
    # ========================================
    # DROP UNUSED COLUMNS FROM 'scan' TABLE
    # ========================================
    scan_columns_to_drop = [
        'bag_id',           # Redundant - we use parent_bag_id and child_bag_id
        'scan_type',        # Relationship already defines type
        'scan_location',    # Location tracking removed
        'device_info',      # Not used in current workflow
        'scan_duration_ms', # Not utilized
        'dispatch_area',    # Lookup via relationships instead
        'location',         # Duplicate of scan_location
        'duration_seconds'  # Duplicate of scan_duration_ms
    ]
    
    for col in scan_columns_to_drop:
        if column_exists('scan', col):
            op.drop_column('scan', col)
    
    # ========================================
    # DROP UNUSED COLUMNS FROM 'bag' TABLE
    # ========================================
    bag_columns_to_drop = [
        'created_by',       # Redundant with user_id
        'current_location', # Location tracking removed
        'qr_code',          # Duplicate of qr_id
        'bag_type'          # Duplicate of type column
    ]
    
    for col in bag_columns_to_drop:
        if column_exists('bag', col):
            op.drop_column('bag', col)


def downgrade():
    """Re-add the legacy columns if needed (all nullable to avoid data issues).
    
    Note: Original data cannot be restored - columns will be empty after downgrade.
    """
    
    # Re-add bag columns (all nullable)
    if not column_exists('bag', 'bag_type'):
        op.add_column('bag', sa.Column('bag_type', sa.String(50), nullable=True))
    if not column_exists('bag', 'qr_code'):
        op.add_column('bag', sa.Column('qr_code', sa.String(100), nullable=True))
    if not column_exists('bag', 'current_location'):
        op.add_column('bag', sa.Column('current_location', sa.String(200), nullable=True))
    if not column_exists('bag', 'created_by'):
        op.add_column('bag', sa.Column('created_by', sa.String(100), nullable=True))
    
    # Re-add scan columns (all nullable)
    if not column_exists('scan', 'duration_seconds'):
        op.add_column('scan', sa.Column('duration_seconds', sa.Float, nullable=True))
    if not column_exists('scan', 'location'):
        op.add_column('scan', sa.Column('location', sa.String(200), nullable=True))
    if not column_exists('scan', 'dispatch_area'):
        op.add_column('scan', sa.Column('dispatch_area', sa.String(100), nullable=True))
    if not column_exists('scan', 'scan_duration_ms'):
        op.add_column('scan', sa.Column('scan_duration_ms', sa.Integer, nullable=True))
    if not column_exists('scan', 'device_info'):
        op.add_column('scan', sa.Column('device_info', sa.String(500), nullable=True))
    if not column_exists('scan', 'scan_location'):
        op.add_column('scan', sa.Column('scan_location', sa.String(200), nullable=True))
    if not column_exists('scan', 'scan_type'):
        op.add_column('scan', sa.Column('scan_type', sa.String(50), nullable=True))
    if not column_exists('scan', 'bag_id'):
        op.add_column('scan', sa.Column('bag_id', sa.Integer, nullable=True))

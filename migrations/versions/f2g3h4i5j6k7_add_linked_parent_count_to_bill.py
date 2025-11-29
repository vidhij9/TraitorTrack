"""Add linked_parent_count column to bill for capacity tracking

Revision ID: f2g3h4i5j6k7
Revises: e1f2a3b4c5d6
Create Date: 2025-11-29 12:50:00.000000

Adds capacity tracking for bills:
- linked_parent_count: Tracks actual number of parent bags linked (vs capacity target)
- Auto-close: Bills automatically close when linked_parent_count >= parent_bag_count

Weight calculation:
- Each child bag = 1kg
- total_weight_kg = total_child_bags * 1kg
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = 'f2g3h4i5j6k7'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    """Check if a column already exists in the table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(index_name):
    """Check if an index already exists in the database."""
    bind = op.get_bind()
    result = bind.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = :name"
    ), {'name': index_name})
    return result.fetchone() is not None


def constraint_exists(constraint_name, table_name):
    """Check if a constraint already exists."""
    bind = op.get_bind()
    inspector = inspect(bind)
    check_constraints = inspector.get_check_constraints(table_name)
    return any(c['name'] == constraint_name for c in check_constraints)


def upgrade():
    if not column_exists('bill', 'linked_parent_count'):
        op.add_column('bill', sa.Column('linked_parent_count', sa.Integer(), nullable=True, server_default='0'))
        
        op.execute("""
            UPDATE bill b SET linked_parent_count = (
                SELECT COUNT(*) FROM bill_bag bb WHERE bb.bill_id = b.id
            )
        """)
        
        op.alter_column('bill', 'linked_parent_count', nullable=False, server_default='0')
    
    if not index_exists('idx_bill_linked_count'):
        op.create_index('idx_bill_linked_count', 'bill', ['linked_parent_count'])
    
    if not constraint_exists('check_bill_linked_count_non_negative', 'bill'):
        op.create_check_constraint(
            'check_bill_linked_count_non_negative',
            'bill',
            'linked_parent_count >= 0'
        )


def downgrade():
    if constraint_exists('check_bill_linked_count_non_negative', 'bill'):
        op.drop_constraint('check_bill_linked_count_non_negative', 'bill', type_='check')
    
    if index_exists('idx_bill_linked_count'):
        op.drop_index('idx_bill_linked_count', table_name='bill')
    
    if column_exists('bill', 'linked_parent_count'):
        op.drop_column('bill', 'linked_parent_count')

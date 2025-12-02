"""Add all precomputed columns to bill for capacity and weight tracking

Revision ID: f2g3h4i5j6k7
Revises: e1f2a3b4c5d6
Create Date: 2025-11-29 12:50:00.000000

Adds capacity and weight tracking for bills:
- linked_parent_count: Tracks actual number of parent bags linked (vs capacity target)
- total_child_bags: Total number of child bags linked to all parent bags in bill
- total_weight_kg: Actual weight = total_child_bags * 1kg  
- expected_weight_kg: Expected weight based on linked parent bag types

Weight calculation:
- Each child bag = 1kg
- SB bags: 30kg expected weight
- Mxxx-xx bags: 15kg expected weight
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
    # Add linked_parent_count column
    if not column_exists('bill', 'linked_parent_count'):
        op.add_column('bill', sa.Column('linked_parent_count', sa.Integer(), nullable=True, server_default='0'))
        
        # Backfill linked_parent_count from bill_bag table
        op.execute("""
            UPDATE bill b SET linked_parent_count = (
                SELECT COUNT(*) FROM bill_bag bb WHERE bb.bill_id = b.id
            )
        """)
        
        op.alter_column('bill', 'linked_parent_count', nullable=False, server_default='0')
    
    # Add total_child_bags column
    if not column_exists('bill', 'total_child_bags'):
        op.add_column('bill', sa.Column('total_child_bags', sa.Integer(), nullable=True, server_default='0'))
        
        # Backfill total_child_bags: count child bags linked to parent bags in each bill
        op.execute("""
            UPDATE bill b SET total_child_bags = COALESCE((
                SELECT COUNT(DISTINCT l.child_bag_id)
                FROM bill_bag bb
                JOIN bag parent ON bb.bag_id = parent.id AND parent.type = 'parent'
                JOIN link l ON parent.id = l.parent_bag_id
                WHERE bb.bill_id = b.id
            ), 0)
        """)
        
        op.alter_column('bill', 'total_child_bags', nullable=False, server_default='0')
    
    # Add total_weight_kg column (actual weight = child_count * 1kg)
    if not column_exists('bill', 'total_weight_kg'):
        op.add_column('bill', sa.Column('total_weight_kg', sa.Float(), nullable=True, server_default='0.0'))
        
        # Backfill total_weight_kg from total_child_bags (1kg per child bag)
        op.execute("""
            UPDATE bill SET total_weight_kg = COALESCE(total_child_bags, 0) * 1.0
        """)
        
        op.alter_column('bill', 'total_weight_kg', nullable=False, server_default='0.0')
    
    # Add expected_weight_kg column
    if not column_exists('bill', 'expected_weight_kg'):
        op.add_column('bill', sa.Column('expected_weight_kg', sa.Float(), nullable=True, server_default='0.0'))
        
        # Backfill expected_weight_kg based on parent bag types
        # SB bags = 30kg, Mxxx-xx bags = 15kg, default = 30kg
        op.execute("""
            UPDATE bill b SET expected_weight_kg = COALESCE((
                SELECT SUM(
                    CASE 
                        WHEN parent.qr_id ~ '^M[0-9]{3,4}-[0-9]+' THEN 15.0
                        ELSE 30.0
                    END
                )
                FROM bill_bag bb
                JOIN bag parent ON bb.bag_id = parent.id AND parent.type = 'parent'
                WHERE bb.bill_id = b.id
            ), 0.0)
        """)
        
        op.alter_column('bill', 'expected_weight_kg', nullable=False, server_default='0.0')
    
    # Create index for linked_parent_count
    if not index_exists('idx_bill_linked_count'):
        op.create_index('idx_bill_linked_count', 'bill', ['linked_parent_count'])
    
    # Create CHECK constraints for non-negative values
    if not constraint_exists('check_bill_linked_count_non_negative', 'bill'):
        op.create_check_constraint(
            'check_bill_linked_count_non_negative',
            'bill',
            'linked_parent_count >= 0'
        )
    
    if not constraint_exists('check_bill_total_weight_non_negative', 'bill'):
        op.create_check_constraint(
            'check_bill_total_weight_non_negative',
            'bill',
            'total_weight_kg >= 0'
        )
    
    if not constraint_exists('check_bill_expected_weight_non_negative', 'bill'):
        op.create_check_constraint(
            'check_bill_expected_weight_non_negative',
            'bill',
            'expected_weight_kg >= 0'
        )


def downgrade():
    # Remove CHECK constraints
    if constraint_exists('check_bill_expected_weight_non_negative', 'bill'):
        op.drop_constraint('check_bill_expected_weight_non_negative', 'bill', type_='check')
    
    if constraint_exists('check_bill_total_weight_non_negative', 'bill'):
        op.drop_constraint('check_bill_total_weight_non_negative', 'bill', type_='check')
    
    if constraint_exists('check_bill_linked_count_non_negative', 'bill'):
        op.drop_constraint('check_bill_linked_count_non_negative', 'bill', type_='check')
    
    # Remove index
    if index_exists('idx_bill_linked_count'):
        op.drop_index('idx_bill_linked_count', table_name='bill')
    
    # Remove columns
    if column_exists('bill', 'expected_weight_kg'):
        op.drop_column('bill', 'expected_weight_kg')
    
    if column_exists('bill', 'total_weight_kg'):
        op.drop_column('bill', 'total_weight_kg')
    
    if column_exists('bill', 'total_child_bags'):
        op.drop_column('bill', 'total_child_bags')
    
    if column_exists('bill', 'linked_parent_count'):
        op.drop_column('bill', 'linked_parent_count')

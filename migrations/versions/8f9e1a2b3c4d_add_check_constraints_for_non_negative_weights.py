"""Add CHECK constraints for non-negative weights

Revision ID: 8f9e1a2b3c4d
Revises: a1b2c3d4e5f6
Create Date: 2025-11-11 06:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '8f9e1a2b3c4d'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def constraint_exists(constraint_name, table_name):
    """Check if a constraint already exists."""
    bind = op.get_bind()
    inspector = inspect(bind)
    check_constraints = inspector.get_check_constraints(table_name)
    return any(c['name'] == constraint_name for c in check_constraints)


def column_exists(table, column):
    """Check if a column exists in a table"""
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = :table AND column_name = :column AND table_schema = 'public'
    """), {"table": table, "column": column})
    return result.fetchone() is not None


def upgrade():
    if column_exists('bag', 'weight_kg') and not constraint_exists('check_bag_weight_non_negative', 'bag'):
        op.create_check_constraint(
            'check_bag_weight_non_negative',
            'bag',
            'weight_kg >= 0'
        )
        print("Created check_bag_weight_non_negative constraint")
    else:
        print("check_bag_weight_non_negative: already exists or column missing")
    
    if column_exists('bill', 'total_weight_kg') and not constraint_exists('check_bill_total_weight_non_negative', 'bill'):
        op.create_check_constraint(
            'check_bill_total_weight_non_negative',
            'bill',
            'total_weight_kg >= 0'
        )
        print("Created check_bill_total_weight_non_negative constraint")
    else:
        print("check_bill_total_weight_non_negative: already exists or column missing")
    
    if column_exists('bill', 'expected_weight_kg') and not constraint_exists('check_bill_expected_weight_non_negative', 'bill'):
        op.create_check_constraint(
            'check_bill_expected_weight_non_negative',
            'bill',
            'expected_weight_kg >= 0'
        )
        print("Created check_bill_expected_weight_non_negative constraint")
    else:
        print("check_bill_expected_weight_non_negative: already exists or column missing")


def downgrade():
    if constraint_exists('check_bill_expected_weight_non_negative', 'bill'):
        op.drop_constraint('check_bill_expected_weight_non_negative', 'bill', type_='check')
    if constraint_exists('check_bill_total_weight_non_negative', 'bill'):
        op.drop_constraint('check_bill_total_weight_non_negative', 'bill', type_='check')
    if constraint_exists('check_bag_weight_non_negative', 'bag'):
        op.drop_constraint('check_bag_weight_non_negative', 'bag', type_='check')

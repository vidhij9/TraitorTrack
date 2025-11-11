"""Add CHECK constraints for non-negative weights

Revision ID: 8f9e1a2b3c4d
Revises: a1b2c3d4e5f6
Create Date: 2025-11-11 06:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8f9e1a2b3c4d'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Add CHECK constraint to bag table for non-negative weight
    op.create_check_constraint(
        'check_bag_weight_non_negative',
        'bag',
        'weight_kg >= 0'
    )
    
    # Add CHECK constraints to bill table for non-negative weights
    op.create_check_constraint(
        'check_bill_total_weight_non_negative',
        'bill',
        'total_weight_kg >= 0'
    )
    
    op.create_check_constraint(
        'check_bill_expected_weight_non_negative',
        'bill',
        'expected_weight_kg >= 0'
    )


def downgrade():
    # Remove CHECK constraints in reverse order
    op.drop_constraint('check_bill_expected_weight_non_negative', 'bill', type_='check')
    op.drop_constraint('check_bill_total_weight_non_negative', 'bill', type_='check')
    op.drop_constraint('check_bag_weight_non_negative', 'bag', type_='check')

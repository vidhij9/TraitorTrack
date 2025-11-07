"""Add account lockout fields to User model

Revision ID: a1b2c3d4e5f6
Revises: 6830e8e892ce
Create Date: 2025-11-07 08:27:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '6830e8e892ce'
branch_labels = None
depends_on = None


def upgrade():
    # Add account lockout fields to user table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('failed_login_attempts', sa.Integer(), nullable=True, server_default='0'))
        batch_op.add_column(sa.Column('locked_until', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('last_failed_login', sa.DateTime(), nullable=True))


def downgrade():
    # Remove account lockout fields from user table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('last_failed_login')
        batch_op.drop_column('locked_until')
        batch_op.drop_column('failed_login_attempts')

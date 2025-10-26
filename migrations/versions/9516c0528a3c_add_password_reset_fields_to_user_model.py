"""Add password reset fields to User model

Revision ID: 9516c0528a3c
Revises: bc112eaa12f2
Create Date: 2025-10-26 07:13:19.155315

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9516c0528a3c'
down_revision = 'bc112eaa12f2'
branch_labels = None
depends_on = None


def upgrade():
    # Add password reset fields to user table ONLY
    # NO table drops, NO index changes - just add new columns
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('password_reset_token', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('password_reset_token_expires', sa.DateTime(), nullable=True))


def downgrade():
    # Remove password reset fields from user table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('password_reset_token_expires')
        batch_op.drop_column('password_reset_token')

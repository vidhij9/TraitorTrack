"""Add two-factor authentication fields to User model

Revision ID: 6830e8e892ce
Revises: 9516c0528a3c
Create Date: 2025-10-26 10:06:41.664599

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '6830e8e892ce'
down_revision = '9516c0528a3c'
branch_labels = None
depends_on = None


def column_exists(table, column):
    """Check if a column exists in a table"""
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = :table AND column_name = :column AND table_schema = 'public'
    """), {"table": table, "column": column})
    return result.fetchone() is not None


def table_exists(table):
    """Check if a table exists"""
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = :table AND table_schema = 'public'
    """), {"table": table})
    return result.fetchone() is not None


def upgrade():
    if table_exists('statistics_cache'):
        print("Dropping statistics_cache table...")
        op.drop_table('statistics_cache')
    else:
        print("statistics_cache table doesn't exist (already dropped or never created)")
    
    if not column_exists('user', 'totp_secret'):
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.add_column(sa.Column('totp_secret', sa.String(length=32), nullable=True))
        print("Added totp_secret column")
    else:
        print("totp_secret column already exists")
    
    if not column_exists('user', 'two_fa_enabled'):
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.add_column(sa.Column('two_fa_enabled', sa.Boolean(), nullable=True))
        print("Added two_fa_enabled column")
    else:
        print("two_fa_enabled column already exists")


def downgrade():
    if column_exists('user', 'two_fa_enabled'):
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.drop_column('two_fa_enabled')
    
    if column_exists('user', 'totp_secret'):
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.drop_column('totp_secret')
    
    if not table_exists('statistics_cache'):
        op.create_table('statistics_cache',
            sa.Column('id', sa.INTEGER(), server_default=sa.text('1'), autoincrement=False, nullable=False),
            sa.Column('total_bags', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=True),
            sa.Column('parent_bags', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=True),
            sa.Column('child_bags', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=True),
            sa.Column('total_scans', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=True),
            sa.Column('total_bills', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=True),
            sa.Column('total_users', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=True),
            sa.Column('last_updated', postgresql.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), autoincrement=False, nullable=True),
            sa.CheckConstraint('id = 1', name=op.f('single_row')),
            sa.PrimaryKeyConstraint('id', name=op.f('statistics_cache_pkey'))
        )

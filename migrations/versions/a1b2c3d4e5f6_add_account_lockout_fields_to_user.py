"""Add account lockout fields to User model

Revision ID: a1b2c3d4e5f6
Revises: 6830e8e892ce
Create Date: 2025-11-07 08:27:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = '6830e8e892ce'
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


def upgrade():
    if not column_exists('user', 'failed_login_attempts'):
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.add_column(sa.Column('failed_login_attempts', sa.Integer(), nullable=True, server_default='0'))
        print("Added failed_login_attempts column")
    else:
        print("failed_login_attempts column already exists")
    
    if not column_exists('user', 'locked_until'):
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.add_column(sa.Column('locked_until', sa.DateTime(), nullable=True))
        print("Added locked_until column")
    else:
        print("locked_until column already exists")
    
    if not column_exists('user', 'last_failed_login'):
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.add_column(sa.Column('last_failed_login', sa.DateTime(), nullable=True))
        print("Added last_failed_login column")
    else:
        print("last_failed_login column already exists")


def downgrade():
    if column_exists('user', 'last_failed_login'):
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.drop_column('last_failed_login')
    
    if column_exists('user', 'locked_until'):
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.drop_column('locked_until')
    
    if column_exists('user', 'failed_login_attempts'):
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.drop_column('failed_login_attempts')

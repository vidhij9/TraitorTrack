"""Add password reset fields to User model

Revision ID: 9516c0528a3c
Revises: bc112eaa12f2
Create Date: 2025-10-26 07:13:19.155315

"""
from alembic import op
import sqlalchemy as sa

revision = '9516c0528a3c'
down_revision = 'bc112eaa12f2'
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
    if not column_exists('user', 'password_reset_token'):
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.add_column(sa.Column('password_reset_token', sa.String(length=100), nullable=True))
        print("Added password_reset_token column")
    else:
        print("password_reset_token column already exists")
    
    if not column_exists('user', 'password_reset_token_expires'):
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.add_column(sa.Column('password_reset_token_expires', sa.DateTime(), nullable=True))
        print("Added password_reset_token_expires column")
    else:
        print("password_reset_token_expires column already exists")


def downgrade():
    if column_exists('user', 'password_reset_token_expires'):
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.drop_column('password_reset_token_expires')
    
    if column_exists('user', 'password_reset_token'):
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.drop_column('password_reset_token')

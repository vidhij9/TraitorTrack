"""Sync audit_log and notification schema with production

Revision ID: d54b4a63f31c
Revises: 8f9e1a2b3c4d
Create Date: 2025-11-19 12:50:46.895914

This migration safely synchronizes the database schema to match models.py.
It handles both development (where columns/tables don't exist) and production
(where they were added manually via SQL).

Changes:
1. Add before_state, after_state, request_id columns to audit_log table
2. Create notification table if it doesn't exist
3. Add necessary indexes

The migration uses conditional DDL to safely add columns/tables only if they don't exist,
preventing errors when running on production database.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'd54b4a63f31c'
down_revision = '8f9e1a2b3c4d'
branch_labels = None
depends_on = None


def upgrade():
    """
    Safely add audit_log columns and notification table.
    Uses conditional DDL to prevent errors if objects already exist.
    """
    conn = op.get_bind()
    
    # ================================================================
    # 1. Add audit_log columns if they don't exist
    # ================================================================
    print("Checking audit_log table schema...")
    
    # Check and add before_state column
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name='audit_log' AND column_name='before_state'
    """))
    if not result.fetchone():
        print("  Adding before_state column to audit_log...")
        op.add_column('audit_log', sa.Column('before_state', sa.Text(), nullable=True))
    else:
        print("  before_state column already exists")
    
    # Check and add after_state column
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name='audit_log' AND column_name='after_state'
    """))
    if not result.fetchone():
        print("  Adding after_state column to audit_log...")
        op.add_column('audit_log', sa.Column('after_state', sa.Text(), nullable=True))
    else:
        print("  after_state column already exists")
    
    # Check and add request_id column
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name='audit_log' AND column_name='request_id'
    """))
    if not result.fetchone():
        print("  Adding request_id column to audit_log...")
        op.add_column('audit_log', sa.Column('request_id', sa.String(length=36), nullable=True))
    else:
        print("  request_id column already exists")
    
    # Add index on request_id if it doesn't exist
    result = conn.execute(text("""
        SELECT indexname FROM pg_indexes 
        WHERE tablename='audit_log' AND indexname='idx_audit_request_id'
    """))
    if not result.fetchone():
        print("  Creating idx_audit_request_id index...")
        op.create_index('idx_audit_request_id', 'audit_log', ['request_id'], unique=False)
    else:
        print("  idx_audit_request_id index already exists")
    
    # ================================================================
    # 2. Create notification table if it doesn't exist
    # ================================================================
    print("Checking notification table...")
    
    result = conn.execute(text("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_name='notification'
    """))
    if not result.fetchone():
        print("  Creating notification table...")
        op.create_table('notification',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('notification_type', sa.String(length=20), server_default='info', nullable=True),
            sa.Column('priority', sa.Integer(), server_default='0', nullable=True),
            sa.Column('is_read', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('link', sa.String(length=500), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('read_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        )
        
        # Create notification indexes
        print("  Creating notification indexes...")
        op.create_index('idx_notification_user', 'notification', ['user_id'], unique=False)
        op.create_index('idx_notification_user_read', 'notification', ['user_id', 'is_read'], unique=False)
        op.create_index('idx_notification_user_created', 'notification', ['user_id', 'created_at'], unique=False)
        op.create_index('idx_notification_created', 'notification', ['created_at'], unique=False)
    else:
        print("  notification table already exists")
    
    print("✅ Migration completed successfully")


def downgrade():
    """
    Downgrade is NOT SUPPORTED for this migration.
    
    This migration adds critical audit logging and notification infrastructure
    that may contain production data. Dropping these columns/tables would cause
    irreversible data loss.
    
    If you absolutely must downgrade:
    1. Backup your database
    2. Manually remove the safety check below
    3. Accept that ALL notification data will be lost
    4. Accept that audit_log state snapshots will be lost
    """
    import os
    
    # Safety check: Prevent accidental downgrade in production
    is_production = (
        os.environ.get('REPLIT_DEPLOYMENT') == '1' or
        os.environ.get('REPLIT_ENVIRONMENT') == 'production'
    )
    
    if is_production:
        raise RuntimeError(
            "❌ DOWNGRADE BLOCKED: Cannot downgrade this migration in production. "
            "This would drop the notification table and audit_log columns, causing data loss. "
            "If you must downgrade, set ALLOW_DESTRUCTIVE_DOWNGRADE=1 and acknowledge data loss."
        )
    
    # Allow downgrade in development if explicitly enabled
    allow_destructive = os.environ.get('ALLOW_DESTRUCTIVE_DOWNGRADE') == '1'
    if not allow_destructive:
        raise RuntimeError(
            "❌ DOWNGRADE BLOCKED: This migration adds critical tables/columns. "
            "Downgrading will DELETE notification data and audit_log state snapshots. "
            "Set ALLOW_DESTRUCTIVE_DOWNGRADE=1 to proceed (not recommended)."
        )
    
    print("⚠️  WARNING: Performing destructive downgrade...")
    print("⚠️  This will drop notification table and audit_log columns!")
    
    # Drop notification table and indexes
    op.drop_index('idx_notification_created', table_name='notification')
    op.drop_index('idx_notification_user_created', table_name='notification')
    op.drop_index('idx_notification_user_read', table_name='notification')
    op.drop_index('idx_notification_user', table_name='notification')
    op.drop_table('notification')
    
    # Drop audit_log columns and index
    op.drop_index('idx_audit_request_id', table_name='audit_log')
    op.drop_column('audit_log', 'request_id')
    op.drop_column('audit_log', 'after_state')
    op.drop_column('audit_log', 'before_state')
    
    print("✅ Destructive downgrade completed")

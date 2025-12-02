"""Add performance indexes for user metrics queries

Revision ID: g3h4i5j6k7l8
Revises: f2g3h4i5j6k7
Create Date: 2025-12-02 09:45:00.000000

Adds composite indexes to support optimized admin_user_profile CTE query:
- idx_scan_user_timestamp: ON scan (user_id, timestamp DESC) - for user activity queries
- idx_audit_log_user_action: ON audit_log (user_id, action, timestamp DESC) - for audit lookups
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = 'g3h4i5j6k7l8'
down_revision = 'f2g3h4i5j6k7'
branch_labels = None
depends_on = None


def index_exists(index_name):
    """Check if an index already exists in the database."""
    bind = op.get_bind()
    result = bind.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = :name"
    ), {'name': index_name})
    return result.fetchone() is not None


def upgrade():
    # Composite index for user scan queries (admin_user_profile optimization)
    if not index_exists('idx_scan_user_timestamp'):
        op.create_index(
            'idx_scan_user_timestamp',
            'scan',
            ['user_id', sa.text('timestamp DESC')],
            unique=False
        )
    
    # Composite index for audit log user/action queries
    if not index_exists('idx_audit_log_user_action'):
        op.create_index(
            'idx_audit_log_user_action',
            'audit_log',
            ['user_id', 'action', sa.text('timestamp DESC')],
            unique=False
        )


def downgrade():
    if index_exists('idx_audit_log_user_action'):
        op.drop_index('idx_audit_log_user_action', table_name='audit_log')
    
    if index_exists('idx_scan_user_timestamp'):
        op.drop_index('idx_scan_user_timestamp', table_name='scan')

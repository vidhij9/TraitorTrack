"""Add IPT (Inter Party Transfer) tables for return ticket management

Revision ID: j6k7l8m9n0o1
Revises: i5j6k7l8m9n0
Create Date: 2025-12-07

This migration adds three new tables for IPT functionality:
1. return_ticket - Tracks return sessions at C&F points
2. return_ticket_bag - Links returned bags to tickets with original bill info
3. bill_return_event - Historical record of returns affecting bills
"""
from alembic import op
import sqlalchemy as sa


revision = 'j6k7l8m9n0o1'
down_revision = 'i5j6k7l8m9n0'
branch_labels = None
depends_on = None


def table_exists(table_name):
    """Check if a table exists"""
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = :table AND table_schema = 'public'
    """), {"table": table_name})
    return result.fetchone() is not None


def index_exists(index_name):
    """Check if an index exists"""
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT 1 FROM pg_indexes WHERE indexname = :name
    """), {"name": index_name})
    return result.fetchone() is not None


def upgrade():
    if not table_exists('return_ticket'):
        print("Creating return_ticket table...")
        op.create_table('return_ticket',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('ticket_code', sa.String(length=50), nullable=False),
            sa.Column('cf_location', sa.String(length=100), nullable=False),
            sa.Column('status', sa.String(length=20), server_default='open', nullable=True),
            sa.Column('bags_scanned_count', sa.Integer(), server_default='0', nullable=True),
            sa.Column('total_weight_returned_kg', sa.Float(), server_default='0.0', nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_by_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.Column('finalized_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['created_by_id'], ['user.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('ticket_code')
        )
        
        if not index_exists('idx_return_ticket_code'):
            op.create_index('idx_return_ticket_code', 'return_ticket', ['ticket_code'], unique=False)
        if not index_exists('idx_return_ticket_status'):
            op.create_index('idx_return_ticket_status', 'return_ticket', ['status'], unique=False)
        if not index_exists('idx_return_ticket_cf_location'):
            op.create_index('idx_return_ticket_cf_location', 'return_ticket', ['cf_location'], unique=False)
        if not index_exists('idx_return_ticket_created'):
            op.create_index('idx_return_ticket_created', 'return_ticket', ['created_at'], unique=False)
        if not index_exists('idx_return_ticket_status_created'):
            op.create_index('idx_return_ticket_status_created', 'return_ticket', ['status', 'created_at'], unique=False)
    else:
        print("return_ticket table already exists")
    
    if not table_exists('return_ticket_bag'):
        print("Creating return_ticket_bag table...")
        op.create_table('return_ticket_bag',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('return_ticket_id', sa.Integer(), nullable=False),
            sa.Column('bag_id', sa.Integer(), nullable=False),
            sa.Column('original_bill_id', sa.Integer(), nullable=True),
            sa.Column('weight_at_return_kg', sa.Float(), server_default='0.0', nullable=True),
            sa.Column('child_count_at_return', sa.Integer(), server_default='0', nullable=True),
            sa.Column('scanned_by_id', sa.Integer(), nullable=True),
            sa.Column('scanned_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['bag_id'], ['bag.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['original_bill_id'], ['bill.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['return_ticket_id'], ['return_ticket.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['scanned_by_id'], ['user.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('return_ticket_id', 'bag_id', name='uq_return_ticket_bag')
        )
        
        if not index_exists('idx_rtb_ticket_id'):
            op.create_index('idx_rtb_ticket_id', 'return_ticket_bag', ['return_ticket_id'], unique=False)
        if not index_exists('idx_rtb_bag_id'):
            op.create_index('idx_rtb_bag_id', 'return_ticket_bag', ['bag_id'], unique=False)
        if not index_exists('idx_rtb_bill_id'):
            op.create_index('idx_rtb_bill_id', 'return_ticket_bag', ['original_bill_id'], unique=False)
        if not index_exists('idx_rtb_scanned_at'):
            op.create_index('idx_rtb_scanned_at', 'return_ticket_bag', ['scanned_at'], unique=False)
    else:
        print("return_ticket_bag table already exists")
    
    if not table_exists('bill_return_event'):
        print("Creating bill_return_event table...")
        op.create_table('bill_return_event',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('bill_id', sa.Integer(), nullable=False),
            sa.Column('return_ticket_id', sa.Integer(), nullable=True),
            sa.Column('bag_id', sa.Integer(), nullable=True),
            sa.Column('bag_qr_id', sa.String(length=255), nullable=True),
            sa.Column('previous_linked_count', sa.Integer(), nullable=False),
            sa.Column('new_linked_count', sa.Integer(), nullable=False),
            sa.Column('previous_weight_kg', sa.Float(), nullable=False),
            sa.Column('new_weight_kg', sa.Float(), nullable=False),
            sa.Column('previous_child_count', sa.Integer(), server_default='0', nullable=True),
            sa.Column('new_child_count', sa.Integer(), server_default='0', nullable=True),
            sa.Column('removed_by_id', sa.Integer(), nullable=True),
            sa.Column('removed_at', sa.DateTime(), nullable=True),
            sa.Column('reason', sa.String(length=200), server_default='IPT Return', nullable=True),
            sa.ForeignKeyConstraint(['bag_id'], ['bag.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['bill_id'], ['bill.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['removed_by_id'], ['user.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['return_ticket_id'], ['return_ticket.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        
        if not index_exists('idx_bre_bill_id'):
            op.create_index('idx_bre_bill_id', 'bill_return_event', ['bill_id'], unique=False)
        if not index_exists('idx_bre_ticket_id'):
            op.create_index('idx_bre_ticket_id', 'bill_return_event', ['return_ticket_id'], unique=False)
        if not index_exists('idx_bre_bag_id'):
            op.create_index('idx_bre_bag_id', 'bill_return_event', ['bag_id'], unique=False)
        if not index_exists('idx_bre_removed_at'):
            op.create_index('idx_bre_removed_at', 'bill_return_event', ['removed_at'], unique=False)
        if not index_exists('idx_bre_bill_removed'):
            op.create_index('idx_bre_bill_removed', 'bill_return_event', ['bill_id', 'removed_at'], unique=False)
    else:
        print("bill_return_event table already exists")
    
    print("IPT tables migration completed")


def downgrade():
    if table_exists('bill_return_event'):
        if index_exists('idx_bre_bill_removed'):
            op.drop_index('idx_bre_bill_removed', table_name='bill_return_event')
        if index_exists('idx_bre_removed_at'):
            op.drop_index('idx_bre_removed_at', table_name='bill_return_event')
        if index_exists('idx_bre_bag_id'):
            op.drop_index('idx_bre_bag_id', table_name='bill_return_event')
        if index_exists('idx_bre_ticket_id'):
            op.drop_index('idx_bre_ticket_id', table_name='bill_return_event')
        if index_exists('idx_bre_bill_id'):
            op.drop_index('idx_bre_bill_id', table_name='bill_return_event')
        op.drop_table('bill_return_event')
    
    if table_exists('return_ticket_bag'):
        if index_exists('idx_rtb_scanned_at'):
            op.drop_index('idx_rtb_scanned_at', table_name='return_ticket_bag')
        if index_exists('idx_rtb_bill_id'):
            op.drop_index('idx_rtb_bill_id', table_name='return_ticket_bag')
        if index_exists('idx_rtb_bag_id'):
            op.drop_index('idx_rtb_bag_id', table_name='return_ticket_bag')
        if index_exists('idx_rtb_ticket_id'):
            op.drop_index('idx_rtb_ticket_id', table_name='return_ticket_bag')
        op.drop_table('return_ticket_bag')
    
    if table_exists('return_ticket'):
        if index_exists('idx_return_ticket_status_created'):
            op.drop_index('idx_return_ticket_status_created', table_name='return_ticket')
        if index_exists('idx_return_ticket_created'):
            op.drop_index('idx_return_ticket_created', table_name='return_ticket')
        if index_exists('idx_return_ticket_cf_location'):
            op.drop_index('idx_return_ticket_cf_location', table_name='return_ticket')
        if index_exists('idx_return_ticket_status'):
            op.drop_index('idx_return_ticket_status', table_name='return_ticket')
        if index_exists('idx_return_ticket_code'):
            op.drop_index('idx_return_ticket_code', table_name='return_ticket')
        op.drop_table('return_ticket')

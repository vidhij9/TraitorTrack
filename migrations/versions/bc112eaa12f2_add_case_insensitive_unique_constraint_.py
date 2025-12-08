"""add_case_insensitive_unique_constraint_to_qr_id

Revision ID: bc112eaa12f2
Revises: c25e20b7535f
Create Date: 2025-10-25 17:03:24.905321

"""
from alembic import op
import sqlalchemy as sa


revision = 'bc112eaa12f2'
down_revision = 'c25e20b7535f'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add case-insensitive unique constraint to bag.qr_id
    
    Steps:
    1. Handle case-insensitive duplicates by renaming them
    2. Normalize all existing QR codes to uppercase
    3. Drop old case-sensitive unique constraint
    4. Create new case-insensitive unique index
    """
    
    op.execute("""
        WITH duplicates AS (
            SELECT 
                id,
                qr_id,
                UPPER(qr_id) as upper_qr,
                ROW_NUMBER() OVER (PARTITION BY UPPER(qr_id) ORDER BY created_at DESC, id DESC) as rn
            FROM bag
        )
        UPDATE bag
        SET qr_id = bag.qr_id || '_DUP_' || duplicates.id::text
        FROM duplicates
        WHERE bag.id = duplicates.id AND duplicates.rn > 1
    """)
    
    op.execute("UPDATE bag SET qr_id = UPPER(qr_id)")
    
    try:
        op.drop_constraint('bag_qr_id_key', 'bag', type_='unique')
    except Exception:
        pass
    
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_bag_qr_id_unique_ci 
        ON bag (UPPER(qr_id))
    """)
    
    print("Migration complete: QR codes are now case-insensitive unique")


def downgrade():
    """
    Revert to case-sensitive unique constraint
    
    Warning: This may fail if case-insensitive duplicates exist
    """
    
    op.drop_index('idx_bag_qr_id_unique_ci', table_name='bag')
    
    op.create_unique_constraint('bag_qr_id_key', 'bag', ['qr_id'])
    
    print("Downgrade complete: QR codes are now case-sensitive unique (original behavior)")

"""add_case_insensitive_unique_constraint_to_qr_id

Revision ID: bc112eaa12f2
Revises: c25e20b7535f
Create Date: 2025-10-25 17:03:24.905321

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bc112eaa12f2'
down_revision = 'c25e20b7535f'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add case-insensitive unique constraint to bag.qr_id
    
    Steps:
    1. Normalize all existing QR codes to uppercase
    2. Drop old case-sensitive unique constraint
    3. Create new case-insensitive unique index
    """
    
    # Step 1: Normalize all existing QR codes to uppercase
    op.execute("UPDATE bag SET qr_id = UPPER(qr_id)")
    
    # Step 2: Drop the old case-sensitive unique constraint (if exists)
    # PostgreSQL auto-creates a unique index named 'bag_qr_id_key'
    op.drop_constraint('bag_qr_id_key', 'bag', type_='unique')
    
    # Step 3: Create a new case-insensitive unique index
    # This uses a functional index on UPPER(qr_id) to enforce case-insensitive uniqueness
    op.execute("""
        CREATE UNIQUE INDEX idx_bag_qr_id_unique_ci 
        ON bag (UPPER(qr_id))
    """)
    
    print("✅ Migration complete: QR codes are now case-insensitive unique")


def downgrade():
    """
    Revert to case-sensitive unique constraint
    
    Warning: This may fail if case-insensitive duplicates exist
    """
    
    # Drop the case-insensitive unique index
    op.drop_index('idx_bag_qr_id_unique_ci', table_name='bag')
    
    # Recreate the old case-sensitive unique constraint
    op.create_unique_constraint('bag_qr_id_key', 'bag', ['qr_id'])
    
    print("⚠️  Downgrade complete: QR codes are now case-sensitive unique (original behavior)")

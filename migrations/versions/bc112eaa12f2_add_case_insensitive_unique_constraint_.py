"""add_case_insensitive_unique_constraint_to_qr_id

Revision ID: bc112eaa12f2
Revises: c25e20b7535f
Create Date: 2025-10-25 17:03:24.905321

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.engine import Connection


revision = 'bc112eaa12f2'
down_revision = 'c25e20b7535f'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add case-insensitive unique constraint to bag.qr_id
    
    This migration is idempotent and handles:
    - Pre-existing duplicates (renames them with _DUP_ suffix)
    - Normalizes QR codes to uppercase
    - Drops old case-sensitive unique constraint if it exists
    - Creates new case-insensitive unique index CONCURRENTLY (non-blocking)
    
    Note: If data has been pre-cleaned manually, the UPDATE statements
    will simply affect 0 rows (fast no-op).
    
    Production note: Duplicate QR codes (PANKAJ014, PAWAN 011, PAWAN GODARA 09, 
    RAVI SINGH 12) were manually renamed on 2025-12-08 before this migration ran.
    919 lowercase QR codes were normalized to uppercase.
    Index idx_bag_qr_id_unique_ci already exists in production.
    """
    conn = op.get_bind()
    
    index_exists = conn.execute(text("""
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'idx_bag_qr_id_unique_ci' 
        AND tablename = 'bag'
    """)).fetchone()
    
    if index_exists:
        print("Case-insensitive index idx_bag_qr_id_unique_ci already exists - skipping migration")
        return
    
    dups_result = conn.execute(text("""
        SELECT COUNT(*) FROM (
            SELECT UPPER(qr_id) FROM bag 
            GROUP BY UPPER(qr_id) HAVING COUNT(*) > 1
        ) x
    """))
    dup_count = dups_result.fetchone()[0]
    
    if dup_count > 0:
        print(f"Found {dup_count} duplicate QR code groups, renaming...")
        conn.execute(text("""
            WITH duplicates AS (
                SELECT 
                    id,
                    qr_id,
                    ROW_NUMBER() OVER (PARTITION BY UPPER(qr_id) ORDER BY created_at DESC, id DESC) as rn
                FROM bag
            )
            UPDATE bag
            SET qr_id = bag.qr_id || '_DUP_' || duplicates.id::text
            FROM duplicates
            WHERE bag.id = duplicates.id AND duplicates.rn > 1
        """))
    else:
        print("No duplicate QR codes found (already cleaned)")
    
    needs_upper_result = conn.execute(text("""
        SELECT COUNT(*) FROM bag WHERE qr_id != UPPER(qr_id)
    """))
    needs_upper = needs_upper_result.fetchone()[0]
    
    if needs_upper > 0:
        print(f"Normalizing {needs_upper} QR codes to uppercase...")
        conn.execute(text("UPDATE bag SET qr_id = UPPER(qr_id) WHERE qr_id != UPPER(qr_id)"))
    else:
        print("All QR codes already uppercase (already normalized)")
    
    constraint_exists = conn.execute(text("""
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'bag_qr_id_key' 
        AND table_name = 'bag' 
        AND table_schema = 'public'
    """)).fetchone()
    
    if constraint_exists:
        print("Dropping old case-sensitive unique constraint...")
        op.drop_constraint('bag_qr_id_key', 'bag', type_='unique')
    else:
        print("Old constraint bag_qr_id_key already dropped or doesn't exist")
    
    print("Creating case-insensitive unique index CONCURRENTLY (non-blocking)...")
    with op.get_context().autocommit_block():
        op.execute(text("""
            CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_bag_qr_id_unique_ci 
            ON bag (UPPER(qr_id))
        """))
    print("Index created successfully")
    
    print("Migration complete: QR codes are now case-insensitive unique")


def downgrade():
    """
    Revert to case-sensitive unique constraint
    
    Warning: This may fail if case-insensitive duplicates exist
    """
    conn = op.get_bind()
    
    index_exists = conn.execute(sa.text("""
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'idx_bag_qr_id_unique_ci' 
        AND tablename = 'bag'
    """)).fetchone()
    
    if index_exists:
        op.drop_index('idx_bag_qr_id_unique_ci', table_name='bag')
    
    constraint_exists = conn.execute(sa.text("""
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'bag_qr_id_key' 
        AND table_name = 'bag' 
        AND table_schema = 'public'
    """)).fetchone()
    
    if not constraint_exists:
        op.create_unique_constraint('bag_qr_id_key', 'bag', ['qr_id'])
    
    print("Downgrade complete: QR codes are now case-sensitive unique (original behavior)")

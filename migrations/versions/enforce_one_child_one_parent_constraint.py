"""enforce one child one parent constraint

Revision ID: e1f2a3b4c5d6
Revises: d54b4a63f31c
Create Date: 2025-11-24 08:20:00.000000

CRITICAL FIX: Enforce one-child-one-parent business rule
- A child bag can only be linked to ONE parent bag
- Prevents duplicate parent links which violate warehouse logistics rules

Changes:
1. Clean up any existing duplicate links (keep oldest)
2. Add UNIQUE constraint on link.child_bag_id
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1f2a3b4c5d6'
down_revision = 'd54b4a63f31c'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Clean up duplicate links (keep oldest link for each child)
    # Keep the first parent link created (earliest created_at)
    # This preserves the original/intended parent relationship
    op.execute("""
        WITH ranked_links AS (
            SELECT 
                id,
                child_bag_id,
                ROW_NUMBER() OVER (
                    PARTITION BY child_bag_id 
                    ORDER BY created_at ASC NULLS LAST, id ASC
                ) as rn
            FROM link
        )
        DELETE FROM link
        WHERE id IN (
            SELECT id FROM ranked_links WHERE rn > 1
        );
    """)
    
    # Step 2: Add UNIQUE constraint to enforce one child = one parent
    op.create_unique_constraint(
        'link_child_bag_id_unique',
        'link',
        ['child_bag_id']
    )


def downgrade():
    # Remove the UNIQUE constraint
    op.drop_constraint('link_child_bag_id_unique', 'link', type_='unique')
    
    # Note: We cannot restore deleted duplicate links
    # Manual intervention required if rollback is needed

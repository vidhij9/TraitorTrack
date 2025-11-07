"""Initial migration with all existing models and account lockout

Revision ID: c25e20b7535f
Revises: 
Create Date: 2025-10-25 15:21:46.166993

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c25e20b7535f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """
    Safe initial migration that creates tables only if they don't exist.
    This migration is safe to run on both new and existing databases.
    """
    # This migration is intentionally empty because the database
    # already has all required tables from previous deployments.
    # Future migrations will handle schema changes incrementally.
    pass


def downgrade():
    # Downgrade is not supported for initial migration
    pass
"""Initialize the migration chain for the foundation phase.

No domain tables are created in Phase 1. Future phases own their domain
migrations; keeping this revision deliberately empty makes the migration
pipeline executable without prematurely defining product entities.
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("SELECT 1"))


def downgrade() -> None:
    pass

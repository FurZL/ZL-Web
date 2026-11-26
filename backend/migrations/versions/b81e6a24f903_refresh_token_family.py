"""Track refresh token families for replay detection."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "b81e6a24f903"
down_revision = "a7d2e9c14b83"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_sessions", sa.Column("family_id", UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE user_sessions SET family_id = id")
    op.alter_column("user_sessions", "family_id", nullable=False)
    op.create_index("ix_user_sessions_family_id", "user_sessions", ["family_id"])


def downgrade() -> None:
    op.drop_index("ix_user_sessions_family_id", table_name="user_sessions")
    op.drop_column("user_sessions", "family_id")

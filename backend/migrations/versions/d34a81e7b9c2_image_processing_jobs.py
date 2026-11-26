"""Persist image jobs and recover previously unfinished processing."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "d34a81e7b9c2"
down_revision = "b81e6a24f903"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "image_processing_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("image_id", UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("lease_token", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("kind", "image_id", name="uq_image_job_kind_image"),
    )
    op.create_index("ix_image_processing_jobs_status", "image_processing_jobs", ["status"])
    # UUIDs are supplied by PostgreSQL for existing unfinished rows.
    op.execute("""INSERT INTO image_processing_jobs (id, kind, image_id, status, attempts)
        SELECT gen_random_uuid(), 'gallery', i.id, 'pending', 0
        FROM images i JOIN stored_objects s ON s.id = i.stored_object_id
        WHERE s.processing_status IN ('pending', 'processing') AND s.visibility = 'public'""")
    op.execute("""INSERT INTO image_processing_jobs (id, kind, image_id, status, attempts)
        SELECT gen_random_uuid(), 'profile', i.id, 'pending', 0
        FROM profile_images i JOIN stored_objects s ON s.id = i.stored_object_id
        WHERE s.processing_status IN ('pending', 'processing') AND s.visibility = 'private'""")


def downgrade() -> None:
    op.drop_index("ix_image_processing_jobs_status", table_name="image_processing_jobs")
    op.drop_table("image_processing_jobs")

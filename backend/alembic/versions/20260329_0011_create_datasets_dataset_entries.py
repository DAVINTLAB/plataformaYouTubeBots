"""create datasets and dataset_entries tables

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-29 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column(
            "collection_id",
            sa.Uuid(),
            sa.ForeignKey("collections.id"),
            nullable=False,
        ),
        sa.Column(
            "criteria_applied",
            sa.ARRAY(sa.String()),
            nullable=False,
        ),
        sa.Column("thresholds", JSONB, nullable=False, server_default="{}"),
        sa.Column("total_users_original", sa.Integer(), nullable=False),
        sa.Column("total_users_selected", sa.Integer(), nullable=False),
        sa.Column(
            "created_by",
            sa.Uuid(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "dataset_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "dataset_id",
            sa.Uuid(),
            sa.ForeignKey("datasets.id"),
            nullable=False,
        ),
        sa.Column("author_channel_id", sa.String(64), nullable=False),
        sa.Column("author_display_name", sa.String(256)),
        sa.Column("comment_count", sa.Integer(), nullable=False),
        sa.Column(
            "matched_criteria",
            sa.ARRAY(sa.String()),
            nullable=False,
        ),
        sa.UniqueConstraint("dataset_id", "author_channel_id", name="uq_dataset_user"),
    )


def downgrade() -> None:
    op.drop_table("dataset_entries")
    op.drop_table("datasets")

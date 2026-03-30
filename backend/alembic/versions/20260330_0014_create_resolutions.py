"""create resolutions table

Revision ID: 0014
Revises: 0013
Create Date: 2026-03-30 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resolutions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "conflict_id",
            sa.Uuid(),
            sa.ForeignKey("annotation_conflicts.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("resolved_label", sa.String(8), nullable=False),
        sa.Column(
            "resolved_by",
            sa.Uuid(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "resolved_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "resolved_label IN ('bot', 'humano')", name="ck_resolution_label"
        ),
    )


def downgrade() -> None:
    op.drop_table("resolutions")

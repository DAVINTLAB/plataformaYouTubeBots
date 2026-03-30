"""create annotations and annotation_conflicts tables

Revision ID: 0013
Revises: 0012
Create Date: 2026-03-30 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "annotations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "comment_id",
            sa.Uuid(),
            sa.ForeignKey("comments.id"),
            nullable=False,
        ),
        sa.Column(
            "annotator_id",
            sa.Uuid(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("label", sa.String(8), nullable=False),
        sa.Column("justificativa", sa.Text(), nullable=True),
        sa.Column(
            "annotated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("comment_id", "annotator_id", name="uq_comment_annotator"),
        sa.CheckConstraint("label IN ('bot', 'humano')", name="ck_valid_label"),
    )

    op.create_table(
        "annotation_conflicts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "comment_id",
            sa.Uuid(),
            sa.ForeignKey("comments.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "annotation_a_id",
            sa.Uuid(),
            sa.ForeignKey("annotations.id"),
            nullable=False,
        ),
        sa.Column(
            "annotation_b_id",
            sa.Uuid(),
            sa.ForeignKey("annotations.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "resolved_by",
            sa.Uuid(),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("resolved_label", sa.String(8), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("annotation_conflicts")
    op.drop_table("annotations")

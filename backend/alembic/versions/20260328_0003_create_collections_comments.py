"""create collections and comments tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-28 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "collections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("video_id", sa.String(20), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("total_comments", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("collected_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("next_page_token", sa.String(256), nullable=True),
        sa.ForeignKeyConstraint(["collected_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("comment_id", sa.String(64), nullable=False),
        sa.Column("author_display_name", sa.String(256), nullable=False),
        sa.Column("author_channel_id", sa.String(64), nullable=True),
        sa.Column("text_original", sa.Text(), nullable=False),
        sa.Column("like_count", sa.Integer(), nullable=False),
        sa.Column("reply_count", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "collection_id", "comment_id", name="uq_collection_comment"
        ),
    )


def downgrade() -> None:
    op.drop_table("comments")
    op.drop_table("collections")

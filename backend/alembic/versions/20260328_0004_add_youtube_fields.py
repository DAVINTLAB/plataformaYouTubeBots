"""add youtube fields to collections and comments

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-28 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Video metadata on collections (populated on YouTube import)
    op.add_column(
        "collections", sa.Column("video_title", sa.String(500), nullable=True)
    )
    op.add_column(
        "collections", sa.Column("video_description", sa.Text(), nullable=True)
    )
    op.add_column(
        "collections", sa.Column("video_channel_id", sa.String(64), nullable=True)
    )
    op.add_column(
        "collections", sa.Column("video_channel_title", sa.String(256), nullable=True)
    )
    op.add_column(
        "collections", sa.Column("video_published_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "collections", sa.Column("video_view_count", sa.BigInteger(), nullable=True)
    )
    op.add_column(
        "collections", sa.Column("video_like_count", sa.BigInteger(), nullable=True)
    )
    op.add_column(
        "collections", sa.Column("video_comment_count", sa.BigInteger(), nullable=True)
    )

    # Full YouTube comment fields on comments
    op.add_column("comments", sa.Column("text_display", sa.Text(), nullable=True))
    op.add_column(
        "comments", sa.Column("author_profile_image_url", sa.String(512), nullable=True)
    )
    op.add_column(
        "comments", sa.Column("author_channel_url", sa.String(512), nullable=True)
    )
    op.add_column("comments", sa.Column("is_public", sa.Boolean(), nullable=True))
    op.add_column("comments", sa.Column("can_reply", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("collections", "video_title")
    op.drop_column("collections", "video_description")
    op.drop_column("collections", "video_channel_id")
    op.drop_column("collections", "video_channel_title")
    op.drop_column("collections", "video_published_at")
    op.drop_column("collections", "video_view_count")
    op.drop_column("collections", "video_like_count")
    op.drop_column("collections", "video_comment_count")

    op.drop_column("comments", "text_display")
    op.drop_column("comments", "author_profile_image_url")
    op.drop_column("comments", "author_channel_url")
    op.drop_column("comments", "is_public")
    op.drop_column("comments", "can_reply")

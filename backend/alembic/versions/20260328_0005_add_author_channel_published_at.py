"""add author_channel_published_at to comments

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-28 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "comments",
        sa.Column("author_channel_published_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("comments", "author_channel_published_at")

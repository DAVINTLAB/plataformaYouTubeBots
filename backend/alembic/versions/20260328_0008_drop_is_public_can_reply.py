"""drop is_public and can_reply from comments

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-28 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("comments", "is_public")
    op.drop_column("comments", "can_reply")


def downgrade() -> None:
    op.add_column(
        "comments",
        sa.Column("is_public", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "comments",
        sa.Column("can_reply", sa.Boolean(), nullable=True),
    )

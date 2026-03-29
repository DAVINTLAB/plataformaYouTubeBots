"""add enrich_status to collections

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-29 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "collections",
        sa.Column("enrich_status", sa.String(16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("collections", "enrich_status")

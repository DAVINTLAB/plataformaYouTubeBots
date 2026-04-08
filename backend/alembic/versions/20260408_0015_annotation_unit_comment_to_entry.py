"""alterar unidade de anotação de comentário para dataset_entry (usuário)

Revision ID: 0015
Revises: 0014
Create Date: 2026-04-08 00:00:00.000000

Migração destrutiva: remove todas as anotações, conflitos e resoluções
existentes antes de alterar as FKs. Necessário porque a mudança de
granularidade (comentário → usuário) invalida os dados anteriores.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1) Limpar dados existentes (mudança de granularidade os invalida)
    op.execute("DELETE FROM resolutions")
    op.execute("DELETE FROM annotation_conflicts")
    op.execute("DELETE FROM annotations")

    # 2) annotations: comment_id → dataset_entry_id
    op.drop_constraint("uq_comment_annotator", "annotations", type_="unique")
    op.drop_constraint("annotations_comment_id_fkey", "annotations", type_="foreignkey")
    op.drop_column("annotations", "comment_id")

    op.add_column(
        "annotations",
        sa.Column(
            "dataset_entry_id",
            sa.Uuid(),
            sa.ForeignKey("dataset_entries.id"),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_entry_annotator",
        "annotations",
        ["dataset_entry_id", "annotator_id"],
    )

    # 3) annotation_conflicts: comment_id → dataset_entry_id
    op.drop_constraint(
        "annotation_conflicts_comment_id_key",
        "annotation_conflicts",
        type_="unique",
    )
    op.drop_constraint(
        "annotation_conflicts_comment_id_fkey",
        "annotation_conflicts",
        type_="foreignkey",
    )
    op.drop_column("annotation_conflicts", "comment_id")

    op.add_column(
        "annotation_conflicts",
        sa.Column(
            "dataset_entry_id",
            sa.Uuid(),
            sa.ForeignKey("dataset_entries.id"),
            nullable=False,
            unique=True,
        ),
    )


def downgrade() -> None:
    # Reverter: dataset_entry_id → comment_id
    op.execute("DELETE FROM resolutions")
    op.execute("DELETE FROM annotation_conflicts")
    op.execute("DELETE FROM annotations")

    # annotation_conflicts
    op.drop_constraint(
        "annotation_conflicts_dataset_entry_id_key",
        "annotation_conflicts",
        type_="unique",
    )
    op.drop_column("annotation_conflicts", "dataset_entry_id")
    op.add_column(
        "annotation_conflicts",
        sa.Column(
            "comment_id",
            sa.Uuid(),
            sa.ForeignKey("comments.id"),
            nullable=False,
            unique=True,
        ),
    )

    # annotations
    op.drop_constraint("uq_entry_annotator", "annotations", type_="unique")
    op.drop_column("annotations", "dataset_entry_id")
    op.add_column(
        "annotations",
        sa.Column(
            "comment_id",
            sa.Uuid(),
            sa.ForeignKey("comments.id"),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_comment_annotator",
        "annotations",
        ["comment_id", "annotator_id"],
    )

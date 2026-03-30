import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Annotation(Base):
    __tablename__ = "annotations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    comment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("comments.id"))
    annotator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    label: Mapped[str] = mapped_column(String(8), nullable=False)
    justificativa: Mapped[str | None] = mapped_column(Text, nullable=True)
    annotated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    comment: Mapped["Comment"] = relationship()  # noqa: F821
    annotator: Mapped["User"] = relationship()  # noqa: F821

    __table_args__ = (
        UniqueConstraint("comment_id", "annotator_id", name="uq_comment_annotator"),
        CheckConstraint("label IN ('bot', 'humano')", name="ck_valid_label"),
    )


class AnnotationConflict(Base):
    __tablename__ = "annotation_conflicts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    comment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("comments.id"), unique=True
    )
    annotation_a_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("annotations.id"))
    annotation_b_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("annotations.id"))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Preenchidos na US-05 (revisão de conflitos)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    resolved_label: Mapped[str | None] = mapped_column(String(8), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)

    annotation_a: Mapped["Annotation"] = relationship(foreign_keys=[annotation_a_id])
    annotation_b: Mapped["Annotation"] = relationship(foreign_keys=[annotation_b_id])

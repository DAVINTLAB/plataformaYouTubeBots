import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Resolution(Base):
    """Registro imutável de cada decisão de desempate do admin."""

    __tablename__ = "resolutions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conflict_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("annotation_conflicts.id"), unique=True
    )
    resolved_label: Mapped[str] = mapped_column(String(8), nullable=False)
    resolved_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "resolved_label IN ('bot', 'humano')", name="ck_resolution_label"
        ),
    )

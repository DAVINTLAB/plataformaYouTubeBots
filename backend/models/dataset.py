import uuid
from datetime import datetime

from sqlalchemy import ARRAY, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    collection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collections.id"))
    criteria_applied: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    thresholds: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    total_users_original: Mapped[int] = mapped_column(Integer, nullable=False)
    total_users_selected: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    collection: Mapped["Collection"] = relationship()  # noqa: F821
    entries: Mapped[list["DatasetEntry"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )


class DatasetEntry(Base):
    """Um usuario do YouTube selecionado como suspeito."""

    __tablename__ = "dataset_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.id"))
    author_channel_id: Mapped[str] = mapped_column(String(64), nullable=False)
    author_display_name: Mapped[str] = mapped_column(String(256))
    comment_count: Mapped[int] = mapped_column(Integer, nullable=False)
    matched_criteria: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)

    dataset: Mapped["Dataset"] = relationship(back_populates="entries")

    __table_args__ = (
        UniqueConstraint("dataset_id", "author_channel_id", name="uq_dataset_user"),
    )

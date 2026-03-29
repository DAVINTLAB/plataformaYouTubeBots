import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    video_id: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    total_comments: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    collected_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    next_page_token: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Indicador de falha ao obter datas de criação dos canais (channels.list)
    # None = não tentou (import), False = sucesso, True = falha em alguma página
    channel_dates_failed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Enriquecimento pós-coleta (replies extras + channel dates)
    # None = não aplicável (import/legado), pending, enriching, done
    enrich_status: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Video metadata — populated on YouTube import (videos.list response)
    video_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_channel_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    video_channel_title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    video_published_at: Mapped[datetime | None] = mapped_column(nullable=True)
    video_view_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    video_like_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    video_comment_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    comments: Mapped[list["Comment"]] = relationship(back_populates="collection")


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    collection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collections.id"))
    comment_id: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    author_display_name: Mapped[str] = mapped_column(String(256))
    author_channel_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    text_original: Mapped[str] = mapped_column(Text, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)

    # Full YouTube API fields — populated during collection and import
    text_display: Mapped[str | None] = mapped_column(Text, nullable=True)
    author_profile_image_url: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    author_channel_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    author_channel_published_at: Mapped[datetime | None] = mapped_column(nullable=True)

    collection: Mapped["Collection"] = relationship(back_populates="comments")

    __table_args__ = (
        UniqueConstraint("collection_id", "comment_id", name="uq_collection_comment"),
    )

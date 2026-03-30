import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# ─── Request ─────────────────────────────────────────────────────────────────


class ResolveRequest(BaseModel):
    conflict_id: uuid.UUID
    resolved_label: Literal["bot", "humano"]


class ReviewImportComment(BaseModel):
    comment_db_id: uuid.UUID
    author_channel_id: str
    author_display_name: str
    text_original: str
    final_label: Literal["bot", "humano"]
    annotations: list[dict] = []
    resolution: dict | None = None


class ReviewImport(BaseModel):
    """Aceita o mesmo formato JSON exportado pelo export."""

    dataset_name: str
    video_id: str
    comments: list[ReviewImportComment] = Field(min_length=1)
    done: bool = True


class ReviewImportChunk(BaseModel):
    """Batch adicional de comentários revisados para import paginado."""

    comments: list[ReviewImportComment] = Field(min_length=1)
    done: bool = False


# ─── Response ────────────────────────────────────────────────────────────────


class ConflictListItem(BaseModel):
    conflict_id: uuid.UUID
    comment_id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_name: str
    author_display_name: str
    text_original: str
    label_a: str
    annotator_a: str
    justificativa_a: str | None
    label_b: str
    annotator_b: str
    justificativa_b: str | None
    status: str
    created_at: datetime


class AnnotationSide(BaseModel):
    annotator: str
    label: str
    justificativa: str | None
    annotated_at: datetime


class ConflictComment(BaseModel):
    comment_db_id: uuid.UUID
    text_original: str
    like_count: int
    reply_count: int
    published_at: datetime


class ConflictDetail(BaseModel):
    conflict_id: uuid.UUID
    status: str
    dataset_name: str
    author_channel_id: str
    author_display_name: str
    comments: list[ConflictComment]
    annotation_a: AnnotationSide
    annotation_b: AnnotationSide
    resolved_by: str | None
    resolved_label: str | None
    resolved_at: datetime | None


class ResolveResponse(BaseModel):
    conflict_id: uuid.UUID
    status: str
    resolved_label: str
    resolved_by: str
    resolved_at: datetime


class BotAnnotationDetail(BaseModel):
    annotator_name: str
    label: str
    justificativa: str | None


class BotCommentItem(BaseModel):
    comment_db_id: uuid.UUID
    text_original: str
    author_display_name: str
    author_channel_id: str
    dataset_id: uuid.UUID
    dataset_name: str
    annotations: list[BotAnnotationDetail]
    has_conflict: bool
    conflict_id: uuid.UUID | None


class ReviewStats(BaseModel):
    total_conflicts: int
    pending_conflicts: int
    resolved_conflicts: int
    total_bots_flagged: int


class ImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]


class ImportChunkResponse(BaseModel):
    total_imported: int
    chunk_received: int
    done: bool

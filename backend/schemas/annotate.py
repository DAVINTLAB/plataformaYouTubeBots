import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ─── Request ─────────────────────────────────────────────────────────────────


class AnnotationCreate(BaseModel):
    entry_id: uuid.UUID
    label: Literal["bot", "humano"]
    justificativa: str | None = None

    @model_validator(mode="after")
    def justificativa_required_for_bot(self):
        if self.label == "bot" and not (self.justificativa or "").strip():
            raise ValueError("Justificativa é obrigatória para classificação 'bot'.")
        return self


class AnnotationImportItem(BaseModel):
    entry_id: uuid.UUID
    label: Literal["bot", "humano"]
    justificativa: str | None = None


class AnnotationImport(BaseModel):
    """Aceita o mesmo formato JSON exportado pelo export."""

    dataset_id: uuid.UUID | None = None
    dataset_name: str | None = None
    video_id: str | None = None
    annotations: list[AnnotationImportItem] = Field(min_length=1)
    done: bool = True


class AnnotationImportChunk(BaseModel):
    """Batch adicional de anotações para import paginado."""

    annotations: list[AnnotationImportItem] = Field(min_length=1)
    done: bool = False


class ImportChunkResponse(BaseModel):
    total_imported: int
    total_updated: int
    chunk_received: int
    done: bool


# ─── Response ────────────────────────────────────────────────────────────────


class AnnotationResult(BaseModel):
    annotation_id: uuid.UUID
    entry_id: uuid.UUID
    label: str
    conflict_created: bool


class MyAnnotation(BaseModel):
    label: str
    justificativa: str | None
    annotated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnnotatorAnnotation(BaseModel):
    annotator_name: str
    label: str
    justificativa: str | None
    annotated_at: datetime


class CommentItem(BaseModel):
    """Comentário exibido como evidência (sem anotação individual)."""

    comment_db_id: uuid.UUID
    text_original: str
    like_count: int
    reply_count: int
    published_at: datetime


class UserCommentsResponse(BaseModel):
    entry_id: uuid.UUID
    author_display_name: str
    author_channel_id: str
    comments: list[CommentItem]
    my_annotation: MyAnnotation | None
    all_annotations: list[AnnotatorAnnotation] | None = None


class UserItem(BaseModel):
    entry_id: uuid.UUID
    author_channel_id: str
    author_display_name: str
    comment_count: int
    is_annotated_by_me: bool
    my_label: str | None = None


class DatasetUsersResponse(BaseModel):
    dataset_id: uuid.UUID
    dataset_name: str
    total_users: int
    annotated_users_by_me: int
    page: int
    page_size: int
    total_pages: int
    items: list[UserItem]


class DatasetProgress(BaseModel):
    dataset_id: uuid.UUID
    dataset_name: str
    total_users: int
    annotated: int
    bots: int
    humans: int
    percent_complete: float


class ImportResult(BaseModel):
    imported: int
    updated: int
    skipped: int
    errors: list[str]


class AnnotatorProgress(BaseModel):
    annotator_id: uuid.UUID
    annotator_name: str
    dataset_id: uuid.UUID
    dataset_name: str
    total_users: int
    annotated: int
    bots: int
    humans: int
    percent_complete: float

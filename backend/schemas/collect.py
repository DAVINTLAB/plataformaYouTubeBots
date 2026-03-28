import uuid
from datetime import datetime
from typing import Literal
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class CollectRequest(BaseModel):
    video_id: str = Field(min_length=1)
    api_key: SecretStr  # nunca serializado, nunca logado

    @field_validator("video_id")
    @classmethod
    def extract_video_id(cls, v: str) -> str:
        if "youtube.com" in v:
            parsed = urlparse(v)
            params = parse_qs(parsed.query)
            if "v" in params:
                return params["v"][0]
        elif "youtu.be" in v:
            parsed = urlparse(v)
            return parsed.path.lstrip("/").split("?")[0]
        return v


class CollectNextPageRequest(BaseModel):
    collection_id: uuid.UUID
    api_key: SecretStr  # nunca serializado, nunca logado


# ─── Import — formato flat (mesmo do export da plataforma) ───────────────────


class ImportVideoMeta(BaseModel):
    id: str
    title: str | None = None
    channel_id: str | None = None
    channel_title: str | None = None
    published_at: datetime | None = None
    view_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None


class ImportComment(BaseModel):
    comment_id: str
    parent_id: str | None = None
    author_display_name: str = ""
    author_channel_id: str | None = None
    author_channel_published_at: datetime | None = None
    author_profile_image_url: str | None = None
    author_channel_url: str | None = None
    text_original: str
    text_display: str | None = None
    like_count: int = 0
    reply_count: int = 0
    published_at: datetime
    updated_at: datetime


class ImportRequest(BaseModel):
    """Formato flat — idêntico ao JSON exportado pela plataforma."""

    video: ImportVideoMeta
    comments: list[ImportComment] = Field(min_length=1)


# ─── Response schemas ─────────────────────────────────────────────────────────


class CollectionStarted(BaseModel):
    collection_id: uuid.UUID
    video_id: str
    status: Literal["pending", "running", "completed", "failed"]
    total_comments: int | None = None
    next_page_token: str | None = None
    channel_dates_failed: bool | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CollectionStatus(BaseModel):
    collection_id: uuid.UUID
    video_id: str
    video_title: str | None = None
    status: Literal["pending", "running", "completed", "failed"]
    total_comments: int | None = None
    channel_dates_failed: bool | None = None
    collected_at: datetime | None = None
    collected_by: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CollectionSummary(BaseModel):
    collection_id: uuid.UUID
    video_id: str
    video_title: str | None = None
    status: Literal["pending", "running", "completed", "failed"]
    total_comments: int | None = None
    channel_dates_failed: bool | None = None
    collected_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

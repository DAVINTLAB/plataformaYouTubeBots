import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DataSummary(BaseModel):
    collections_count: int
    comments_count: int
    datasets_count: int
    annotations_count: int
    estimated_size_mb: float


class DataCollection(BaseModel):
    collection_id: uuid.UUID
    video_id: str
    video_title: str | None = None
    total_comments: int | None = None
    status: str
    enrich_status: str | None = None
    channel_dates_failed: bool | None = None
    total_users: int
    collected_by: str
    created_at: datetime
    completed_at: datetime | None = None
    duration_seconds: int | None = None

    model_config = ConfigDict(from_attributes=True)


class DataDataset(BaseModel):
    dataset_id: uuid.UUID
    name: str
    collection_id: uuid.UUID
    video_id: str
    criteria: list[str]
    total_users_original: int
    total_selected: int
    total_comments: int
    created_by: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DataAnnotationProgress(BaseModel):
    dataset_id: uuid.UUID
    dataset_name: str
    total: int
    annotated: int
    pending: int
    conflicts: int
    conflicts_resolved: int
    annotators_count: int
    bots_users: int
    bots_comments: int

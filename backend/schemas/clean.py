import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

VALID_CRITERIA = Literal[
    "percentil",
    "media",
    "moda",
    "mediana",
    "curtos",
    "intervalo",
    "identicos",
    "perfil",
]


class CleanThresholds(BaseModel):
    threshold_chars: int = Field(default=20, ge=1, le=500)
    threshold_seconds: int = Field(default=30, ge=1, le=3600)


# ─── Request ─────────────────────────────────────────────────────────────────


class DatasetCreate(BaseModel):
    collection_id: uuid.UUID
    criteria: list[VALID_CRITERIA] = Field(min_length=1)
    thresholds: CleanThresholds = CleanThresholds()


class DatasetImportUser(BaseModel):
    author_channel_id: str = Field(min_length=1)
    author_display_name: str = ""
    comment_count: int = Field(default=0, ge=0)
    matched_criteria: list[str] = Field(default_factory=list)


class DatasetImportMeta(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    video_id: str = Field(default="", min_length=0)
    criteria_applied: list[str] = Field(default_factory=list)
    total_users_original: int | None = None
    total_users_selected: int | None = None


class DatasetImport(BaseModel):
    """Aceita o mesmo formato JSON exportado pelo download."""

    dataset: DatasetImportMeta
    users: list[DatasetImportUser] = Field(min_length=1)
    comments: list | None = None  # ignorado no import — comments já estão na coleta


# ─── Response — Preview ──────────────────────────────────────────────────────


class CriteriaCount(BaseModel):
    selected_users: int
    threshold_chars: int | None = None
    threshold_seconds: int | None = None


class CentralMeasures(BaseModel):
    mean: float
    mode: float
    median: float
    iqr_lower: float
    iqr_upper: float


class PreviewResponse(BaseModel):
    collection_id: uuid.UUID
    total_users: int
    central_measures: CentralMeasures
    by_criteria: dict[str, CriteriaCount]
    union_if_combined: int


# ─── Response — Dataset ──────────────────────────────────────────────────────


class DatasetResponse(BaseModel):
    dataset_id: uuid.UUID
    name: str
    collection_id: uuid.UUID
    video_id: str
    total_users_original: int
    total_users_selected: int
    criteria_applied: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatasetSummary(BaseModel):
    dataset_id: uuid.UUID
    name: str
    video_id: str
    total_users_selected: int
    criteria_applied: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

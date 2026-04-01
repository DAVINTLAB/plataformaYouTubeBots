"""Schemas Pydantic da US-06 — Dashboard de Análise."""

import uuid

from pydantic import BaseModel

# ── Visão Geral (Global) ───────────────────────────────────────────


class GlobalSummary(BaseModel):
    total_datasets: int
    total_comments_annotated: int
    total_comments_in_datasets: int
    annotation_progress: float
    total_bots: int
    total_humans: int
    total_conflicts: int
    pending_conflicts: int
    agreement_rate: float


class GlobalDashboardResponse(BaseModel):
    summary: GlobalSummary
    active_criteria_filter: list[str]
    label_distribution_chart: str
    comparativo_por_dataset_chart: str
    annotations_over_time_chart: str
    bot_rate_by_dataset_chart: str
    agreement_by_dataset_chart: str
    criteria_effectiveness_chart: str


# ── Eficácia por Critério ──────────────────────────────────────────


class CriteriaEffectivenessItem(BaseModel):
    criteria: str
    group: str
    total_datasets: int
    total_comments_selected: int
    total_bots: int
    bot_rate: float


# ── Por Vídeo ──────────────────────────────────────────────────────


class VideoSummary(BaseModel):
    total_comments_collected: int
    total_comments_in_datasets: int
    total_annotated: int
    total_bots: int
    total_humans: int
    total_conflicts: int
    pending_conflicts: int
    agreement_rate: float


class VideoHighlight(BaseModel):
    label: str
    value: str
    detail: str | None = None


class VideoDashboardResponse(BaseModel):
    video_id: str
    summary: VideoSummary
    highlights: list[VideoHighlight]
    active_criteria_filter: list[str]
    label_distribution_chart: str
    comparativo_por_dataset_chart: str
    bot_rate_by_criteria_chart: str
    comment_timeline_chart: str


# ── Meu Progresso ──────────────────────────────────────────────────


class UserSummary(BaseModel):
    total_datasets_assigned: int
    datasets_completed: int
    datasets_pending: int
    total_annotated: int
    total_pending: int
    bots: int
    humans: int
    conflicts_generated: int


class UserDatasetProgress(BaseModel):
    dataset_id: uuid.UUID
    dataset_name: str
    video_id: str
    total_comments: int
    annotated_by_me: int
    pending: int
    percent_complete: float
    my_bots: int
    my_conflicts: int
    status: str


class UserDashboardResponse(BaseModel):
    summary: UserSummary
    datasets: list[UserDatasetProgress]
    my_label_distribution_chart: str
    my_progress_by_dataset_chart: str
    my_annotations_over_time_chart: str


# ── Tabela de Bots ─────────────────────────────────────────────────


class BotCommentItem(BaseModel):
    dataset_name: str
    author_display_name: str
    text_original: str
    concordance_pct: int
    conflict_status: str | None = None
    annotators_count: int = 0
    criteria: list[str] = []


class BotCommentsResponse(BaseModel):
    total: int
    items: list[BotCommentItem]

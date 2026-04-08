"""Serviço da US-06 — Dashboard de Análise.

Agregações SQL + geração de gráficos Plotly (JSON).
Unidade de análise: DatasetEntry (autor/canal do YouTube).
"""

import logging
import uuid
from collections import defaultdict

import plotly.graph_objects as go
import plotly.io as pio
from sqlalchemy import Date, case, cast, func
from sqlalchemy.orm import Session

from models.annotation import Annotation, AnnotationConflict
from models.collection import Collection, Comment
from models.dataset import Dataset, DatasetEntry

logger = logging.getLogger(__name__)

COLORS = {
    "humano": "#10b981",
    "bot": "#ef4444",
    "conflito": "#f59e0b",
    "indigo": "#6366f1",
    "slate": "#64748b",
    "teal": "#14b8a6",
    "sky": "#0ea5e9",
}

_BASE_LAYOUT = {
    "font": {"family": "Inter, system-ui, sans-serif", "size": 12},
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "margin": {"t": 20, "b": 40, "l": 50, "r": 20},
    "showlegend": True,
    "legend": {
        "orientation": "h",
        "yanchor": "bottom",
        "y": 1.02,
        "xanchor": "center",
        "x": 0.5,
        "font": {"size": 11},
    },
}

CRITERIA_GROUPS = {
    "percentil": "numerico",
    "media": "numerico",
    "moda": "numerico",
    "mediana": "numerico",
    "curtos": "comportamental",
    "intervalo": "comportamental",
    "identicos": "comportamental",
    "perfil": "comportamental",
}


# ═══════════════════════════════════════════════════════════════════
#  Helpers — batch loading por entry (usuário)
# ═══════════════════════════════════════════════════════════════════


def _get_datasets_filtered(
    db: Session, criteria: list[str] | None, video_id: str | None = None
) -> list[Dataset]:
    q = db.query(Dataset)
    if video_id:
        q = q.join(Collection, Dataset.collection_id == Collection.id).filter(
            Collection.video_id == video_id
        )
    datasets = q.order_by(Dataset.created_at.desc()).all()

    if criteria:
        datasets = [
            ds
            for ds in datasets
            if all(c in (ds.criteria_applied or []) for c in criteria)
        ]
    return datasets


def _get_entry_ids_for_datasets(
    db: Session, datasets: list[Dataset]
) -> dict[uuid.UUID, list[uuid.UUID]]:
    """Retorna ds_id → [entry_ids]."""
    if not datasets:
        return {}

    ds_ids = [ds.id for ds in datasets]
    all_entries = (
        db.query(DatasetEntry.dataset_id, DatasetEntry.id)
        .filter(DatasetEntry.dataset_id.in_(ds_ids))
        .all()
    )

    ds_entry_ids: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for dataset_id, entry_id in all_entries:
        ds_entry_ids[dataset_id].append(entry_id)

    return ds_entry_ids


def _get_annotations_and_conflicts(
    db: Session, all_entry_ids: list[uuid.UUID]
) -> tuple[
    dict[uuid.UUID, list[tuple[uuid.UUID, str]]],
    dict[uuid.UUID, tuple[str, str | None]],
]:
    """Retorna anotações e conflitos por entry_id."""
    anns_by_entry: dict[uuid.UUID, list[tuple[uuid.UUID, str]]] = defaultdict(list)
    conflict_map: dict[uuid.UUID, tuple[str, str | None]] = {}

    if not all_entry_ids:
        return anns_by_entry, conflict_map

    all_annotations = (
        db.query(Annotation.dataset_entry_id, Annotation.annotator_id, Annotation.label)
        .filter(Annotation.dataset_entry_id.in_(all_entry_ids))
        .all()
    )
    for entry_id, annotator_id, label in all_annotations:
        anns_by_entry[entry_id].append((annotator_id, label))

    all_conflicts = (
        db.query(
            AnnotationConflict.dataset_entry_id,
            AnnotationConflict.status,
            AnnotationConflict.resolved_label,
        )
        .filter(AnnotationConflict.dataset_entry_id.in_(all_entry_ids))
        .all()
    )
    for entry_id, conflict_status, resolved_label in all_conflicts:
        conflict_map[entry_id] = (conflict_status, resolved_label)

    return anns_by_entry, conflict_map


def _classify_entry(
    eid: uuid.UUID,
    anns_by_entry: dict[uuid.UUID, list[tuple[uuid.UUID, str]]],
    conflict_map: dict[uuid.UUID, tuple[str, str | None]],
) -> str | None:
    """Classifica um entry: 'bot', 'humano', 'conflito' ou None."""
    anns = anns_by_entry.get(eid, [])
    if not anns:
        return None

    if eid in conflict_map:
        entry_status, resolved_label = conflict_map[eid]
        if entry_status == "resolved" and resolved_label:
            return resolved_label
        return "conflito"

    labels = {label for _, label in anns}
    if len(labels) == 1:
        return labels.pop()
    return None


def _compute_agreement_rate(
    entry_ids: list[uuid.UUID],
    anns_by_entry: dict[uuid.UUID, list[tuple[uuid.UUID, str]]],
) -> float:
    """Agreement rate = consenso / total com 2+ anotações."""
    with_two = 0
    consensus = 0
    for eid in entry_ids:
        anns = anns_by_entry.get(eid, [])
        if len(anns) >= 2:
            with_two += 1
            labels = {label for _, label in anns}
            if len(labels) == 1:
                consensus += 1
    if with_two == 0:
        return 0.0
    return round(consensus / with_two, 4)


# ═══════════════════════════════════════════════════════════════════
#  Gráficos Plotly
# ═══════════════════════════════════════════════════════════════════


def _layout(**overrides) -> dict:
    layout = {**_BASE_LAYOUT}
    for key, val in overrides.items():
        if isinstance(val, dict) and key in layout and isinstance(layout[key], dict):
            layout[key] = {**layout[key], **val}
        else:
            layout[key] = val
    return layout


def _make_donut_chart(bots: int, humans: int, conflicts: int) -> str:
    total = bots + humans + conflicts
    fig = go.Figure(
        go.Pie(
            labels=["Humano", "Bot", "Conflito"],
            values=[humans, bots, conflicts],
            hole=0.55,
            marker_colors=[
                COLORS["humano"],
                COLORS["bot"],
                COLORS["conflito"],
            ],
            textinfo="label+percent",
            textfont_size=12,
            hovertemplate=(
                "<b>%{label}</b><br>" "%{value} usuários (%{percent})" "<extra></extra>"
            ),
            pull=[0, 0.03, 0],
        )
    )
    fig.update_layout(
        **_layout(
            annotations=[
                {
                    "text": f"<b>{total}</b>",
                    "x": 0.5,
                    "y": 0.5,
                    "font_size": 28,
                    "font_color": "#1e293b",
                    "showarrow": False,
                }
            ],
            margin={"t": 10, "b": 10, "l": 10, "r": 10},
        )
    )
    return pio.to_json(fig, validate=False)


def _make_comparativo_chart(datasets_data: list[dict]) -> str:
    names = [d["name"] for d in datasets_data]
    fig = go.Figure(
        data=[
            go.Bar(
                name="Humano",
                x=names,
                y=[d["humans"] for d in datasets_data],
                marker_color=COLORS["humano"],
                marker_line_width=0,
            ),
            go.Bar(
                name="Bot",
                x=names,
                y=[d["bots"] for d in datasets_data],
                marker_color=COLORS["bot"],
                marker_line_width=0,
            ),
            go.Bar(
                name="Conflito",
                x=names,
                y=[d["conflicts"] for d in datasets_data],
                marker_color=COLORS["conflito"],
                marker_line_width=0,
            ),
        ]
    )
    fig.update_layout(
        **_layout(
            barmode="group",
            bargap=0.25,
            bargroupgap=0.1,
            xaxis={
                "tickangle": -20,
                "tickfont": {"size": 10},
                "showgrid": False,
            },
            yaxis={
                "gridcolor": "#f1f5f9",
                "title": {"text": "Usuários", "font": {"size": 11}},
            },
        )
    )
    return pio.to_json(fig, validate=False)


def _make_timeline_chart(
    buckets: list[dict], title: str = "Evolução das Anotações"
) -> str:
    fig = go.Figure(
        go.Scatter(
            x=[b["date"] for b in buckets],
            y=[b["count"] for b in buckets],
            mode="lines+markers",
            line={"color": COLORS["indigo"], "width": 2.5},
            marker={"size": 7, "color": COLORS["indigo"]},
            fill="tozeroy",
            fillcolor="rgba(99,102,241,0.08)",
            hovertemplate=("<b>%{x|%d/%m/%Y}</b><br>" "%{y} anotações<extra></extra>"),
        )
    )
    fig.update_layout(
        **_layout(
            showlegend=False,
            xaxis={"showgrid": False},
            yaxis={
                "gridcolor": "#f1f5f9",
                "title": {"text": "Anotações", "font": {"size": 11}},
            },
        )
    )
    return pio.to_json(fig, validate=False)


def _make_bot_rate_chart(datasets_data: list[dict], orientation: str = "h") -> str:
    names = [d["name"] for d in datasets_data]
    rates = [d["bot_rate"] for d in datasets_data]
    colors = [COLORS["bot"] if r > 10 else COLORS["teal"] for r in rates]

    if orientation == "h":
        fig = go.Figure(
            go.Bar(
                y=names,
                x=rates,
                orientation="h",
                marker_color=colors,
                marker_line_width=0,
                text=[f"{r:.1f}%" for r in rates],
                textposition="outside",
                textfont={"size": 10},
                hovertemplate=("<b>%{y}</b><br>" "Taxa: %{x:.1f}%<extra></extra>"),
            )
        )
        fig.update_layout(
            **_layout(
                showlegend=False,
                xaxis={
                    "showgrid": False,
                    "title": {"text": "% de Bots", "font": {"size": 11}},
                },
                yaxis={"tickfont": {"size": 10}},
                margin={"l": 100},
            )
        )
    else:
        fig = go.Figure(
            go.Bar(
                x=names,
                y=rates,
                marker_color=colors,
                marker_line_width=0,
                text=[f"{r:.1f}%" for r in rates],
                textposition="outside",
                textfont={"size": 10},
                hovertemplate=("<b>%{x}</b><br>" "Taxa: %{y:.1f}%<extra></extra>"),
            )
        )
        fig.update_layout(
            **_layout(
                showlegend=False,
                yaxis={
                    "gridcolor": "#f1f5f9",
                    "title": {"text": "% de Bots", "font": {"size": 11}},
                },
            )
        )
    return pio.to_json(fig, validate=False)


def _make_criteria_effectiveness_chart(data: list[dict]) -> str:
    criterios = [d["criteria"].capitalize() for d in data]
    rates = [round(d["bot_rate"] * 100, 1) for d in data]
    colors = [COLORS["bot"] if r > 10 else COLORS["teal"] for r in rates]

    fig = go.Figure(
        go.Bar(
            y=criterios,
            x=rates,
            orientation="h",
            marker_color=colors,
            marker_line_width=0,
            text=[f"{r:.1f}%" for r in rates],
            textposition="outside",
            textfont={"size": 10},
            hovertemplate=("<b>%{y}</b><br>" "Taxa de bots: %{x:.1f}%<extra></extra>"),
        )
    )
    fig.update_layout(
        **_layout(
            showlegend=False,
            xaxis={
                "showgrid": False,
                "title": {
                    "text": "Taxa de bots (%)",
                    "font": {"size": 11},
                },
            },
            yaxis={"tickfont": {"size": 11}},
            margin={"l": 90},
        )
    )
    return pio.to_json(fig, validate=False)


def _make_agreement_by_dataset_chart(datasets_data: list[dict]) -> str:
    names = [d["name"] for d in datasets_data]
    rates = [d["agreement_rate"] for d in datasets_data]
    colors = [
        COLORS["humano"]
        if r >= 80
        else COLORS["conflito"]
        if r >= 50
        else COLORS["bot"]
        for r in rates
    ]

    fig = go.Figure(
        go.Bar(
            y=names,
            x=rates,
            orientation="h",
            marker_color=colors,
            marker_line_width=0,
            text=[f"{r:.0f}%" for r in rates],
            textposition="outside",
            textfont={"size": 10},
            hovertemplate=("<b>%{y}</b><br>" "Concordância: %{x:.1f}%<extra></extra>"),
        )
    )
    fig.update_layout(
        **_layout(
            showlegend=False,
            xaxis={
                "range": [0, 110],
                "showgrid": False,
                "title": {
                    "text": "Concordância (%)",
                    "font": {"size": 11},
                },
            },
            yaxis={"tickfont": {"size": 10}},
            margin={"l": 100},
        )
    )
    return pio.to_json(fig, validate=False)


def _make_comment_timeline_chart(buckets: list[dict]) -> str:
    fig = go.Figure(
        go.Bar(
            x=[b["date"] for b in buckets],
            y=[b["count"] for b in buckets],
            marker_color=COLORS["teal"],
            marker_line_width=0,
            hovertemplate=(
                "<b>%{x|%d/%m/%Y}</b><br>" "%{y} comentários<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        **_layout(
            showlegend=False,
            xaxis={"showgrid": False},
            yaxis={
                "gridcolor": "#f1f5f9",
                "title": {"text": "Comentários", "font": {"size": 11}},
            },
        )
    )
    return pio.to_json(fig, validate=False)


def _make_user_progress_chart(datasets_data: list[dict]) -> str:
    names = [d["name"] for d in datasets_data]
    percents = [d["percent"] for d in datasets_data]
    colors = [
        COLORS["humano"] if p == 100 else COLORS["indigo"] if p > 0 else "#cbd5e1"
        for p in percents
    ]
    fig = go.Figure(
        go.Bar(
            y=names,
            x=percents,
            orientation="h",
            marker_color=colors,
            marker_line_width=0,
            text=[f"{p:.0f}%" for p in percents],
            textposition="outside",
            textfont={"size": 10},
            hovertemplate=("<b>%{y}</b><br>" "%{x:.0f}% concluído<extra></extra>"),
        )
    )
    fig.update_layout(
        **_layout(
            showlegend=False,
            xaxis={
                "range": [0, 110],
                "showgrid": False,
                "showticklabels": False,
            },
            yaxis={"tickfont": {"size": 10}},
            margin={"l": 100},
        )
    )
    return pio.to_json(fig, validate=False)


# ═══════════════════════════════════════════════════════════════════
#  Endpoints — lógica principal
# ═══════════════════════════════════════════════════════════════════


def get_global_dashboard(db: Session, criteria: list[str] | None = None) -> dict:
    """Seção 1 — Visão Geral."""
    datasets = _get_datasets_filtered(db, criteria)
    ds_entry_ids = _get_entry_ids_for_datasets(db, datasets)

    all_eids = list({eid for eids in ds_entry_ids.values() for eid in eids})
    anns_by_entry, conflict_map = _get_annotations_and_conflicts(db, all_eids)

    total_bots = 0
    total_humans = 0
    total_conflicts = 0
    pending_conflicts = 0
    annotated_eids: set[uuid.UUID] = set()

    for eid in all_eids:
        classification = _classify_entry(eid, anns_by_entry, conflict_map)
        if classification == "bot":
            total_bots += 1
        elif classification == "humano":
            total_humans += 1
        elif classification == "conflito":
            total_conflicts += 1

        if anns_by_entry.get(eid):
            annotated_eids.add(eid)

    for eid in all_eids:
        if eid in conflict_map:
            entry_status, _ = conflict_map[eid]
            if entry_status == "pending":
                pending_conflicts += 1

    total_all_conflicts = sum(1 for eid in all_eids if eid in conflict_map)
    agreement_rate = _compute_agreement_rate(all_eids, anns_by_entry)

    datasets_chart_data = []
    for ds in datasets:
        eids = ds_entry_ids.get(ds.id, [])
        bots = humans = conflicts = annotated = 0
        for eid in eids:
            cl = _classify_entry(eid, anns_by_entry, conflict_map)
            if cl == "bot":
                bots += 1
            elif cl == "humano":
                humans += 1
            elif cl == "conflito":
                conflicts += 1
            if anns_by_entry.get(eid):
                annotated += 1
        bot_rate = (bots / annotated * 100) if annotated > 0 else 0.0
        ds_agreement = _compute_agreement_rate(eids, anns_by_entry)
        datasets_chart_data.append(
            {
                "name": ds.name,
                "bots": bots,
                "humans": humans,
                "conflicts": conflicts,
                "bot_rate": bot_rate,
                "agreement_rate": round(ds_agreement * 100, 1),
            }
        )

    annotation_buckets = _get_annotation_timeline(db, all_eids)

    criteria_data = _compute_criteria_effectiveness(
        db, datasets, ds_entry_ids, anns_by_entry, conflict_map
    )

    total_in_datasets = len(all_eids)
    total_annotated_count = len(annotated_eids)
    annotation_progress = (
        round(total_annotated_count / total_in_datasets * 100, 1)
        if total_in_datasets > 0
        else 0.0
    )

    return {
        "summary": {
            "total_datasets": len(datasets),
            "total_users_annotated": total_annotated_count,
            "total_users_in_datasets": total_in_datasets,
            "annotation_progress": annotation_progress,
            "total_bots": total_bots,
            "total_humans": total_humans,
            "total_conflicts": total_all_conflicts,
            "pending_conflicts": pending_conflicts,
            "agreement_rate": agreement_rate,
        },
        "active_criteria_filter": criteria or [],
        "label_distribution_chart": _make_donut_chart(
            total_bots, total_humans, total_conflicts
        ),
        "comparativo_por_dataset_chart": _make_comparativo_chart(datasets_chart_data),
        "annotations_over_time_chart": _make_timeline_chart(annotation_buckets),
        "bot_rate_by_dataset_chart": _make_bot_rate_chart(datasets_chart_data),
        "agreement_by_dataset_chart": _make_agreement_by_dataset_chart(
            datasets_chart_data
        ),
        "criteria_effectiveness_chart": _make_criteria_effectiveness_chart(
            criteria_data
        ),
    }


def get_video_dashboard(
    db: Session, video_id: str, criteria: list[str] | None = None
) -> dict:
    """Seção 2 — Por Vídeo."""
    total_collected = (
        db.query(func.count(Comment.id))
        .join(Collection)
        .filter(Collection.video_id == video_id)
        .scalar()
    ) or 0

    datasets = _get_datasets_filtered(db, criteria, video_id=video_id)
    ds_entry_ids = _get_entry_ids_for_datasets(db, datasets)

    all_eids = list({eid for eids in ds_entry_ids.values() for eid in eids})
    anns_by_entry, conflict_map = _get_annotations_and_conflicts(db, all_eids)

    total_bots = 0
    total_humans = 0
    total_conflicts = 0
    pending_conflicts = 0
    annotated_count = 0

    for eid in all_eids:
        cl = _classify_entry(eid, anns_by_entry, conflict_map)
        if cl == "bot":
            total_bots += 1
        elif cl == "humano":
            total_humans += 1
        elif cl == "conflito":
            total_conflicts += 1
        if anns_by_entry.get(eid):
            annotated_count += 1
        if eid in conflict_map and conflict_map[eid][0] == "pending":
            pending_conflicts += 1

    all_conflicts_count = sum(1 for eid in all_eids if eid in conflict_map)
    agreement_rate = _compute_agreement_rate(all_eids, anns_by_entry)

    datasets_chart_data = []
    for ds in datasets:
        eids = ds_entry_ids.get(ds.id, [])
        bots = humans = conflicts = annotated = 0
        for eid in eids:
            cl = _classify_entry(eid, anns_by_entry, conflict_map)
            if cl == "bot":
                bots += 1
            elif cl == "humano":
                humans += 1
            elif cl == "conflito":
                conflicts += 1
            if anns_by_entry.get(eid):
                annotated += 1
        bot_rate = (bots / annotated * 100) if annotated > 0 else 0.0
        datasets_chart_data.append(
            {
                "name": ds.name,
                "bots": bots,
                "humans": humans,
                "conflicts": conflicts,
                "bot_rate": bot_rate,
            }
        )

    criteria_rates = _compute_bot_rate_by_criteria(
        datasets, ds_entry_ids, anns_by_entry, conflict_map
    )

    comment_timeline = _get_comment_published_timeline(db, video_id)
    highlights = _compute_video_highlights(db, video_id)

    return {
        "video_id": video_id,
        "summary": {
            "total_comments_collected": total_collected,
            "total_users_in_datasets": len(all_eids),
            "total_annotated": annotated_count,
            "total_bots": total_bots,
            "total_humans": total_humans,
            "total_conflicts": all_conflicts_count,
            "pending_conflicts": pending_conflicts,
            "agreement_rate": agreement_rate,
        },
        "highlights": highlights,
        "active_criteria_filter": criteria or [],
        "label_distribution_chart": _make_donut_chart(
            total_bots, total_humans, total_conflicts
        ),
        "comparativo_por_dataset_chart": _make_comparativo_chart(datasets_chart_data),
        "bot_rate_by_criteria_chart": _make_bot_rate_chart(
            criteria_rates, orientation="h"
        ),
        "comment_timeline_chart": _make_comment_timeline_chart(comment_timeline),
    }


def get_user_dashboard(db: Session, user_id: uuid.UUID) -> dict:
    """Seção 3 — Meu Progresso."""
    datasets = db.query(Dataset).order_by(Dataset.created_at.desc()).all()
    if not datasets:
        return _empty_user_response()

    ds_entry_ids = _get_entry_ids_for_datasets(db, datasets)
    all_eids = list({eid for eids in ds_entry_ids.values() for eid in eids})

    # Anotações do usuário autenticado (por entry)
    my_annotations: dict[uuid.UUID, str] = {}
    if all_eids:
        rows = (
            db.query(Annotation.dataset_entry_id, Annotation.label)
            .filter(
                Annotation.dataset_entry_id.in_(all_eids),
                Annotation.annotator_id == user_id,
            )
            .all()
        )
        my_annotations = {eid: label for eid, label in rows}

    # Conflitos gerados pelo usuário
    my_conflict_eids: set[uuid.UUID] = set()
    if all_eids:
        conflict_rows = (
            db.query(AnnotationConflict.dataset_entry_id)
            .join(Annotation, AnnotationConflict.annotation_a_id == Annotation.id)
            .filter(
                AnnotationConflict.dataset_entry_id.in_(all_eids),
                Annotation.annotator_id == user_id,
            )
            .all()
        )
        my_conflict_eids.update(r[0] for r in conflict_rows)
        conflict_rows_b = (
            db.query(AnnotationConflict.dataset_entry_id)
            .join(Annotation, AnnotationConflict.annotation_b_id == Annotation.id)
            .filter(
                AnnotationConflict.dataset_entry_id.in_(all_eids),
                Annotation.annotator_id == user_id,
            )
            .all()
        )
        my_conflict_eids.update(r[0] for r in conflict_rows_b)

    # collection_id por dataset
    ds_col_map = {ds.id: ds.collection_id for ds in datasets}
    col_video_map: dict[uuid.UUID, str] = {}
    col_ids = list({ds.collection_id for ds in datasets})
    if col_ids:
        cols = (
            db.query(Collection.id, Collection.video_id)
            .filter(Collection.id.in_(col_ids))
            .all()
        )
        col_video_map = {c_id: vid for c_id, vid in cols}

    ds_progress = []
    total_annotated = 0
    total_pending = 0
    total_bots = 0
    total_humans = 0
    total_conflicts = 0
    datasets_completed = 0
    datasets_with_data = 0

    for ds in datasets:
        eids = ds_entry_ids.get(ds.id, [])
        if not eids:
            continue

        annotated_by_me = sum(1 for eid in eids if eid in my_annotations)
        pending = len(eids) - annotated_by_me

        datasets_with_data += 1

        my_bots = sum(1 for eid in eids if my_annotations.get(eid) == "bot")
        my_humans = sum(1 for eid in eids if my_annotations.get(eid) == "humano")
        my_conflicts = sum(1 for eid in eids if eid in my_conflict_eids)

        percent = round(annotated_by_me / len(eids) * 100, 1) if eids else 0.0

        if annotated_by_me == len(eids):
            ds_status = "completed"
            datasets_completed += 1
        elif annotated_by_me > 0:
            ds_status = "in_progress"
        else:
            ds_status = "not_started"

        total_annotated += annotated_by_me
        total_pending += pending
        total_bots += my_bots
        total_humans += my_humans
        total_conflicts += my_conflicts

        ds_progress.append(
            {
                "dataset_id": ds.id,
                "dataset_name": ds.name,
                "video_id": col_video_map.get(ds_col_map[ds.id], ""),
                "total_users": len(eids),
                "annotated_by_me": annotated_by_me,
                "pending": pending,
                "percent_complete": percent,
                "my_bots": my_bots,
                "my_conflicts": my_conflicts,
                "status": ds_status,
            }
        )

    datasets_pending = datasets_with_data - datasets_completed

    my_timeline = _get_user_annotation_timeline(db, user_id)

    progress_chart_data = [
        {"name": d["dataset_name"], "percent": d["percent_complete"]}
        for d in ds_progress
    ]

    return {
        "summary": {
            "total_datasets_assigned": datasets_with_data,
            "datasets_completed": datasets_completed,
            "datasets_pending": datasets_pending,
            "total_annotated": total_annotated,
            "total_pending": total_pending,
            "bots": total_bots,
            "humans": total_humans,
            "conflicts_generated": total_conflicts,
        },
        "datasets": ds_progress,
        "my_label_distribution_chart": _make_donut_chart(total_bots, total_humans, 0),
        "my_progress_by_dataset_chart": _make_user_progress_chart(progress_chart_data),
        "my_annotations_over_time_chart": _make_timeline_chart(
            my_timeline, title="Minhas Anotações ao Longo do Tempo"
        ),
    }


def get_bot_users(
    db: Session,
    dataset_id: str | None = None,
    video_id: str | None = None,
    author: str | None = None,
    search: str | None = None,
    criteria_filter: list[str] | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Tabela de usuários classificados como bot."""
    q = (
        db.query(
            Dataset.name.label("dataset_name"),
            Dataset.id.label("dataset_id"),
            DatasetEntry.id.label("entry_id"),
            DatasetEntry.author_display_name,
            DatasetEntry.author_channel_id,
        )
        .join(DatasetEntry, DatasetEntry.dataset_id == Dataset.id)
        .join(Annotation, Annotation.dataset_entry_id == DatasetEntry.id)
        .filter(Annotation.label == "bot")
    )

    if dataset_id:
        q = q.filter(Dataset.id == dataset_id)
    if video_id:
        q = q.join(Collection, Collection.id == Dataset.collection_id).filter(
            Collection.video_id == video_id
        )
    if author:
        q = q.filter(DatasetEntry.author_display_name.ilike(f"%{author}%"))
    if criteria_filter:
        for crit in criteria_filter:
            q = q.filter(Dataset.criteria_applied.any(crit))

    q = q.distinct(DatasetEntry.id)
    total = q.count()

    rows = (
        q.order_by(DatasetEntry.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    entry_ids = [r.entry_id for r in rows]

    # Batch: conflitos
    conflict_status_map: dict[uuid.UUID, str] = {}
    if entry_ids:
        conflicts = (
            db.query(AnnotationConflict.dataset_entry_id, AnnotationConflict.status)
            .filter(AnnotationConflict.dataset_entry_id.in_(entry_ids))
            .all()
        )
        conflict_status_map = {eid: st for eid, st in conflicts}

    # Batch: concordância + nº de anotadores
    concordance_map: dict[uuid.UUID, int] = {}
    annotators_map: dict[uuid.UUID, int] = {}
    if entry_ids:
        ann_counts = (
            db.query(
                Annotation.dataset_entry_id,
                func.count(Annotation.id).label("total"),
                func.count(
                    case(
                        (Annotation.label == "bot", 1),
                    )
                ).label("bot_count"),
            )
            .filter(Annotation.dataset_entry_id.in_(entry_ids))
            .group_by(Annotation.dataset_entry_id)
            .all()
        )
        for eid, total_anns, bot_count in ann_counts:
            annotators_map[eid] = total_anns
            if total_anns > 0:
                concordance_map[eid] = round(bot_count / total_anns * 100)

    # Batch: critérios + comment_count
    ds_ids = list({r.dataset_id for r in rows})
    author_ids = list({r.author_channel_id for r in rows if r.author_channel_id})
    criteria_map: dict[str, list[str]] = {}
    if ds_ids and author_ids:
        entries = (
            db.query(
                DatasetEntry.author_channel_id,
                DatasetEntry.matched_criteria,
            )
            .filter(
                DatasetEntry.dataset_id.in_(ds_ids),
                DatasetEntry.author_channel_id.in_(author_ids),
            )
            .all()
        )
        for aid, matched in entries:
            if aid not in criteria_map:
                criteria_map[aid] = []
            for c in matched or []:
                if c not in criteria_map[aid]:
                    criteria_map[aid].append(c)

    # Comment counts
    cc_map: dict[uuid.UUID, int] = {}
    if entry_ids:
        comment_counts = (
            db.query(
                DatasetEntry.id,
                func.count(Comment.id).label("cc"),
            )
            .join(Dataset, Dataset.id == DatasetEntry.dataset_id)
            .join(
                Comment,
                (Comment.collection_id == Dataset.collection_id)
                & (Comment.author_channel_id == DatasetEntry.author_channel_id),
            )
            .filter(DatasetEntry.id.in_(entry_ids))
            .group_by(DatasetEntry.id)
            .all()
        )
        cc_map = {eid: cc for eid, cc in comment_counts}

    items = []
    for row in rows:
        items.append(
            {
                "dataset_name": row.dataset_name,
                "author_display_name": row.author_display_name,
                "author_channel_id": row.author_channel_id,
                "comment_count": cc_map.get(row.entry_id, 0),
                "concordance_pct": concordance_map.get(row.entry_id, 0),
                "conflict_status": conflict_status_map.get(row.entry_id),
                "annotators_count": annotators_map.get(row.entry_id, 0),
                "criteria": criteria_map.get(row.author_channel_id, []),
            }
        )

    return {"total": total, "items": items}


def get_criteria_effectiveness(db: Session, video_id: str | None = None) -> list[dict]:
    datasets = _get_datasets_filtered(db, criteria=None, video_id=video_id)
    if not datasets:
        return []

    ds_entry_ids = _get_entry_ids_for_datasets(db, datasets)
    all_eids = list({eid for eids in ds_entry_ids.values() for eid in eids})
    anns_by_entry, conflict_map = _get_annotations_and_conflicts(db, all_eids)

    return _compute_criteria_effectiveness(
        db, datasets, ds_entry_ids, anns_by_entry, conflict_map
    )


# ═══════════════════════════════════════════════════════════════════
#  Helpers internos
# ═══════════════════════════════════════════════════════════════════


def _get_annotation_timeline(db: Session, entry_ids: list[uuid.UUID]) -> list[dict]:
    if not entry_ids:
        return []
    rows = (
        db.query(
            cast(Annotation.annotated_at, Date).label("day"),
            func.count(Annotation.id),
        )
        .filter(Annotation.dataset_entry_id.in_(entry_ids))
        .group_by("day")
        .order_by("day")
        .all()
    )
    return [{"date": str(day), "count": count} for day, count in rows]


def _get_user_annotation_timeline(db: Session, user_id: uuid.UUID) -> list[dict]:
    rows = (
        db.query(
            cast(Annotation.annotated_at, Date).label("day"),
            func.count(Annotation.id),
        )
        .filter(Annotation.annotator_id == user_id)
        .group_by("day")
        .order_by("day")
        .all()
    )
    return [{"date": str(day), "count": count} for day, count in rows]


def _get_comment_published_timeline(db: Session, video_id: str) -> list[dict]:
    rows = (
        db.query(
            cast(Comment.published_at, Date).label("day"),
            func.count(Comment.id),
        )
        .join(Collection)
        .filter(Collection.video_id == video_id)
        .group_by("day")
        .order_by("day")
        .all()
    )
    return [{"date": str(day), "count": count} for day, count in rows]


def _compute_bot_rate_by_criteria(
    datasets: list[Dataset],
    ds_entry_ids: dict[uuid.UUID, list[uuid.UUID]],
    anns_by_entry: dict[uuid.UUID, list[tuple[uuid.UUID, str]]],
    conflict_map: dict[uuid.UUID, tuple[str, str | None]],
) -> list[dict]:
    criteria_stats: dict[str, dict] = {}

    for ds in datasets:
        eids = ds_entry_ids.get(ds.id, [])
        if not eids:
            continue

        bots = sum(
            1
            for eid in eids
            if _classify_entry(eid, anns_by_entry, conflict_map) == "bot"
        )
        annotated = sum(1 for eid in eids if anns_by_entry.get(eid))

        for crit in ds.criteria_applied or []:
            if crit not in criteria_stats:
                criteria_stats[crit] = {"bots": 0, "annotated": 0}
            criteria_stats[crit]["bots"] += bots
            criteria_stats[crit]["annotated"] += annotated

    result = []
    for crit, stats in sorted(criteria_stats.items()):
        bot_rate = (
            stats["bots"] / stats["annotated"] * 100 if stats["annotated"] > 0 else 0
        )
        result.append({"name": crit, "bot_rate": bot_rate})
    return result


def _compute_criteria_effectiveness(
    db: Session,
    datasets: list[Dataset],
    ds_entry_ids: dict[uuid.UUID, list[uuid.UUID]],
    anns_by_entry: dict[uuid.UUID, list[tuple[uuid.UUID, str]]],
    conflict_map: dict[uuid.UUID, tuple[str, str | None]],
) -> list[dict]:
    criteria_stats: dict[str, dict] = {}

    for ds in datasets:
        eids = ds_entry_ids.get(ds.id, [])
        bots = sum(
            1
            for eid in eids
            if _classify_entry(eid, anns_by_entry, conflict_map) == "bot"
        )
        for crit in ds.criteria_applied or []:
            if crit not in criteria_stats:
                criteria_stats[crit] = {
                    "total_datasets": 0,
                    "total_users_selected": 0,
                    "total_bots": 0,
                }
            criteria_stats[crit]["total_datasets"] += 1
            criteria_stats[crit]["total_users_selected"] += len(eids)
            criteria_stats[crit]["total_bots"] += bots

    ordered_criteria = [
        "percentil",
        "media",
        "moda",
        "mediana",
        "curtos",
        "intervalo",
        "identicos",
        "perfil",
    ]

    result = []
    for crit in ordered_criteria:
        if crit not in criteria_stats:
            continue
        stats = criteria_stats[crit]
        bot_rate = (
            stats["total_bots"] / stats["total_users_selected"]
            if stats["total_users_selected"] > 0
            else 0.0
        )
        result.append(
            {
                "criteria": crit,
                "group": CRITERIA_GROUPS.get(crit, "outro"),
                "total_datasets": stats["total_datasets"],
                "total_users_selected": stats["total_users_selected"],
                "total_bots": stats["total_bots"],
                "bot_rate": round(bot_rate, 4),
            }
        )
    return result


def _compute_video_highlights(db: Session, video_id: str) -> list[dict]:
    base = db.query(Comment).join(Collection).filter(Collection.video_id == video_id)
    highlights: list[dict] = []

    top_author = (
        db.query(
            Comment.author_display_name,
            func.count(Comment.id).label("cnt"),
        )
        .join(Collection)
        .filter(Collection.video_id == video_id)
        .group_by(Comment.author_display_name)
        .order_by(func.count(Comment.id).desc())
        .first()
    )
    if top_author:
        highlights.append(
            {
                "label": "Autor mais ativo",
                "value": top_author[0],
                "detail": f"{top_author[1]} comentários",
            }
        )

    top_replies = base.order_by(Comment.reply_count.desc()).first()
    if top_replies and top_replies.reply_count > 0:
        text = top_replies.text_original
        preview = (text[:60] + "...") if len(text) > 60 else text
        highlights.append(
            {
                "label": "Mais respostas",
                "value": f"{top_replies.reply_count} respostas",
                "detail": preview,
            }
        )

    top_likes = base.order_by(Comment.like_count.desc()).first()
    if top_likes and top_likes.like_count > 0:
        text = top_likes.text_original
        preview = (text[:60] + "...") if len(text) > 60 else text
        highlights.append(
            {
                "label": "Mais curtido",
                "value": f"{top_likes.like_count} likes",
                "detail": preview,
            }
        )

    newest = (
        base.filter(Comment.author_channel_published_at.isnot(None))
        .order_by(Comment.author_channel_published_at.desc())
        .first()
    )
    if newest and newest.author_channel_published_at:
        dt = newest.author_channel_published_at
        highlights.append(
            {
                "label": "Conta mais nova",
                "value": newest.author_display_name,
                "detail": f"Criada em {dt.strftime('%d/%m/%Y')}",
            }
        )

    oldest = (
        base.filter(Comment.author_channel_published_at.isnot(None))
        .order_by(Comment.author_channel_published_at.asc())
        .first()
    )
    if (
        oldest
        and oldest.author_channel_published_at
        and oldest.author_channel_published_at.year > 1970
    ):
        dt = oldest.author_channel_published_at
        highlights.append(
            {
                "label": "Conta mais antiga",
                "value": oldest.author_display_name,
                "detail": f"Criada em {dt.strftime('%d/%m/%Y')}",
            }
        )

    avg_likes = (
        db.query(func.avg(Comment.like_count))
        .join(Collection)
        .filter(Collection.video_id == video_id)
        .scalar()
    )
    if avg_likes is not None:
        highlights.append(
            {
                "label": "Média de likes",
                "value": f"{avg_likes:.1f}",
                "detail": "Por comentário",
            }
        )

    return highlights


def _empty_user_response() -> dict:
    return {
        "summary": {
            "total_datasets_assigned": 0,
            "datasets_completed": 0,
            "datasets_pending": 0,
            "total_annotated": 0,
            "total_pending": 0,
            "bots": 0,
            "humans": 0,
            "conflicts_generated": 0,
        },
        "datasets": [],
        "my_label_distribution_chart": _make_donut_chart(0, 0, 0),
        "my_progress_by_dataset_chart": _make_user_progress_chart([]),
        "my_annotations_over_time_chart": _make_timeline_chart(
            [], title="Minhas Anotações ao Longo do Tempo"
        ),
    }

"""Serviço da US-06 — Dashboard de Análise.

Agregações SQL + geração de gráficos Plotly (JSON).
Regra: nunca carregar registros em Python para calcular —
usar func.count, func.avg, GROUP BY no SQLAlchemy.
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

# Layout base compartilhado por todos os gráficos
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
#  Helpers — batch loading reutilizável
# ═══════════════════════════════════════════════════════════════════


def _get_datasets_filtered(
    db: Session, criteria: list[str] | None, video_id: str | None = None
) -> list[Dataset]:
    """Retorna datasets, opcionalmente filtrados por critério e/ou vídeo."""
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


def _get_comment_ids_for_datasets(
    db: Session, datasets: list[Dataset]
) -> tuple[
    dict[uuid.UUID, list[uuid.UUID]],
    dict[uuid.UUID, tuple[uuid.UUID, str]],
]:
    """Retorna (ds_id → [comment_ids], comment_id → (collection_id, author_channel_id)).

    Batch loading sem N+1.
    """
    if not datasets:
        return {}, {}

    ds_ids = [ds.id for ds in datasets]

    # entries → authors por dataset
    all_entries = (
        db.query(DatasetEntry.dataset_id, DatasetEntry.author_channel_id)
        .filter(DatasetEntry.dataset_id.in_(ds_ids))
        .all()
    )
    authors_by_ds: dict[uuid.UUID, list[str]] = defaultdict(list)
    for dataset_id, author_channel_id in all_entries:
        authors_by_ds[dataset_id].append(author_channel_id)

    # pares (collection_id, author_ids) para buscar comentários
    ds_col_map = {ds.id: ds.collection_id for ds in datasets}
    col_authors: dict[uuid.UUID, set[str]] = defaultdict(set)
    for ds in datasets:
        for author_id in authors_by_ds.get(ds.id, []):
            col_authors[ds.collection_id].add(author_id)

    # batch: todos os comentários relevantes
    comment_info: dict[uuid.UUID, tuple[uuid.UUID, str]] = {}
    comments_by_col_author: dict[tuple[uuid.UUID, str], list[uuid.UUID]] = defaultdict(
        list
    )

    for col_id, author_set in col_authors.items():
        if not author_set:
            continue
        rows = (
            db.query(Comment.id, Comment.collection_id, Comment.author_channel_id)
            .filter(
                Comment.collection_id == col_id,
                Comment.author_channel_id.in_(list(author_set)),
            )
            .all()
        )
        for cid, c_col_id, c_author_id in rows:
            comment_info[cid] = (c_col_id, c_author_id)
            comments_by_col_author[(c_col_id, c_author_id)].append(cid)

    # montar comment_ids por dataset
    ds_comment_ids: dict[uuid.UUID, list[uuid.UUID]] = {}
    for ds in datasets:
        ids: list[uuid.UUID] = []
        for author_id in authors_by_ds.get(ds.id, []):
            ids.extend(comments_by_col_author.get((ds_col_map[ds.id], author_id), []))
        ds_comment_ids[ds.id] = ids

    return ds_comment_ids, comment_info


def _get_annotations_and_conflicts(
    db: Session, all_comment_ids: list[uuid.UUID]
) -> tuple[
    dict[uuid.UUID, list[tuple[uuid.UUID, str]]],
    dict[uuid.UUID, tuple[str, str | None]],
]:
    """Retorna anotações e conflitos por comment_id."""
    anns_by_comment: dict[uuid.UUID, list[tuple[uuid.UUID, str]]] = defaultdict(list)
    conflict_map: dict[uuid.UUID, tuple[str, str | None]] = {}

    if not all_comment_ids:
        return anns_by_comment, conflict_map

    all_annotations = (
        db.query(Annotation.comment_id, Annotation.annotator_id, Annotation.label)
        .filter(Annotation.comment_id.in_(all_comment_ids))
        .all()
    )
    for comment_id, annotator_id, label in all_annotations:
        anns_by_comment[comment_id].append((annotator_id, label))

    all_conflicts = (
        db.query(
            AnnotationConflict.comment_id,
            AnnotationConflict.status,
            AnnotationConflict.resolved_label,
        )
        .filter(AnnotationConflict.comment_id.in_(all_comment_ids))
        .all()
    )
    for comment_id, status, resolved_label in all_conflicts:
        conflict_map[comment_id] = (status, resolved_label)

    return anns_by_comment, conflict_map


def _classify_comment(
    cid: uuid.UUID,
    anns_by_comment: dict[uuid.UUID, list[tuple[uuid.UUID, str]]],
    conflict_map: dict[uuid.UUID, tuple[str, str | None]],
) -> str | None:
    """Classifica um comentário: 'bot', 'humano', 'conflito' ou None (sem anotação)."""
    anns = anns_by_comment.get(cid, [])
    if not anns:
        return None

    if cid in conflict_map:
        status, resolved_label = conflict_map[cid]
        if status == "resolved" and resolved_label:
            return resolved_label
        return "conflito"

    labels = {label for _, label in anns}
    if len(labels) == 1:
        return labels.pop()
    return None


def _compute_agreement_rate(
    comment_ids: list[uuid.UUID],
    anns_by_comment: dict[uuid.UUID, list[tuple[uuid.UUID, str]]],
) -> float:
    """Agreement rate = consenso / total com 2+ anotações."""
    with_two = 0
    consensus = 0
    for cid in comment_ids:
        anns = anns_by_comment.get(cid, [])
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
    """Mescla layout base com overrides específicos do gráfico."""
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
                "<b>%{label}</b><br>"
                "%{value} comentários (%{percent})"
                "<extra></extra>"
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
                "title": {"text": "Comentários", "font": {"size": 11}},
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
    """Bar horizontal simples: taxa de bots (%) por critério."""
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


def _make_agreement_by_dataset_chart(
    datasets_data: list[dict],
) -> str:
    """Bar horizontal: concordância (%) por dataset."""
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
    ds_comment_ids, comment_info = _get_comment_ids_for_datasets(db, datasets)

    all_cids = []
    for cids in ds_comment_ids.values():
        all_cids.extend(cids)
    all_cids = list(set(all_cids))

    anns_by_comment, conflict_map = _get_annotations_and_conflicts(db, all_cids)

    # KPIs
    total_bots = 0
    total_humans = 0
    total_conflicts = 0
    pending_conflicts = 0
    annotated_cids: set[uuid.UUID] = set()

    for cid in all_cids:
        classification = _classify_comment(cid, anns_by_comment, conflict_map)
        if classification == "bot":
            total_bots += 1
        elif classification == "humano":
            total_humans += 1
        elif classification == "conflito":
            total_conflicts += 1

        if anns_by_comment.get(cid):
            annotated_cids.add(cid)

    # conflitos totais e pendentes
    for cid in all_cids:
        if cid in conflict_map:
            status, _ = conflict_map[cid]
            if status == "pending":
                pending_conflicts += 1

    total_all_conflicts = sum(1 for cid in all_cids if cid in conflict_map)
    agreement_rate = _compute_agreement_rate(all_cids, anns_by_comment)

    # Dados por dataset para gráficos
    datasets_chart_data = []
    for ds in datasets:
        cids = ds_comment_ids.get(ds.id, [])
        bots = humans = conflicts = 0
        annotated = 0
        for cid in cids:
            cl = _classify_comment(cid, anns_by_comment, conflict_map)
            if cl == "bot":
                bots += 1
            elif cl == "humano":
                humans += 1
            elif cl == "conflito":
                conflicts += 1
            if anns_by_comment.get(cid):
                annotated += 1
        bot_rate = (bots / annotated * 100) if annotated > 0 else 0.0
        ds_agreement = _compute_agreement_rate(cids, anns_by_comment)
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

    # Timeline de anotações (agrupado por dia)
    annotation_buckets = _get_annotation_timeline(db, all_cids)

    # Eficácia por critério
    criteria_data = _compute_criteria_effectiveness(
        db, datasets, ds_comment_ids, anns_by_comment, conflict_map
    )

    # Progresso geral
    total_in_datasets = len(all_cids)
    total_annotated_count = len(annotated_cids)
    annotation_progress = (
        round(total_annotated_count / total_in_datasets * 100, 1)
        if total_in_datasets > 0
        else 0.0
    )

    return {
        "summary": {
            "total_datasets": len(datasets),
            "total_comments_annotated": total_annotated_count,
            "total_comments_in_datasets": total_in_datasets,
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
    # Total de comentários coletados para este vídeo
    total_collected = (
        db.query(func.count(Comment.id))
        .join(Collection)
        .filter(Collection.video_id == video_id)
        .scalar()
    ) or 0

    datasets = _get_datasets_filtered(db, criteria, video_id=video_id)
    ds_comment_ids, comment_info = _get_comment_ids_for_datasets(db, datasets)

    all_cids = list({cid for cids in ds_comment_ids.values() for cid in cids})
    anns_by_comment, conflict_map = _get_annotations_and_conflicts(db, all_cids)

    total_bots = 0
    total_humans = 0
    total_conflicts = 0
    pending_conflicts = 0
    annotated_count = 0

    for cid in all_cids:
        cl = _classify_comment(cid, anns_by_comment, conflict_map)
        if cl == "bot":
            total_bots += 1
        elif cl == "humano":
            total_humans += 1
        elif cl == "conflito":
            total_conflicts += 1
        if anns_by_comment.get(cid):
            annotated_count += 1
        if cid in conflict_map and conflict_map[cid][0] == "pending":
            pending_conflicts += 1

    all_conflicts_count = sum(1 for cid in all_cids if cid in conflict_map)
    agreement_rate = _compute_agreement_rate(all_cids, anns_by_comment)

    # Dados por dataset
    datasets_chart_data = []
    for ds in datasets:
        cids = ds_comment_ids.get(ds.id, [])
        bots = humans = conflicts = annotated = 0
        for cid in cids:
            cl = _classify_comment(cid, anns_by_comment, conflict_map)
            if cl == "bot":
                bots += 1
            elif cl == "humano":
                humans += 1
            elif cl == "conflito":
                conflicts += 1
            if anns_by_comment.get(cid):
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

    # Taxa de bots por critério neste vídeo
    criteria_rates = _compute_bot_rate_by_criteria(
        datasets, ds_comment_ids, anns_by_comment, conflict_map
    )

    # Timeline de comentários postados
    comment_timeline = _get_comment_published_timeline(db, video_id)

    # Destaques do vídeo
    highlights = _compute_video_highlights(db, video_id)

    return {
        "video_id": video_id,
        "summary": {
            "total_comments_collected": total_collected,
            "total_comments_in_datasets": len(all_cids),
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
    # Todos os datasets (sem filtro — o usuário pode anotar em qualquer um)
    datasets = db.query(Dataset).order_by(Dataset.created_at.desc()).all()
    if not datasets:
        return _empty_user_response()

    ds_comment_ids, comment_info = _get_comment_ids_for_datasets(db, datasets)
    all_cids = list({cid for cids in ds_comment_ids.values() for cid in cids})

    # Anotações do usuário autenticado
    my_annotations: dict[uuid.UUID, str] = {}
    if all_cids:
        rows = (
            db.query(Annotation.comment_id, Annotation.label)
            .filter(
                Annotation.comment_id.in_(all_cids),
                Annotation.annotator_id == user_id,
            )
            .all()
        )
        my_annotations = {cid: label for cid, label in rows}

    # Conflitos gerados pelo usuário
    my_conflict_cids: set[uuid.UUID] = set()
    if all_cids:
        conflict_rows = (
            db.query(AnnotationConflict.comment_id)
            .join(Annotation, AnnotationConflict.annotation_a_id == Annotation.id)
            .filter(
                AnnotationConflict.comment_id.in_(all_cids),
                Annotation.annotator_id == user_id,
            )
            .all()
        )
        my_conflict_cids.update(r[0] for r in conflict_rows)
        conflict_rows_b = (
            db.query(AnnotationConflict.comment_id)
            .join(Annotation, AnnotationConflict.annotation_b_id == Annotation.id)
            .filter(
                AnnotationConflict.comment_id.in_(all_cids),
                Annotation.annotator_id == user_id,
            )
            .all()
        )
        my_conflict_cids.update(r[0] for r in conflict_rows_b)

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

    # Progresso por dataset
    ds_progress = []
    total_annotated = 0
    total_pending = 0
    total_bots = 0
    total_humans = 0
    total_conflicts = 0
    datasets_completed = 0
    datasets_with_data = 0

    for ds in datasets:
        cids = ds_comment_ids.get(ds.id, [])
        if not cids:
            continue

        annotated_by_me = sum(1 for cid in cids if cid in my_annotations)
        pending = len(cids) - annotated_by_me

        # Apenas contar o dataset se o usuário tem algo para anotar
        # (todos os datasets são atribuídos a todos os anotadores)
        datasets_with_data += 1

        my_bots = sum(1 for cid in cids if my_annotations.get(cid) == "bot")
        my_humans = sum(1 for cid in cids if my_annotations.get(cid) == "humano")
        my_conflicts = sum(1 for cid in cids if cid in my_conflict_cids)

        percent = round(annotated_by_me / len(cids) * 100, 1) if cids else 0.0

        if annotated_by_me == len(cids):
            status = "completed"
            datasets_completed += 1
        elif annotated_by_me > 0:
            status = "in_progress"
        else:
            status = "not_started"

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
                "total_comments": len(cids),
                "annotated_by_me": annotated_by_me,
                "pending": pending,
                "percent_complete": percent,
                "my_bots": my_bots,
                "my_conflicts": my_conflicts,
                "status": status,
            }
        )

    datasets_pending = datasets_with_data - datasets_completed

    # Timeline de minhas anotações
    my_timeline = _get_user_annotation_timeline(db, user_id)

    # Gráficos
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


def get_bot_comments(
    db: Session,
    dataset_id: str | None = None,
    video_id: str | None = None,
    author: str | None = None,
    search: str | None = None,
    criteria_filter: list[str] | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Tabela de comentários classificados como bot."""
    q = (
        db.query(
            Dataset.name.label("dataset_name"),
            Dataset.id.label("dataset_id"),
            Comment.author_display_name,
            Comment.author_channel_id,
            Comment.text_original,
            Annotation.comment_id,
        )
        .join(DatasetEntry, DatasetEntry.dataset_id == Dataset.id)
        .join(
            Comment,
            (Comment.collection_id == Dataset.collection_id)
            & (Comment.author_channel_id == DatasetEntry.author_channel_id),
        )
        .join(Annotation, Annotation.comment_id == Comment.id)
        .filter(Annotation.label == "bot")
    )

    if dataset_id:
        q = q.filter(Dataset.id == dataset_id)
    if video_id:
        q = q.join(Collection, Collection.id == Dataset.collection_id).filter(
            Collection.video_id == video_id
        )
    if author:
        q = q.filter(Comment.author_display_name.ilike(f"%{author}%"))
    if search:
        q = q.filter(Comment.text_original.ilike(f"%{search}%"))
    if criteria_filter:
        for crit in criteria_filter:
            q = q.filter(Dataset.criteria_applied.any(crit))

    q = q.distinct(Annotation.comment_id)
    total = q.count()

    rows = (
        q.order_by(Annotation.comment_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    comment_ids = [r.comment_id for r in rows]

    # Batch: conflitos
    conflict_status_map: dict[uuid.UUID, str] = {}
    if comment_ids:
        conflicts = (
            db.query(AnnotationConflict.comment_id, AnnotationConflict.status)
            .filter(AnnotationConflict.comment_id.in_(comment_ids))
            .all()
        )
        conflict_status_map = {cid: st for cid, st in conflicts}

    # Batch: concordância + nº de anotadores
    concordance_map: dict[uuid.UUID, int] = {}
    annotators_map: dict[uuid.UUID, int] = {}
    if comment_ids:
        ann_counts = (
            db.query(
                Annotation.comment_id,
                func.count(Annotation.id).label("total"),
                func.count(
                    case(
                        (Annotation.label == "bot", 1),
                    )
                ).label("bot_count"),
            )
            .filter(Annotation.comment_id.in_(comment_ids))
            .group_by(Annotation.comment_id)
            .all()
        )
        for cid, total_anns, bot_count in ann_counts:
            annotators_map[cid] = total_anns
            if total_anns > 0:
                concordance_map[cid] = round(bot_count / total_anns * 100)

    # Batch: critérios que flagaram cada autor (via DatasetEntry)
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

    items = []
    for row in rows:
        items.append(
            {
                "dataset_name": row.dataset_name,
                "author_display_name": row.author_display_name,
                "text_original": row.text_original,
                "concordance_pct": concordance_map.get(row.comment_id, 0),
                "conflict_status": conflict_status_map.get(row.comment_id),
                "annotators_count": annotators_map.get(row.comment_id, 0),
                "criteria": criteria_map.get(row.author_channel_id, []),
            }
        )

    return {"total": total, "items": items}


def get_criteria_effectiveness(db: Session, video_id: str | None = None) -> list[dict]:
    """Eficácia de cada critério de limpeza."""
    datasets = _get_datasets_filtered(db, criteria=None, video_id=video_id)
    if not datasets:
        return []

    ds_comment_ids, _ = _get_comment_ids_for_datasets(db, datasets)
    all_cids = list({cid for cids in ds_comment_ids.values() for cid in cids})
    anns_by_comment, conflict_map = _get_annotations_and_conflicts(db, all_cids)

    return _compute_criteria_effectiveness(
        db, datasets, ds_comment_ids, anns_by_comment, conflict_map
    )


# ═══════════════════════════════════════════════════════════════════
#  Helpers internos
# ═══════════════════════════════════════════════════════════════════


def _get_annotation_timeline(db: Session, comment_ids: list[uuid.UUID]) -> list[dict]:
    """Anotações agrupadas por dia."""
    if not comment_ids:
        return []
    rows = (
        db.query(
            cast(Annotation.annotated_at, Date).label("day"),
            func.count(Annotation.id),
        )
        .filter(Annotation.comment_id.in_(comment_ids))
        .group_by("day")
        .order_by("day")
        .all()
    )
    return [{"date": str(day), "count": count} for day, count in rows]


def _get_user_annotation_timeline(db: Session, user_id: uuid.UUID) -> list[dict]:
    """Anotações do usuário agrupadas por dia."""
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
    """Comentários publicados agrupados por dia para um vídeo."""
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
    ds_comment_ids: dict[uuid.UUID, list[uuid.UUID]],
    anns_by_comment: dict[uuid.UUID, list[tuple[uuid.UUID, str]]],
    conflict_map: dict[uuid.UUID, tuple[str, str | None]],
) -> list[dict]:
    """Taxa de bots agrupada por critério para gráfico horizontal."""
    criteria_stats: dict[str, dict] = {}

    for ds in datasets:
        cids = ds_comment_ids.get(ds.id, [])
        if not cids:
            continue

        bots = sum(
            1
            for cid in cids
            if _classify_comment(cid, anns_by_comment, conflict_map) == "bot"
        )
        annotated = sum(1 for cid in cids if anns_by_comment.get(cid))

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
    ds_comment_ids: dict[uuid.UUID, list[uuid.UUID]],
    anns_by_comment: dict[uuid.UUID, list[tuple[uuid.UUID, str]]],
    conflict_map: dict[uuid.UUID, tuple[str, str | None]],
) -> list[dict]:
    """Calcula eficácia de cada critério: datasets, comentários, bots, taxa."""
    criteria_stats: dict[str, dict] = {}

    for ds in datasets:
        cids = ds_comment_ids.get(ds.id, [])
        bots = sum(
            1
            for cid in cids
            if _classify_comment(cid, anns_by_comment, conflict_map) == "bot"
        )
        for crit in ds.criteria_applied or []:
            if crit not in criteria_stats:
                criteria_stats[crit] = {
                    "total_datasets": 0,
                    "total_comments_selected": 0,
                    "total_bots": 0,
                }
            criteria_stats[crit]["total_datasets"] += 1
            criteria_stats[crit]["total_comments_selected"] += len(cids)
            criteria_stats[crit]["total_bots"] += bots

    # Ordenar: numéricos primeiro, depois comportamentais
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
            stats["total_bots"] / stats["total_comments_selected"]
            if stats["total_comments_selected"] > 0
            else 0.0
        )
        result.append(
            {
                "criteria": crit,
                "group": CRITERIA_GROUPS.get(crit, "outro"),
                "total_datasets": stats["total_datasets"],
                "total_comments_selected": stats["total_comments_selected"],
                "total_bots": stats["total_bots"],
                "bot_rate": round(bot_rate, 4),
            }
        )
    return result


def _compute_video_highlights(db: Session, video_id: str) -> list[dict]:
    """Destaques estatísticos do vídeo baseados nos comentários coletados."""
    base = db.query(Comment).join(Collection).filter(Collection.video_id == video_id)

    highlights: list[dict] = []

    # 1. Autor com mais comentários
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

    # 2. Comentário com mais respostas
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

    # 3. Comentário com mais likes
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

    # 4. Conta mais nova (canal criado mais recentemente)
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

    # 5. Conta mais antiga
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

    # 6. Média de likes por comentário
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
    """Resposta vazia para quando não há datasets."""
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

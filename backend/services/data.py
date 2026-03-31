"""Serviço da US-07 — catálogo centralizado de dados."""

import logging
import uuid
from collections import defaultdict

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from models.annotation import Annotation, AnnotationConflict
from models.collection import Collection, Comment
from models.dataset import Dataset, DatasetEntry
from models.user import User

logger = logging.getLogger(__name__)

# Tabelas cujo tamanho é somado para estimar uso do banco
_SIZE_TABLES = (
    "collections",
    "comments",
    "datasets",
    "dataset_entries",
    "annotations",
    "annotation_conflicts",
    "resolutions",
    "users",
)


def get_summary(db: Session) -> dict:
    """Contagem de registros + estimativa de tamanho via pg_total_relation_size."""
    collections_count = db.query(func.count(Collection.id)).scalar() or 0
    comments_count = db.query(func.count(Comment.id)).scalar() or 0
    datasets_count = db.query(func.count(Dataset.id)).scalar() or 0
    annotations_count = db.query(func.count(Annotation.id)).scalar() or 0

    # Estimativa de tamanho em MB (dados + índices + TOAST)
    total_bytes = 0
    for table in _SIZE_TABLES:
        try:
            row = db.execute(
                text("SELECT pg_total_relation_size(:t)"),
                {"t": table},
            ).scalar()
            total_bytes += row or 0
        except Exception:
            logger.debug("pg_total_relation_size falhou para %s", table)

    estimated_size_mb = round(total_bytes / (1024 * 1024), 2)

    return {
        "collections_count": collections_count,
        "comments_count": comments_count,
        "datasets_count": datasets_count,
        "annotations_count": annotations_count,
        "estimated_size_mb": estimated_size_mb,
    }


def list_all_collections(db: Session) -> list[dict]:
    """Todas as coletas com nome do coletor, ordenadas por data decrescente."""
    collections = db.query(Collection).order_by(Collection.created_at.desc()).all()

    if not collections:
        return []

    # Batch load users
    user_ids = {c.collected_by for c in collections}
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {u.id: u for u in users}

    # Batch: autores distintos por coleta
    col_ids = [c.id for c in collections]
    user_counts = (
        db.query(
            Comment.collection_id,
            func.count(func.distinct(Comment.author_channel_id)),
        )
        .filter(Comment.collection_id.in_(col_ids))
        .group_by(Comment.collection_id)
        .all()
    )
    users_by_col = {row[0]: row[1] for row in user_counts}

    return [
        {
            "collection_id": c.id,
            "video_id": c.video_id,
            "video_title": c.video_title,
            "total_comments": c.total_comments,
            "total_users": users_by_col.get(c.id, 0),
            "status": c.status,
            "enrich_status": c.enrich_status,
            "channel_dates_failed": c.channel_dates_failed,
            "collected_by": user_map[c.collected_by].username
            if c.collected_by in user_map
            else "",
            "created_at": c.created_at,
            "completed_at": c.completed_at,
            "duration_seconds": c.duration_seconds,
        }
        for c in collections
    ]


def list_all_datasets(db: Session) -> list[dict]:
    """Todos os datasets limpos, ordenados por data decrescente.

    Otimizado: 5 queries constantes independente do número de datasets.
    """
    datasets = db.query(Dataset).order_by(Dataset.created_at.desc()).all()

    if not datasets:
        return []

    ds_ids = [ds.id for ds in datasets]

    # Batch load collections e users
    collection_ids = {ds.collection_id for ds in datasets}
    collections = db.query(Collection).filter(Collection.id.in_(collection_ids)).all()
    col_map = {c.id: c for c in collections}

    user_ids = {ds.created_by for ds in datasets}
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {u.id: u for u in users}

    # Batch: entries por dataset → author_ids agrupados
    all_entries = (
        db.query(
            DatasetEntry.dataset_id,
            DatasetEntry.author_channel_id,
        )
        .filter(DatasetEntry.dataset_id.in_(ds_ids))
        .all()
    )
    authors_by_ds: dict[uuid.UUID, list[str]] = defaultdict(list)
    for dataset_id, author_channel_id in all_entries:
        authors_by_ds[dataset_id].append(author_channel_id)

    # Batch: contagem de comentários por (collection_id, author_channel_id)
    # Coletamos todos os pares (collection_id, author_channel_id) necessários
    all_pairs: set[tuple[uuid.UUID, str]] = set()
    for ds in datasets:
        for author_id in authors_by_ds.get(ds.id, []):
            all_pairs.add((ds.collection_id, author_id))

    # Uma query para contar todos os comentários de todos os pares
    comments_count_map: dict[tuple[uuid.UUID, str], int] = {}
    if all_pairs:
        # Agrupar por collection_id para queries menores
        by_col: dict[uuid.UUID, list[str]] = defaultdict(list)
        for col_id, author_id in all_pairs:
            by_col[col_id].append(author_id)

        for col_id, author_list in by_col.items():
            rows = (
                db.query(
                    Comment.author_channel_id,
                    func.count(Comment.id),
                )
                .filter(
                    Comment.collection_id == col_id,
                    Comment.author_channel_id.in_(author_list),
                )
                .group_by(Comment.author_channel_id)
                .all()
            )
            for author_id, cnt in rows:
                comments_count_map[(col_id, author_id)] = cnt

    results = []
    for ds in datasets:
        ds_authors = authors_by_ds.get(ds.id, [])
        total_comments = sum(
            comments_count_map.get((ds.collection_id, a), 0) for a in ds_authors
        )

        results.append(
            {
                "dataset_id": ds.id,
                "name": ds.name,
                "collection_id": ds.collection_id,
                "video_id": col_map[ds.collection_id].video_id
                if ds.collection_id in col_map
                else "",
                "criteria": ds.criteria_applied,
                "total_users_original": ds.total_users_original,
                "total_selected": ds.total_users_selected,
                "total_comments": total_comments,
                "created_by": user_map[ds.created_by].username
                if ds.created_by in user_map
                else "",
                "created_at": ds.created_at,
            }
        )

    return results


def get_annotation_progress(db: Session) -> list[dict]:
    """Progresso de anotação por dataset.

    Otimizado: número constante de queries independente do número de datasets
    e comentários. Sem loops N+1.
    """
    datasets = db.query(Dataset).order_by(Dataset.created_at.desc()).all()

    if not datasets:
        return []

    ds_ids = [ds.id for ds in datasets]

    # 1) Batch: entries → authors por dataset
    all_entries = (
        db.query(DatasetEntry.dataset_id, DatasetEntry.author_channel_id)
        .filter(DatasetEntry.dataset_id.in_(ds_ids))
        .all()
    )
    authors_by_ds: dict[uuid.UUID, list[str]] = defaultdict(list)
    for dataset_id, author_channel_id in all_entries:
        authors_by_ds[dataset_id].append(author_channel_id)

    # 2) Batch: todos os comentários relevantes (id, collection_id, author_channel_id)
    #    Monta pares (collection_id, [author_ids]) para buscar de uma vez
    col_authors: dict[uuid.UUID, set[str]] = defaultdict(set)
    ds_col_map = {ds.id: ds.collection_id for ds in datasets}
    for ds in datasets:
        for author_id in authors_by_ds.get(ds.id, []):
            col_authors[ds.collection_id].add(author_id)

    # Buscar todos os comentários necessários em batch por collection
    # comment_id → (collection_id, author_channel_id)
    comment_info: dict[uuid.UUID, tuple[uuid.UUID, str]] = {}
    # (collection_id, author_channel_id) → [comment_ids]
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

    # Coletar todos os comment_ids relevantes
    all_comment_ids = list(comment_info.keys())

    # 3) Batch: anotações (comment_id, annotator_id, label)
    all_annotations: list[tuple[uuid.UUID, uuid.UUID, str]] = []
    if all_comment_ids:
        all_annotations = (
            db.query(
                Annotation.comment_id,
                Annotation.annotator_id,
                Annotation.label,
            )
            .filter(Annotation.comment_id.in_(all_comment_ids))
            .all()
        )

    # Agrupar: comment_id → [(annotator_id, label)]
    anns_by_comment: dict[uuid.UUID, list[tuple[uuid.UUID, str]]] = defaultdict(list)
    for comment_id, annotator_id, label in all_annotations:
        anns_by_comment[comment_id].append((annotator_id, label))

    # 4) Batch: conflitos (comment_id, status, resolved_label)
    all_conflicts: list[tuple[uuid.UUID, str, str | None]] = []
    if all_comment_ids:
        all_conflicts = (
            db.query(
                AnnotationConflict.comment_id,
                AnnotationConflict.status,
                AnnotationConflict.resolved_label,
            )
            .filter(AnnotationConflict.comment_id.in_(all_comment_ids))
            .all()
        )

    # conflict_comment_id → (status, resolved_label)
    conflict_map: dict[uuid.UUID, tuple[str, str | None]] = {}
    for comment_id, status, resolved_label in all_conflicts:
        conflict_map[comment_id] = (status, resolved_label)

    # 5) Montar resultados por dataset — tudo em Python, sem mais queries
    results = []
    for ds in datasets:
        ds_authors = authors_by_ds.get(ds.id, [])

        if not ds_authors:
            results.append(
                {
                    "dataset_id": ds.id,
                    "dataset_name": ds.name,
                    "total": 0,
                    "annotated": 0,
                    "pending": 0,
                    "conflicts": 0,
                    "conflicts_resolved": 0,
                    "annotators_count": 0,
                    "bots_users": 0,
                    "bots_comments": 0,
                }
            )
            continue

        # Comentários deste dataset
        ds_comment_ids: list[uuid.UUID] = []
        for author_id in ds_authors:
            ds_comment_ids.extend(
                comments_by_col_author.get((ds_col_map[ds.id], author_id), [])
            )

        total = len(ds_comment_ids)

        # Anotados: comentários com pelo menos uma anotação
        annotated_set: set[uuid.UUID] = set()
        annotator_ids: set[uuid.UUID] = set()
        for cid in ds_comment_ids:
            anns = anns_by_comment.get(cid)
            if anns:
                annotated_set.add(cid)
                for annotator_id, _ in anns:
                    annotator_ids.add(annotator_id)

        annotated = len(annotated_set)

        # Conflitos
        conflicts = 0
        conflicts_resolved = 0
        for cid in ds_comment_ids:
            if cid in conflict_map:
                conflicts += 1
                if conflict_map[cid][0] == "resolved":
                    conflicts_resolved += 1

        # Bots: consenso "bot" (sem conflito) OU conflito resolvido como "bot"
        bots_comments = 0
        bot_author_ids: set[str] = set()
        for cid in ds_comment_ids:
            anns = anns_by_comment.get(cid, [])
            if not anns:
                continue

            if cid in conflict_map:
                # Tem conflito — só conta se resolvido como bot
                status, resolved_label = conflict_map[cid]
                if status == "resolved" and resolved_label == "bot":
                    bots_comments += 1
                    _, author_id = comment_info[cid]
                    bot_author_ids.add(author_id)
            else:
                # Sem conflito — consenso
                if all(label == "bot" for _, label in anns):
                    bots_comments += 1
                    _, author_id = comment_info[cid]
                    bot_author_ids.add(author_id)

        results.append(
            {
                "dataset_id": ds.id,
                "dataset_name": ds.name,
                "total": total,
                "annotated": annotated,
                "pending": total - annotated,
                "conflicts": conflicts,
                "conflicts_resolved": conflicts_resolved,
                "annotators_count": len(annotator_ids),
                "bots_users": len(bot_author_ids),
                "bots_comments": bots_comments,
            }
        )

    return results

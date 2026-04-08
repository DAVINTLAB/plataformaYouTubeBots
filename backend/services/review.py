"""Serviço da US-05 — revisão de conflitos e desempate por usuário."""

import json
import logging
import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.annotation import Annotation, AnnotationConflict
from models.collection import Collection, Comment
from models.dataset import Dataset, DatasetEntry
from models.resolution import Resolution
from models.user import User

logger = logging.getLogger(__name__)


# ─── Listar conflitos ────────────────────────────────────────────────────────


def list_conflicts(
    db: Session,
    *,
    conflict_status: str | None = None,
    video_id: str | None = None,
    dataset_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    query = (
        db.query(AnnotationConflict)
        .join(DatasetEntry, AnnotationConflict.dataset_entry_id == DatasetEntry.id)
        .join(Dataset, Dataset.id == DatasetEntry.dataset_id)
    )

    if conflict_status:
        query = query.filter(AnnotationConflict.status == conflict_status)
    if dataset_id:
        query = query.filter(Dataset.id == dataset_id)
    if video_id:
        query = query.join(Collection, Collection.id == Dataset.collection_id).filter(
            Collection.video_id == video_id
        )

    total = query.count()
    offset = (page - 1) * page_size
    conflicts = (
        query.order_by(AnnotationConflict.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    if not conflicts:
        return _empty_page(page, page_size, total)

    # Batch load
    ann_ids = set()
    entry_ids = set()
    for c in conflicts:
        ann_ids.update([c.annotation_a_id, c.annotation_b_id])
        entry_ids.add(c.dataset_entry_id)

    annotations = db.query(Annotation).filter(Annotation.id.in_(ann_ids)).all()
    ann_map = {a.id: a for a in annotations}

    entries = db.query(DatasetEntry).filter(DatasetEntry.id.in_(entry_ids)).all()
    entry_map = {e.id: e for e in entries}

    user_ids = {a.annotator_id for a in annotations}
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {u.id: u for u in users}

    ds_ids = {e.dataset_id for e in entries}
    datasets = db.query(Dataset).filter(Dataset.id.in_(ds_ids)).all()
    ds_map = {d.id: d for d in datasets}

    # Comment counts por entry
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
    for c in conflicts:
        ann_a = ann_map.get(c.annotation_a_id)
        ann_b = ann_map.get(c.annotation_b_id)
        if not ann_a or not ann_b:
            continue

        entry = entry_map.get(c.dataset_entry_id)
        if not entry:
            continue

        ds = ds_map.get(entry.dataset_id)
        annotator_a = user_map.get(ann_a.annotator_id)
        annotator_b = user_map.get(ann_b.annotator_id)

        items.append(
            {
                "conflict_id": c.id,
                "entry_id": c.dataset_entry_id,
                "dataset_id": ds.id if ds else None,
                "dataset_name": ds.name if ds else "",
                "author_display_name": entry.author_display_name,
                "author_channel_id": entry.author_channel_id,
                "comment_count": cc_map.get(entry.id, 0),
                "label_a": ann_a.label,
                "annotator_a": annotator_a.name if annotator_a else "",
                "justificativa_a": ann_a.justificativa,
                "label_b": ann_b.label,
                "annotator_b": annotator_b.name if annotator_b else "",
                "justificativa_b": ann_b.justificativa,
                "status": c.status,
                "created_at": c.created_at,
            }
        )

    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "items": items,
    }


def _empty_page(page: int, page_size: int, total: int = 0) -> dict:
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "items": [],
    }


# ─── Detalhe de um conflito ──────────────────────────────────────────────────


def get_conflict_detail(db: Session, conflict_id: uuid.UUID) -> dict:
    conflict = (
        db.query(AnnotationConflict)
        .filter(AnnotationConflict.id == conflict_id)
        .first()
    )
    if not conflict:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Conflito não encontrado."
        )

    ann_a = (
        db.query(Annotation).filter(Annotation.id == conflict.annotation_a_id).first()
    )
    ann_b = (
        db.query(Annotation).filter(Annotation.id == conflict.annotation_b_id).first()
    )
    entry = (
        db.query(DatasetEntry)
        .filter(DatasetEntry.id == conflict.dataset_entry_id)
        .first()
    )
    dataset = db.query(Dataset).filter(Dataset.id == entry.dataset_id).first()

    # Todos os comentários do autor como evidências
    all_comments = (
        db.query(Comment)
        .filter(
            Comment.collection_id == dataset.collection_id,
            Comment.author_channel_id == entry.author_channel_id,
        )
        .order_by(Comment.published_at.asc())
        .all()
    )

    annotator_a = db.query(User).filter(User.id == ann_a.annotator_id).first()
    annotator_b = db.query(User).filter(User.id == ann_b.annotator_id).first()

    resolved_by_name = None
    if conflict.resolved_by:
        resolver = db.query(User).filter(User.id == conflict.resolved_by).first()
        resolved_by_name = resolver.name if resolver else None

    return {
        "conflict_id": conflict.id,
        "status": conflict.status,
        "dataset_name": dataset.name if dataset else "",
        "author_channel_id": entry.author_channel_id,
        "author_display_name": entry.author_display_name,
        "comments": [
            {
                "comment_db_id": c.id,
                "text_original": c.text_original,
                "like_count": c.like_count,
                "reply_count": c.reply_count,
                "published_at": c.published_at,
            }
            for c in all_comments
        ],
        "annotation_a": {
            "annotator": annotator_a.name if annotator_a else "",
            "label": ann_a.label,
            "justificativa": ann_a.justificativa,
            "annotated_at": ann_a.annotated_at,
        },
        "annotation_b": {
            "annotator": annotator_b.name if annotator_b else "",
            "label": ann_b.label,
            "justificativa": ann_b.justificativa,
            "annotated_at": ann_b.annotated_at,
        },
        "resolved_by": resolved_by_name,
        "resolved_label": conflict.resolved_label,
        "resolved_at": conflict.resolved_at,
    }


# ─── Resolver conflito ───────────────────────────────────────────────────────


def resolve_conflict(
    db: Session,
    conflict_id: uuid.UUID,
    admin_id: uuid.UUID,
    resolved_label: str,
) -> dict:
    conflict = (
        db.query(AnnotationConflict)
        .filter(AnnotationConflict.id == conflict_id)
        .first()
    )
    if not conflict:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Conflito não encontrado."
        )

    if conflict.status == "resolved":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Este conflito já foi resolvido.",
        )

    now = datetime.utcnow()

    conflict.status = "resolved"
    conflict.resolved_by = admin_id
    conflict.resolved_label = resolved_label
    conflict.resolved_at = now

    resolution = Resolution(
        conflict_id=conflict_id,
        resolved_label=resolved_label,
        resolved_by=admin_id,
        resolved_at=now,
    )
    db.add(resolution)
    db.commit()

    admin = db.query(User).filter(User.id == admin_id).first()

    logger.info(
        "Conflito %s resolvido como '%s' por %s",
        conflict_id,
        resolved_label,
        admin.name if admin else admin_id,
    )

    return {
        "conflict_id": conflict.id,
        "status": "resolved",
        "resolved_label": resolved_label,
        "resolved_by": admin.name if admin else "",
        "resolved_at": now,
    }


# ─── Listar bots (por usuário) ──────────────────────────────────────────────


def list_bots(
    db: Session,
    *,
    video_id: str | None = None,
    dataset_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Lista entries (usuários do YouTube) com pelo menos uma anotação 'bot'."""
    bot_entry_ids = (
        db.query(Annotation.dataset_entry_id)
        .filter(Annotation.label == "bot")
        .distinct()
        .subquery()
    )

    query = (
        db.query(DatasetEntry)
        .filter(DatasetEntry.id.in_(bot_entry_ids.select()))
        .join(Dataset, Dataset.id == DatasetEntry.dataset_id)
    )

    if dataset_id:
        query = query.filter(Dataset.id == dataset_id)
    if video_id:
        query = query.join(Collection, Collection.id == Dataset.collection_id).filter(
            Collection.video_id == video_id
        )

    total = query.count()
    offset = (page - 1) * page_size
    entries = (
        query.order_by(DatasetEntry.author_display_name)
        .offset(offset)
        .limit(page_size)
        .all()
    )

    if not entries:
        return _empty_page(page, page_size, total)

    # Batch load
    entry_ids = [e.id for e in entries]
    ds_ids = {e.dataset_id for e in entries}

    datasets = db.query(Dataset).filter(Dataset.id.in_(ds_ids)).all()
    ds_map = {d.id: d for d in datasets}

    all_annotations = (
        db.query(Annotation).filter(Annotation.dataset_entry_id.in_(entry_ids)).all()
    )
    ann_by_entry: dict[uuid.UUID, list[Annotation]] = {}
    for a in all_annotations:
        ann_by_entry.setdefault(a.dataset_entry_id, []).append(a)

    user_ids = {a.annotator_id for a in all_annotations}
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {u.id: u for u in users}

    all_conflicts = (
        db.query(AnnotationConflict)
        .filter(AnnotationConflict.dataset_entry_id.in_(entry_ids))
        .all()
    )
    conflict_map = {c.dataset_entry_id: c for c in all_conflicts}

    # Comment counts
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
    for entry in entries:
        ds = ds_map.get(entry.dataset_id)
        annotations = ann_by_entry.get(entry.id, [])
        ann_list = [
            {
                "annotator_name": user_map.get(a.annotator_id, User()).name
                if user_map.get(a.annotator_id)
                else "",
                "label": a.label,
                "justificativa": a.justificativa,
            }
            for a in annotations
        ]

        conflict = conflict_map.get(entry.id)

        items.append(
            {
                "entry_id": entry.id,
                "author_display_name": entry.author_display_name,
                "author_channel_id": entry.author_channel_id,
                "comment_count": cc_map.get(entry.id, 0),
                "dataset_id": ds.id if ds else None,
                "dataset_name": ds.name if ds else "",
                "annotations": ann_list,
                "has_conflict": conflict is not None,
                "conflict_id": conflict.id if conflict else None,
            }
        )

    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "items": items,
    }


# ─── Estatísticas ─────────────────────────────────────────────────────────────


def get_stats(db: Session) -> dict:
    total = db.query(func.count(AnnotationConflict.id)).scalar()
    pending = (
        db.query(func.count(AnnotationConflict.id))
        .filter(AnnotationConflict.status == "pending")
        .scalar()
    )
    resolved = (
        db.query(func.count(AnnotationConflict.id))
        .filter(AnnotationConflict.status == "resolved")
        .scalar()
    )

    # Total de usuários flagados como bot por pelo menos um anotador
    bots_flagged = (
        db.query(func.count(func.distinct(Annotation.dataset_entry_id)))
        .filter(Annotation.label == "bot")
        .scalar()
    )

    return {
        "total_conflicts": total,
        "pending_conflicts": pending,
        "resolved_conflicts": resolved,
        "total_bots_flagged": bots_flagged,
    }


# ─── Export (JSON streaming) ─────────────────────────────────────────────────


def export_review_json(
    db: Session,
    dataset_id: uuid.UUID,
):
    """Gerador de JSON streaming com dataset final (anotado + desempatado)."""
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if not dataset:
        yield '{"error": "Dataset não encontrado."}\n'
        return

    collection = (
        db.query(Collection).filter(Collection.id == dataset.collection_id).first()
    )

    meta = {
        "dataset_name": dataset.name,
        "video_id": collection.video_id if collection else "",
        "exported_at": datetime.utcnow().isoformat() + "Z",
    }

    yield "{\n"
    yield f'  "dataset_name": {json.dumps(meta["dataset_name"])},\n'
    yield f'  "video_id": {json.dumps(meta["video_id"])},\n'
    yield f'  "exported_at": {json.dumps(meta["exported_at"])},\n'
    yield '  "users": [\n'

    entries = db.query(DatasetEntry).filter(DatasetEntry.dataset_id == dataset.id).all()

    first_entry = True
    for entry in entries:
        # Anotações para este entry (usuário)
        annotations = (
            db.query(Annotation).filter(Annotation.dataset_entry_id == entry.id).all()
        )
        if not annotations:
            continue

        # Conflito/resolução
        conflict = (
            db.query(AnnotationConflict)
            .filter(AnnotationConflict.dataset_entry_id == entry.id)
            .first()
        )

        resolution_data = None
        if conflict and conflict.status == "resolved":
            resolver = db.query(User).filter(User.id == conflict.resolved_by).first()
            resolution_data = {
                "resolved_by": resolver.name if resolver else "",
                "resolved_label": conflict.resolved_label,
                "resolved_at": conflict.resolved_at.isoformat() + "Z"
                if conflict.resolved_at
                else None,
            }
            final_label = conflict.resolved_label
        else:
            labels = {a.label for a in annotations}
            if len(labels) == 1:
                final_label = labels.pop()
            else:
                final_label = "pending"

        ann_list = []
        for a in annotations:
            annotator = db.query(User).filter(User.id == a.annotator_id).first()
            ann_list.append(
                {
                    "annotator": annotator.name if annotator else "",
                    "label": a.label,
                    "justificativa": a.justificativa,
                }
            )

        item = {
            "entry_id": str(entry.id),
            "author_channel_id": entry.author_channel_id,
            "author_display_name": entry.author_display_name,
            "final_label": final_label,
            "annotations": ann_list,
            "resolution": resolution_data,
        }

        prefix = "    " if first_entry else ",\n    "
        first_entry = False
        yield prefix + json.dumps(item, ensure_ascii=False)

    yield "\n  ]\n}\n"


# ─── Export (CSV streaming) ──────────────────────────────────────────────────


def export_review_csv(
    db: Session,
    dataset_id: uuid.UUID,
):
    """Gerador de CSV streaming com dataset final."""
    import csv
    import io

    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if not dataset:
        yield "error\nDataset não encontrado.\n"
        return

    yield "entry_id,author_channel_id,author_display_name,final_label\n"

    entries = db.query(DatasetEntry).filter(DatasetEntry.dataset_id == dataset.id).all()

    for entry in entries:
        annotations = (
            db.query(Annotation).filter(Annotation.dataset_entry_id == entry.id).all()
        )
        if not annotations:
            continue

        conflict = (
            db.query(AnnotationConflict)
            .filter(AnnotationConflict.dataset_entry_id == entry.id)
            .first()
        )

        if conflict and conflict.status == "resolved":
            final_label = conflict.resolved_label
        else:
            labels = {a.label for a in annotations}
            final_label = labels.pop() if len(labels) == 1 else "pending"

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                str(entry.id),
                entry.author_channel_id,
                entry.author_display_name,
                final_label,
            ]
        )
        yield buf.getvalue()


# ─── Import (lógica interna) ─────────────────────────────────────────────────


def _resolve_users(
    db: Session,
    admin_id: uuid.UUID,
    users: list,
) -> dict:
    """Resolve conflitos a partir de uma lista de usuários importados."""
    imported = 0
    skipped = 0
    errors = []

    for item in users:
        entry = db.query(DatasetEntry).filter(DatasetEntry.id == item.entry_id).first()
        if not entry:
            skipped += 1
            errors.append(f"Entrada {item.entry_id} não encontrada.")
            continue

        if not item.resolution:
            skipped += 1
            continue

        conflict = (
            db.query(AnnotationConflict)
            .filter(AnnotationConflict.dataset_entry_id == entry.id)
            .first()
        )
        if not conflict:
            skipped += 1
            errors.append(f"Entrada {item.entry_id} não possui conflito registrado.")
            continue

        if conflict.status == "resolved":
            skipped += 1
            continue

        resolved_label = item.resolution.get("resolved_label", item.final_label)
        if resolved_label not in ("bot", "humano"):
            skipped += 1
            errors.append(
                f"Entrada {item.entry_id}: label '{resolved_label}' inválido."
            )
            continue

        now = datetime.utcnow()
        conflict.status = "resolved"
        conflict.resolved_by = admin_id
        conflict.resolved_label = resolved_label
        conflict.resolved_at = now

        resolution = Resolution(
            conflict_id=conflict.id,
            resolved_label=resolved_label,
            resolved_by=admin_id,
            resolved_at=now,
        )
        db.add(resolution)
        imported += 1

    db.commit()

    logger.info(
        "Import de revisões: imported=%d, skipped=%d",
        imported,
        skipped,
    )

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
    }


# ─── Import (endpoints) ─────────────────────────────────────────────────────


def import_review(
    db: Session,
    admin_id: uuid.UUID,
    video_id: str,
    users: list,
) -> dict:
    """Importa dataset revisado (formato simétrico ao export)."""
    collection = db.query(Collection).filter(Collection.video_id == video_id).first()
    if not collection:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Coleta com video_id '{video_id}' não encontrada.",
        )

    return _resolve_users(db, admin_id, users)


def import_review_chunk(
    db: Session,
    admin_id: uuid.UUID,
    users: list,
    done: bool,
) -> dict:
    """Batch adicional de usuários revisados para import paginado."""
    result = _resolve_users(db, admin_id, users)
    return {
        "total_imported": result["imported"],
        "chunk_received": len(users),
        "done": done,
    }

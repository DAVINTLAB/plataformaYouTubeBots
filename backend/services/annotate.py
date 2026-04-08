"""Serviço da US-04 — anotação de usuários do YouTube (bot/humano).

Unidade de anotação: DatasetEntry (autor/canal do YouTube).
Comentários são evidências — a classificação é do autor, não do comentário.
"""

import csv
import io
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

logger = logging.getLogger(__name__)


# ─── Listar usuários do YouTube em um dataset ─────────────────────────────


def list_dataset_users(
    db: Session,
    dataset_id: uuid.UUID,
    annotator_id: uuid.UUID,
    *,
    is_admin: bool = False,
    page: int = 1,
    page_size: int = 20,
    pending_first: bool = False,
    only_pending: bool = False,
) -> dict:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if dataset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Dataset não encontrado.")

    collection_id = dataset.collection_id

    # Subquery: comment_count por autor no dataset
    comment_count_sub = (
        db.query(
            Comment.author_channel_id,
            func.count(Comment.id).label("cc"),
        )
        .filter(Comment.collection_id == collection_id)
        .group_by(Comment.author_channel_id)
        .subquery()
    )

    # Subquery: anotação do pesquisador para cada entry
    if is_admin:
        ann_sub = (
            db.query(
                Annotation.dataset_entry_id,
                func.count(func.distinct(Annotation.annotator_id)).label("ac"),
            )
            .group_by(Annotation.dataset_entry_id)
            .subquery()
        )
    else:
        ann_sub = (
            db.query(
                Annotation.dataset_entry_id,
                Annotation.label,
            )
            .filter(Annotation.annotator_id == annotator_id)
            .subquery()
        )

    cc_col = func.coalesce(comment_count_sub.c.cc, 0)

    if is_admin:
        ac_col = func.coalesce(ann_sub.c.ac, 0)
        base_query = (
            db.query(DatasetEntry, cc_col.label("cc"), ac_col.label("ac"))
            .outerjoin(
                comment_count_sub,
                comment_count_sub.c.author_channel_id == DatasetEntry.author_channel_id,
            )
            .outerjoin(ann_sub, ann_sub.c.dataset_entry_id == DatasetEntry.id)
            .filter(DatasetEntry.dataset_id == dataset_id)
        )
    else:
        base_query = (
            db.query(
                DatasetEntry,
                cc_col.label("cc"),
                ann_sub.c.label.label("my_label"),
            )
            .outerjoin(
                comment_count_sub,
                comment_count_sub.c.author_channel_id == DatasetEntry.author_channel_id,
            )
            .outerjoin(ann_sub, ann_sub.c.dataset_entry_id == DatasetEntry.id)
            .filter(DatasetEntry.dataset_id == dataset_id)
        )

    if only_pending:
        if is_admin:
            base_query = base_query.filter(ac_col == 0)
        else:
            base_query = base_query.filter(ann_sub.c.label.is_(None))

    total_users = base_query.count()

    if pending_first:
        if is_admin:
            order = [ac_col.asc(), DatasetEntry.author_display_name]
        else:
            order = [ann_sub.c.label.asc(), DatasetEntry.author_display_name]
    else:
        order = [DatasetEntry.author_display_name]

    offset = (page - 1) * page_size
    rows = base_query.order_by(*order).offset(offset).limit(page_size).all()

    # Total global de anotados
    if is_admin:
        total_annotated = (
            db.query(func.count(func.distinct(Annotation.dataset_entry_id)))
            .join(DatasetEntry, Annotation.dataset_entry_id == DatasetEntry.id)
            .filter(DatasetEntry.dataset_id == dataset_id)
            .scalar()
        ) or 0
    else:
        total_annotated = (
            db.query(func.count(Annotation.id))
            .join(DatasetEntry, Annotation.dataset_entry_id == DatasetEntry.id)
            .filter(
                DatasetEntry.dataset_id == dataset_id,
                Annotation.annotator_id == annotator_id,
            )
            .scalar()
        ) or 0

    items = []
    for row in rows:
        if is_admin:
            entry, cc, ac = row
            items.append(
                {
                    "entry_id": entry.id,
                    "author_channel_id": entry.author_channel_id,
                    "author_display_name": entry.author_display_name,
                    "comment_count": cc,
                    "is_annotated_by_me": ac > 0,
                    "my_label": None,
                }
            )
        else:
            entry, cc, my_label = row
            items.append(
                {
                    "entry_id": entry.id,
                    "author_channel_id": entry.author_channel_id,
                    "author_display_name": entry.author_display_name,
                    "comment_count": cc,
                    "is_annotated_by_me": my_label is not None,
                    "my_label": my_label,
                }
            )

    return {
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "total_users": total_users,
        "annotated_users_by_me": total_annotated,
        "page": page,
        "page_size": page_size,
        "total_pages": _total_pages(total_users, page_size),
        "items": items,
    }


def _total_pages(total: int, page_size: int) -> int:
    return max(1, (total + page_size - 1) // page_size)


# ─── Comentários de um usuário (entry) — evidências ──────────────────────


def get_entry_comments(
    db: Session,
    entry_id: uuid.UUID,
    annotator_id: uuid.UUID,
    *,
    is_admin: bool = False,
) -> dict:
    entry = db.query(DatasetEntry).filter(DatasetEntry.id == entry_id).first()
    if entry is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Entrada de dataset não encontrada."
        )

    dataset = db.query(Dataset).filter(Dataset.id == entry.dataset_id).first()

    comments = (
        db.query(Comment)
        .filter(
            Comment.collection_id == dataset.collection_id,
            Comment.author_channel_id == entry.author_channel_id,
        )
        .order_by(Comment.published_at.asc())
        .all()
    )

    result_comments = [
        {
            "comment_db_id": c.id,
            "text_original": c.text_original,
            "like_count": c.like_count,
            "reply_count": c.reply_count,
            "published_at": c.published_at,
        }
        for c in comments
    ]

    # Anotação do pesquisador logado (por entry, não por comment)
    my_ann = None
    if not is_admin:
        annotation = (
            db.query(Annotation)
            .filter(
                Annotation.dataset_entry_id == entry.id,
                Annotation.annotator_id == annotator_id,
            )
            .first()
        )
        if annotation:
            my_ann = {
                "label": annotation.label,
                "justificativa": annotation.justificativa,
                "annotated_at": annotation.annotated_at,
            }

    # Admin vê todas as anotações de todos os pesquisadores (por entry)
    all_anns = None
    if is_admin:
        annotations = (
            db.query(Annotation).filter(Annotation.dataset_entry_id == entry.id).all()
        )
        if annotations:
            all_anns = [
                {
                    "annotator_name": a.annotator.name,
                    "label": a.label,
                    "justificativa": a.justificativa,
                    "annotated_at": a.annotated_at,
                }
                for a in annotations
            ]

    return {
        "entry_id": entry.id,
        "author_display_name": entry.author_display_name,
        "author_channel_id": entry.author_channel_id,
        "comments": result_comments,
        "my_annotation": my_ann,
        "all_annotations": all_anns,
    }


# ─── Upsert de anotação + detecção de conflito ─────────────────────────────


def upsert_annotation(
    db: Session,
    entry_id: uuid.UUID,
    annotator_id: uuid.UUID,
    label: str,
    justificativa: str | None,
) -> dict:
    entry = db.query(DatasetEntry).filter(DatasetEntry.id == entry_id).first()
    if entry is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Entrada de dataset não encontrada."
        )

    # Upsert: cria ou atualiza
    existing = (
        db.query(Annotation)
        .filter_by(dataset_entry_id=entry_id, annotator_id=annotator_id)
        .first()
    )

    if existing:
        existing.label = label
        existing.justificativa = justificativa
        existing.updated_at = datetime.utcnow()
        annotation = existing
    else:
        annotation = Annotation(
            dataset_entry_id=entry_id,
            annotator_id=annotator_id,
            label=label,
            justificativa=justificativa,
        )
        db.add(annotation)

    db.flush()

    # Verificar conflito: outro pesquisador anotou com label diferente?
    other = (
        db.query(Annotation)
        .filter(
            Annotation.dataset_entry_id == entry_id,
            Annotation.annotator_id != annotator_id,
        )
        .first()
    )

    conflict_created = False

    if other and other.label != label:
        conflict = (
            db.query(AnnotationConflict).filter_by(dataset_entry_id=entry_id).first()
        )
        if not conflict:
            conflict = AnnotationConflict(
                dataset_entry_id=entry_id,
                annotation_a_id=other.id,
                annotation_b_id=annotation.id,
            )
            db.add(conflict)
            conflict_created = True
        elif conflict.status == "resolved":
            # Reanotação após resolução → reabre o conflito
            conflict.status = "pending"
            conflict.resolved_by = None
            conflict.resolved_label = None
            conflict.resolved_at = None
            conflict_created = True
    elif other and other.label == label:
        # Labels agora concordam — resolver conflito se existir
        conflict = (
            db.query(AnnotationConflict).filter_by(dataset_entry_id=entry_id).first()
        )
        if conflict and conflict.status == "pending":
            db.delete(conflict)

    db.commit()

    return {
        "annotation_id": annotation.id,
        "entry_id": entry_id,
        "label": label,
        "conflict_created": conflict_created,
    }


# ─── Progresso do pesquisador ───────────────────────────────────────────────


def get_my_progress(
    db: Session,
    annotator_id: uuid.UUID,
) -> list[dict]:
    datasets = db.query(Dataset).order_by(Dataset.created_at.desc()).all()

    result = []
    for ds in datasets:
        total_users = (
            db.query(func.count(DatasetEntry.id))
            .filter(DatasetEntry.dataset_id == ds.id)
            .scalar()
        )

        if total_users == 0:
            continue

        # Minhas anotações para entries neste dataset
        my_annotations = (
            db.query(Annotation)
            .join(DatasetEntry, Annotation.dataset_entry_id == DatasetEntry.id)
            .filter(
                DatasetEntry.dataset_id == ds.id,
                Annotation.annotator_id == annotator_id,
            )
            .all()
        )

        annotated = len(my_annotations)
        bots = sum(1 for a in my_annotations if a.label == "bot")
        humans = sum(1 for a in my_annotations if a.label == "humano")

        result.append(
            {
                "dataset_id": ds.id,
                "dataset_name": ds.name,
                "total_users": total_users,
                "annotated": annotated,
                "bots": bots,
                "humans": humans,
                "percent_complete": round(annotated / total_users * 100, 1),
            }
        )

    return result


# ─── Progresso de todos os anotadores (admin) ──────────────────────────────


def get_all_progress(db: Session) -> list[dict]:
    from models.user import User

    datasets = db.query(Dataset).order_by(Dataset.created_at.desc()).all()
    annotators = db.query(User).filter(User.is_active.is_(True)).all()

    result = []
    for ds in datasets:
        total_users = (
            db.query(func.count(DatasetEntry.id))
            .filter(DatasetEntry.dataset_id == ds.id)
            .scalar()
        )
        if total_users == 0:
            continue

        for annotator in annotators:
            if annotator.role == "admin":
                continue

            annotations = (
                db.query(Annotation)
                .join(DatasetEntry, Annotation.dataset_entry_id == DatasetEntry.id)
                .filter(
                    DatasetEntry.dataset_id == ds.id,
                    Annotation.annotator_id == annotator.id,
                )
                .all()
            )

            annotated = len(annotations)
            bots = sum(1 for a in annotations if a.label == "bot")
            humans = sum(1 for a in annotations if a.label == "humano")

            result.append(
                {
                    "annotator_id": annotator.id,
                    "annotator_name": annotator.name,
                    "dataset_id": ds.id,
                    "dataset_name": ds.name,
                    "total_users": total_users,
                    "annotated": annotated,
                    "bots": bots,
                    "humans": humans,
                    "percent_complete": round(annotated / total_users * 100, 1),
                }
            )

    return result


# ─── Import de anotações (JSON simétrico) ──────────────────────────────────


def import_annotations(
    db: Session,
    annotator_id: uuid.UUID,
    annotations: list,
) -> dict:
    imported = 0
    updated = 0
    skipped = 0
    errors = []

    for item in annotations:
        entry = db.query(DatasetEntry).filter(DatasetEntry.id == item.entry_id).first()
        if entry is None:
            skipped += 1
            errors.append(f"Entrada {item.entry_id} não encontrada.")
            continue

        if item.label == "bot" and not (item.justificativa or "").strip():
            skipped += 1
            errors.append(
                f"Entrada {item.entry_id}: " "justificativa obrigatória para 'bot'."
            )
            continue

        existing = (
            db.query(Annotation)
            .filter_by(dataset_entry_id=item.entry_id, annotator_id=annotator_id)
            .first()
        )

        if existing:
            existing.label = item.label
            existing.justificativa = item.justificativa
            existing.updated_at = datetime.utcnow()
            updated += 1
        else:
            annotation = Annotation(
                dataset_entry_id=item.entry_id,
                annotator_id=annotator_id,
                label=item.label,
                justificativa=item.justificativa,
            )
            db.add(annotation)
            imported += 1

    db.commit()

    logger.info(
        "Import de anotações: imported=%d, updated=%d, skipped=%d",
        imported,
        updated,
        skipped,
    )
    return {
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
    }


def import_annotations_chunk(
    db: Session,
    annotator_id: uuid.UUID,
    annotations: list,
    done: bool,
) -> dict:
    """Batch adicional de anotações para import paginado."""
    result = import_annotations(db, annotator_id, annotations)
    return {
        "total_imported": result["imported"],
        "total_updated": result["updated"],
        "chunk_received": len(annotations),
        "done": done,
    }


# ─── Export de anotações (JSON streaming) ───────────────────────────────────


def export_annotations_json(
    db: Session,
    annotator_id: uuid.UUID,
    dataset_id: uuid.UUID | None = None,
):
    """Gerador de JSON streaming com anotações do pesquisador."""
    query = (
        db.query(Annotation)
        .join(DatasetEntry, Annotation.dataset_entry_id == DatasetEntry.id)
        .filter(Annotation.annotator_id == annotator_id)
    )

    if dataset_id:
        query = query.filter(DatasetEntry.dataset_id == dataset_id)

    # Metadados do dataset se filtrado
    meta = {}
    if dataset_id:
        ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if ds:
            collection = (
                db.query(Collection).filter(Collection.id == ds.collection_id).first()
            )
            meta = {
                "dataset_id": str(ds.id),
                "dataset_name": ds.name,
                "video_id": collection.video_id if collection else "",
            }

    yield "{\n"
    if meta:
        yield f'  "dataset_id": {json.dumps(meta.get("dataset_id", ""))},\n'
        yield f'  "dataset_name": {json.dumps(meta.get("dataset_name", ""))},\n'
        yield f'  "video_id": {json.dumps(meta.get("video_id", ""))},\n'
    yield '  "annotations": [\n'

    first = True
    for ann in query.yield_per(500):
        prefix = "    " if first else ",\n    "
        first = False
        item = {
            "entry_id": str(ann.dataset_entry_id),
            "author_channel_id": ann.dataset_entry.author_channel_id,
            "author_display_name": ann.dataset_entry.author_display_name,
            "label": ann.label,
            "justificativa": ann.justificativa,
            "annotated_at": ann.annotated_at.isoformat() + "Z"
            if ann.annotated_at
            else None,
        }
        yield prefix + json.dumps(item, ensure_ascii=False)

    yield "\n  ]\n}\n"


def export_annotations_csv(
    db: Session,
    annotator_id: uuid.UUID,
    dataset_id: uuid.UUID | None = None,
):
    """Gerador de CSV streaming com anotações do pesquisador."""
    query = (
        db.query(Annotation)
        .join(DatasetEntry, Annotation.dataset_entry_id == DatasetEntry.id)
        .filter(Annotation.annotator_id == annotator_id)
    )

    if dataset_id:
        query = query.filter(DatasetEntry.dataset_id == dataset_id)

    yield "entry_id,author_channel_id,label,justificativa\n"

    for ann in query.yield_per(500):
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                str(ann.dataset_entry_id),
                ann.dataset_entry.author_channel_id,
                ann.label,
                ann.justificativa or "",
            ]
        )
        yield buf.getvalue()

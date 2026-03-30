"""Serviço da US-04 — anotação de comentários (bot/humano)."""

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
) -> dict:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if dataset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Dataset não encontrado.")

    entries = db.query(DatasetEntry).filter(DatasetEntry.dataset_id == dataset_id).all()

    collection_id = dataset.collection_id
    total_annotated = 0
    total_comments = 0

    items = []
    for entry in entries:
        comment_count = (
            db.query(func.count(Comment.id))
            .filter(
                Comment.collection_id == collection_id,
                Comment.author_channel_id == entry.author_channel_id,
            )
            .scalar()
        )

        if is_admin:
            # Admin: comentários com pelo menos 1 anotação de qualquer pesquisador
            annotated = (
                db.query(func.count(func.distinct(Annotation.comment_id)))
                .join(Comment, Annotation.comment_id == Comment.id)
                .filter(
                    Comment.collection_id == collection_id,
                    Comment.author_channel_id == entry.author_channel_id,
                )
                .scalar()
            )
        else:
            # Pesquisador: apenas as próprias anotações
            annotated = (
                db.query(func.count(Annotation.id))
                .join(Comment, Annotation.comment_id == Comment.id)
                .filter(
                    Comment.collection_id == collection_id,
                    Comment.author_channel_id == entry.author_channel_id,
                    Annotation.annotator_id == annotator_id,
                )
                .scalar()
            )

        total_comments += comment_count
        total_annotated += annotated

        items.append(
            {
                "entry_id": entry.id,
                "author_channel_id": entry.author_channel_id,
                "author_display_name": entry.author_display_name,
                "comment_count": comment_count,
                "my_annotated_count": annotated,
                "my_pending_count": comment_count - annotated,
            }
        )

    return {
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "total_users": len(entries),
        "total_comments": total_comments,
        "annotated_comments_by_me": total_annotated,
        "items": items,
    }


# ─── Comentários de um usuário (entry) ──────────────────────────────────────


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

    result_comments = []
    for c in comments:
        # Anotação do pesquisador logado
        my_ann = None
        if not is_admin:
            annotation = (
                db.query(Annotation)
                .filter(
                    Annotation.comment_id == c.id,
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

        # Admin vê todas as anotações de todos os pesquisadores
        all_anns = None
        if is_admin:
            annotations = (
                db.query(Annotation).filter(Annotation.comment_id == c.id).all()
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

        result_comments.append(
            {
                "comment_db_id": c.id,
                "text_original": c.text_original,
                "like_count": c.like_count,
                "reply_count": c.reply_count,
                "published_at": c.published_at,
                "my_annotation": my_ann,
                "all_annotations": all_anns,
            }
        )

    return {
        "entry_id": entry.id,
        "author_display_name": entry.author_display_name,
        "author_channel_id": entry.author_channel_id,
        "comments": result_comments,
    }


# ─── Upsert de anotação + detecção de conflito ─────────────────────────────


def upsert_annotation(
    db: Session,
    comment_id: uuid.UUID,
    annotator_id: uuid.UUID,
    label: str,
    justificativa: str | None,
) -> dict:
    # Verificar que o comentário existe
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if comment is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Comentário não encontrado."
        )

    # Upsert: cria ou atualiza
    existing = (
        db.query(Annotation)
        .filter_by(comment_id=comment_id, annotator_id=annotator_id)
        .first()
    )

    if existing:
        existing.label = label
        existing.justificativa = justificativa
        existing.updated_at = datetime.utcnow()
        annotation = existing
    else:
        annotation = Annotation(
            comment_id=comment_id,
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
            Annotation.comment_id == comment_id,
            Annotation.annotator_id != annotator_id,
        )
        .first()
    )

    conflict_created = False

    if other and other.label != label:
        conflict = db.query(AnnotationConflict).filter_by(comment_id=comment_id).first()
        if not conflict:
            conflict = AnnotationConflict(
                comment_id=comment_id,
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
        conflict = db.query(AnnotationConflict).filter_by(comment_id=comment_id).first()
        if conflict and conflict.status == "pending":
            db.delete(conflict)

    db.commit()

    return {
        "annotation_id": annotation.id,
        "comment_db_id": comment_id,
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
        # Total de comentários dos usuários selecionados neste dataset
        total_comments = (
            db.query(func.count(Comment.id))
            .join(
                DatasetEntry,
                (DatasetEntry.author_channel_id == Comment.author_channel_id)
                & (DatasetEntry.dataset_id == ds.id),
            )
            .filter(Comment.collection_id == ds.collection_id)
            .scalar()
        )

        # Minhas anotações para comentários neste dataset
        my_annotations = (
            db.query(Annotation)
            .join(Comment, Annotation.comment_id == Comment.id)
            .join(
                DatasetEntry,
                (DatasetEntry.author_channel_id == Comment.author_channel_id)
                & (DatasetEntry.dataset_id == ds.id),
            )
            .filter(
                Comment.collection_id == ds.collection_id,
                Annotation.annotator_id == annotator_id,
            )
            .all()
        )

        annotated = len(my_annotations)
        bots = sum(1 for a in my_annotations if a.label == "bot")
        humans = sum(1 for a in my_annotations if a.label == "humano")

        if total_comments > 0:
            result.append(
                {
                    "dataset_id": ds.id,
                    "dataset_name": ds.name,
                    "total_comments": total_comments,
                    "annotated": annotated,
                    "bots": bots,
                    "humans": humans,
                    "percent_complete": round(annotated / total_comments * 100, 1),
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
        total_comments = (
            db.query(func.count(Comment.id))
            .join(
                DatasetEntry,
                (DatasetEntry.author_channel_id == Comment.author_channel_id)
                & (DatasetEntry.dataset_id == ds.id),
            )
            .filter(Comment.collection_id == ds.collection_id)
            .scalar()
        )
        if total_comments == 0:
            continue

        for annotator in annotators:
            if annotator.role == "admin":
                continue

            annotations = (
                db.query(Annotation)
                .join(Comment, Annotation.comment_id == Comment.id)
                .join(
                    DatasetEntry,
                    (DatasetEntry.author_channel_id == Comment.author_channel_id)
                    & (DatasetEntry.dataset_id == ds.id),
                )
                .filter(
                    Comment.collection_id == ds.collection_id,
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
                    "total_comments": total_comments,
                    "annotated": annotated,
                    "bots": bots,
                    "humans": humans,
                    "percent_complete": round(annotated / total_comments * 100, 1),
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
        comment = db.query(Comment).filter(Comment.id == item.comment_db_id).first()
        if comment is None:
            skipped += 1
            errors.append(f"Comentário {item.comment_db_id} não encontrado.")
            continue

        if item.label == "bot" and not (item.justificativa or "").strip():
            skipped += 1
            errors.append(
                f"Comentário {item.comment_db_id}: "
                "justificativa obrigatória para 'bot'."
            )
            continue

        existing = (
            db.query(Annotation)
            .filter_by(comment_id=item.comment_db_id, annotator_id=annotator_id)
            .first()
        )

        if existing:
            existing.label = item.label
            existing.justificativa = item.justificativa
            existing.updated_at = datetime.utcnow()
            updated += 1
        else:
            annotation = Annotation(
                comment_id=item.comment_db_id,
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
        .join(Comment, Annotation.comment_id == Comment.id)
        .filter(Annotation.annotator_id == annotator_id)
    )

    if dataset_id:
        query = (
            query.join(
                DatasetEntry,
                (DatasetEntry.author_channel_id == Comment.author_channel_id)
                & (DatasetEntry.dataset_id == dataset_id),
            )
            .join(Dataset, Dataset.id == DatasetEntry.dataset_id)
            .filter(
                Comment.collection_id == Dataset.collection_id,
            )
        )

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
            "comment_db_id": str(ann.comment_id),
            "author_channel_id": ann.comment.author_channel_id,
            "text_original": ann.comment.text_original,
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
        .join(Comment, Annotation.comment_id == Comment.id)
        .filter(Annotation.annotator_id == annotator_id)
    )

    if dataset_id:
        query = (
            query.join(
                DatasetEntry,
                (DatasetEntry.author_channel_id == Comment.author_channel_id)
                & (DatasetEntry.dataset_id == dataset_id),
            )
            .join(Dataset, Dataset.id == DatasetEntry.dataset_id)
            .filter(
                Comment.collection_id == Dataset.collection_id,
            )
        )

    yield "comment_db_id,label,justificativa\n"

    for ann in query.yield_per(500):
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([str(ann.comment_id), ann.label, ann.justificativa or ""])
        yield buf.getvalue()

import csv
import io
import json
import uuid

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models.collection import Collection, Comment
from models.user import User
from schemas.clean import (
    DatasetCreate,
    DatasetImport,
    DatasetImportChunk,
    DatasetImportChunkResponse,
    DatasetResponse,
    DatasetSummary,
    PreviewResponse,
)
from services.auth import get_current_user
from services.clean.service import (
    create_dataset,
    delete_dataset,
    get_dataset_with_entries,
    import_dataset,
    import_dataset_chunk,
    list_datasets,
    preview,
)

router = APIRouter(prefix="/clean", tags=["clean"])


# ─── Preview ─────────────────────────────────────────────────────────────────


@router.get("/preview", response_model=PreviewResponse)
def preview_endpoint(
    collection_id: uuid.UUID,
    criteria: str = Query(..., description="Critérios separados por vírgula"),
    threshold_chars: int = Query(default=20, ge=1, le=500),
    threshold_seconds: int = Query(default=30, ge=1, le=3600),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    criteria_list = [c.strip() for c in criteria.split(",") if c.strip()]
    return preview(
        db,
        collection_id,
        criteria_list,
        threshold_chars=threshold_chars,
        threshold_seconds=threshold_seconds,
    )


# ─── Criação de Dataset ──────────────────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DatasetResponse)
def create_dataset_endpoint(
    payload: DatasetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = create_dataset(
        db,
        payload.collection_id,
        list(payload.criteria),
        payload.thresholds.threshold_chars,
        payload.thresholds.threshold_seconds,
        current_user.id,
    )
    collection = (
        db.query(Collection).filter(Collection.id == dataset.collection_id).first()
    )
    return DatasetResponse(
        dataset_id=dataset.id,
        name=dataset.name,
        collection_id=dataset.collection_id,
        video_id=collection.video_id,
        total_users_original=dataset.total_users_original,
        total_users_selected=dataset.total_users_selected,
        criteria_applied=dataset.criteria_applied,
        created_at=dataset.created_at,
    )


# ─── Import de dataset ────────────────────────────────────────────────────────


@router.post(
    "/import", status_code=status.HTTP_201_CREATED, response_model=DatasetResponse
)
def import_dataset_endpoint(
    payload: DatasetImport,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = import_dataset(
        db,
        payload.dataset.video_id,
        payload.dataset.name,
        payload.dataset.criteria_applied,
        payload.users,
        current_user.id,
    )
    collection = (
        db.query(Collection).filter(Collection.id == dataset.collection_id).first()
    )
    return DatasetResponse(
        dataset_id=dataset.id,
        name=dataset.name,
        collection_id=dataset.collection_id,
        video_id=collection.video_id,
        total_users_original=dataset.total_users_original,
        total_users_selected=dataset.total_users_selected,
        criteria_applied=dataset.criteria_applied,
        created_at=dataset.created_at,
    )


@router.post("/import-chunk", response_model=DatasetImportChunkResponse)
def import_chunk_endpoint(
    payload: DatasetImportChunk,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = import_dataset_chunk(db, payload.dataset_id, payload.users, payload.done)
    return DatasetImportChunkResponse(**result)


# ─── Listagem ────────────────────────────────────────────────────────────────


@router.get("/datasets", response_model=list[DatasetSummary])
def list_datasets_endpoint(
    video_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    datasets = list_datasets(db, video_id)
    result = []
    for ds in datasets:
        collection = (
            db.query(Collection).filter(Collection.id == ds.collection_id).first()
        )
        result.append(
            DatasetSummary(
                dataset_id=ds.id,
                name=ds.name,
                video_id=collection.video_id if collection else "",
                total_users_selected=ds.total_users_selected,
                criteria_applied=ds.criteria_applied,
                created_at=ds.created_at,
            )
        )
    return result


# ─── Download ────────────────────────────────────────────────────────────────


_DATASET_CSV_FIELDS = [
    "author_channel_id",
    "author_display_name",
    "text_original",
    "like_count",
    "reply_count",
    "published_at",
    "author_channel_published_at",
]


@router.get("/datasets/{dataset_id}/download")
def download_dataset_endpoint(
    dataset_id: uuid.UUID,
    fmt: str = Query(default="json", alias="format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = get_dataset_with_entries(db, dataset_id)
    collection = (
        db.query(Collection).filter(Collection.id == dataset.collection_id).first()
    )

    entry_channel_ids = [e.author_channel_id for e in dataset.entries]

    def _comments_iter():
        return (
            db.query(Comment)
            .filter(
                Comment.collection_id == dataset.collection_id,
                Comment.author_channel_id.in_(entry_channel_ids),
            )
            .order_by(Comment.published_at)
            .yield_per(500)
        )

    if fmt == "csv":

        def csv_stream():
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=_DATASET_CSV_FIELDS)
            writer.writeheader()
            yield "\ufeff" + buf.getvalue()
            for c in _comments_iter():
                buf = io.StringIO()
                writer = csv.DictWriter(buf, fieldnames=_DATASET_CSV_FIELDS)
                writer.writerow(
                    {
                        "author_channel_id": c.author_channel_id or "",
                        "author_display_name": c.author_display_name,
                        "text_original": c.text_original,
                        "like_count": c.like_count,
                        "reply_count": c.reply_count,
                        "published_at": c.published_at.isoformat(),
                        "author_channel_published_at": (
                            c.author_channel_published_at.isoformat()
                            if c.author_channel_published_at
                            else ""
                        ),
                    }
                )
                yield buf.getvalue()

        return StreamingResponse(
            csv_stream(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{dataset.name}.csv"',
            },
        )

    def json_stream():
        meta = {
            "name": dataset.name,
            "video_id": collection.video_id if collection else "",
            "criteria_applied": dataset.criteria_applied,
            "total_users_original": dataset.total_users_original,
            "total_users_selected": dataset.total_users_selected,
        }
        users = [
            {
                "author_channel_id": e.author_channel_id,
                "author_display_name": e.author_display_name,
                "comment_count": e.comment_count,
                "matched_criteria": e.matched_criteria,
            }
            for e in dataset.entries
        ]
        yield '{\n  "dataset": ' + json.dumps(meta, ensure_ascii=False) + ",\n"
        yield '  "users": ' + json.dumps(users, ensure_ascii=False, indent=4) + ",\n"
        yield '  "comments": [\n'
        first = True
        for c in _comments_iter():
            prefix = "    " if first else ",\n    "
            first = False
            yield prefix + json.dumps(
                {
                    "author_channel_id": c.author_channel_id,
                    "author_display_name": c.author_display_name,
                    "text_original": c.text_original,
                    "like_count": c.like_count,
                    "reply_count": c.reply_count,
                    "published_at": c.published_at.isoformat(),
                    "author_channel_published_at": (
                        c.author_channel_published_at.isoformat()
                        if c.author_channel_published_at
                        else None
                    ),
                },
                ensure_ascii=False,
            )
        yield "\n  ]\n}\n"

    return StreamingResponse(
        json_stream(),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{dataset.name}.json"',
        },
    )


# ─── Deletar ─────────────────────────────────────────────────────────────────


@router.delete("/datasets/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset_endpoint(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    delete_dataset(db, dataset_id)

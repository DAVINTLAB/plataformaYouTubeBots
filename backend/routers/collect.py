import csv
import io
import json
import uuid

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.collect import (
    CollectionStarted,
    CollectionStatus,
    CollectionSummary,
    CollectNextPageRequest,
    CollectRequest,
    EnrichRequest,
    EnrichResponse,
    ImportChunkRequest,
    ImportChunkResponse,
    ImportRequest,
)
from services.auth import get_current_user
from services.collect import (
    collect_next_page,
    delete_collection,
    enrich_collection,
    export_comments_iter,
    get_collection_status,
    import_chunk,
    import_collection,
    list_collections,
    start_collection,
)

router = APIRouter(prefix="/collect", tags=["collect"])


def _to_started(collection, next_page_token: str | None) -> CollectionStarted:
    return CollectionStarted(
        collection_id=collection.id,
        video_id=collection.video_id,
        status=collection.status,
        total_comments=collection.total_comments,
        next_page_token=next_page_token,
        enrich_status=collection.enrich_status,
        duration_seconds=collection.duration_seconds,
        created_at=collection.created_at,
    )


def _to_status(collection, username: str) -> CollectionStatus:
    return CollectionStatus(
        collection_id=collection.id,
        video_id=collection.video_id,
        video_title=collection.video_title,
        status=collection.status,
        total_comments=collection.total_comments,
        channel_dates_failed=collection.channel_dates_failed,
        enrich_status=collection.enrich_status,
        duration_seconds=collection.duration_seconds,
        collected_at=collection.completed_at,
        collected_by=username,
    )


def _to_summary(collection) -> CollectionSummary:
    return CollectionSummary(
        collection_id=collection.id,
        video_id=collection.video_id,
        video_title=collection.video_title,
        status=collection.status,
        total_comments=collection.total_comments,
        channel_dates_failed=collection.channel_dates_failed,
        enrich_status=collection.enrich_status,
        duration_seconds=collection.duration_seconds,
        collected_at=collection.completed_at,
    )


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=CollectionStarted)
async def start(
    payload: CollectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    collection, next_page_token = await start_collection(db, payload, current_user.id)
    return _to_started(collection, next_page_token)


@router.post("/next-page", response_model=CollectionStarted)
async def next_page(
    payload: CollectNextPageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    collection, next_page_token = await collect_next_page(db, payload, current_user.id)
    return _to_started(collection, next_page_token)


@router.post(
    "/import", status_code=status.HTTP_201_CREATED, response_model=CollectionStarted
)
def import_endpoint(
    payload: ImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    collection = import_collection(db, payload, current_user.id)
    return _to_started(collection, None)


@router.post("/import-chunk", response_model=ImportChunkResponse)
def import_chunk_endpoint(
    payload: ImportChunkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = import_chunk(db, payload.collection_id, payload.comments, payload.done)
    return ImportChunkResponse(**result)


@router.post("/{collection_id}/enrich", response_model=EnrichResponse)
async def enrich(
    collection_id: uuid.UUID,
    payload: EnrichRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await enrich_collection(
        db,
        collection_id,
        payload.api_key.get_secret_value(),
    )
    return EnrichResponse(**result)


@router.get("/status", response_model=CollectionStatus)
def get_status(
    collection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    collection = get_collection_status(db, collection_id)
    return _to_status(collection, current_user.username)


_CSV_FIELDS = [
    "video_id",
    "video_title",
    "video_channel_id",
    "video_channel_title",
    "video_published_at",
    "video_view_count",
    "video_like_count",
    "video_comment_count",
    "comment_id",
    "parent_id",
    "author_display_name",
    "author_channel_id",
    "author_channel_published_at",
    "author_profile_image_url",
    "author_channel_url",
    "text_original",
    "text_display",
    "like_count",
    "reply_count",
    "published_at",
    "updated_at",
]


def _comment_to_csv_row(c, collection) -> dict:
    return {
        "video_id": collection.video_id,
        "video_title": collection.video_title or "",
        "video_channel_id": collection.video_channel_id or "",
        "video_channel_title": collection.video_channel_title or "",
        "video_published_at": (
            collection.video_published_at.isoformat()
            if collection.video_published_at
            else ""
        ),
        "video_view_count": collection.video_view_count or "",
        "video_like_count": collection.video_like_count or "",
        "video_comment_count": collection.video_comment_count or "",
        "comment_id": c.comment_id,
        "parent_id": c.parent_id or "",
        "author_display_name": c.author_display_name,
        "author_channel_id": c.author_channel_id or "",
        "author_channel_published_at": (
            c.author_channel_published_at.isoformat()
            if c.author_channel_published_at
            else ""
        ),
        "author_profile_image_url": c.author_profile_image_url or "",
        "author_channel_url": c.author_channel_url or "",
        "text_original": c.text_original,
        "text_display": c.text_display or "",
        "like_count": c.like_count,
        "reply_count": c.reply_count,
        "published_at": c.published_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
    }


def _comment_to_json_dict(c) -> dict:
    return {
        "comment_id": c.comment_id,
        "parent_id": c.parent_id,
        "author_display_name": c.author_display_name,
        "author_channel_id": c.author_channel_id,
        "author_channel_published_at": (
            c.author_channel_published_at.isoformat()
            if c.author_channel_published_at
            else None
        ),
        "author_profile_image_url": c.author_profile_image_url,
        "author_channel_url": c.author_channel_url,
        "text_original": c.text_original,
        "text_display": c.text_display,
        "like_count": c.like_count,
        "reply_count": c.reply_count,
        "published_at": c.published_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
    }


@router.get("/{collection_id}/export")
def export_endpoint(
    collection_id: uuid.UUID,
    fmt: str = Query(default="json", alias="format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    collection = get_collection_status(db, collection_id)
    video_id = collection.video_id

    if fmt == "csv":

        def csv_stream():
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=_CSV_FIELDS)
            writer.writeheader()
            # BOM para compatibilidade Excel
            yield "\ufeff" + output.getvalue()
            for c in export_comments_iter(db, collection_id):
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=_CSV_FIELDS)
                writer.writerow(_comment_to_csv_row(c, collection))
                yield output.getvalue()

        return StreamingResponse(
            csv_stream(),
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{video_id}_comments.csv"'
                ),
            },
        )

    def json_stream():
        video = {
            "id": collection.video_id,
            "title": collection.video_title,
            "channel_id": collection.video_channel_id,
            "channel_title": collection.video_channel_title,
            "published_at": (
                collection.video_published_at.isoformat()
                if collection.video_published_at
                else None
            ),
            "view_count": collection.video_view_count,
            "like_count": collection.video_like_count,
            "comment_count": collection.video_comment_count,
        }
        yield '{\n  "video": ' + json.dumps(video, ensure_ascii=False) + ",\n"
        yield '  "comments": [\n'
        first = True
        for c in export_comments_iter(db, collection_id):
            prefix = "    " if first else ",\n    "
            first = False
            yield prefix + json.dumps(_comment_to_json_dict(c), ensure_ascii=False)
        yield "\n  ]\n}\n"

    return StreamingResponse(
        json_stream(),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{video_id}_comments.json"',
        },
    )


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection_endpoint(
    collection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    delete_collection(db, collection_id)


@router.get("", response_model=list[CollectionSummary])
def list_user_collections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    collections = list_collections(db)
    return [_to_summary(c) for c in collections]

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models.dataset import Dataset
from models.user import User
from schemas.review import (
    ConflictDetail,
    ImportChunkResponse,
    ImportResult,
    PaginatedBots,
    PaginatedConflicts,
    ResolveRequest,
    ResolveResponse,
    ReviewImport,
    ReviewImportChunk,
    ReviewStats,
)
from services.auth import require_admin
from services.review import (
    export_review_csv,
    export_review_json,
    get_conflict_detail,
    get_stats,
    import_review,
    import_review_chunk,
    list_bots,
    list_conflicts,
    resolve_conflict,
)

router = APIRouter(prefix="/review", tags=["review"])


# ─── Listar conflitos ────────────────────────────────────────────────────────


@router.get("/conflicts", response_model=PaginatedConflicts)
def list_conflicts_endpoint(
    status: str | None = Query(default=None),
    video_id: str | None = Query(default=None),
    dataset_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return list_conflicts(
        db,
        conflict_status=status,
        video_id=video_id,
        dataset_id=dataset_id,
        page=page,
        page_size=page_size,
    )


# ─── Detalhe de um conflito ──────────────────────────────────────────────────


@router.get("/conflicts/{conflict_id}", response_model=ConflictDetail)
def get_conflict_endpoint(
    conflict_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return get_conflict_detail(db, conflict_id)


# ─── Resolver conflito ───────────────────────────────────────────────────────


@router.post("/resolve", response_model=ResolveResponse)
def resolve_endpoint(
    payload: ResolveRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return resolve_conflict(db, payload.conflict_id, admin.id, payload.resolved_label)


# ─── Listar bots ─────────────────────────────────────────────────────────────


@router.get("/bots", response_model=PaginatedBots)
def list_bots_endpoint(
    video_id: str | None = Query(default=None),
    dataset_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return list_bots(
        db,
        video_id=video_id,
        dataset_id=dataset_id,
        page=page,
        page_size=page_size,
    )


# ─── Estatisticas ────────────────────────────────────────────────────────────


@router.get("/stats", response_model=ReviewStats)
def stats_endpoint(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return get_stats(db)


# ─── Export ───────────────────────────────────────────────────────────────────


@router.get("/export")
def export_endpoint(
    dataset_id: uuid.UUID = Query(),
    fmt: str = Query(default="json", alias="format"),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Dataset não encontrado.")

    safe_name = dataset.name.replace(" ", "_")

    if fmt == "csv":
        return StreamingResponse(
            export_review_csv(db, dataset_id),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="review_{safe_name}.csv"',
            },
        )

    return StreamingResponse(
        export_review_json(db, dataset_id),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="review_{safe_name}.json"',
        },
    )


# ─── Import ──────────────────────────────────────────────────────────────────


@router.post("/import", response_model=ImportResult)
def import_endpoint(
    payload: ReviewImport,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return import_review(db, admin.id, payload.video_id, payload.comments)


@router.post("/import-chunk", response_model=ImportChunkResponse)
def import_chunk_endpoint(
    payload: ReviewImportChunk,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    result = import_review_chunk(db, admin.id, payload.comments, payload.done)
    return ImportChunkResponse(**result)

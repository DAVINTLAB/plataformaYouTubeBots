import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.annotate import (
    AnnotationCreate,
    AnnotationImport,
    AnnotationImportChunk,
    AnnotationResult,
    AnnotatorProgress,
    DatasetProgress,
    DatasetUsersResponse,
    ImportChunkResponse,
    ImportResult,
    UserCommentsResponse,
)
from services.annotate import (
    export_annotations_csv,
    export_annotations_json,
    get_all_progress,
    get_entry_comments,
    get_my_progress,
    import_annotations,
    import_annotations_chunk,
    list_dataset_users,
    upsert_annotation,
)
from services.auth import get_current_user, require_admin

router = APIRouter(prefix="/annotate", tags=["annotate"])


# ─── Listar usuários do dataset ─────────────────────────────────────────────


@router.get("/users", response_model=DatasetUsersResponse)
def list_users_endpoint(
    dataset_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_dataset_users(
        db,
        dataset_id,
        current_user.id,
        is_admin=current_user.role == "admin",
        page=page,
        page_size=page_size,
    )


# ─── Comentários de um usuário (entry) ──────────────────────────────────────


@router.get("/comments/{entry_id}", response_model=UserCommentsResponse)
def get_comments_endpoint(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_entry_comments(
        db, entry_id, current_user.id, is_admin=current_user.role == "admin"
    )


# ─── Anotar comentário ──────────────────────────────────────────────────────


@router.post("", response_model=AnnotationResult)
def annotate_endpoint(
    payload: AnnotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "admin":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Administradores não podem anotar. "
            "Use a etapa de Revisão para desempatar conflitos.",
        )

    result = upsert_annotation(
        db,
        payload.comment_db_id,
        current_user.id,
        payload.label,
        payload.justificativa,
    )

    return result


# ─── Progresso do pesquisador ────────────────────────────────────────────────


@router.get("/my-progress", response_model=list[DatasetProgress])
def my_progress_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_my_progress(db, current_user.id)


# ─── Progresso de todos os anotadores (admin) ───────────────────────────────


@router.get("/all-progress", response_model=list[AnnotatorProgress])
def all_progress_endpoint(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return get_all_progress(db)


# ─── Import ─────────────────────────────────────────────────────────────────


@router.post("/import", response_model=ImportResult)
def import_endpoint(
    payload: AnnotationImport,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return import_annotations(db, current_user.id, payload.annotations)


@router.post("/import-chunk", response_model=ImportChunkResponse)
def import_chunk_endpoint(
    payload: AnnotationImportChunk,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = import_annotations_chunk(
        db, current_user.id, payload.annotations, payload.done
    )
    return ImportChunkResponse(**result)


# ─── Export ──────────────────────────────────────────────────────────────────


@router.get("/export")
def export_endpoint(
    dataset_id: uuid.UUID | None = Query(default=None),
    fmt: str = Query(default="json", alias="format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if fmt == "csv":
        return StreamingResponse(
            export_annotations_csv(db, current_user.id, dataset_id),
            media_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="annotations.csv"',
            },
        )

    return StreamingResponse(
        export_annotations_json(db, current_user.id, dataset_id),
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="annotations.json"',
        },
    )

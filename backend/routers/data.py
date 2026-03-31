from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.data import (
    DataAnnotationProgress,
    DataCollection,
    DataDataset,
    DataSummary,
)
from services.auth import get_current_user
from services.data import (
    get_annotation_progress,
    get_summary,
    list_all_collections,
    list_all_datasets,
)

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/summary", response_model=DataSummary)
def summary_endpoint(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return get_summary(db)


@router.get("/collections", response_model=list[DataCollection])
def collections_endpoint(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return list_all_collections(db)


@router.get("/datasets", response_model=list[DataDataset])
def datasets_endpoint(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return list_all_datasets(db)


@router.get("/annotations", response_model=list[DataAnnotationProgress])
def annotations_endpoint(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return get_annotation_progress(db)

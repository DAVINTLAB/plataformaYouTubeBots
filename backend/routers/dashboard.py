"""Router da US-06 — Dashboard de Análise."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.dashboard import (
    BotCommentsResponse,
    CriteriaEffectivenessItem,
    GlobalDashboardResponse,
    UserDashboardResponse,
    VideoDashboardResponse,
)
from services.auth import get_current_user
from services.dashboard import (
    get_bot_comments,
    get_criteria_effectiveness,
    get_global_dashboard,
    get_user_dashboard,
    get_video_dashboard,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/global", response_model=GlobalDashboardResponse)
def global_endpoint(
    criteria: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    criteria_list = (
        [c.strip() for c in criteria.split(",") if c.strip()] if criteria else None
    )
    return get_global_dashboard(db, criteria=criteria_list)


@router.get(
    "/criteria-effectiveness",
    response_model=list[CriteriaEffectivenessItem],
)
def criteria_effectiveness_endpoint(
    video_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return get_criteria_effectiveness(db, video_id=video_id)


@router.get("/video", response_model=VideoDashboardResponse)
def video_endpoint(
    video_id: str = Query(),
    criteria: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    criteria_list = (
        [c.strip() for c in criteria.split(",") if c.strip()] if criteria else None
    )
    return get_video_dashboard(db, video_id=video_id, criteria=criteria_list)


@router.get("/user", response_model=UserDashboardResponse)
def user_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_user_dashboard(db, user_id=current_user.id)


@router.get("/bots", response_model=BotCommentsResponse)
def bots_endpoint(
    dataset_id: str | None = Query(default=None),
    video_id: str | None = Query(default=None),
    author: str | None = Query(default=None),
    search: str | None = Query(default=None),
    criteria: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    criteria_list = (
        [c.strip() for c in criteria.split(",") if c.strip()] if criteria else None
    )
    return get_bot_comments(
        db,
        dataset_id=dataset_id,
        video_id=video_id,
        author=author,
        search=search,
        criteria_filter=criteria_list,
        page=page,
        page_size=page_size,
    )

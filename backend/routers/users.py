import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.user import UserCreate, UserOut
from services.auth import require_admin
from services import user as user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserOut])
def list_users(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return user_service.list_all_users(db)


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return user_service.create_user(db, body)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: uuid.UUID,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user_service.deactivate_user(db, user_id, current_admin.id)


@router.post("/{user_id}/reactivate", response_model=UserOut)
def reactivate_user(
    user_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return user_service.reactivate_user(db, user_id)

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from services.auth import require_admin
from services.seed import delete_seed, run_seed

router = APIRouter(prefix="/seed", tags=["seed"])


@router.post("", status_code=status.HTTP_201_CREATED)
def seed_endpoint(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return run_seed(db)


@router.delete("", status_code=status.HTTP_200_OK)
def delete_seed_endpoint(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return delete_seed(db)

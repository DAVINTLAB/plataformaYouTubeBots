import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.user import User
from schemas.user import UserCreate
from services.auth import get_password_hash


def list_all_users(db: Session) -> list[User]:
    return db.query(User).all()


def create_user(db: Session, data: UserCreate) -> User:
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username já existe.",
        )
    user = User(
        username=data.username,
        hashed_password=get_password_hash(data.password),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def deactivate_user(
    db: Session, user_id: uuid.UUID, requesting_user_id: uuid.UUID
) -> None:
    if requesting_user_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Não é possível desativar seu próprio usuário.",
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )
    user.is_active = False
    db.commit()


def reactivate_user(db: Session, user_id: uuid.UUID) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Usuário já está ativo.",
        )
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user

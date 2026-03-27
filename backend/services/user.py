import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.user import User
from schemas.user import UserCreate
from services.auth import get_password_hash


def list_active_users(db: Session) -> list[User]:
    return db.query(User).filter(User.is_active == True).all()  # noqa: E712


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


def delete_user(
    db: Session, user_id: uuid.UUID, requesting_user_id: uuid.UUID
) -> None:
    if requesting_user_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Não é possível remover seu próprio usuário.",
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )
    db.delete(user)
    db.commit()

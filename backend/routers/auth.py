from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from core.rate_limit import limiter
from database import get_db
from schemas.user import LoginRequest, RefreshRequest, TokenResponse
from services.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_current_user,
    verify_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, body.username, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_data = {
        "sub": user.username,
        "role": user.role,
        "name": user.name,
    }
    return TokenResponse(
        access_token=create_access_token(data=token_data),
        refresh_token=create_refresh_token(data=token_data),
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
def refresh(request: Request, body: RefreshRequest, db: Session = Depends(get_db)):
    payload = verify_refresh_token(body.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido ou expirado.",
        )
    from models.user import User

    user = (
        db.query(User)
        .filter(
            User.username == payload.get("sub"),
            User.is_active == True,  # noqa: E712
        )
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou desativado.",
        )
    token_data = {
        "sub": user.username,
        "role": user.role,
        "name": user.name,
    }
    return TokenResponse(
        access_token=create_access_token(data=token_data),
        refresh_token=create_refresh_token(data=token_data),
    )


@router.post("/logout")
def logout(_current_user: object = Depends(get_current_user)):
    return {"detail": "Logout realizado com sucesso."}

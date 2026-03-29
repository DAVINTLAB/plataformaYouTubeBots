import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8)

    @field_validator("username")
    @classmethod
    def username_format(cls, v: str) -> str:
        import re

        if not re.fullmatch(r"[a-z0-9_.]+", v):
            raise ValueError(
                "Username deve conter apenas letras minúsculas, "
                "dígitos, ponto ou sublinhado."
            )
        return v


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8)


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    name: str
    role: str
    created_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

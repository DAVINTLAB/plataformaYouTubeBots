import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8)


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    role: str
    created_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

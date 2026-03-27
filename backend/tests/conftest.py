import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models.user import User
from services.auth import get_current_user, get_password_hash


@pytest.fixture
def db():
    # StaticPool garante que todas as conexões usem o mesmo banco in-memory
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db):
    user = User(
        username="admin",
        hashed_password=get_password_hash("adminpass1"),
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def regular_user(db):
    user = User(
        username="user1",
        hashed_password=get_password_hash("userpass1!"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_as_user(client, regular_user):
    """Stub: get_current_user retorna usuário com role='user'."""
    app.dependency_overrides[get_current_user] = lambda: regular_user
    yield regular_user


@pytest.fixture
def auth_as_admin(client, admin_user):
    """Stub: get_current_user retorna usuário com role='admin'."""
    app.dependency_overrides[get_current_user] = lambda: admin_user
    yield admin_user


@pytest.fixture
def fake_admin():
    """Dummy admin — sem persistência em banco."""
    return User(
        id=uuid.uuid4(),
        username="admin",
        hashed_password="hash",
        role="admin",
        is_active=True,
    )


@pytest.fixture
def fake_user():
    """Dummy user — sem persistência em banco."""
    return User(
        id=uuid.uuid4(),
        username="user1",
        hashed_password="hash",
        role="user",
        is_active=True,
    )

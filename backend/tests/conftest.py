import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from database import Base, get_db
from main import app
from models.user import User
from services.auth import get_current_user, get_password_hash

# Banco de testes: usa DATABASE_URL do ambiente se definida, senão PostgreSQL local
_base_url = os.getenv(
    "DATABASE_URL", "postgresql://davint:davint@localhost:5432/davint"
)
# Troca o banco pelo banco de teste (evita poluir o banco de dev/prod)
TEST_DATABASE_URL = _base_url.rsplit("/", 1)[0] + "/davint_test"


@pytest.fixture(scope="session")
def pg_engine():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db(pg_engine):
    """
    Cada teste roda dentro de uma transação que é revertida ao final —
    sem SQLite, sem dados residuais entre testes.
    `join_transaction_mode='create_savepoint'` faz com que os commit()
    internos apontem para um SAVEPOINT, não para a transação externa.
    """
    with pg_engine.connect() as connection:
        connection.begin()
        session = Session(connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            connection.rollback()


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
        name="Admin Teste",
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
        name="Usuário Teste",
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
        name="Admin Fake",
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
        name="Usuário Fake",
        hashed_password="hash",
        role="user",
        is_active=True,
    )

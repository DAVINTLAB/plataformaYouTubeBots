from models.user import User
from services.auth import get_password_hash


def test_login_valid_credentials_returns_jwt(client, db):
    """Fake: banco SQLite com usuário pré-criado. Bcrypt real."""
    user = User(
        username="testuser",
        name="Usuário Teste",
        hashed_password=get_password_hash("password123"),
        role="user",
    )
    db.add(user)
    db.commit()

    response = client.post(
        "/auth/login", json={"username": "testuser", "password": "password123"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials_returns_generic_401(client, db, mocker):
    """Stub: verify_password retorna False. Mensagem não revela qual campo falhou."""
    user = User(
        username="testuser",
        name="Usuário Teste",
        hashed_password="some_hash",
        role="user",
    )
    db.add(user)
    db.commit()

    mocker.patch("services.auth.verify_password", return_value=False)

    response = client.post(
        "/auth/login", json={"username": "testuser", "password": "wrong"}
    )

    assert response.status_code == 401
    body = response.text.lower()
    assert "senha" not in body
    assert "usuário" not in body
    assert "usuario" not in body


def test_protected_route_without_token_returns_401(client):
    """Dummy: ausência de header Authorization."""
    response = client.get("/users/")
    assert response.status_code == 401


def test_expired_token_returns_401(client, mocker):
    """Stub: jwt.decode levanta ExpiredSignatureError."""
    import jwt as pyjwt

    mocker.patch("services.auth.jwt.decode", side_effect=pyjwt.ExpiredSignatureError)

    response = client.get("/users/", headers={"Authorization": "Bearer expired_token"})
    assert response.status_code == 401


def test_password_not_stored_in_plain_text(mocker):
    """Mock: pwd_context.hash verificado para garantir que nunca armazena em texto plano."""
    mock_hash = mocker.patch("services.auth.pwd_context.hash", return_value="hashed_pw")

    from services.auth import get_password_hash as hash_fn

    plain = "mysecretpassword"
    result = hash_fn(plain)

    mock_hash.assert_called_once_with(plain)
    assert result != plain


# ---------------------------------------------------------------------------
# Testes de refresh token
# ---------------------------------------------------------------------------


def test_login_retorna_refresh_token(client, db):
    """Login deve retornar access_token e refresh_token."""
    user = User(
        username="refreshuser",
        name="Refresh Teste",
        hashed_password=get_password_hash("password123"),
        role="user",
    )
    db.add(user)
    db.commit()

    response = client.post(
        "/auth/login",
        json={"username": "refreshuser", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_retorna_novos_tokens(client, db):
    """POST /auth/refresh com refresh_token válido retorna novos tokens."""
    user = User(
        username="refreshuser2",
        name="Refresh Teste 2",
        hashed_password=get_password_hash("password123"),
        role="user",
    )
    db.add(user)
    db.commit()

    login_resp = client.post(
        "/auth/login",
        json={"username": "refreshuser2", "password": "password123"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    refresh_resp = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200
    data = refresh_resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_token_invalido_retorna_401(client):
    """POST /auth/refresh com token inválido retorna 401."""
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": "token_invalido"},
    )
    assert response.status_code == 401


def test_refresh_com_access_token_retorna_401(client, db):
    """POST /auth/refresh com access_token (tipo errado) retorna 401."""
    user = User(
        username="refreshuser3",
        name="Refresh Teste 3",
        hashed_password=get_password_hash("password123"),
        role="user",
    )
    db.add(user)
    db.commit()

    login_resp = client.post(
        "/auth/login",
        json={"username": "refreshuser3", "password": "password123"},
    )
    access_token = login_resp.json()["access_token"]

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401

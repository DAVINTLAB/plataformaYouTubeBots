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
    from jose.exceptions import ExpiredSignatureError

    mocker.patch("services.auth.jwt.decode", side_effect=ExpiredSignatureError)

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

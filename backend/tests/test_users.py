import uuid

from main import app
from models.user import User
from services.auth import get_current_user, get_password_hash


def test_user_role_cannot_access_users_list(client, fake_user):
    """Stub: get_current_user retorna User com role='user'."""
    app.dependency_overrides[get_current_user] = lambda: fake_user

    response = client.get("/users/")
    assert response.status_code == 403


def test_admin_can_list_users(client, db, fake_admin, regular_user):
    """Stub: get_current_user retorna admin. Fake: banco com usuário."""
    app.dependency_overrides[get_current_user] = lambda: fake_admin

    response = client.get("/users/")
    assert response.status_code == 200
    data = response.json()
    assert any(u["username"] == regular_user.username for u in data)


def test_admin_can_create_user(client, db, fake_admin):
    """Stub: get_current_user retorna admin. Fake: banco SQLite persiste novo usuário."""
    app.dependency_overrides[get_current_user] = lambda: fake_admin

    response = client.post(
        "/users/",
        json={"username": "newuser", "name": "Novo Usuário", "password": "password123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["name"] == "Novo Usuário"
    assert data["role"] == "user"
    assert "id" in data
    assert "created_at" in data


def test_create_user_duplicate_username_returns_409(client, db, fake_admin):
    """Fake: username duplicado no banco retorna 409."""
    app.dependency_overrides[get_current_user] = lambda: fake_admin

    existing = User(
        username="duplicate",
        name="Usuário Duplicado",
        hashed_password=get_password_hash("pass1234"),
        role="user",
    )
    db.add(existing)
    db.commit()

    response = client.post(
        "/users/",
        json={"username": "duplicate", "name": "Outro Nome", "password": "password123"},
    )
    assert response.status_code == 409


def test_delete_self_returns_403(client, db, admin_user):
    """Admin não pode se auto-deletar."""
    app.dependency_overrides[get_current_user] = lambda: admin_user

    response = client.delete(f"/users/{admin_user.id}")
    assert response.status_code == 403


def test_delete_nonexistent_user_returns_404(client, fake_admin):
    """Usuário não encontrado retorna 404."""
    app.dependency_overrides[get_current_user] = lambda: fake_admin

    response = client.delete(f"/users/{uuid.uuid4()}")
    assert response.status_code == 404


def test_create_user_short_password_returns_422(client, fake_admin):
    """Senha < 8 caracteres retorna 422 (validação Pydantic)."""
    app.dependency_overrides[get_current_user] = lambda: fake_admin

    response = client.post(
        "/users/",
        json={"username": "newuser", "name": "Novo Usuário", "password": "short"},
    )
    assert response.status_code == 422


def test_create_user_invalid_username_returns_422(client, fake_admin):
    """Username com caracteres inválidos (maiúsculas, espaço) retorna 422."""
    app.dependency_overrides[get_current_user] = lambda: fake_admin

    for bad_username in ("NewUser", "new user", "new@user", "NEW"):
        response = client.post(
            "/users/",
            json={"username": bad_username, "name": "Teste", "password": "password123"},
        )
        assert (
            response.status_code == 422
        ), f"esperado 422 para username={bad_username!r}"


def test_create_user_missing_name_returns_422(client, fake_admin):
    """Campo name ausente retorna 422 (validação Pydantic)."""
    app.dependency_overrides[get_current_user] = lambda: fake_admin

    response = client.post(
        "/users/",
        json={"username": "newuser", "password": "password123"},
    )
    assert response.status_code == 422


def test_deactivate_user_sets_is_active_false(client, db, admin_user, regular_user):
    """Fake: desativar usuário ativo persiste is_active=False no banco."""
    app.dependency_overrides[get_current_user] = lambda: admin_user

    response = client.delete(f"/users/{regular_user.id}")
    assert response.status_code == 204

    db.refresh(regular_user)
    assert regular_user.is_active is False


def test_deactivated_user_still_appears_in_list(client, db, admin_user, regular_user):
    """Fake: usuário desativado continua visível na listagem com is_active=False."""
    app.dependency_overrides[get_current_user] = lambda: admin_user

    client.delete(f"/users/{regular_user.id}")

    response = client.get("/users/")
    assert response.status_code == 200
    users = response.json()
    match = next((u for u in users if u["username"] == regular_user.username), None)
    assert match is not None
    assert match["is_active"] is False


def test_reactivate_user_sets_is_active_true(client, db, admin_user, regular_user):
    """Fake: reativar usuário inativo persiste is_active=True no banco."""
    app.dependency_overrides[get_current_user] = lambda: admin_user

    regular_user.is_active = False
    db.commit()

    response = client.post(f"/users/{regular_user.id}/reactivate")
    assert response.status_code == 200
    assert response.json()["is_active"] is True

    db.refresh(regular_user)
    assert regular_user.is_active is True


def test_reactivate_already_active_user_returns_409(
    client, db, admin_user, regular_user
):
    """Fake: reativar usuário já ativo retorna 409."""
    app.dependency_overrides[get_current_user] = lambda: admin_user

    assert regular_user.is_active is True

    response = client.post(f"/users/{regular_user.id}/reactivate")
    assert response.status_code == 409


def test_deactivate_then_reactivate_full_cycle(client, db, admin_user, regular_user):
    """Fake: ciclo completo ativo → inativo → ativo verifica estado a cada transição."""
    app.dependency_overrides[get_current_user] = lambda: admin_user

    # ativo → inativo
    r = client.delete(f"/users/{regular_user.id}")
    assert r.status_code == 204
    db.refresh(regular_user)
    assert regular_user.is_active is False

    # inativo → ativo
    r = client.post(f"/users/{regular_user.id}/reactivate")
    assert r.status_code == 200
    assert r.json()["is_active"] is True
    db.refresh(regular_user)
    assert regular_user.is_active is True


# ---------------------------------------------------------------------------
# Troca e reset de senha
# ---------------------------------------------------------------------------


def test_user_can_change_own_password(client, db, regular_user):
    """Fake: usuário autenticado troca a própria senha com a senha atual correta."""
    app.dependency_overrides[get_current_user] = lambda: regular_user

    response = client.patch(
        "/users/me/password",
        json={"current_password": "userpass1!", "new_password": "newsecure99"},
    )
    assert response.status_code == 204

    db.refresh(regular_user)
    from services.auth import verify_password

    assert verify_password("newsecure99", regular_user.hashed_password)


def test_change_password_wrong_current_returns_400(client, regular_user):
    """Fake: senha atual incorreta retorna 400."""
    app.dependency_overrides[get_current_user] = lambda: regular_user

    response = client.patch(
        "/users/me/password",
        json={"current_password": "errada123", "new_password": "newsecure99"},
    )
    assert response.status_code == 400


def test_change_password_short_new_returns_422(client, regular_user):
    """Fake: nova senha < 8 caracteres retorna 422 (validação Pydantic)."""
    app.dependency_overrides[get_current_user] = lambda: regular_user

    response = client.patch(
        "/users/me/password",
        json={"current_password": "userpass1!", "new_password": "curta"},
    )
    assert response.status_code == 422


def test_admin_can_reset_any_password(client, db, admin_user, regular_user):
    """Fake: admin redefine senha de outro usuário sem precisar da senha atual."""
    app.dependency_overrides[get_current_user] = lambda: admin_user

    response = client.patch(
        f"/users/{regular_user.id}/password",
        json={"new_password": "resetado99"},
    )
    assert response.status_code == 204

    db.refresh(regular_user)
    from services.auth import verify_password

    assert verify_password("resetado99", regular_user.hashed_password)


def test_reset_nonexistent_user_returns_404(client, fake_admin):
    """Fake: reset de usuário inexistente retorna 404."""
    app.dependency_overrides[get_current_user] = lambda: fake_admin

    response = client.patch(
        f"/users/{uuid.uuid4()}/password",
        json={"new_password": "qualquer99"},
    )
    assert response.status_code == 404

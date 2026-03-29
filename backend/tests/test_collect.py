import logging
import uuid
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from models.collection import Collection, Comment

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_item(i: int) -> dict:
    return {
        "snippet": {
            "topLevelComment": {
                "id": f"comment_{i}",
                "snippet": {
                    "textOriginal": f"comentário {i}",
                    "authorDisplayName": f"user{i}",
                    "authorChannelId": {"value": f"UC{i}"},
                    "likeCount": 0,
                    "publishedAt": "2024-01-01T00:00:00Z",
                    "updatedAt": "2024-01-01T00:00:00Z",
                },
            },
            "totalReplyCount": 0,
        }
    }


def _page(items: list[dict], next_token: str | None = None) -> dict:
    return {"items": items, "nextPageToken": next_token}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def dummy_user_id():
    """Dummy: user_id irrelevante para testes que focam na lógica de coleta."""
    return uuid.uuid4()


@pytest.fixture(autouse=True)
def stub_youtube_utils(mocker):
    """
    Autouse: impede chamadas reais à YouTube API em todos os testes.
    - fetch_video_info → None (Collection sem metadados de vídeo)
    - fetch_channels_info → {} (sem datas de criação de canal)
    - fetch_replies_page → sem replies extras
    """
    mocker.patch(
        "services.collect.fetch_video_info",
        new=AsyncMock(return_value=None),
    )
    mocker.patch(
        "services.collect.fetch_channels_info",
        new=AsyncMock(return_value={}),
    )
    mocker.patch(
        "services.collect.fetch_replies_page",
        new=AsyncMock(return_value={"items": [], "nextPageToken": None}),
    )


@pytest.fixture
def stub_youtube_3_comments(mocker):
    """Stub: fetch_comments_page retorna 3 comentários, sem próxima página."""
    mocker.patch(
        "services.collect.fetch_comments_page",
        new=AsyncMock(return_value=_page([_make_item(i) for i in range(3)])),
    )


@pytest.fixture
def stub_youtube_403(mocker):
    """Stub: fetch_comments_page levanta HTTPStatusError 403."""
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.json.return_value = {"error": {"errors": [{"reason": "forbidden"}]}}
    exc = httpx.HTTPStatusError("403", request=MagicMock(), response=mock_response)
    mocker.patch(
        "services.collect.fetch_comments_page",
        new=AsyncMock(side_effect=exc),
    )


@pytest.fixture
def stub_youtube_network_error(mocker):
    """Stub: fetch_comments_page levanta Exception genérica."""
    mocker.patch(
        "services.collect.fetch_comments_page",
        new=AsyncMock(side_effect=Exception("network error")),
    )


# ---------------------------------------------------------------------------
# Testes de coleta bem-sucedida
# ---------------------------------------------------------------------------


def test_coleta_bem_sucedida_persiste_comentarios(
    client, db, auth_as_user, stub_youtube_3_comments
):
    """Stub: fetch retorna 3 comentários. Fake: SQLite. Afirma count == 3."""
    response = client.post(
        "/collect",
        json={"video_id": "dQw4w9WgXcQ", "api_key": "AIzaFAKEKEY"},
    )

    assert response.status_code == 202
    assert db.query(Comment).count() == 3
    assert db.query(Collection).count() == 1

    collection = db.query(Collection).first()
    assert collection.status == "completed"
    assert collection.total_comments == 3


def test_coleta_retorna_collection_id_e_video_id(
    client, db, auth_as_user, stub_youtube_3_comments
):
    """Afirma que response contém collection_id e video_id corretos."""
    response = client.post(
        "/collect",
        json={"video_id": "dQw4w9WgXcQ", "api_key": "AIzaFAKEKEY"},
    )

    assert response.status_code == 202
    data = response.json()
    assert "collection_id" in data
    assert data["video_id"] == "dQw4w9WgXcQ"
    assert data["status"] == "completed"


def test_coleta_sem_token_retorna_401(client):
    """Dummy: ausência de header Authorization."""
    response = client.post(
        "/collect",
        json={"video_id": "dQw4w9WgXcQ", "api_key": "AIzaFAKEKEY"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Teste de idempotência dentro da mesma coleta
# ---------------------------------------------------------------------------


def test_recoleta_next_page_com_mesmos_comentarios_nao_duplica(
    client, db, auth_as_user, mocker
):
    """Stub: primeira página retorna 3 comentários com next_page_token.
    Stub: segunda chamada (next-page) retorna os mesmos 3 comment_ids.
    Afirma que COUNT permanece 3 — idempotência por (collection_id, comment_id).
    """
    items = [_make_item(i) for i in range(3)]

    # Primeira chamada: retorna next_page_token para manter a coleta "running"
    # Segunda chamada (next-page): retorna os mesmos comment_ids, sem mais páginas
    mocker.patch(
        "services.collect.fetch_comments_page",
        new=AsyncMock(
            side_effect=[
                _page(items, next_token="TOKEN1"),
                _page(items, next_token=None),  # mesmos comment_ids
            ]
        ),
    )

    # Inicia coleta — cria 3 comentários, fica running
    resp1 = client.post(
        "/collect",
        json={"video_id": "dQw4w9WgXcQ", "api_key": "AIzaFAKE1"},
    )
    assert resp1.status_code == 202
    data1 = resp1.json()
    assert data1["next_page_token"] == "TOKEN1"
    assert db.query(Comment).count() == 3

    # Continua coleta — tenta inserir os mesmos 3 comment_ids (mesmo collection_id)
    resp2 = client.post(
        "/collect/next-page",
        json={
            "collection_id": data1["collection_id"],
            "api_key": "AIzaFAKE1",
        },
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "completed"

    # Unicidade (collection_id, comment_id) impede duplicação
    assert db.query(Comment).count() == 3


# ---------------------------------------------------------------------------
# Testes de erro da YouTube API
# ---------------------------------------------------------------------------


def test_youtube_403_retorna_erro_com_mensagem_amigavel(
    client, auth_as_user, stub_youtube_403
):
    """Stub: HTTPStatusError 403 forbidden. Afirma mensagem amigável."""
    response = client.post(
        "/collect",
        json={"video_id": "dQw4w9WgXcQ", "api_key": "AIzaFAKEKEY"},
    )
    assert response.status_code == 403
    body = response.json()
    assert "detail" in body
    assert "api" in body["detail"].lower() or "acesso" in body["detail"].lower()


def test_youtube_403_quota_retorna_429(client, auth_as_user, mocker):
    """Stub: 403 com reason quotaExceeded retorna 429."""
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.json.return_value = {
        "error": {"errors": [{"reason": "quotaExceeded"}]}
    }
    exc = httpx.HTTPStatusError("403", request=MagicMock(), response=mock_response)
    mocker.patch(
        "services.collect.fetch_comments_page",
        new=AsyncMock(side_effect=exc),
    )

    response = client.post(
        "/collect",
        json={"video_id": "dQw4w9WgXcQ", "api_key": "AIzaFAKEKEY"},
    )
    assert response.status_code == 429
    assert "esgotada" in response.json()["detail"].lower()


def test_youtube_400_key_invalid_retorna_400_com_mensagem_amigavel(
    client, auth_as_user, mocker
):
    """Stub: 400 com reason keyInvalid retorna 400 com mensagem de API key."""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {"error": {"errors": [{"reason": "keyInvalid"}]}}
    exc = httpx.HTTPStatusError("400", request=MagicMock(), response=mock_response)
    mocker.patch(
        "services.collect.fetch_comments_page",
        new=AsyncMock(side_effect=exc),
    )

    response = client.post(
        "/collect",
        json={"video_id": "dQw4w9WgXcQ", "api_key": "AIzaINVALID"},
    )
    assert response.status_code == 400
    assert "api key" in response.json()["detail"].lower()


def test_youtube_403_comments_disabled_retorna_400(client, auth_as_user, mocker):
    """Stub: 403 com reason commentsDisabled retorna 400 com mensagem específica."""
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.json.return_value = {
        "error": {"errors": [{"reason": "commentsDisabled"}]}
    }
    exc = httpx.HTTPStatusError("403", request=MagicMock(), response=mock_response)
    mocker.patch(
        "services.collect.fetch_comments_page",
        new=AsyncMock(side_effect=exc),
    )

    response = client.post(
        "/collect",
        json={"video_id": "dQw4w9WgXcQ", "api_key": "AIzaFAKEKEY"},
    )
    assert response.status_code == 400
    assert "comentários" in response.json()["detail"].lower()


def test_coleta_com_erro_marca_collection_como_failed(
    client, db, auth_as_user, stub_youtube_403
):
    """Afirma que Collection.status == 'failed' após erro da YouTube API."""
    client.post(
        "/collect",
        json={"video_id": "dQw4w9WgXcQ", "api_key": "AIzaFAKEKEY"},
    )
    collection = db.query(Collection).first()
    assert collection is not None
    assert collection.status == "failed"


# ---------------------------------------------------------------------------
# Testes de segurança: API key nunca aparece em logs ou respostas
# ---------------------------------------------------------------------------


def test_api_key_nao_aparece_na_resposta_de_sucesso(
    client, auth_as_user, stub_youtube_3_comments
):
    """Mock: verifica que o body da response não contém o valor da API key."""
    api_key_value = "AIzaSECRET_KEY_TEST_12345"
    response = client.post(
        "/collect",
        json={"video_id": "dQw4w9WgXcQ", "api_key": api_key_value},
    )
    assert response.status_code == 202
    assert api_key_value not in response.text


def test_api_key_nao_aparece_nos_logs_em_caso_de_sucesso(
    client, auth_as_user, stub_youtube_3_comments, mocker
):
    """Spy: logger não recebe a API key como argumento em nenhum nível."""
    api_key_value = "AIzaSECRET_KEY_SPY_67890"

    spy_info = mocker.spy(logging.getLogger("services.collect"), "info")
    spy_error = mocker.spy(logging.getLogger("services.collect"), "error")
    spy_debug = mocker.spy(logging.getLogger("services.collect"), "debug")

    client.post(
        "/collect",
        json={"video_id": "dQw4w9WgXcQ", "api_key": api_key_value},
    )

    all_calls = (
        str(spy_info.call_args_list)
        + str(spy_error.call_args_list)
        + str(spy_debug.call_args_list)
    )
    assert api_key_value not in all_calls


def test_api_key_nao_aparece_no_error_message_de_falha(
    client, db, auth_as_user, stub_youtube_network_error
):
    """Stub: Exception genérica. Afirma error_message não contém a API key."""
    api_key_value = "AIzaSECRET_ERROR_KEY_99999"
    client.post(
        "/collect",
        json={"video_id": "dQw4w9WgXcQ", "api_key": api_key_value},
    )

    collection = db.query(Collection).first()
    assert collection is not None
    assert collection.status == "failed"
    assert collection.error_message is not None
    assert api_key_value not in (collection.error_message or "")


def test_api_key_nao_aparece_na_resposta_de_erro(
    client, auth_as_user, stub_youtube_403
):
    """Mock: verifica que o body de erro não contém o valor da API key."""
    api_key_value = "AIzaSECRET_KEY_ERR_00000"
    response = client.post(
        "/collect",
        json={"video_id": "dQw4w9WgXcQ", "api_key": api_key_value},
    )
    assert api_key_value not in response.text


# ---------------------------------------------------------------------------
# Testes de status e listagem
# ---------------------------------------------------------------------------


def test_get_status_retorna_coleta_do_usuario(
    client, db, auth_as_user, stub_youtube_3_comments
):
    """Afirma que GET /collect/status retorna a coleta correta."""
    resp = client.post(
        "/collect",
        json={"video_id": "dQw4w9WgXcQ", "api_key": "AIzaFAKEKEY"},
    )
    collection_id = resp.json()["collection_id"]

    status_resp = client.get(f"/collect/status?collection_id={collection_id}")
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["collection_id"] == collection_id
    assert data["status"] == "completed"
    assert data["collected_by"] == auth_as_user.username


def test_get_status_sem_token_retorna_401(client):
    """Dummy: ausência de token."""
    response = client.get(f"/collect/status?collection_id={uuid.uuid4()}")
    assert response.status_code == 401


def test_get_status_coleta_inexistente_retorna_404(client, auth_as_user):
    """Afirma 404 para collection_id desconhecido."""
    response = client.get(f"/collect/status?collection_id={uuid.uuid4()}")
    assert response.status_code == 404


def test_list_collections_retorna_apenas_as_do_usuario(
    client, db, auth_as_user, stub_youtube_3_comments
):
    """Afirma que GET /collect retorna lista com as coletas do usuário autenticado."""
    client.post("/collect", json={"video_id": "abc123", "api_key": "AIzaFAKE"})
    client.post("/collect", json={"video_id": "xyz789", "api_key": "AIzaFAKE"})

    response = client.get("/collect")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    video_ids = {item["video_id"] for item in data}
    assert video_ids == {"abc123", "xyz789"}


def test_list_collections_sem_token_retorna_401(client):
    """Dummy: ausência de token."""
    response = client.get("/collect")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Teste de extração de video_id a partir de URL
# ---------------------------------------------------------------------------


def test_extrai_video_id_de_url_completa(client, auth_as_user, stub_youtube_3_comments):
    """Afirma que URL do YouTube é normalizada para o video_id puro."""
    response = client.post(
        "/collect",
        json={
            "video_id": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "api_key": "AIzaFAKEKEY",
        },
    )
    assert response.status_code == 202
    assert response.json()["video_id"] == "dQw4w9WgXcQ"


def test_extrai_video_id_de_url_curta(client, auth_as_user, stub_youtube_3_comments):
    """Afirma que URL youtu.be é normalizada para o video_id puro."""
    response = client.post(
        "/collect",
        json={
            "video_id": "https://youtu.be/dQw4w9WgXcQ",
            "api_key": "AIzaFAKEKEY",
        },
    )
    assert response.status_code == 202
    assert response.json()["video_id"] == "dQw4w9WgXcQ"


def test_payload_invalido_retorna_422(client, auth_as_user):
    """Afirma 422 para payload sem campo obrigatório api_key."""
    response = client.post("/collect", json={"video_id": "dQw4w9WgXcQ"})
    assert response.status_code == 422

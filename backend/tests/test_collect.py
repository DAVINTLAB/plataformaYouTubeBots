import asyncio
import logging
import uuid
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import HTTPException

from models.collection import Collection, Comment


def _run(coro):
    """Executa coroutine reutilizando o loop se possível."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


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


# ---------------------------------------------------------------------------
# Testes de utilitários
# ---------------------------------------------------------------------------


def test_safe_int_converte_string_numerica():
    from services.collect import _safe_int

    assert _safe_int("42") == 42
    assert _safe_int("0") == 0
    assert _safe_int(None) is None
    assert _safe_int("abc") is None
    assert _safe_int("") is None


# ===================================================================
# Novos testes — cobertura 100% services/collect.py, routers/collect.py,
# services/youtube.py
# ===================================================================


# ---------------------------------------------------------------------------
# Helpers extras
# ---------------------------------------------------------------------------


def _make_collection(db, user_id, **overrides):
    """Cria uma Collection no banco com valores padrão sensíveis."""
    from models.collection import Collection

    defaults = {
        "video_id": "dQw4w9WgXcQ",
        "status": "completed",
        "collected_by": user_id,
        "total_comments": 0,
    }
    defaults.update(overrides)
    c = Collection(**defaults)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _make_comment(db, collection_id, idx, **overrides):
    """Cria um Comment no banco com valores padrão."""
    from datetime import UTC, datetime

    from models.collection import Comment

    defaults = {
        "collection_id": collection_id,
        "comment_id": f"cmt_{idx}",
        "author_display_name": f"user{idx}",
        "author_channel_id": f"UC{idx}",
        "text_original": f"text {idx}",
        "like_count": 0,
        "reply_count": 0,
        "published_at": datetime(2024, 1, 1, tzinfo=UTC),
        "updated_at": datetime(2024, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    cmt = Comment(**defaults)
    db.add(cmt)
    db.commit()
    db.refresh(cmt)
    return cmt


def _make_item_with_replies(idx: int, reply_count: int = 2) -> dict:
    """Cria um item de commentThread COM replies inline."""
    item = _make_item(idx)
    item["snippet"]["totalReplyCount"] = reply_count
    replies = []
    for r in range(reply_count):
        replies.append(
            {
                "id": f"reply_{idx}_{r}",
                "snippet": {
                    "textOriginal": f"reply {idx}_{r}",
                    "textDisplay": f"reply {idx}_{r}",
                    "authorDisplayName": f"replier{r}",
                    "authorChannelId": {"value": f"UCR{r}"},
                    "likeCount": 0,
                    "publishedAt": "2024-01-02T00:00:00Z",
                    "updatedAt": "2024-01-02T00:00:00Z",
                },
            }
        )
    item["replies"] = {"comments": replies}
    return item


def _yt_error_exc(
    status_code: int,
    reason: str = "",
    message: str = "",
    *,
    json_raises: bool = False,
):
    """Constrói httpx.HTTPStatusError com resposta mockada."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    if json_raises:
        mock_response.json.side_effect = ValueError("no json")
    else:
        errors = [{"reason": reason, "message": message}] if reason else []
        mock_response.json.return_value = {"error": {"errors": errors}}
    return httpx.HTTPStatusError(
        str(status_code),
        request=MagicMock(),
        response=mock_response,
    )


def _import_payload(
    video_id="vid123",
    n_comments=2,
    done=True,
):
    """Constrói payload JSON para POST /collect/import."""
    comments = []
    for i in range(n_comments):
        comments.append(
            {
                "comment_id": f"imp_{i}",
                "text_original": f"imported text {i}",
                "published_at": "2024-06-01T00:00:00Z",
                "updated_at": "2024-06-01T00:00:00Z",
            }
        )
    return {
        "video": {"id": video_id, "title": "Test Video"},
        "comments": comments,
        "done": done,
    }


# ---------------------------------------------------------------------------
# _parse_youtube_error — branches não cobertas
# ---------------------------------------------------------------------------


class TestParseYoutubeError:
    """Testes unitários de _parse_youtube_error."""

    def test_json_decode_error_fallback(self):
        """Cobre linhas 42-44: response.json() levanta exceção."""
        from services.collect import _parse_youtube_error

        exc = _yt_error_exc(500, json_raises=True)
        result = _parse_youtube_error(exc)
        assert result.status_code == 502
        assert "HTTP 500" in result.detail

    def test_400_without_key_reason(self):
        """Cobre linha 58: 400 sem keyInvalid/keyExpired."""
        from services.collect import _parse_youtube_error

        exc = _yt_error_exc(400, reason="badRequest")
        result = _parse_youtube_error(exc)
        assert result.status_code == 400
        assert "requisição inválida" in result.detail.lower()

    def test_403_video_not_found(self):
        """Cobre linha 74: 403 com reason=videoNotFound."""
        from services.collect import _parse_youtube_error

        exc = _yt_error_exc(403, reason="videoNotFound")
        result = _parse_youtube_error(exc)
        assert result.status_code == 400
        assert "privado" in result.detail.lower()

    def test_403_unknown_reason_fallback(self):
        """Cobre linhas 87-94: 403 com reason desconhecida."""
        from services.collect import _parse_youtube_error

        exc = _yt_error_exc(403, reason="somethingNew")
        result = _parse_youtube_error(exc)
        assert result.status_code == 403
        assert "somethingNew" in result.detail

    def test_404_returns_video_not_found(self):
        """Cobre linhas 92-93: status 404."""
        from services.collect import _parse_youtube_error

        exc = _yt_error_exc(404)
        result = _parse_youtube_error(exc)
        assert result.status_code == 404
        assert "não encontrado" in result.detail.lower()

    @pytest.mark.parametrize(
        "status_code",
        [500, 502, 503],
        ids=["500", "502", "503"],
    )
    def test_other_status_returns_502(self, status_code):
        """Cobre linha 94: fallback para códigos não mapeados."""
        from services.collect import _parse_youtube_error

        exc = _yt_error_exc(status_code)
        result = _parse_youtube_error(exc)
        assert result.status_code == 502

    def test_400_empty_errors_list(self):
        """Cobre quando errors list está vazia (reason='')."""
        from services.collect import _parse_youtube_error

        exc = _yt_error_exc(400, reason="")
        result = _parse_youtube_error(exc)
        assert result.status_code == 400
        assert "requisição inválida" in result.detail.lower()


# ---------------------------------------------------------------------------
# _bulk_insert — empty rows
# ---------------------------------------------------------------------------


def test_bulk_insert_empty_rows_returns_zero(db):
    """Cobre linha 137: _bulk_insert com lista vazia retorna 0."""
    from services.collect import _bulk_insert

    assert _bulk_insert(db, []) == 0


# ---------------------------------------------------------------------------
# _insert_comments — comment with replies
# ---------------------------------------------------------------------------


def test_insert_comments_with_inline_replies(db, regular_user):
    """Cobre linha 162: comentário com replies inline."""
    from services.collect import _insert_comments

    col = _make_collection(db, regular_user.id, status="running")
    items = [_make_item_with_replies(0, reply_count=3)]
    inserted = _insert_comments(db, col.id, items)
    # 1 top-level + 3 replies = 4
    assert inserted == 4
    total = db.query(Comment).filter(Comment.collection_id == col.id).count()
    assert total == 4
    # Confirmar que replies têm parent_id
    replies = (
        db.query(Comment)
        .filter(
            Comment.collection_id == col.id,
            Comment.parent_id.isnot(None),
        )
        .all()
    )
    assert len(replies) == 3


# ---------------------------------------------------------------------------
# _populate_video_metadata
# ---------------------------------------------------------------------------


def test_populate_video_metadata(db, regular_user):
    """Cobre linhas 175-187: preenchendo campos de metadados."""
    from services.collect import _populate_video_metadata

    col = _make_collection(db, regular_user.id)
    video_info = {
        "snippet": {
            "title": "Test Video Title",
            "description": "A description",
            "channelId": "UCxyz",
            "channelTitle": "Test Channel",
            "publishedAt": "2023-06-15T10:30:00Z",
        },
        "statistics": {
            "viewCount": "1000",
            "likeCount": "50",
            "commentCount": "10",
        },
    }
    _populate_video_metadata(col, video_info)
    assert col.video_title == "Test Video Title"
    assert col.video_description == "A description"
    assert col.video_channel_id == "UCxyz"
    assert col.video_channel_title == "Test Channel"
    assert col.video_published_at is not None
    assert col.video_view_count == 1000
    assert col.video_like_count == 50
    assert col.video_comment_count == 10


def test_populate_video_metadata_no_published_at(db, regular_user):
    """Cobre branch: publishedAt ausente → None."""
    from services.collect import _populate_video_metadata

    col = _make_collection(db, regular_user.id)
    video_info = {"snippet": {}, "statistics": {}}
    _populate_video_metadata(col, video_info)
    assert col.video_published_at is None
    assert col.video_view_count is None


# ---------------------------------------------------------------------------
# collect_next_page — branches
# ---------------------------------------------------------------------------


def test_collect_next_page_not_found(db, regular_user):
    """Cobre linha 271: collection não encontrada → 404."""
    from services.collect import collect_next_page

    payload = MagicMock()
    payload.collection_id = uuid.uuid4()
    payload.api_key = MagicMock()
    payload.api_key.get_secret_value.return_value = "KEY"
    with pytest.raises(HTTPException) as exc_info:
        _run(collect_next_page(db, payload, regular_user.id))
    assert exc_info.value.status_code == 404


def test_collect_next_page_already_completed(db, regular_user):
    """Cobre linha 273: collection já completed → retorna (col, None)."""
    from services.collect import collect_next_page

    col = _make_collection(db, regular_user.id, status="completed")
    payload = MagicMock()
    payload.collection_id = col.id
    payload.api_key = MagicMock()
    payload.api_key.get_secret_value.return_value = "KEY"
    result_col, token = _run(collect_next_page(db, payload, regular_user.id))
    assert result_col.status == "completed"
    assert token is None


def test_collect_next_page_failed_raises_400(db, regular_user):
    """Cobre linha 275: collection falhou → 400."""
    from services.collect import collect_next_page

    col = _make_collection(db, regular_user.id, status="failed")
    payload = MagicMock()
    payload.collection_id = col.id
    payload.api_key = MagicMock()
    payload.api_key.get_secret_value.return_value = "KEY"
    with pytest.raises(HTTPException) as exc_info:
        _run(collect_next_page(db, payload, regular_user.id))
    assert exc_info.value.status_code == 400
    assert "falhou" in exc_info.value.detail.lower()


def test_collect_next_page_no_token_marks_complete(db, regular_user):
    """Cobre linhas 280-285: sem next_page_token → marca completed."""
    from services.collect import collect_next_page

    col = _make_collection(
        db,
        regular_user.id,
        status="running",
        next_page_token=None,
    )
    payload = MagicMock()
    payload.collection_id = col.id
    payload.api_key = MagicMock()
    payload.api_key.get_secret_value.return_value = "KEY"
    result_col, token = _run(collect_next_page(db, payload, regular_user.id))
    assert result_col.status == "completed"
    assert result_col.enrich_status == "pending"
    assert token is None


def test_collect_next_page_updates_token(db, regular_user, mocker):
    """Cobre linha 310: atualiza next_page_token para próxima página."""
    from services.collect import collect_next_page

    col = _make_collection(
        db,
        regular_user.id,
        status="running",
        next_page_token="TOKEN_A",
    )
    mocker.patch(
        "services.collect.fetch_comments_page",
        new=AsyncMock(return_value=_page([_make_item(10)], next_token="TOKEN_B")),
    )
    payload = MagicMock()
    payload.collection_id = col.id
    payload.api_key = MagicMock()
    payload.api_key.get_secret_value.return_value = "KEY"
    result_col, token = _run(collect_next_page(db, payload, regular_user.id))
    assert token == "TOKEN_B"
    assert result_col.next_page_token == "TOKEN_B"
    assert result_col.status == "running"


def test_collect_next_page_completes_when_no_more(db, regular_user, mocker):
    """Cobre linhas 304-308: próxima página sem nextPageToken."""
    from services.collect import collect_next_page

    col = _make_collection(
        db,
        regular_user.id,
        status="running",
        next_page_token="TOKEN_A",
    )
    mocker.patch(
        "services.collect.fetch_comments_page",
        new=AsyncMock(return_value=_page([_make_item(20)])),
    )
    payload = MagicMock()
    payload.collection_id = col.id
    payload.api_key = MagicMock()
    payload.api_key.get_secret_value.return_value = "KEY"
    result_col, token = _run(collect_next_page(db, payload, regular_user.id))
    assert result_col.status == "completed"
    assert result_col.enrich_status == "pending"
    assert token is None


def test_collect_next_page_http_error(db, regular_user, mocker):
    """Cobre linhas 315-324: HTTPStatusError no next_page."""
    from services.collect import collect_next_page

    col = _make_collection(
        db,
        regular_user.id,
        status="running",
        next_page_token="TOKEN_A",
    )
    exc = _yt_error_exc(403, reason="quotaExceeded")
    mocker.patch(
        "services.collect.fetch_comments_page",
        new=AsyncMock(side_effect=exc),
    )
    payload = MagicMock()
    payload.collection_id = col.id
    payload.api_key = MagicMock()
    payload.api_key.get_secret_value.return_value = "KEY"
    with pytest.raises(HTTPException) as exc_info:
        _run(collect_next_page(db, payload, regular_user.id))
    assert exc_info.value.status_code == 429
    db.refresh(col)
    assert col.status == "failed"


def test_collect_next_page_generic_exception(db, regular_user, mocker):
    """Cobre linhas 325-333: Exception genérica no next_page."""
    from services.collect import collect_next_page

    col = _make_collection(
        db,
        regular_user.id,
        status="running",
        next_page_token="TOKEN_A",
    )
    mocker.patch(
        "services.collect.fetch_comments_page",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    )
    payload = MagicMock()
    payload.collection_id = col.id
    payload.api_key = MagicMock()
    payload.api_key.get_secret_value.return_value = "KEY"
    with pytest.raises(HTTPException) as exc_info:
        _run(collect_next_page(db, payload, regular_user.id))
    assert exc_info.value.status_code == 500
    db.refresh(col)
    assert col.status == "failed"


# ---------------------------------------------------------------------------
# _threads_needing_replies & _channels_needing_dates
# ---------------------------------------------------------------------------


def test_threads_needing_replies(db, regular_user):
    """Cobre linhas 352-380: SQL query para threads com replies faltando."""
    from services.collect import _threads_needing_replies

    col = _make_collection(db, regular_user.id)
    # Top-level com reply_count=3, mas sem replies no banco
    _make_comment(
        db,
        col.id,
        "thr1",
        comment_id="thread_1",
        reply_count=3,
        parent_id=None,
    )
    # Top-level com reply_count=0 — não deve aparecer
    _make_comment(
        db,
        col.id,
        "thr2",
        comment_id="thread_2",
        reply_count=0,
        parent_id=None,
    )
    result = _threads_needing_replies(db, col.id)
    assert len(result) == 1
    assert result[0] == ("thread_1", 3)


def test_threads_needing_replies_already_fetched(db, regular_user):
    """Thread com todas as replies já inseridas não aparece."""
    from services.collect import _threads_needing_replies

    col = _make_collection(db, regular_user.id)
    _make_comment(
        db,
        col.id,
        "thr3",
        comment_id="thread_3",
        reply_count=1,
        parent_id=None,
    )
    # 1 reply já existe
    _make_comment(
        db,
        col.id,
        "rep3",
        comment_id="reply_3_0",
        parent_id="thread_3",
        reply_count=0,
    )
    result = _threads_needing_replies(db, col.id)
    assert len(result) == 0


def test_channels_needing_dates(db, regular_user):
    """Cobre linhas 389-400: canais sem published_at."""
    from services.collect import _channels_needing_dates

    col = _make_collection(db, regular_user.id)
    _make_comment(
        db,
        col.id,
        "ch1",
        author_channel_id="UCAAA",
        author_channel_published_at=None,
    )
    _make_comment(
        db,
        col.id,
        "ch2",
        author_channel_id="UCBBB",
        author_channel_published_at=None,
    )
    result = _channels_needing_dates(db, col.id)
    assert set(result) == {"UCAAA", "UCBBB"}


def test_channels_needing_dates_excludes_populated(db, regular_user):
    """Canais com published_at preenchido não aparecem."""
    from datetime import UTC, datetime

    from services.collect import _channels_needing_dates

    col = _make_collection(db, regular_user.id)
    _make_comment(
        db,
        col.id,
        "chp",
        author_channel_id="UCPOP",
        author_channel_published_at=datetime(2020, 1, 1, tzinfo=UTC),
    )
    result = _channels_needing_dates(db, col.id)
    assert result == []


# ---------------------------------------------------------------------------
# enrich_collection — all 3 phases + error handling
# ---------------------------------------------------------------------------


def test_enrich_collection_not_found(db):
    """Cobre linha 414-415: coleta não encontrada."""
    from services.collect import enrich_collection

    with pytest.raises(HTTPException) as exc_info:
        _run(enrich_collection(db, uuid.uuid4(), "KEY"))
    assert exc_info.value.status_code == 404


def test_enrich_collection_not_completed(db, regular_user):
    """Cobre linhas 416-420: coleta não completed → 400."""
    from services.collect import enrich_collection

    col = _make_collection(db, regular_user.id, status="running")
    with pytest.raises(HTTPException) as exc_info:
        _run(enrich_collection(db, col.id, "KEY"))
    assert exc_info.value.status_code == 400


def test_enrich_collection_already_done(db, regular_user):
    """Cobre linhas 421-427: enrich_status=done retorna imediatamente."""
    from services.collect import enrich_collection

    col = _make_collection(
        db,
        regular_user.id,
        status="completed",
        enrich_status="done",
    )
    result = _run(enrich_collection(db, col.id, "KEY"))
    assert result["done"] is True
    assert result["phase"] == "channels"


def test_enrich_phase_video(db, regular_user, mocker):
    """Cobre fase 0 do enrich: video metadata."""
    from services.collect import enrich_collection

    col = _make_collection(
        db,
        regular_user.id,
        status="completed",
        enrich_status="pending",
        video_title=None,
    )
    mocker.patch(
        "services.collect.fetch_video_info",
        new=AsyncMock(
            return_value={
                "snippet": {
                    "title": "Test",
                    "channelId": "UCx",
                    "channelTitle": "Ch",
                    "publishedAt": "2024-01-01T00:00:00Z",
                },
                "statistics": {"viewCount": "100"},
            }
        ),
    )
    result = _run(enrich_collection(db, col.id, "KEY"))
    assert result["phase"] == "video"
    assert result["processed"] == 1
    assert result["done"] is False
    db.refresh(col)
    assert col.video_title == "Test"
    assert col.enrich_status == "enriching"


def test_enrich_phase_video_no_info(db, regular_user, mocker):
    """Fase 0: fetch_video_info returns None → processed=0."""
    from services.collect import enrich_collection

    col = _make_collection(
        db,
        regular_user.id,
        status="completed",
        enrich_status="pending",
        video_title=None,
    )
    mocker.patch(
        "services.collect.fetch_video_info",
        new=AsyncMock(return_value=None),
    )
    result = _run(enrich_collection(db, col.id, "KEY"))
    assert result["phase"] == "video"
    assert result["processed"] == 0


def test_enrich_phase_replies(db, regular_user, mocker):
    """Cobre fase 1: busca replies extras."""
    from services.collect import enrich_collection

    col = _make_collection(
        db,
        regular_user.id,
        status="completed",
        enrich_status="enriching",
        video_title="Already Set",
    )
    # Top-level com 2 replies mas nenhuma no banco
    _make_comment(
        db,
        col.id,
        "thr_e",
        comment_id="thread_enrich",
        reply_count=2,
        parent_id=None,
    )
    col.total_comments = 1
    db.commit()

    mocker.patch(
        "services.collect.fetch_replies_page",
        new=AsyncMock(
            return_value={
                "items": [
                    {
                        "id": "reply_e_0",
                        "snippet": {
                            "textOriginal": "r0",
                            "textDisplay": "r0",
                            "authorDisplayName": "u0",
                            "authorChannelId": {"value": "UC0"},
                            "likeCount": 0,
                            "publishedAt": "2024-01-02T00:00:00Z",
                            "updatedAt": "2024-01-02T00:00:00Z",
                        },
                    },
                    {
                        "id": "reply_e_1",
                        "snippet": {
                            "textOriginal": "r1",
                            "textDisplay": "r1",
                            "authorDisplayName": "u1",
                            "authorChannelId": {"value": "UC1"},
                            "likeCount": 0,
                            "publishedAt": "2024-01-02T00:00:00Z",
                            "updatedAt": "2024-01-02T00:00:00Z",
                        },
                    },
                ],
                "nextPageToken": None,
            }
        ),
    )
    result = _run(enrich_collection(db, col.id, "KEY"))
    assert result["phase"] == "replies"
    assert result["processed"] == 1
    assert result["done"] is False


def test_enrich_phase_channels(db, regular_user, mocker):
    """Cobre fase 2: busca datas de canal."""
    from datetime import UTC, datetime

    from services.collect import enrich_collection

    col = _make_collection(
        db,
        regular_user.id,
        status="completed",
        enrich_status="enriching",
        video_title="Set",
    )
    _make_comment(
        db,
        col.id,
        "ch_e",
        author_channel_id="UCENRICH",
        author_channel_published_at=None,
    )

    mocker.patch(
        "services.collect.fetch_channels_info",
        new=AsyncMock(return_value={"UCENRICH": datetime(2020, 5, 1, tzinfo=UTC)}),
    )
    result = _run(enrich_collection(db, col.id, "KEY"))
    assert result["phase"] == "channels"
    assert result["processed"] == 1
    assert result["done"] is False


def test_enrich_completes_all_phases(db, regular_user, mocker):
    """Cobre linhas 493-506: tudo concluído → done=True."""
    from services.collect import enrich_collection

    col = _make_collection(
        db,
        regular_user.id,
        status="completed",
        enrich_status="enriching",
        video_title="Set",
    )
    # Nenhum thread pendente, nenhum canal pendente
    result = _run(enrich_collection(db, col.id, "KEY"))
    assert result["done"] is True
    assert result["phase"] == "channels"
    db.refresh(col)
    assert col.enrich_status == "done"
    assert col.channel_dates_failed is False


def test_enrich_http_error_raises(db, regular_user, mocker):
    """Cobre linhas 508-514: HTTPStatusError no enrich."""
    from services.collect import enrich_collection

    col = _make_collection(
        db,
        regular_user.id,
        status="completed",
        enrich_status="pending",
        video_title=None,
    )
    exc = _yt_error_exc(403, reason="quotaExceeded")
    mocker.patch(
        "services.collect.fetch_video_info",
        new=AsyncMock(side_effect=exc),
    )
    with pytest.raises(HTTPException) as exc_info:
        _run(enrich_collection(db, col.id, "KEY"))
    assert exc_info.value.status_code == 429


def test_enrich_generic_exception(db, regular_user, mocker):
    """Cobre linhas 515-525: Exception genérica no enrich."""
    from services.collect import enrich_collection

    col = _make_collection(
        db,
        regular_user.id,
        status="completed",
        enrich_status="pending",
        video_title=None,
    )
    mocker.patch(
        "services.collect.fetch_video_info",
        new=AsyncMock(side_effect=RuntimeError("fail")),
    )
    with pytest.raises(HTTPException) as exc_info:
        _run(enrich_collection(db, col.id, "KEY"))
    assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# _fetch_thread_replies — paginated
# ---------------------------------------------------------------------------


def test_fetch_thread_replies_paginated(db, regular_user, mocker):
    """Cobre linhas 535-552: paginação de replies."""
    from services.collect import _fetch_thread_replies

    col = _make_collection(db, regular_user.id)

    def _reply_item(rid):
        return {
            "id": rid,
            "snippet": {
                "textOriginal": f"text {rid}",
                "textDisplay": f"text {rid}",
                "authorDisplayName": "user",
                "authorChannelId": {"value": "UCX"},
                "likeCount": 0,
                "publishedAt": "2024-01-01T00:00:00Z",
                "updatedAt": "2024-01-01T00:00:00Z",
            },
        }

    mocker.patch(
        "services.collect.fetch_replies_page",
        new=AsyncMock(
            side_effect=[
                {
                    "items": [_reply_item("rp1")],
                    "nextPageToken": "PAGE2",
                },
                {
                    "items": [_reply_item("rp2")],
                    "nextPageToken": None,
                },
            ]
        ),
    )
    inserted = _run(_fetch_thread_replies(db, col.id, "parent_1", "KEY"))
    assert inserted == 2


# ---------------------------------------------------------------------------
# _enrich_channel_dates — batch + epoch fallback
# ---------------------------------------------------------------------------


def test_enrich_channel_dates_with_epoch_fallback(db, regular_user, mocker):
    """Cobre linhas 565-593: canais não encontrados recebem epoch."""
    from datetime import UTC, datetime

    from services.collect import _enrich_channel_dates

    col = _make_collection(db, regular_user.id)
    _make_comment(
        db,
        col.id,
        "cd1",
        author_channel_id="UCFOUND",
        author_channel_published_at=None,
    )
    _make_comment(
        db,
        col.id,
        "cd2",
        author_channel_id="UCMISSING",
        author_channel_published_at=None,
    )
    mocker.patch(
        "services.collect.fetch_channels_info",
        new=AsyncMock(return_value={"UCFOUND": datetime(2019, 3, 15, tzinfo=UTC)}),
    )
    success = _run(_enrich_channel_dates(db, col.id, ["UCFOUND", "UCMISSING"], "KEY"))
    assert success is True

    found = db.query(Comment).filter(Comment.author_channel_id == "UCFOUND").first()
    # DB pode retornar naive ou aware — comparar só data
    assert found.author_channel_published_at.year == 2019
    assert found.author_channel_published_at.month == 3
    assert found.author_channel_published_at.day == 15
    missing = db.query(Comment).filter(Comment.author_channel_id == "UCMISSING").first()
    # Epoch fallback (1970-01-01)
    assert missing.author_channel_published_at.year == 1970
    assert missing.author_channel_published_at.month == 1
    assert missing.author_channel_published_at.day == 1


def test_enrich_channel_dates_empty_list():
    """Cobre linha 565: lista vazia retorna True."""
    from services.collect import _enrich_channel_dates

    result = _run(_enrich_channel_dates(MagicMock(), uuid.uuid4(), [], "KEY"))
    assert result is True


def test_enrich_channel_dates_exception_returns_false(db, regular_user, mocker):
    """Cobre linhas 586-593: exceção → retorna False."""
    from services.collect import _enrich_channel_dates

    col = _make_collection(db, regular_user.id)
    _make_comment(
        db,
        col.id,
        "cde",
        author_channel_id="UCERR",
        author_channel_published_at=None,
    )
    mocker.patch(
        "services.collect.fetch_channels_info",
        new=AsyncMock(side_effect=Exception("API down")),
    )
    success = _run(_enrich_channel_dates(db, col.id, ["UCERR"], "KEY"))
    assert success is False


# ---------------------------------------------------------------------------
# import_collection
# ---------------------------------------------------------------------------


def test_import_collection_creates_and_persists(client, db, auth_as_user):
    """Cobre linhas 613-654: import com metadata e comentários."""
    payload = _import_payload(n_comments=3, done=True)
    resp = client.post("/collect/import", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["video_id"] == "vid123"
    assert data["status"] == "completed"
    # Confirmar que comentários foram inseridos
    total = db.query(Comment).count()
    assert total == 3


def test_import_collection_not_done(client, db, auth_as_user):
    """Import com done=False cria collection como 'importing'."""
    payload = _import_payload(done=False)
    resp = client.post("/collect/import", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "importing"


# ---------------------------------------------------------------------------
# import_chunk
# ---------------------------------------------------------------------------


def test_import_chunk_appends_comments(client, db, auth_as_user):
    """Cobre linhas 664-699: append de batch."""
    # Primeiro, criar a coleta via import
    payload = _import_payload(n_comments=2, done=False)
    resp = client.post("/collect/import", json=payload)
    collection_id = resp.json()["collection_id"]

    # Enviar chunk
    chunk_payload = {
        "collection_id": collection_id,
        "comments": [
            {
                "comment_id": "chunk_1",
                "text_original": "chunk text",
                "published_at": "2024-06-01T00:00:00Z",
                "updated_at": "2024-06-01T00:00:00Z",
            }
        ],
        "done": True,
    }
    resp2 = client.post("/collect/import-chunk", json=chunk_payload)
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["total_comments"] == 3
    assert data["chunk_received"] == 1
    assert data["done"] is True

    # Confirmar status mudou
    col = db.query(Collection).filter(Collection.id == uuid.UUID(collection_id)).first()
    assert col.status == "completed"


def test_import_chunk_not_found(client, auth_as_user):
    """Cobre import_chunk com collection_id inexistente."""
    chunk_payload = {
        "collection_id": str(uuid.uuid4()),
        "comments": [
            {
                "comment_id": "x",
                "text_original": "x",
                "published_at": "2024-06-01T00:00:00Z",
                "updated_at": "2024-06-01T00:00:00Z",
            }
        ],
        "done": False,
    }
    resp = client.post("/collect/import-chunk", json=chunk_payload)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# delete_collection
# ---------------------------------------------------------------------------


def test_delete_collection_success(client, db, auth_as_user, stub_youtube_3_comments):
    """Cobre linhas 716-720: delete bem-sucedido."""
    resp = client.post(
        "/collect",
        json={
            "video_id": "dQw4w9WgXcQ",
            "api_key": "AIzaFAKE",
        },
    )
    cid = resp.json()["collection_id"]
    del_resp = client.delete(f"/collect/{cid}")
    assert del_resp.status_code == 204
    assert db.query(Collection).count() == 0
    assert db.query(Comment).count() == 0


def test_delete_collection_not_found(client, auth_as_user):
    """Cobre linha 710: collection não encontrada → 404."""
    resp = client.delete(f"/collect/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_delete_collection_running_returns_409(client, db, auth_as_user, mocker):
    """Cobre linhas 711-715: coleta running → 409."""
    items = [_make_item(i) for i in range(2)]
    mocker.patch(
        "services.collect.fetch_comments_page",
        new=AsyncMock(return_value=_page(items, next_token="HAS_MORE")),
    )
    resp = client.post(
        "/collect",
        json={
            "video_id": "dQw4w9WgXcQ",
            "api_key": "AIzaFAKE",
        },
    )
    cid = resp.json()["collection_id"]
    del_resp = client.delete(f"/collect/{cid}")
    assert del_resp.status_code == 409


# ---------------------------------------------------------------------------
# export_comments_iter
# ---------------------------------------------------------------------------


def test_export_comments_iter_streaming(db, regular_user):
    """Cobre linha 725: generator com yield_per."""
    from services.collect import export_comments_iter

    col = _make_collection(db, regular_user.id)
    for i in range(5):
        _make_comment(db, col.id, f"exp_{i}")
    results = list(export_comments_iter(db, col.id))
    assert len(results) == 5


# ---------------------------------------------------------------------------
# routers/collect.py — export endpoints (JSON + CSV)
# ---------------------------------------------------------------------------


def test_export_json_streaming(client, db, auth_as_user, stub_youtube_3_comments):
    """Cobre linhas 237-288: export JSON completo."""
    import json as json_mod

    resp = client.post(
        "/collect",
        json={
            "video_id": "dQw4w9WgXcQ",
            "api_key": "AIzaFAKE",
        },
    )
    cid = resp.json()["collection_id"]
    export_resp = client.get(f"/collect/{cid}/export?format=json")
    assert export_resp.status_code == 200
    assert "application/json" in export_resp.headers["content-type"]
    data = json_mod.loads(export_resp.text)
    assert "video" in data
    assert "comments" in data
    assert len(data["comments"]) == 3
    assert data["video"]["id"] == "dQw4w9WgXcQ"


def test_export_csv_streaming(client, db, auth_as_user, stub_youtube_3_comments):
    """Cobre linhas 240-262: export CSV com header e BOM."""
    resp = client.post(
        "/collect",
        json={
            "video_id": "dQw4w9WgXcQ",
            "api_key": "AIzaFAKE",
        },
    )
    cid = resp.json()["collection_id"]
    export_resp = client.get(f"/collect/{cid}/export?format=csv")
    assert export_resp.status_code == 200
    assert "text/csv" in export_resp.headers["content-type"]
    # BOM
    assert export_resp.text.startswith("\ufeff")
    lines = export_resp.text.strip().split("\n")
    # Header + 3 data rows
    assert len(lines) == 4
    assert "comment_id" in lines[0]


def test_export_not_found(client, auth_as_user):
    """Export de collection inexistente retorna 404."""
    resp = client.get(f"/collect/{uuid.uuid4()}/export?format=json")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# routers/collect.py — enrich endpoint
# ---------------------------------------------------------------------------


def test_enrich_endpoint_via_router(client, db, auth_as_user, mocker):
    """Cobre linhas 131-136: POST /{id}/enrich via router."""
    # Criar coleta completada com video_title já set
    col = _make_collection(
        db,
        auth_as_user.id,
        status="completed",
        enrich_status="enriching",
        video_title="Set",
    )
    # Sem threads nem canais pendentes → done
    resp = client.post(
        f"/collect/{col.id}/enrich",
        json={"api_key": "AIzaFAKEKEY"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["done"] is True


def test_enrich_endpoint_not_completed(client, db, auth_as_user):
    """Enrich em coleta não completada retorna 400."""
    col = _make_collection(db, auth_as_user.id, status="running")
    resp = client.post(
        f"/collect/{col.id}/enrich",
        json={"api_key": "AIzaFAKEKEY"},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# services/youtube.py — fetch_comments_page
# ---------------------------------------------------------------------------


def test_fetch_comments_page_constructs_params(mocker):
    """Cobre linhas 15-32: construção de parâmetros e chamada."""
    from services.youtube import fetch_comments_page

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "items": [],
        "nextPageToken": None,
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    mocker.patch(
        "services.youtube.httpx.AsyncClient",
        return_value=mock_client,
    )

    result = _run(fetch_comments_page("vid123", "KEY", max_results=50))
    assert result == {"items": [], "nextPageToken": None}
    call_kwargs = mock_client.get.call_args
    params = call_kwargs.kwargs.get("params", call_kwargs[1].get("params", {}))
    assert params["videoId"] == "vid123"
    assert params["maxResults"] == 50
    assert "pageToken" not in params


def test_fetch_comments_page_with_page_token(mocker):
    """Cobre linha 23: pageToken adicionado quando presente."""
    from services.youtube import fetch_comments_page

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"items": []}
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    mocker.patch(
        "services.youtube.httpx.AsyncClient",
        return_value=mock_client,
    )

    _run(fetch_comments_page("vid123", "KEY", page_token="ABC"))
    call_kwargs = mock_client.get.call_args
    params = call_kwargs.kwargs.get("params", call_kwargs[1].get("params", {}))
    assert params["pageToken"] == "ABC"


# ---------------------------------------------------------------------------
# services/youtube.py — fetch_video_info
# ---------------------------------------------------------------------------


def test_fetch_video_info_returns_first_item(mocker):
    """Cobre linhas 37-49: retorna primeiro item."""
    from services.youtube import fetch_video_info

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"items": [{"id": "vid", "snippet": {"title": "T"}}]}
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    mocker.patch(
        "services.youtube.httpx.AsyncClient",
        return_value=mock_client,
    )

    result = _run(fetch_video_info("vid", "KEY"))
    assert result["snippet"]["title"] == "T"


def test_fetch_video_info_returns_none_empty(mocker):
    """Cobre linha 49: items vazio → None."""
    from services.youtube import fetch_video_info

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"items": []}
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    mocker.patch(
        "services.youtube.httpx.AsyncClient",
        return_value=mock_client,
    )

    result = _run(fetch_video_info("vid", "KEY"))
    assert result is None


# ---------------------------------------------------------------------------
# services/youtube.py — fetch_replies_page
# ---------------------------------------------------------------------------


def test_fetch_replies_page_constructs_params(mocker):
    """Cobre linhas 58-75: parâmetros de replies."""
    from services.youtube import fetch_replies_page

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"items": []}
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    mocker.patch(
        "services.youtube.httpx.AsyncClient",
        return_value=mock_client,
    )

    _run(fetch_replies_page("parent1", "KEY"))
    call_kwargs = mock_client.get.call_args
    params = call_kwargs.kwargs.get("params", call_kwargs[1].get("params", {}))
    assert params["parentId"] == "parent1"
    assert "pageToken" not in params


def test_fetch_replies_page_with_page_token(mocker):
    """Cobre linha 66: pageToken para replies."""
    from services.youtube import fetch_replies_page

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"items": []}
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    mocker.patch(
        "services.youtube.httpx.AsyncClient",
        return_value=mock_client,
    )

    _run(fetch_replies_page("parent1", "KEY", page_token="P2"))
    call_kwargs = mock_client.get.call_args
    params = call_kwargs.kwargs.get("params", call_kwargs[1].get("params", {}))
    assert params["pageToken"] == "P2"


# ---------------------------------------------------------------------------
# services/youtube.py — fetch_channels_info (batching)
# ---------------------------------------------------------------------------


def test_fetch_channels_info_batching(mocker):
    """Cobre linhas 85-105: batching de >50 canais."""
    from services.youtube import fetch_channels_info

    # 60 channel IDs → 2 batches (50 + 10)
    ids = [f"UC{i:04d}" for i in range(60)]

    def _make_channel_resp(batch_ids):
        items = []
        for cid in batch_ids[:3]:  # retorna 3 por batch
            items.append(
                {
                    "id": cid,
                    "snippet": {"publishedAt": "2020-01-01T00:00:00Z"},
                }
            )
        resp = MagicMock()
        resp.json.return_value = {"items": items}
        resp.raise_for_status = MagicMock()
        return resp

    call_count = 0

    async def mock_get(url, params, timeout):
        nonlocal call_count
        call_count += 1
        batch_ids = params["id"].split(",")
        return _make_channel_resp(batch_ids)

    mock_client = AsyncMock()
    mock_client.get = mock_get
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    mocker.patch(
        "services.youtube.httpx.AsyncClient",
        return_value=mock_client,
    )

    result = _run(fetch_channels_info(ids, "KEY"))
    # 2 batches, each returning 3 → 6 results
    assert len(result) == 6
    assert call_count == 2


def test_fetch_channels_info_no_published_at(mocker):
    """Canal sem publishedAt é ignorado no resultado."""
    from services.youtube import fetch_channels_info

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "items": [
            {"id": "UC1", "snippet": {}},
            {
                "id": "UC2",
                "snippet": {"publishedAt": "2021-06-01T00:00:00Z"},
            },
        ]
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    mocker.patch(
        "services.youtube.httpx.AsyncClient",
        return_value=mock_client,
    )

    result = _run(fetch_channels_info(["UC1", "UC2"], "KEY"))
    assert "UC1" not in result
    assert "UC2" in result


# ---------------------------------------------------------------------------
# Parametrize: SQL injection payloads no video_id
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "malicious_id",
    [
        "';DROP comments;--",
        "1 OR 1=1",
        "x;DELETE FROM col",
        "<script>a(1)</scrip",
        "'UNION SELECT *--",
    ],
    ids=[
        "sql-drop",
        "sql-or",
        "sql-delete",
        "xss",
        "sql-union",
    ],
)
def test_sql_injection_video_id_is_safe(
    client,
    db,
    auth_as_user,
    stub_youtube_3_comments,
    malicious_id,
):
    """SQL injection no video_id nao afeta o banco."""
    resp = client.post(
        "/collect",
        json={
            "video_id": malicious_id,
            "api_key": "AIzaFAKEKEY",
        },
    )
    # Deve processar normalmente (202) — parameterized queries
    assert resp.status_code == 202
    # Tabelas devem continuar existindo
    assert db.query(Collection).count() >= 1


# ---------------------------------------------------------------------------
# Enrich — channel_dates_failed flag when _enrich_channel_dates fails
# ---------------------------------------------------------------------------


def test_enrich_channel_dates_failed_flag(db, regular_user, mocker):
    """Cobre linhas 481-483: channel_dates_failed=True quando falha."""
    from services.collect import enrich_collection

    col = _make_collection(
        db,
        regular_user.id,
        status="completed",
        enrich_status="enriching",
        video_title="Set",
    )
    _make_comment(
        db,
        col.id,
        "cdf",
        author_channel_id="UCFAIL",
        author_channel_published_at=None,
    )
    mocker.patch(
        "services.collect.fetch_channels_info",
        new=AsyncMock(side_effect=Exception("API fail")),
    )
    result = _run(enrich_collection(db, col.id, "KEY"))
    assert result["phase"] == "channels"
    db.refresh(col)
    assert col.channel_dates_failed is True


# ---------------------------------------------------------------------------
# next-page via router (integration tests)
# ---------------------------------------------------------------------------


def test_next_page_router_not_found(client, auth_as_user):
    """POST /collect/next-page com collection inexistente → 404."""
    resp = client.post(
        "/collect/next-page",
        json={
            "collection_id": str(uuid.uuid4()),
            "api_key": "AIzaFAKE",
        },
    )
    assert resp.status_code == 404


def test_next_page_router_completed(client, db, auth_as_user, stub_youtube_3_comments):
    """POST /collect/next-page com coleta completed → retorna ok."""
    # Create completed collection
    resp = client.post(
        "/collect",
        json={
            "video_id": "dQw4w9WgXcQ",
            "api_key": "AIzaFAKE",
        },
    )
    cid = resp.json()["collection_id"]
    resp2 = client.post(
        "/collect/next-page",
        json={
            "collection_id": cid,
            "api_key": "AIzaFAKE",
        },
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "completed"


# ---------------------------------------------------------------------------
# Enrich — duration_seconds calculation
# ---------------------------------------------------------------------------


def test_enrich_sets_duration_seconds(db, regular_user):
    """Cobre linhas 497-499: calcula duration_seconds."""
    from datetime import datetime

    from services.collect import enrich_collection

    col = _make_collection(
        db,
        regular_user.id,
        status="completed",
        enrich_status="enriching",
        video_title="Set",
    )
    # Ensure created_at is set
    col.created_at = datetime(2024, 1, 1, 0, 0, 0)
    db.commit()

    result = _run(enrich_collection(db, col.id, "KEY"))
    assert result["done"] is True
    db.refresh(col)
    assert col.duration_seconds is not None
    assert col.duration_seconds > 0


# ---------------------------------------------------------------------------
# Enrich — wall-clock time limit break
# ---------------------------------------------------------------------------


def test_enrich_replies_wall_clock_break(db, regular_user, mocker):
    """Cobre linha 455: break quando wall-clock excede limite."""
    from services.collect import enrich_collection

    col = _make_collection(
        db,
        regular_user.id,
        status="completed",
        enrich_status="enriching",
        video_title="Set",
    )
    # Criar 2 threads que precisam de replies
    _make_comment(
        db,
        col.id,
        "wc1",
        comment_id="thread_wc1",
        reply_count=5,
        parent_id=None,
    )
    _make_comment(
        db,
        col.id,
        "wc2",
        comment_id="thread_wc2",
        reply_count=5,
        parent_id=None,
    )

    # We need to patch time.monotonic only inside services.collect
    # without affecting asyncio's internal calls.
    # services.collect does `import time` then `time.monotonic()`.
    # asyncio uses `time.monotonic()` from the real `time` module.
    # mocker.patch("services.collect.time") replaces the module ref
    # inside services.collect only.
    import time as real_time

    call_count = 0

    class FakeTime:
        """Proxy: only override monotonic, delegate rest."""

        def __getattr__(self, name):
            return getattr(real_time, name)

        def monotonic(self):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return 0.0  # t0
            if call_count == 2:
                return 1.0  # 1st thread check: 1-0=1 < 45
            return 100.0  # 2nd thread check: 100-0=100 > 45

    mocker.patch("services.collect.time", FakeTime())
    mocker.patch(
        "services.collect.fetch_replies_page",
        new=AsyncMock(
            return_value={
                "items": [],
                "nextPageToken": None,
            }
        ),
    )
    result = _run(enrich_collection(db, col.id, "KEY"))
    assert result["phase"] == "replies"
    # Processou apenas 1 thread (break no 2o)
    assert result["processed"] == 1

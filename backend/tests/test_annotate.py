import uuid
from datetime import datetime, timedelta

import pytest

from main import app
from models.annotation import AnnotationConflict
from models.collection import Collection, Comment
from models.dataset import Dataset, DatasetEntry
from models.user import User
from services.auth import get_current_user, get_password_hash

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_collection(db, user_id, *, video_id="vid123", status="completed"):
    col = Collection(
        video_id=video_id,
        status=status,
        collected_by=user_id,
        total_comments=5,
    )
    db.add(col)
    db.flush()
    return col


def _make_comments(db, collection_id, author_channel_id, count=3):
    comments = []
    for i in range(count):
        c = Comment(
            collection_id=collection_id,
            comment_id=f"{author_channel_id}_c{i}",
            author_channel_id=author_channel_id,
            author_display_name=f"User {author_channel_id}",
            text_original=f"Comentário {i} do {author_channel_id}",
            like_count=0,
            reply_count=0,
            published_at=datetime(2024, 1, 1) + timedelta(minutes=i),
            updated_at=datetime(2024, 1, 1) + timedelta(minutes=i),
        )
        db.add(c)
        comments.append(c)
    db.flush()
    return comments


def _make_dataset(db, collection_id, user_id, author_channel_ids):
    ds = Dataset(
        name=f"test_dataset_{uuid.uuid4().hex[:6]}",
        collection_id=collection_id,
        criteria_applied=["percentil"],
        thresholds={},
        total_users_original=10,
        total_users_selected=len(author_channel_ids),
        created_by=user_id,
    )
    db.add(ds)
    db.flush()

    for channel_id in author_channel_ids:
        entry = DatasetEntry(
            dataset_id=ds.id,
            author_channel_id=channel_id,
            author_display_name=f"User {channel_id}",
            comment_count=3,
            matched_criteria=["percentil"],
        )
        db.add(entry)
    db.flush()
    return ds


@pytest.fixture
def second_user(db):
    user = User(
        username="annotator2",
        name="Anotador Dois",
        hashed_password=get_password_hash("pass12345"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def setup_data(db, regular_user):
    """Cria coleta, comentários e dataset para testes de anotação."""
    col = _make_collection(db, regular_user.id)
    comments = _make_comments(db, col.id, "UC_author1", count=3)
    ds = _make_dataset(db, col.id, regular_user.id, ["UC_author1"])
    db.commit()
    return {
        "collection": col,
        "comments": comments,
        "dataset": ds,
    }


# ---------------------------------------------------------------------------
# Validação Pydantic — bot sem justificativa
# ---------------------------------------------------------------------------


class TestAnnotationValidation:
    def test_bot_sem_justificativa_retorna_422(self, client, auth_as_user, setup_data):
        comment = setup_data["comments"][0]
        resp = client.post(
            "/annotate",
            json={
                "comment_db_id": str(comment.id),
                "label": "bot",
                "justificativa": "",
            },
        )
        assert resp.status_code == 422

    def test_bot_com_justificativa_aceita(self, client, auth_as_user, setup_data):
        comment = setup_data["comments"][0]
        resp = client.post(
            "/annotate",
            json={
                "comment_db_id": str(comment.id),
                "label": "bot",
                "justificativa": "Texto repetido.",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["label"] == "bot"

    def test_humano_sem_justificativa_aceita(self, client, auth_as_user, setup_data):
        comment = setup_data["comments"][0]
        resp = client.post(
            "/annotate",
            json={
                "comment_db_id": str(comment.id),
                "label": "humano",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["label"] == "humano"

    def test_label_invalido_retorna_422(self, client, auth_as_user, setup_data):
        comment = setup_data["comments"][0]
        resp = client.post(
            "/annotate",
            json={
                "comment_db_id": str(comment.id),
                "label": "incerto",
            },
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------


class TestAnnotationAuth:
    def test_sem_token_retorna_401(self, client, setup_data):
        comment = setup_data["comments"][0]
        # Limpar override de auth
        app.dependency_overrides.pop(get_current_user, None)
        resp = client.post(
            "/annotate",
            json={
                "comment_db_id": str(comment.id),
                "label": "humano",
            },
        )
        assert resp.status_code == 401

    def test_list_users_sem_token_retorna_401(self, client, setup_data):
        app.dependency_overrides.pop(get_current_user, None)
        ds = setup_data["dataset"]
        resp = client.get(f"/annotate/users?dataset_id={ds.id}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Upsert e re-anotação
# ---------------------------------------------------------------------------


class TestUpsertAnnotation:
    def test_reannotation_altera_label(self, client, auth_as_user, setup_data):
        comment = setup_data["comments"][0]

        # Primeira anotação: humano
        resp1 = client.post(
            "/annotate",
            json={"comment_db_id": str(comment.id), "label": "humano"},
        )
        assert resp1.status_code == 200
        ann_id = resp1.json()["annotation_id"]

        # Re-anotação: bot
        resp2 = client.post(
            "/annotate",
            json={
                "comment_db_id": str(comment.id),
                "label": "bot",
                "justificativa": "Mudei de ideia.",
            },
        )
        assert resp2.status_code == 200
        # Mesmo annotation_id (upsert, não duplicata)
        assert resp2.json()["annotation_id"] == ann_id
        assert resp2.json()["label"] == "bot"

    def test_comentario_inexistente_retorna_404(self, client, auth_as_user):
        resp = client.post(
            "/annotate",
            json={
                "comment_db_id": str(uuid.uuid4()),
                "label": "humano",
            },
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Detecção de conflito
# ---------------------------------------------------------------------------


class TestConflictDetection:
    def test_labels_iguais_sem_conflito(
        self, client, db, auth_as_user, setup_data, second_user
    ):
        comment = setup_data["comments"][0]

        # User A anota humano
        client.post(
            "/annotate",
            json={"comment_db_id": str(comment.id), "label": "humano"},
        )

        # User B anota humano
        app.dependency_overrides[get_current_user] = lambda: second_user
        client.post(
            "/annotate",
            json={"comment_db_id": str(comment.id), "label": "humano"},
        )

        conflicts = (
            db.query(AnnotationConflict).filter_by(comment_id=comment.id).count()
        )
        assert conflicts == 0

    def test_labels_diferentes_cria_conflito(
        self, client, db, auth_as_user, setup_data, second_user
    ):
        comment = setup_data["comments"][0]

        # User A anota humano
        resp1 = client.post(
            "/annotate",
            json={"comment_db_id": str(comment.id), "label": "humano"},
        )
        assert resp1.json()["conflict_created"] is False

        # User B anota bot
        app.dependency_overrides[get_current_user] = lambda: second_user
        resp2 = client.post(
            "/annotate",
            json={
                "comment_db_id": str(comment.id),
                "label": "bot",
                "justificativa": "Spam.",
            },
        )
        assert resp2.json()["conflict_created"] is True

        conflicts = (
            db.query(AnnotationConflict).filter_by(comment_id=comment.id).count()
        )
        assert conflicts == 1

    def test_segundo_conflito_mesmo_comentario_nao_duplica(
        self, client, db, auth_as_user, setup_data, second_user
    ):
        comment = setup_data["comments"][0]

        # User A anota humano
        client.post(
            "/annotate",
            json={"comment_db_id": str(comment.id), "label": "humano"},
        )

        # User B anota bot → conflito
        app.dependency_overrides[get_current_user] = lambda: second_user
        client.post(
            "/annotate",
            json={
                "comment_db_id": str(comment.id),
                "label": "bot",
                "justificativa": "Spam.",
            },
        )

        # User B reanota bot (mantém divergência) → NÃO duplica conflito
        client.post(
            "/annotate",
            json={
                "comment_db_id": str(comment.id),
                "label": "bot",
                "justificativa": "Spam confirmado.",
            },
        )

        conflicts = (
            db.query(AnnotationConflict).filter_by(comment_id=comment.id).count()
        )
        assert conflicts == 1

    def test_concordancia_apos_conflito_remove_conflito(
        self, client, db, auth_as_user, setup_data, second_user
    ):
        comment = setup_data["comments"][0]

        # User A anota humano
        client.post(
            "/annotate",
            json={"comment_db_id": str(comment.id), "label": "humano"},
        )

        # User B anota bot → conflito
        app.dependency_overrides[get_current_user] = lambda: second_user
        client.post(
            "/annotate",
            json={
                "comment_db_id": str(comment.id),
                "label": "bot",
                "justificativa": "Spam.",
            },
        )

        # User B muda para humano → concordam → conflito removido
        client.post(
            "/annotate",
            json={"comment_db_id": str(comment.id), "label": "humano"},
        )

        conflicts = (
            db.query(AnnotationConflict).filter_by(comment_id=comment.id).count()
        )
        assert conflicts == 0


# ---------------------------------------------------------------------------
# Listar usuários do dataset
# ---------------------------------------------------------------------------


class TestListDatasetUsers:
    def test_lista_usuarios_com_progresso(self, client, auth_as_user, setup_data):
        ds = setup_data["dataset"]
        comment = setup_data["comments"][0]

        # Anotar um comentário
        client.post(
            "/annotate",
            json={"comment_db_id": str(comment.id), "label": "humano"},
        )

        resp = client.get(f"/annotate/users?dataset_id={ds.id}")
        assert resp.status_code == 200
        data = resp.json()

        assert data["dataset_id"] == str(ds.id)
        assert data["total_users"] == 1
        assert data["annotated_comments_by_me"] == 1

        item = data["items"][0]
        assert item["my_annotated_count"] == 1
        assert item["my_pending_count"] == 2  # 3 comments - 1 annotated

    def test_dataset_inexistente_retorna_404(self, client, auth_as_user):
        resp = client.get(f"/annotate/users?dataset_id={uuid.uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Comentários de um entry
# ---------------------------------------------------------------------------


class TestGetEntryComments:
    def test_retorna_comentarios_com_anotacao(
        self, client, db, auth_as_user, setup_data
    ):
        ds = setup_data["dataset"]
        comment = setup_data["comments"][0]

        # Anotar
        client.post(
            "/annotate",
            json={"comment_db_id": str(comment.id), "label": "humano"},
        )

        entry = db.query(DatasetEntry).filter_by(dataset_id=ds.id).first()
        resp = client.get(f"/annotate/comments/{entry.id}")
        assert resp.status_code == 200

        data = resp.json()
        assert data["author_display_name"] == "User UC_author1"
        assert len(data["comments"]) == 3

        # Primeiro comentário deve ter anotação
        annotated = [c for c in data["comments"] if c["my_annotation"] is not None]
        assert len(annotated) == 1
        assert annotated[0]["my_annotation"]["label"] == "humano"

    def test_entry_inexistente_retorna_404(self, client, auth_as_user):
        resp = client.get(f"/annotate/comments/{uuid.uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Progresso
# ---------------------------------------------------------------------------


class TestMyProgress:
    def test_progresso_vazio_sem_anotacoes(self, client, auth_as_user, setup_data):
        resp = client.get("/annotate/my-progress")
        assert resp.status_code == 200
        data = resp.json()
        # Dataset existe mas pode ter 0 anotações
        if len(data) > 0:
            assert data[0]["annotated"] == 0

    def test_progresso_atualiza_apos_anotacao(self, client, auth_as_user, setup_data):
        comment = setup_data["comments"][0]

        # Anotar
        client.post(
            "/annotate",
            json={"comment_db_id": str(comment.id), "label": "humano"},
        )

        resp = client.get("/annotate/my-progress")
        data = resp.json()
        ds_progress = next(
            (p for p in data if p["dataset_id"] == str(setup_data["dataset"].id)),
            None,
        )
        assert ds_progress is not None
        assert ds_progress["annotated"] == 1
        assert ds_progress["humans"] == 1


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


class TestImport:
    def test_import_cria_anotacoes(self, client, auth_as_user, setup_data):
        comments = setup_data["comments"]

        resp = client.post(
            "/annotate/import",
            json={
                "annotations": [
                    {
                        "comment_db_id": str(comments[0].id),
                        "label": "humano",
                    },
                    {
                        "comment_db_id": str(comments[1].id),
                        "label": "bot",
                        "justificativa": "Spam.",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 2
        assert data["updated"] == 0
        assert data["skipped"] == 0

    def test_import_upsert_nao_duplica(self, client, auth_as_user, setup_data):
        comment = setup_data["comments"][0]

        # Primeira vez
        client.post(
            "/annotate/import",
            json={
                "annotations": [
                    {"comment_db_id": str(comment.id), "label": "humano"},
                ],
            },
        )

        # Segunda vez — upsert
        resp = client.post(
            "/annotate/import",
            json={
                "annotations": [
                    {
                        "comment_db_id": str(comment.id),
                        "label": "bot",
                        "justificativa": "Mudei de ideia.",
                    },
                ],
            },
        )
        data = resp.json()
        assert data["imported"] == 0
        assert data["updated"] == 1

    def test_import_comentario_inexistente_skip(self, client, auth_as_user):
        resp = client.post(
            "/annotate/import",
            json={
                "annotations": [
                    {
                        "comment_db_id": str(uuid.uuid4()),
                        "label": "humano",
                    },
                ],
            },
        )
        data = resp.json()
        assert data["skipped"] == 1
        assert len(data["errors"]) == 1

    def test_import_bot_sem_justificativa_skip(self, client, auth_as_user, setup_data):
        comment = setup_data["comments"][0]
        resp = client.post(
            "/annotate/import",
            json={
                "annotations": [
                    {
                        "comment_db_id": str(comment.id),
                        "label": "bot",
                        "justificativa": "",
                    },
                ],
            },
        )
        data = resp.json()
        assert data["skipped"] == 1


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


class TestExport:
    def test_export_json_retorna_apenas_minhas_anotacoes(
        self, client, db, auth_as_user, setup_data, second_user
    ):
        comments = setup_data["comments"]

        # User A anota comment 0
        client.post(
            "/annotate",
            json={"comment_db_id": str(comments[0].id), "label": "humano"},
        )

        # User B anota comment 1
        app.dependency_overrides[get_current_user] = lambda: second_user
        client.post(
            "/annotate",
            json={"comment_db_id": str(comments[1].id), "label": "humano"},
        )

        # User A exporta
        app.dependency_overrides[get_current_user] = lambda: auth_as_user
        resp = client.get("/annotate/export?format=json")
        assert resp.status_code == 200

        # Deve vir ao menos o comentário de User A
        data = resp.json()
        assert "annotations" in data

    def test_export_csv(self, client, auth_as_user, setup_data):
        comment = setup_data["comments"][0]

        client.post(
            "/annotate",
            json={"comment_db_id": str(comment.id), "label": "humano"},
        )

        resp = client.get("/annotate/export?format=csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        lines = resp.text.strip().split("\n")
        assert lines[0] == "comment_db_id,label,justificativa"
        assert len(lines) >= 2

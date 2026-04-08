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

    entries = []
    for channel_id in author_channel_ids:
        entry = DatasetEntry(
            dataset_id=ds.id,
            author_channel_id=channel_id,
            author_display_name=f"User {channel_id}",
            comment_count=3,
            matched_criteria=["percentil"],
        )
        db.add(entry)
        entries.append(entry)
    db.flush()
    return ds, entries


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
    """Cria coleta, comentários, dataset e entries para testes de anotação."""
    col = _make_collection(db, regular_user.id)
    comments = _make_comments(db, col.id, "UC_author1", count=3)
    ds, entries = _make_dataset(db, col.id, regular_user.id, ["UC_author1"])
    db.commit()
    return {
        "collection": col,
        "comments": comments,
        "dataset": ds,
        "entry": entries[0],
    }


# ---------------------------------------------------------------------------
# Validação Pydantic — bot sem justificativa
# ---------------------------------------------------------------------------


class TestAnnotationValidation:
    def test_bot_sem_justificativa_retorna_422(self, client, auth_as_user, setup_data):
        entry = setup_data["entry"]
        resp = client.post(
            "/annotate",
            json={
                "entry_id": str(entry.id),
                "label": "bot",
                "justificativa": "",
            },
        )
        assert resp.status_code == 422

    def test_bot_com_justificativa_aceita(self, client, auth_as_user, setup_data):
        entry = setup_data["entry"]
        resp = client.post(
            "/annotate",
            json={
                "entry_id": str(entry.id),
                "label": "bot",
                "justificativa": "Texto repetido.",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["label"] == "bot"

    def test_humano_sem_justificativa_aceita(self, client, auth_as_user, setup_data):
        entry = setup_data["entry"]
        resp = client.post(
            "/annotate",
            json={
                "entry_id": str(entry.id),
                "label": "humano",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["label"] == "humano"

    def test_label_invalido_retorna_422(self, client, auth_as_user, setup_data):
        entry = setup_data["entry"]
        resp = client.post(
            "/annotate",
            json={
                "entry_id": str(entry.id),
                "label": "incerto",
            },
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------


class TestAnnotationAuth:
    def test_sem_token_retorna_401(self, client, setup_data):
        entry = setup_data["entry"]
        app.dependency_overrides.pop(get_current_user, None)
        resp = client.post(
            "/annotate",
            json={
                "entry_id": str(entry.id),
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
        entry = setup_data["entry"]

        # Primeira anotação: humano
        resp1 = client.post(
            "/annotate",
            json={"entry_id": str(entry.id), "label": "humano"},
        )
        assert resp1.status_code == 200
        ann_id = resp1.json()["annotation_id"]

        # Re-anotação: bot
        resp2 = client.post(
            "/annotate",
            json={
                "entry_id": str(entry.id),
                "label": "bot",
                "justificativa": "Mudei de ideia.",
            },
        )
        assert resp2.status_code == 200
        assert resp2.json()["annotation_id"] == ann_id
        assert resp2.json()["label"] == "bot"

    def test_entry_inexistente_retorna_404(self, client, auth_as_user):
        resp = client.post(
            "/annotate",
            json={
                "entry_id": str(uuid.uuid4()),
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
        entry = setup_data["entry"]

        client.post(
            "/annotate",
            json={"entry_id": str(entry.id), "label": "humano"},
        )

        app.dependency_overrides[get_current_user] = lambda: second_user
        client.post(
            "/annotate",
            json={"entry_id": str(entry.id), "label": "humano"},
        )

        conflicts = (
            db.query(AnnotationConflict).filter_by(dataset_entry_id=entry.id).count()
        )
        assert conflicts == 0

    def test_labels_diferentes_cria_conflito(
        self, client, db, auth_as_user, setup_data, second_user
    ):
        entry = setup_data["entry"]

        resp1 = client.post(
            "/annotate",
            json={"entry_id": str(entry.id), "label": "humano"},
        )
        assert resp1.json()["conflict_created"] is False

        app.dependency_overrides[get_current_user] = lambda: second_user
        resp2 = client.post(
            "/annotate",
            json={
                "entry_id": str(entry.id),
                "label": "bot",
                "justificativa": "Spam.",
            },
        )
        assert resp2.json()["conflict_created"] is True

        conflicts = (
            db.query(AnnotationConflict).filter_by(dataset_entry_id=entry.id).count()
        )
        assert conflicts == 1

    def test_segundo_conflito_mesmo_entry_nao_duplica(
        self, client, db, auth_as_user, setup_data, second_user
    ):
        entry = setup_data["entry"]

        client.post(
            "/annotate",
            json={"entry_id": str(entry.id), "label": "humano"},
        )

        app.dependency_overrides[get_current_user] = lambda: second_user
        client.post(
            "/annotate",
            json={
                "entry_id": str(entry.id),
                "label": "bot",
                "justificativa": "Spam.",
            },
        )

        client.post(
            "/annotate",
            json={
                "entry_id": str(entry.id),
                "label": "bot",
                "justificativa": "Spam confirmado.",
            },
        )

        conflicts = (
            db.query(AnnotationConflict).filter_by(dataset_entry_id=entry.id).count()
        )
        assert conflicts == 1

    def test_concordancia_apos_conflito_remove_conflito(
        self, client, db, auth_as_user, setup_data, second_user
    ):
        entry = setup_data["entry"]

        client.post(
            "/annotate",
            json={"entry_id": str(entry.id), "label": "humano"},
        )

        app.dependency_overrides[get_current_user] = lambda: second_user
        client.post(
            "/annotate",
            json={
                "entry_id": str(entry.id),
                "label": "bot",
                "justificativa": "Spam.",
            },
        )

        client.post(
            "/annotate",
            json={"entry_id": str(entry.id), "label": "humano"},
        )

        conflicts = (
            db.query(AnnotationConflict).filter_by(dataset_entry_id=entry.id).count()
        )
        assert conflicts == 0


# ---------------------------------------------------------------------------
# Listar usuários do dataset
# ---------------------------------------------------------------------------


class TestListDatasetUsers:
    def test_lista_usuarios_com_progresso(self, client, auth_as_user, setup_data):
        ds = setup_data["dataset"]
        entry = setup_data["entry"]

        # Anotar o entry
        client.post(
            "/annotate",
            json={"entry_id": str(entry.id), "label": "humano"},
        )

        resp = client.get(f"/annotate/users?dataset_id={ds.id}")
        assert resp.status_code == 200
        data = resp.json()

        assert data["dataset_id"] == str(ds.id)
        assert data["total_users"] == 1
        assert data["annotated_users_by_me"] == 1

        item = data["items"][0]
        assert item["is_annotated_by_me"] is True
        assert item["my_label"] == "humano"

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
        entry = setup_data["entry"]

        # Anotar o entry
        client.post(
            "/annotate",
            json={"entry_id": str(entry.id), "label": "humano"},
        )

        resp = client.get(f"/annotate/comments/{entry.id}")
        assert resp.status_code == 200

        data = resp.json()
        assert data["author_display_name"] == "User UC_author1"
        assert len(data["comments"]) == 3
        # Anotação está no nível do entry, não do comment
        assert data["my_annotation"] is not None
        assert data["my_annotation"]["label"] == "humano"

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
        if len(data) > 0:
            assert data[0]["annotated"] == 0

    def test_progresso_atualiza_apos_anotacao(self, client, auth_as_user, setup_data):
        entry = setup_data["entry"]

        client.post(
            "/annotate",
            json={"entry_id": str(entry.id), "label": "humano"},
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
        entry = setup_data["entry"]

        resp = client.post(
            "/annotate/import",
            json={
                "annotations": [
                    {
                        "entry_id": str(entry.id),
                        "label": "bot",
                        "justificativa": "Spam.",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 1
        assert data["updated"] == 0
        assert data["skipped"] == 0

    def test_import_upsert_nao_duplica(self, client, auth_as_user, setup_data):
        entry = setup_data["entry"]

        client.post(
            "/annotate/import",
            json={
                "annotations": [
                    {"entry_id": str(entry.id), "label": "humano"},
                ],
            },
        )

        resp = client.post(
            "/annotate/import",
            json={
                "annotations": [
                    {
                        "entry_id": str(entry.id),
                        "label": "bot",
                        "justificativa": "Mudei de ideia.",
                    },
                ],
            },
        )
        data = resp.json()
        assert data["imported"] == 0
        assert data["updated"] == 1

    def test_import_entry_inexistente_skip(self, client, auth_as_user):
        resp = client.post(
            "/annotate/import",
            json={
                "annotations": [
                    {
                        "entry_id": str(uuid.uuid4()),
                        "label": "humano",
                    },
                ],
            },
        )
        data = resp.json()
        assert data["skipped"] == 1
        assert len(data["errors"]) == 1

    def test_import_bot_sem_justificativa_skip(self, client, auth_as_user, setup_data):
        entry = setup_data["entry"]
        resp = client.post(
            "/annotate/import",
            json={
                "annotations": [
                    {
                        "entry_id": str(entry.id),
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
        entry = setup_data["entry"]

        # User A anota
        client.post(
            "/annotate",
            json={"entry_id": str(entry.id), "label": "humano"},
        )

        resp = client.get("/annotate/export?format=json")
        assert resp.status_code == 200
        data = resp.json()
        assert "annotations" in data

    def test_export_csv(self, client, auth_as_user, setup_data):
        entry = setup_data["entry"]

        client.post(
            "/annotate",
            json={"entry_id": str(entry.id), "label": "humano"},
        )

        resp = client.get("/annotate/export?format=csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        lines = resp.text.strip().split("\n")
        assert lines[0] == "entry_id,author_channel_id,label,justificativa"
        assert len(lines) >= 2


# ---------------------------------------------------------------------------
# Testes adicionais — cobertura
# ---------------------------------------------------------------------------


class TestAdminCannotAnnotate:
    def test_admin_post_annotate_retorna_403(self, client, auth_as_admin, setup_data):
        entry = setup_data["entry"]
        resp = client.post(
            "/annotate",
            json={
                "entry_id": str(entry.id),
                "label": "humano",
            },
        )
        assert resp.status_code == 403
        assert "administradores" in resp.json()["detail"].lower()


class TestListDatasetUsersAdmin:
    def test_admin_ve_todas_anotacoes(
        self,
        client,
        db,
        auth_as_admin,
        admin_user,
        regular_user,
        setup_data,
    ):
        from models.annotation import Annotation

        entry = setup_data["entry"]
        ann = Annotation(
            dataset_entry_id=entry.id,
            annotator_id=regular_user.id,
            label="humano",
        )
        db.add(ann)
        db.commit()

        ds = setup_data["dataset"]
        resp = client.get(f"/annotate/users?dataset_id={ds.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["annotated_users_by_me"] == 1


class TestListDatasetUsersFilters:
    def test_only_pending_filter(self, client, auth_as_user, setup_data):
        ds = setup_data["dataset"]
        entry = setup_data["entry"]

        # Anotar o entry
        client.post(
            "/annotate",
            json={"entry_id": str(entry.id), "label": "humano"},
        )

        resp = client.get(f"/annotate/users?dataset_id={ds.id}&only_pending=true")
        assert resp.status_code == 200
        data = resp.json()
        # O único entry foi anotado, então sem pendentes
        assert data["total_users"] == 0

    def test_pending_first_ordering(self, client, auth_as_user, setup_data):
        ds = setup_data["dataset"]
        resp = client.get(f"/annotate/users?dataset_id={ds.id}&pending_first=true")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) >= 1


class TestGetEntryCommentsAdmin:
    def test_admin_ve_all_annotations(
        self,
        client,
        db,
        auth_as_admin,
        admin_user,
        regular_user,
        setup_data,
    ):
        from models.annotation import Annotation

        entry = setup_data["entry"]
        ann = Annotation(
            dataset_entry_id=entry.id,
            annotator_id=regular_user.id,
            label="humano",
        )
        db.add(ann)
        db.commit()

        resp = client.get(f"/annotate/comments/{entry.id}")
        assert resp.status_code == 200
        data = resp.json()

        assert data["all_annotations"] is not None
        assert len(data["all_annotations"]) >= 1
        assert "annotator_name" in data["all_annotations"][0]


class TestConflictReopening:
    def test_reannotation_reabre_conflito_resolvido(
        self, client, db, auth_as_user, setup_data, second_user
    ):
        entry = setup_data["entry"]

        client.post(
            "/annotate",
            json={"entry_id": str(entry.id), "label": "humano"},
        )

        app.dependency_overrides[get_current_user] = lambda: second_user
        client.post(
            "/annotate",
            json={
                "entry_id": str(entry.id),
                "label": "bot",
                "justificativa": "Spam.",
            },
        )

        conflict = (
            db.query(AnnotationConflict).filter_by(dataset_entry_id=entry.id).first()
        )
        conflict.status = "resolved"
        conflict.resolved_label = "bot"
        db.commit()

        resp = client.post(
            "/annotate",
            json={
                "entry_id": str(entry.id),
                "label": "bot",
                "justificativa": "Confirmo spam.",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["conflict_created"] is True

        db.refresh(conflict)
        assert conflict.status == "pending"
        assert conflict.resolved_by is None


class TestGetAllProgress:
    def test_all_progress_retorna_dados_por_anotador(
        self,
        client,
        db,
        auth_as_admin,
        admin_user,
        regular_user,
        setup_data,
    ):
        from models.annotation import Annotation

        entry = setup_data["entry"]
        ann = Annotation(
            dataset_entry_id=entry.id,
            annotator_id=regular_user.id,
            label="humano",
        )
        db.add(ann)
        db.commit()

        resp = client.get("/annotate/all-progress")
        assert resp.status_code == 200
        data = resp.json()
        assert any(p["annotator_name"] == "Usuário Teste" for p in data)

    def test_all_progress_exclui_admin(
        self, client, db, auth_as_admin, admin_user, setup_data
    ):
        resp = client.get("/annotate/all-progress")
        assert resp.status_code == 200
        data = resp.json()
        for p in data:
            assert p["annotator_name"] != admin_user.name

    def test_all_progress_requer_admin(self, client, auth_as_user):
        resp = client.get("/annotate/all-progress")
        assert resp.status_code == 403


class TestImportAnnotationsChunk:
    def test_import_chunk_retorna_totais(self, client, auth_as_user, setup_data):
        entry = setup_data["entry"]
        resp = client.post(
            "/annotate/import-chunk",
            json={
                "annotations": [
                    {
                        "entry_id": str(entry.id),
                        "label": "humano",
                    },
                ],
                "done": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_imported"] == 1
        assert data["chunk_received"] == 1
        assert data["done"] is True


class TestExportWithDatasetFilter:
    def test_export_json_com_dataset_id(self, client, auth_as_user, setup_data):
        entry = setup_data["entry"]
        ds = setup_data["dataset"]

        client.post(
            "/annotate",
            json={"entry_id": str(entry.id), "label": "humano"},
        )

        resp = client.get(f"/annotate/export?format=json&dataset_id={ds.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "dataset_id" in data
        assert "dataset_name" in data
        assert "video_id" in data
        assert "annotations" in data

    def test_export_csv_com_dataset_id(self, client, auth_as_user, setup_data):
        entry = setup_data["entry"]
        ds = setup_data["dataset"]

        client.post(
            "/annotate",
            json={"entry_id": str(entry.id), "label": "humano"},
        )

        resp = client.get(f"/annotate/export?format=csv&dataset_id={ds.id}")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        lines = resp.text.strip().split("\n")
        assert lines[0] == "entry_id,author_channel_id,label,justificativa"


class TestGetAllProgressZeroComments:
    def test_dataset_sem_entries_pulado_no_all_progress(
        self,
        client,
        db,
        auth_as_admin,
        admin_user,
        regular_user,
    ):
        col = _make_collection(db, admin_user.id, video_id="vid_empty_prog")
        ds = Dataset(
            name=f"empty_ap_{uuid.uuid4().hex[:6]}",
            collection_id=col.id,
            criteria_applied=["percentil"],
            thresholds={},
            total_users_original=0,
            total_users_selected=0,
            created_by=admin_user.id,
        )
        db.add(ds)
        db.commit()

        resp = client.get("/annotate/all-progress")
        assert resp.status_code == 200
        data = resp.json()
        ds_ids = [p["dataset_id"] for p in data]
        assert str(ds.id) not in ds_ids

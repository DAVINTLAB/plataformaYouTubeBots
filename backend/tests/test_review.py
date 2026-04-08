import uuid
from datetime import datetime, timedelta

import pytest

from models.annotation import Annotation, AnnotationConflict
from models.collection import Collection, Comment
from models.dataset import Dataset, DatasetEntry
from models.resolution import Resolution
from models.user import User
from services.auth import get_password_hash

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
            text_original=f"Comentario {i} do {author_channel_id}",
            like_count=i,
            reply_count=0,
            published_at=datetime(2024, 1, 1) + timedelta(minutes=i),
            updated_at=datetime(2024, 1, 1) + timedelta(minutes=i),
        )
        db.add(c)
        comments.append(c)
    db.flush()
    return comments


def _make_dataset_with_entries(db, collection_id, user_id, author_channel_ids):
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


def _make_conflict(db, entry, user_a, user_b, *, label_a="bot", label_b="humano"):
    """Cria duas anotacoes divergentes por entry e o AnnotationConflict."""
    ann_a = Annotation(
        dataset_entry_id=entry.id,
        annotator_id=user_a.id,
        label=label_a,
        justificativa="Repetitivo" if label_a == "bot" else None,
    )
    ann_b = Annotation(
        dataset_entry_id=entry.id,
        annotator_id=user_b.id,
        label=label_b,
        justificativa="Repetitivo" if label_b == "bot" else None,
    )
    db.add_all([ann_a, ann_b])
    db.flush()

    conflict = AnnotationConflict(
        dataset_entry_id=entry.id,
        annotation_a_id=ann_a.id,
        annotation_b_id=ann_b.id,
    )
    db.add(conflict)
    db.flush()
    return conflict, ann_a, ann_b


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def annotator_a(db):
    user = User(
        username="annotator_a",
        name="Anotador A",
        hashed_password=get_password_hash("pass12345"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def annotator_b(db):
    user = User(
        username="annotator_b",
        name="Anotador B",
        hashed_password=get_password_hash("pass12345"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def setup_conflict(db, admin_user, annotator_a, annotator_b):
    """Cria cenario completo: coleta + comentarios + dataset + entry + conflito."""
    col = _make_collection(db, admin_user.id)
    comments = _make_comments(db, col.id, "UC_suspect1")
    ds, entries = _make_dataset_with_entries(db, col.id, admin_user.id, ["UC_suspect1"])
    entry = entries[0]
    conflict, ann_a, ann_b = _make_conflict(db, entry, annotator_a, annotator_b)
    db.commit()
    return {
        "collection": col,
        "comments": comments,
        "dataset": ds,
        "entry": entry,
        "conflict": conflict,
        "ann_a": ann_a,
        "ann_b": ann_b,
    }


# ---------------------------------------------------------------------------
# Testes — Autenticacao e autorizacao
# ---------------------------------------------------------------------------


class TestReviewAuth:
    def test_sem_token_retorna_401(self, client):
        resp = client.get("/review/conflicts")
        assert resp.status_code == 401

    def test_user_acessando_conflicts_retorna_403(self, client, auth_as_user):
        resp = client.get("/review/conflicts")
        assert resp.status_code == 403

    def test_user_acessando_resolve_retorna_403(self, client, auth_as_user):
        resp = client.post(
            "/review/resolve",
            json={
                "conflict_id": str(uuid.uuid4()),
                "resolved_label": "bot",
            },
        )
        assert resp.status_code == 403

    def test_user_acessando_bots_retorna_403(self, client, auth_as_user):
        resp = client.get("/review/bots")
        assert resp.status_code == 403

    def test_user_acessando_stats_retorna_403(self, client, auth_as_user):
        resp = client.get("/review/stats")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Testes — Listar conflitos
# ---------------------------------------------------------------------------


class TestListConflicts:
    def test_lista_conflitos_pendentes(self, client, auth_as_admin, setup_conflict):
        resp = client.get("/review/conflicts?status=pending")
        assert resp.status_code == 200
        body = resp.json()
        data = body["items"]
        assert len(data) == 1
        assert data[0]["status"] == "pending"
        assert data[0]["label_a"] == "bot"
        assert data[0]["label_b"] == "humano"
        assert "entry_id" in data[0]
        assert "dataset_id" in data[0]
        assert body["total"] == 1

    def test_lista_vazia_sem_conflitos(self, client, auth_as_admin):
        resp = client.get("/review/conflicts")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_filtro_por_dataset_id(self, client, auth_as_admin, setup_conflict):
        ds_id = str(setup_conflict["dataset"].id)
        resp = client.get(f"/review/conflicts?dataset_id={ds_id}")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    def test_filtro_por_dataset_id_inexistente(
        self, client, auth_as_admin, setup_conflict
    ):
        resp = client.get(f"/review/conflicts?dataset_id={uuid.uuid4()}")
        assert resp.status_code == 200
        assert resp.json()["items"] == []


# ---------------------------------------------------------------------------
# Testes — Detalhe de conflito
# ---------------------------------------------------------------------------


class TestConflictDetail:
    def test_retorna_detalhe_completo(self, client, auth_as_admin, setup_conflict):
        cid = str(setup_conflict["conflict"].id)
        resp = client.get(f"/review/conflicts/{cid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["annotation_a"]["label"] == "bot"
        assert data["annotation_b"]["label"] == "humano"
        assert len(data["comments"]) == 3  # all comments from same author

    def test_conflito_nao_encontrado_retorna_404(self, client, auth_as_admin):
        resp = client.get(f"/review/conflicts/{uuid.uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Testes — Resolver conflito
# ---------------------------------------------------------------------------


class TestResolveConflict:
    def test_resolve_como_bot(self, client, db, auth_as_admin, setup_conflict):
        cid = str(setup_conflict["conflict"].id)
        resp = client.post(
            "/review/resolve",
            json={"conflict_id": cid, "resolved_label": "bot"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "resolved"
        assert data["resolved_label"] == "bot"
        assert data["resolved_by"] == "Admin Teste"

        resolution = (
            db.query(Resolution)
            .filter(Resolution.conflict_id == setup_conflict["conflict"].id)
            .first()
        )
        assert resolution is not None
        assert resolution.resolved_label == "bot"

    def test_resolve_como_humano(self, client, auth_as_admin, setup_conflict):
        cid = str(setup_conflict["conflict"].id)
        resp = client.post(
            "/review/resolve",
            json={"conflict_id": cid, "resolved_label": "humano"},
        )
        assert resp.status_code == 200
        assert resp.json()["resolved_label"] == "humano"

    def test_conflito_ja_resolvido_retorna_409(
        self, client, auth_as_admin, setup_conflict
    ):
        cid = str(setup_conflict["conflict"].id)
        client.post(
            "/review/resolve",
            json={"conflict_id": cid, "resolved_label": "bot"},
        )
        resp = client.post(
            "/review/resolve",
            json={"conflict_id": cid, "resolved_label": "humano"},
        )
        assert resp.status_code == 409

    def test_conflito_inexistente_retorna_404(self, client, auth_as_admin):
        resp = client.post(
            "/review/resolve",
            json={
                "conflict_id": str(uuid.uuid4()),
                "resolved_label": "bot",
            },
        )
        assert resp.status_code == 404

    def test_label_invalido_retorna_422(self, client, auth_as_admin, setup_conflict):
        cid = str(setup_conflict["conflict"].id)
        resp = client.post(
            "/review/resolve",
            json={"conflict_id": cid, "resolved_label": "incerto"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Testes — Listar bots
# ---------------------------------------------------------------------------


class TestListBots:
    def test_lista_usuarios_com_anotacao_bot(
        self, client, db, auth_as_admin, admin_user, annotator_a, annotator_b
    ):
        col = _make_collection(db, admin_user.id)
        _make_comments(db, col.id, "UC_botA", count=2)
        _make_comments(db, col.id, "UC_humanB", count=2)
        ds, entries = _make_dataset_with_entries(
            db, col.id, admin_user.id, ["UC_botA", "UC_humanB"]
        )

        entry_bot = next(e for e in entries if e.author_channel_id == "UC_botA")
        entry_human = next(e for e in entries if e.author_channel_id == "UC_humanB")

        # UC_botA: ambos anotam como bot
        db.add(
            Annotation(
                dataset_entry_id=entry_bot.id,
                annotator_id=annotator_a.id,
                label="bot",
                justificativa="Spam",
            )
        )
        db.add(
            Annotation(
                dataset_entry_id=entry_bot.id,
                annotator_id=annotator_b.id,
                label="bot",
                justificativa="Spam",
            )
        )

        # UC_humanB: ambos anotam como humano
        db.add(
            Annotation(
                dataset_entry_id=entry_human.id,
                annotator_id=annotator_a.id,
                label="humano",
            )
        )
        db.add(
            Annotation(
                dataset_entry_id=entry_human.id,
                annotator_id=annotator_b.id,
                label="humano",
            )
        )
        db.commit()

        resp = client.get("/review/bots")
        assert resp.status_code == 200
        body = resp.json()
        data = body["items"]
        channel_ids = [item["author_channel_id"] for item in data]
        assert "UC_botA" in channel_ids
        assert "UC_humanB" not in channel_ids
        for item in data:
            assert "annotations" in item
            assert len(item["annotations"]) > 0

    def test_consenso_bot_nao_aparece_em_conflicts(
        self, client, db, auth_as_admin, admin_user, annotator_a, annotator_b
    ):
        col = _make_collection(db, admin_user.id)
        _make_comments(db, col.id, "UC_consenso_bot", count=1)
        ds, entries = _make_dataset_with_entries(
            db, col.id, admin_user.id, ["UC_consenso_bot"]
        )
        entry = entries[0]

        db.add(
            Annotation(
                dataset_entry_id=entry.id,
                annotator_id=annotator_a.id,
                label="bot",
                justificativa="Spam",
            )
        )
        db.add(
            Annotation(
                dataset_entry_id=entry.id,
                annotator_id=annotator_b.id,
                label="bot",
                justificativa="Repetitivo",
            )
        )
        db.commit()

        resp_bots = client.get("/review/bots")
        bot_items = [
            b
            for b in resp_bots.json()["items"]
            if b["author_channel_id"] == "UC_consenso_bot"
        ]
        assert len(bot_items) == 1
        assert bot_items[0]["has_conflict"] is False

        resp_conflicts = client.get("/review/conflicts")
        entry_ids_in_conflicts = [c["entry_id"] for c in resp_conflicts.json()["items"]]
        assert str(entry.id) not in entry_ids_in_conflicts


# ---------------------------------------------------------------------------
# Testes — Estatisticas
# ---------------------------------------------------------------------------


class TestReviewStats:
    def test_stats_com_conflito(self, client, auth_as_admin, setup_conflict):
        resp = client.get("/review/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_conflicts"] == 1
        assert data["pending_conflicts"] == 1
        assert data["resolved_conflicts"] == 0

    def test_stats_apos_resolucao(self, client, auth_as_admin, setup_conflict):
        cid = str(setup_conflict["conflict"].id)
        client.post(
            "/review/resolve",
            json={"conflict_id": cid, "resolved_label": "bot"},
        )
        resp = client.get("/review/stats")
        data = resp.json()
        assert data["pending_conflicts"] == 0
        assert data["resolved_conflicts"] == 1


# ---------------------------------------------------------------------------
# Testes — Export
# ---------------------------------------------------------------------------


class TestReviewExport:
    def test_export_json(self, client, db, auth_as_admin, setup_conflict, admin_user):
        ds_id = str(setup_conflict["dataset"].id)

        cid = str(setup_conflict["conflict"].id)
        client.post(
            "/review/resolve",
            json={"conflict_id": cid, "resolved_label": "bot"},
        )

        resp = client.get(f"/review/export?dataset_id={ds_id}&format=json")
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert data["dataset_name"].startswith("test_dataset_")

    def test_export_csv(self, client, auth_as_admin, setup_conflict):
        ds_id = str(setup_conflict["dataset"].id)
        cid = str(setup_conflict["conflict"].id)
        client.post(
            "/review/resolve",
            json={"conflict_id": cid, "resolved_label": "humano"},
        )

        resp = client.get(f"/review/export?dataset_id={ds_id}&format=csv")
        assert resp.status_code == 200
        assert "entry_id" in resp.text


# ---------------------------------------------------------------------------
# Testes — Import
# ---------------------------------------------------------------------------


class TestReviewImport:
    def test_import_resolve_conflito(self, client, db, auth_as_admin, setup_conflict):
        entry = setup_conflict["entry"]
        resp = client.post(
            "/review/import",
            json={
                "dataset_name": "test",
                "video_id": "vid123",
                "users": [
                    {
                        "entry_id": str(entry.id),
                        "author_channel_id": "UC_suspect1",
                        "author_display_name": "User UC_suspect1",
                        "final_label": "bot",
                        "resolution": {
                            "resolved_by": "Admin",
                            "resolved_label": "bot",
                        },
                    }
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["imported"] == 1

    def test_import_video_id_inexistente_retorna_404(self, client, auth_as_admin):
        resp = client.post(
            "/review/import",
            json={
                "dataset_name": "test",
                "video_id": "inexistente",
                "users": [
                    {
                        "entry_id": str(uuid.uuid4()),
                        "author_channel_id": "UC_x",
                        "author_display_name": "X",
                        "final_label": "bot",
                        "resolution": {"resolved_label": "bot"},
                    }
                ],
            },
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Testes adicionais — cobertura
# ---------------------------------------------------------------------------


class TestListConflictsVideoFilter:
    def test_filtro_por_video_id(self, client, auth_as_admin, setup_conflict):
        resp = client.get("/review/conflicts?video_id=vid123")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1

    def test_filtro_por_video_id_inexistente(
        self, client, auth_as_admin, setup_conflict
    ):
        resp = client.get("/review/conflicts?video_id=nao_existe")
        assert resp.status_code == 200
        assert resp.json()["items"] == []


class TestListConflictsStatusFilter:
    def test_filtro_por_status_resolved(
        self, client, db, auth_as_admin, setup_conflict
    ):
        cid = str(setup_conflict["conflict"].id)
        client.post(
            "/review/resolve",
            json={"conflict_id": cid, "resolved_label": "bot"},
        )
        resp = client.get("/review/conflicts?status=resolved")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["status"] == "resolved"

        resp2 = client.get("/review/conflicts?status=pending")
        assert resp2.json()["items"] == []


class TestConflictDetailResolved:
    def test_resolved_conflict_mostra_resolver(
        self, client, db, auth_as_admin, admin_user, setup_conflict
    ):
        cid = str(setup_conflict["conflict"].id)
        client.post(
            "/review/resolve",
            json={"conflict_id": cid, "resolved_label": "bot"},
        )
        resp = client.get(f"/review/conflicts/{cid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["resolved_by"] == "Admin Teste"
        assert data["resolved_label"] == "bot"


class TestListBotsEdgeCases:
    def test_bots_com_filtro_video_id(
        self,
        client,
        db,
        auth_as_admin,
        admin_user,
        annotator_a,
    ):
        col = _make_collection(db, admin_user.id)
        _make_comments(db, col.id, "UC_bot_v", count=1)
        ds, entries = _make_dataset_with_entries(
            db, col.id, admin_user.id, ["UC_bot_v"]
        )
        db.add(
            Annotation(
                dataset_entry_id=entries[0].id,
                annotator_id=annotator_a.id,
                label="bot",
                justificativa="Spam",
            )
        )
        db.commit()

        resp = client.get("/review/bots?video_id=vid123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_bots_sem_resultados_empty_page(self, client, auth_as_admin):
        resp = client.get("/review/bots")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_bots_com_dataset_id_inexistente(self, client, auth_as_admin):
        resp = client.get(f"/review/bots?dataset_id={uuid.uuid4()}")
        assert resp.status_code == 200
        assert resp.json()["items"] == []


class TestExportReviewEdgeCases:
    def test_export_json_dataset_inexistente(self, client, auth_as_admin):
        resp = client.get(f"/review/export?dataset_id={uuid.uuid4()}&format=json")
        assert resp.status_code == 404

    def test_export_csv_dataset_inexistente(self, client, auth_as_admin):
        resp = client.get(f"/review/export?dataset_id={uuid.uuid4()}&format=csv")
        assert resp.status_code == 404

    def test_export_json_consenso_label(
        self,
        client,
        db,
        auth_as_admin,
        admin_user,
        annotator_a,
        annotator_b,
    ):
        col = _make_collection(db, admin_user.id)
        _make_comments(db, col.id, "UC_cons", count=1)
        ds, entries = _make_dataset_with_entries(db, col.id, admin_user.id, ["UC_cons"])
        db.add(
            Annotation(
                dataset_entry_id=entries[0].id,
                annotator_id=annotator_a.id,
                label="bot",
                justificativa="Spam",
            )
        )
        db.add(
            Annotation(
                dataset_entry_id=entries[0].id,
                annotator_id=annotator_b.id,
                label="bot",
                justificativa="Repetitivo",
            )
        )
        db.commit()

        resp = client.get(f"/review/export?dataset_id={ds.id}&format=json")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["users"]) == 1
        assert data["users"][0]["final_label"] == "bot"
        assert data["users"][0]["resolution"] is None


class TestResolveUsersEdgeCases:
    def test_missing_entry_skip(
        self, client, db, auth_as_admin, admin_user, setup_conflict
    ):
        resp = client.post(
            "/review/import",
            json={
                "dataset_name": "test",
                "video_id": "vid123",
                "users": [
                    {
                        "entry_id": str(uuid.uuid4()),
                        "author_channel_id": "UC_x",
                        "author_display_name": "X",
                        "final_label": "bot",
                        "resolution": {"resolved_label": "bot"},
                    },
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["skipped"] == 1
        assert len(data["errors"]) == 1

    def test_no_resolution_field_skip(self, client, db, auth_as_admin, setup_conflict):
        entry = setup_conflict["entry"]
        resp = client.post(
            "/review/import",
            json={
                "dataset_name": "test",
                "video_id": "vid123",
                "users": [
                    {
                        "entry_id": str(entry.id),
                        "author_channel_id": "UC_suspect1",
                        "author_display_name": "X",
                        "final_label": "bot",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["skipped"] == 1

    def test_no_conflict_for_entry_skip(self, client, db, auth_as_admin, admin_user):
        col = _make_collection(db, admin_user.id)
        _make_comments(db, col.id, "UC_noconflict", count=1)
        ds, entries = _make_dataset_with_entries(
            db, col.id, admin_user.id, ["UC_noconflict"]
        )
        db.commit()

        resp = client.post(
            "/review/import",
            json={
                "dataset_name": "test",
                "video_id": "vid123",
                "users": [
                    {
                        "entry_id": str(entries[0].id),
                        "author_channel_id": "UC_noconflict",
                        "author_display_name": "X",
                        "final_label": "bot",
                        "resolution": {"resolved_label": "bot"},
                    },
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["skipped"] == 1
        assert any("conflito" in e.lower() for e in data["errors"])

    def test_already_resolved_conflict_skip(
        self, client, db, auth_as_admin, setup_conflict
    ):
        entry = setup_conflict["entry"]
        cid = str(setup_conflict["conflict"].id)

        client.post(
            "/review/resolve",
            json={"conflict_id": cid, "resolved_label": "bot"},
        )

        resp = client.post(
            "/review/import",
            json={
                "dataset_name": "test",
                "video_id": "vid123",
                "users": [
                    {
                        "entry_id": str(entry.id),
                        "author_channel_id": "UC_suspect1",
                        "author_display_name": "X",
                        "final_label": "humano",
                        "resolution": {"resolved_label": "humano"},
                    },
                ],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["skipped"] == 1

    def test_invalid_label_skip(self, client, db, auth_as_admin, setup_conflict):
        entry = setup_conflict["entry"]
        resp = client.post(
            "/review/import",
            json={
                "dataset_name": "test",
                "video_id": "vid123",
                "users": [
                    {
                        "entry_id": str(entry.id),
                        "author_channel_id": "UC_suspect1",
                        "author_display_name": "X",
                        "final_label": "bot",
                        "resolution": {"resolved_label": "incerto"},
                    },
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["skipped"] == 1
        assert any("inválido" in e or "invalido" in e.lower() for e in data["errors"])


class TestImportReviewChunk:
    def test_import_chunk_resolve_conflitos(
        self, client, db, auth_as_admin, setup_conflict
    ):
        entry = setup_conflict["entry"]
        resp = client.post(
            "/review/import-chunk",
            json={
                "users": [
                    {
                        "entry_id": str(entry.id),
                        "author_channel_id": "UC_suspect1",
                        "author_display_name": "X",
                        "final_label": "bot",
                        "resolution": {"resolved_label": "bot"},
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


# -------------------------------------------------------------------
# Cobertura adicional — service functions diretas
# -------------------------------------------------------------------


class TestExportReviewJsonInvalidDataset:
    def test_export_json_missing_dataset_yields_error(self, db):
        from services.review import export_review_json

        gen = export_review_json(db, uuid.uuid4())
        output = "".join(gen)
        assert "error" in output
        assert "não encontrado" in output.lower()


class TestExportReviewCsvInvalidDataset:
    def test_export_csv_missing_dataset_yields_error(self, db):
        from services.review import export_review_csv

        gen = export_review_csv(db, uuid.uuid4())
        output = "".join(gen)
        assert "error" in output


class TestExportReviewJsonConsensusLabel:
    def test_single_label_consensus_in_json_export(self, db, admin_user, annotator_a):
        from services.review import export_review_json

        col = _make_collection(db, admin_user.id)
        _make_comments(db, col.id, "UC_cons_j", 1)
        ds, entries = _make_dataset_with_entries(
            db, col.id, admin_user.id, ["UC_cons_j"]
        )
        ann = Annotation(
            dataset_entry_id=entries[0].id,
            annotator_id=annotator_a.id,
            label="humano",
        )
        db.add(ann)
        db.commit()

        import json

        gen = export_review_json(db, ds.id)
        output = "".join(gen)
        data = json.loads(output)
        assert len(data["users"]) == 1
        assert data["users"][0]["final_label"] == "humano"

    def test_pending_label_when_divergent_no_resolution(
        self, db, admin_user, annotator_a, annotator_b
    ):
        from services.review import export_review_json

        col = _make_collection(db, admin_user.id, video_id="vid_pend")
        _make_comments(db, col.id, "UC_pend", 1)
        ds, entries = _make_dataset_with_entries(db, col.id, admin_user.id, ["UC_pend"])

        ann_a = Annotation(
            dataset_entry_id=entries[0].id,
            annotator_id=annotator_a.id,
            label="bot",
            justificativa="spam",
        )
        ann_b = Annotation(
            dataset_entry_id=entries[0].id,
            annotator_id=annotator_b.id,
            label="humano",
        )
        db.add_all([ann_a, ann_b])
        db.commit()

        import json

        gen = export_review_json(db, ds.id)
        output = "".join(gen)
        data = json.loads(output)
        assert len(data["users"]) == 1
        assert data["users"][0]["final_label"] == "pending"


class TestExportReviewCsvConsensusLabel:
    def test_pending_label_in_csv_export(
        self, db, admin_user, annotator_a, annotator_b
    ):
        from services.review import export_review_csv

        col = _make_collection(db, admin_user.id, video_id="vid_csv_p")
        _make_comments(db, col.id, "UC_csv_p", 1)
        ds, entries = _make_dataset_with_entries(
            db, col.id, admin_user.id, ["UC_csv_p"]
        )

        ann_a = Annotation(
            dataset_entry_id=entries[0].id,
            annotator_id=annotator_a.id,
            label="bot",
            justificativa="spam",
        )
        ann_b = Annotation(
            dataset_entry_id=entries[0].id,
            annotator_id=annotator_b.id,
            label="humano",
        )
        db.add_all([ann_a, ann_b])
        db.commit()

        gen = export_review_csv(db, ds.id)
        output = "".join(gen)
        assert "pending" in output

    def test_single_label_consensus_in_csv_export(self, db, admin_user, annotator_a):
        from services.review import export_review_csv

        col = _make_collection(db, admin_user.id, video_id="vid_csv_c")
        _make_comments(db, col.id, "UC_csv_c", 1)
        ds, entries = _make_dataset_with_entries(
            db, col.id, admin_user.id, ["UC_csv_c"]
        )

        ann = Annotation(
            dataset_entry_id=entries[0].id,
            annotator_id=annotator_a.id,
            label="bot",
            justificativa="spam",
        )
        db.add(ann)
        db.commit()

        gen = export_review_csv(db, ds.id)
        output = "".join(gen)
        assert "bot" in output

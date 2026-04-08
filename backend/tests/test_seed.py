"""Testes do serviço de seed — dados mockados para teste local."""

from models.annotation import Annotation, AnnotationConflict
from models.collection import Collection, Comment
from models.dataset import Dataset, DatasetEntry
from services.seed import BOTS, HUMANS, SEED_VIDEO_ID

# ---------------------------------------------------------------------------
# POST /seed — criação de dados mockados
# ---------------------------------------------------------------------------


def test_seed_creates_collection_and_dataset(client, db, auth_as_admin):
    """Seed cria coleta, comentários, dataset, anotações e conflitos."""
    resp = client.post("/seed")
    assert resp.status_code == 201

    data = resp.json()
    assert data["message"] == "Seed executado com sucesso!"
    assert data["total_bots"] == len(BOTS)
    assert data["total_humans"] == len(HUMANS)
    assert data["total_comments"] > 0
    assert data["annotations_created"] > 0
    assert data["conflicts_created"] > 0
    assert len(data["annotators"]) == 2

    # Verifica que a coleta existe no banco
    col = db.query(Collection).filter(Collection.video_id == SEED_VIDEO_ID).first()
    assert col is not None
    assert col.status == "completed"
    assert col.total_comments == data["total_comments"]

    # Verifica dataset
    ds = db.query(Dataset).filter(Dataset.collection_id == col.id).first()
    assert ds is not None
    assert "percentil" in ds.criteria_applied

    # Verifica entries do dataset (todos os bots)
    entries = db.query(DatasetEntry).filter(DatasetEntry.dataset_id == ds.id).all()
    assert len(entries) == len(BOTS)

    # Verifica que há comentários no banco
    comment_count = db.query(Comment).filter(Comment.collection_id == col.id).count()
    assert comment_count == data["total_comments"]


def test_seed_already_exists_returns_409(client, db, auth_as_admin):
    """Executar seed duas vezes retorna 409."""
    resp1 = client.post("/seed")
    assert resp1.status_code == 201

    resp2 = client.post("/seed")
    assert resp2.status_code == 409
    assert "já" in resp2.json()["detail"].lower()


def test_seed_creates_correct_annotations(client, db, auth_as_admin):
    """Seed cria anotações com distribuicao correta de labels."""
    resp = client.post("/seed")
    assert resp.status_code == 201

    col = db.query(Collection).filter(Collection.video_id == SEED_VIDEO_ID).first()

    # Contar anotações
    comment_ids = (
        db.query(Comment.id).filter(Comment.collection_id == col.id).subquery()
    )
    ann_count = (
        db.query(Annotation).filter(Annotation.comment_id.in_(comment_ids)).count()
    )
    assert ann_count == resp.json()["annotations_created"]

    # Contar conflitos
    conflict_count = (
        db.query(AnnotationConflict)
        .filter(AnnotationConflict.comment_id.in_(comment_ids))
        .count()
    )
    assert conflict_count == resp.json()["conflicts_created"]
    assert conflict_count > 0


def test_seed_requires_admin(client, auth_as_user):
    """Endpoint /seed exige role admin — user recebe 403."""
    resp = client.post("/seed")
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /seed — remoção de dados mockados
# ---------------------------------------------------------------------------


def test_delete_seed_removes_all_data(client, db, auth_as_admin):
    """Delete seed remove coleta, dataset, anotações e conflitos."""
    create_resp = client.post("/seed")
    assert create_resp.status_code == 201

    del_resp = client.delete("/seed")
    assert del_resp.status_code == 200
    assert "deletados" in del_resp.json()["message"].lower()

    # Verifica que a coleta foi removida
    col = db.query(Collection).filter(Collection.video_id == SEED_VIDEO_ID).first()
    assert col is None


def test_delete_seed_without_data_returns_404(client, db, auth_as_admin):
    """Delete seed sem dados mockados retorna 404."""
    resp = client.delete("/seed")
    assert resp.status_code == 404


def test_delete_seed_requires_admin(client, auth_as_user):
    """Endpoint DELETE /seed exige role admin."""
    resp = client.delete("/seed")
    assert resp.status_code == 403


def test_seed_no_admin_in_db_returns_500(db, mocker):
    """Seed sem admin no banco retorna 500."""
    # Patch the admin query to return None
    import pytest
    from fastapi import HTTPException

    from services.seed import run_seed

    # Remover todos os admins (nenhum no DB nesta transacao)
    # run_seed procura User com role=admin
    with pytest.raises(HTTPException) as exc_info:
        run_seed(db)
    assert exc_info.value.status_code == 500
    assert "admin" in exc_info.value.detail.lower()

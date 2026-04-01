"""Testes da US-06 — Dashboard de Análise."""

import json
import uuid
from datetime import datetime, timedelta

from models.annotation import Annotation, AnnotationConflict
from models.collection import Collection, Comment
from models.dataset import Dataset, DatasetEntry

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


def _make_comments(db, collection_id, author_channel_id, count=5, base_date=None):
    if base_date is None:
        base_date = datetime(2024, 6, 15)
    comments = []
    for i in range(count):
        c = Comment(
            collection_id=collection_id,
            comment_id=f"{author_channel_id}_c{i}_{uuid.uuid4().hex[:4]}",
            author_channel_id=author_channel_id,
            author_display_name=f"User {author_channel_id}",
            text_original=f"Comentario {i} do {author_channel_id}",
            like_count=i * 2,
            reply_count=0,
            published_at=base_date + timedelta(hours=i),
            updated_at=base_date + timedelta(hours=i),
        )
        db.add(c)
        comments.append(c)
    db.flush()
    return comments


def _make_dataset(
    db, collection_id, user_id, author_channel_ids, criteria=None, name=None
):
    if criteria is None:
        criteria = ["percentil"]
    ds = Dataset(
        name=name or f"ds_{uuid.uuid4().hex[:6]}",
        collection_id=collection_id,
        criteria_applied=criteria,
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
            comment_count=5,
            matched_criteria=criteria,
        )
        db.add(entry)
    db.flush()
    return ds


def _annotate(db, comment, user, label, justificativa=None):
    ann = Annotation(
        comment_id=comment.id,
        annotator_id=user.id,
        label=label,
        justificativa=justificativa,
        annotated_at=datetime(2024, 7, 1, 10, 0),
    )
    db.add(ann)
    db.flush()
    return ann


def _make_conflict(
    db,
    comment,
    ann_a,
    ann_b,
    *,
    resolved_by=None,
    resolved_label=None,
    status="pending",
):
    conflict = AnnotationConflict(
        comment_id=comment.id,
        annotation_a_id=ann_a.id,
        annotation_b_id=ann_b.id,
        status=status,
        resolved_by=resolved_by,
        resolved_label=resolved_label,
        resolved_at=datetime(2024, 7, 5) if status == "resolved" else None,
    )
    db.add(conflict)
    db.flush()
    return conflict


def _assert_valid_plotly_json(chart_json: str):
    """Verifica que o chart é JSON parseável com chaves data e layout."""
    fig = json.loads(chart_json)
    assert "data" in fig, "Plotly JSON deve conter 'data'"
    assert "layout" in fig, "Plotly JSON deve conter 'layout'"


def _populate_full_scenario(db, user_a, user_b):
    """Cria cenário completo: 2 vídeos, 3 datasets, anotações, conflitos.

    Retorna dict com referências para assertions nos testes.
    """
    # Vídeo 1 — 2 datasets com critérios diferentes
    col1 = _make_collection(db, user_a.id, video_id="vid_alpha")
    comments_a1 = _make_comments(db, col1.id, "author_a", count=3)
    comments_b1 = _make_comments(db, col1.id, "author_b", count=2)

    ds1 = _make_dataset(
        db,
        col1.id,
        user_a.id,
        ["author_a"],
        criteria=["percentil"],
        name="alpha_percentil",
    )
    ds2 = _make_dataset(
        db,
        col1.id,
        user_a.id,
        ["author_b"],
        criteria=["media", "curtos"],
        name="alpha_media_curtos",
    )

    # Vídeo 2 — 1 dataset
    col2 = _make_collection(db, user_a.id, video_id="vid_beta")
    comments_c2 = _make_comments(db, col2.id, "author_c", count=4)
    ds3 = _make_dataset(
        db,
        col2.id,
        user_a.id,
        ["author_c"],
        criteria=["percentil", "identicos"],
        name="beta_percentil_identicos",
    )

    # ── Anotações do vídeo 1 ──

    # ds1: author_a → 3 comentários
    # comment_a1[0]: consenso bot (ambos dizem bot)
    _annotate(db, comments_a1[0], user_a, "bot", "spam")
    _annotate(db, comments_a1[0], user_b, "bot", "concordo")

    # comment_a1[1]: consenso humano
    _annotate(db, comments_a1[1], user_a, "humano")
    _annotate(db, comments_a1[1], user_b, "humano")

    # comment_a1[2]: conflito pendente
    ann_a2_a = _annotate(db, comments_a1[2], user_a, "bot", "suspeito")
    ann_a2_b = _annotate(db, comments_a1[2], user_b, "humano")
    _make_conflict(db, comments_a1[2], ann_a2_a, ann_a2_b, status="pending")

    # ds2: author_b → 2 comentários
    # comment_b1[0]: conflito resolvido como bot
    ann_b0_a = _annotate(db, comments_b1[0], user_a, "bot", "repetitivo")
    ann_b0_b = _annotate(db, comments_b1[0], user_b, "humano")
    _make_conflict(
        db,
        comments_b1[0],
        ann_b0_a,
        ann_b0_b,
        status="resolved",
        resolved_by=user_a.id,
        resolved_label="bot",
    )

    # comment_b1[1]: apenas user_a anotou (1 anotação)
    _annotate(db, comments_b1[1], user_a, "humano")

    # ── Anotações do vídeo 2 ──

    # ds3: author_c → 4 comentários
    # comment_c2[0]: consenso humano
    _annotate(db, comments_c2[0], user_a, "humano")
    _annotate(db, comments_c2[0], user_b, "humano")

    # comment_c2[1]: consenso bot
    _annotate(db, comments_c2[1], user_a, "bot", "bot óbvio")
    _annotate(db, comments_c2[1], user_b, "bot", "concordo")

    # comment_c2[2] e [3]: sem anotação
    db.commit()

    return {
        "col1": col1,
        "col2": col2,
        "ds1": ds1,
        "ds2": ds2,
        "ds3": ds3,
        "comments_a1": comments_a1,
        "comments_b1": comments_b1,
        "comments_c2": comments_c2,
    }


# ---------------------------------------------------------------------------
# GET /dashboard/global
# ---------------------------------------------------------------------------


class TestGlobalDashboard:
    def test_retorna_kpis_e_charts_validos(self, client, db, auth_as_user, admin_user):
        """KPIs corretos e todos os charts são JSON Plotly válidos."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/global")
        assert resp.status_code == 200
        data = resp.json()

        s = data["summary"]
        assert s["total_datasets"] == 3
        # bots: consenso bot em vid_alpha (author_a[0]) + resolvido bot (author_b[0])
        #        + consenso bot em vid_beta (author_c[1]) = 3
        assert s["total_bots"] == 3
        # humanos: consenso humano (a[1]) + 1 anotação humano (b[1]) + consenso (c[0]) = 3
        assert s["total_humans"] == 3
        # conflitos totais: 2 (pendente + resolvido)
        assert s["total_conflicts"] == 2
        assert s["pending_conflicts"] == 1

        # Progresso geral
        assert s["total_comments_in_datasets"] > 0
        assert 0 <= s["annotation_progress"] <= 100

        # Charts válidos
        for key in [
            "label_distribution_chart",
            "comparativo_por_dataset_chart",
            "annotations_over_time_chart",
            "bot_rate_by_dataset_chart",
            "agreement_by_dataset_chart",
            "criteria_effectiveness_chart",
        ]:
            _assert_valid_plotly_json(data[key])

    def test_sem_token_retorna_401(self, client):
        resp = client.get("/dashboard/global")
        assert resp.status_code == 401

    def test_sem_dados_retorna_zeros(self, client, auth_as_user):
        """Banco vazio retorna zeros e charts válidos — nunca 404."""
        resp = client.get("/dashboard/global")
        assert resp.status_code == 200
        data = resp.json()
        s = data["summary"]
        assert s["total_datasets"] == 0
        assert s["total_bots"] == 0
        assert s["total_humans"] == 0
        assert s["agreement_rate"] == 0.0
        _assert_valid_plotly_json(data["label_distribution_chart"])

    def test_filtro_criteria_filtra_datasets(
        self, client, db, auth_as_user, admin_user
    ):
        """Filtrar por criteria=percentil retorna apenas datasets com percentil."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/global?criteria=percentil")
        assert resp.status_code == 200
        data = resp.json()

        # Datasets com percentil: alpha_percentil e beta_percentil_identicos
        assert data["summary"]["total_datasets"] == 2
        assert data["active_criteria_filter"] == ["percentil"]

    def test_filtro_criteria_multiplo(self, client, db, auth_as_user, admin_user):
        """criteria=percentil,identicos retorna apenas datasets com AMBOS."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/global?criteria=percentil,identicos")
        assert resp.status_code == 200
        data = resp.json()

        # Apenas beta_percentil_identicos tem ambos
        assert data["summary"]["total_datasets"] == 1

    def test_agreement_rate_correto(self, client, db, auth_as_user, admin_user):
        """Agreement = consenso / total com 2 anotações."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/global")
        data = resp.json()
        rate = data["summary"]["agreement_rate"]

        # Com 2 anotações:
        # vid_alpha: a[0]=consenso, a[1]=consenso, a[2]=conflito, b[0]=conflito → 2 consenso / 4
        # vid_beta: c[0]=consenso, c[1]=consenso → 2 consenso / 2
        # Total: 4 consenso / 6 = 0.6667
        assert rate == round(4 / 6, 4)


# ---------------------------------------------------------------------------
# GET /dashboard/video
# ---------------------------------------------------------------------------


class TestVideoDashboard:
    def test_retorna_dados_do_video_filtrado(
        self, client, db, auth_as_user, admin_user
    ):
        """Apenas dados do video_id requisitado."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/video?video_id=vid_alpha")
        assert resp.status_code == 200
        data = resp.json()

        assert data["video_id"] == "vid_alpha"
        s = data["summary"]
        # vid_alpha tem 5 comentários coletados (3 de author_a + 2 de author_b)
        assert s["total_comments_collected"] == 5
        assert s["total_comments_in_datasets"] == 5

        # Charts válidos
        for key in [
            "label_distribution_chart",
            "comparativo_por_dataset_chart",
            "bot_rate_by_criteria_chart",
            "comment_timeline_chart",
        ]:
            _assert_valid_plotly_json(data[key])

    def test_sem_token_retorna_401(self, client):
        resp = client.get("/dashboard/video?video_id=vid_alpha")
        assert resp.status_code == 401

    def test_video_inexistente_retorna_zeros(self, client, db, auth_as_user):
        """video_id que não existe retorna 200 com zeros — nunca 404."""
        resp = client.get("/dashboard/video?video_id=inexistente")
        assert resp.status_code == 200
        data = resp.json()
        s = data["summary"]
        assert s["total_comments_collected"] == 0
        assert s["total_annotated"] == 0
        assert s["total_bots"] == 0

    def test_video_com_filtro_criteria(self, client, db, auth_as_user, admin_user):
        """Filtro por critério no contexto de um vídeo."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/video?video_id=vid_alpha&criteria=media,curtos")
        assert resp.status_code == 200
        data = resp.json()

        # Apenas alpha_media_curtos tem ambos media e curtos
        assert data["summary"]["total_comments_in_datasets"] == 2


# ---------------------------------------------------------------------------
# GET /dashboard/user
# ---------------------------------------------------------------------------


class TestUserDashboard:
    def test_retorna_dados_do_pesquisador_autenticado(
        self, client, db, auth_as_user, admin_user
    ):
        """Apenas anotações do usuário autenticado (auth_as_user)."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/user")
        assert resp.status_code == 200
        data = resp.json()

        s = data["summary"]
        # auth_as_user anotou:
        # vid_alpha: a[0]=bot, a[1]=humano, a[2]=bot, b[0]=bot, b[1]=humano
        # vid_beta: c[0]=humano, c[1]=bot
        # Total: 7 anotados, bots=4, humans=3
        assert s["total_annotated"] == 7
        assert s["bots"] == 4
        assert s["humans"] == 3
        assert s["total_datasets_assigned"] == 3
        assert len(data["datasets"]) == 3

        # Charts válidos
        for key in [
            "my_label_distribution_chart",
            "my_progress_by_dataset_chart",
            "my_annotations_over_time_chart",
        ]:
            _assert_valid_plotly_json(data[key])

    def test_sem_token_retorna_401(self, client):
        resp = client.get("/dashboard/user")
        assert resp.status_code == 401

    def test_nao_expoe_dados_de_outro_pesquisador(
        self, client, db, auth_as_user, admin_user
    ):
        """Dados do admin_user não aparecem no dashboard do auth_as_user."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/user")
        assert resp.status_code == 200
        text = resp.text

        # Username do admin não deve aparecer em nenhum campo
        assert admin_user.username not in text

    def test_sem_dados_retorna_zeros(self, client, auth_as_user):
        """Sem datasets retorna zeros e charts válidos."""
        resp = client.get("/dashboard/user")
        assert resp.status_code == 200
        data = resp.json()
        s = data["summary"]
        assert s["total_datasets_assigned"] == 0
        assert s["total_annotated"] == 0
        assert s["bots"] == 0
        assert data["datasets"] == []
        _assert_valid_plotly_json(data["my_label_distribution_chart"])

    def test_dataset_status_correto(self, client, db, auth_as_user, admin_user):
        """Verifica status completed, in_progress e not_started."""
        col = _make_collection(db, auth_as_user.id, video_id="vid_status")
        comments_a = _make_comments(db, col.id, "ch_a", count=2)
        comments_b = _make_comments(db, col.id, "ch_b", count=2)
        _make_comments(db, col.id, "ch_c", count=2)

        _make_dataset(db, col.id, auth_as_user.id, ["ch_a"], name="ds_done")
        _make_dataset(db, col.id, auth_as_user.id, ["ch_b"], name="ds_partial")
        _make_dataset(db, col.id, auth_as_user.id, ["ch_c"], name="ds_empty")

        # ds_done: anotar todos
        for c in comments_a:
            _annotate(db, c, auth_as_user, "humano")

        # ds_partial: anotar 1 de 2
        _annotate(db, comments_b[0], auth_as_user, "bot", "teste")

        # ds_empty: nenhuma anotação
        db.commit()

        resp = client.get("/dashboard/user")
        data = resp.json()

        ds_map = {d["dataset_name"]: d for d in data["datasets"]}
        assert ds_map["ds_done"]["status"] == "completed"
        assert ds_map["ds_done"]["percent_complete"] == 100.0
        assert ds_map["ds_partial"]["status"] == "in_progress"
        assert ds_map["ds_partial"]["percent_complete"] == 50.0
        assert ds_map["ds_empty"]["status"] == "not_started"
        assert ds_map["ds_empty"]["percent_complete"] == 0.0


# ---------------------------------------------------------------------------
# GET /dashboard/bots
# ---------------------------------------------------------------------------


class TestBotComments:
    def test_retorna_bots_com_concordancia(self, client, db, auth_as_user, admin_user):
        """Tabela de bots retorna concordance_pct correto."""
        col = _make_collection(db, auth_as_user.id, video_id="vid_bots")
        comments = _make_comments(db, col.id, "ch_bot", count=2)
        _make_dataset(db, col.id, auth_as_user.id, ["ch_bot"])

        # Consenso bot no comment[0]
        _annotate(db, comments[0], auth_as_user, "bot", "spam")
        _annotate(db, comments[0], admin_user, "bot", "concordo")

        # Conflito no comment[1]
        ann_a = _annotate(db, comments[1], auth_as_user, "bot", "suspeito")
        ann_b = _annotate(db, comments[1], admin_user, "humano")
        _make_conflict(db, comments[1], ann_a, ann_b, status="pending")
        db.commit()

        resp = client.get("/dashboard/bots")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total"] >= 1
        # Consenso bot → 100%
        bot_items = [i for i in data["items"] if i["concordance_pct"] == 100]
        assert len(bot_items) >= 1

    def test_sem_token_retorna_401(self, client):
        resp = client.get("/dashboard/bots")
        assert resp.status_code == 401

    def test_filtro_por_search(self, client, db, auth_as_user, admin_user):
        """Filtro de busca por texto do comentário."""
        col = _make_collection(db, auth_as_user.id, video_id="vid_search")
        c = Comment(
            collection_id=col.id,
            comment_id="unique_search_c1",
            author_channel_id="ch_search",
            author_display_name="Busca User",
            text_original="TEXTO ÚNICO PARA BUSCA",
            like_count=0,
            reply_count=0,
            published_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
        )
        db.add(c)
        db.flush()
        _make_dataset(db, col.id, auth_as_user.id, ["ch_search"])
        _annotate(db, c, auth_as_user, "bot", "teste busca")
        db.commit()

        resp = client.get("/dashboard/bots?search=ÚNICO PARA")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any("ÚNICO" in i["text_original"] for i in data["items"])


# ---------------------------------------------------------------------------
# GET /dashboard/criteria-effectiveness
# ---------------------------------------------------------------------------


class TestCriteriaEffectiveness:
    def test_retorna_eficacia_por_criterio(self, client, db, auth_as_user, admin_user):
        """Cada critério retorna total_datasets, total_bots e bot_rate."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/criteria-effectiveness")
        assert resp.status_code == 200
        data = resp.json()

        assert len(data) > 0
        for item in data:
            assert "criteria" in item
            assert "group" in item
            assert item["group"] in ("numerico", "comportamental")
            assert "total_datasets" in item
            assert "bot_rate" in item

        # percentil aparece em 2 datasets
        percentil = next(i for i in data if i["criteria"] == "percentil")
        assert percentil["total_datasets"] == 2

    def test_sem_token_retorna_401(self, client):
        resp = client.get("/dashboard/criteria-effectiveness")
        assert resp.status_code == 401

    def test_filtro_por_video_id(self, client, db, auth_as_user, admin_user):
        """Filtra eficácia por vídeo específico."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/criteria-effectiveness?video_id=vid_alpha")
        assert resp.status_code == 200
        data = resp.json()

        criterios = {i["criteria"] for i in data}
        # vid_alpha tem percentil e media+curtos
        assert "percentil" in criterios
        assert "media" in criterios
        # identicos é do vid_beta — não deve aparecer
        assert "identicos" not in criterios

    def test_sem_dados_retorna_vazio(self, client, auth_as_user):
        resp = client.get("/dashboard/criteria-effectiveness")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# Segurança — nenhum endpoint expõe username de outro pesquisador
# ---------------------------------------------------------------------------


class TestSeguranca:
    def test_global_nao_expoe_username(self, client, db, auth_as_user, admin_user):
        """Visão geral não expõe username de nenhum pesquisador."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/global")
        text = resp.text
        assert admin_user.username not in text
        assert auth_as_user.username not in text

    def test_video_nao_expoe_username(self, client, db, auth_as_user, admin_user):
        """Por Vídeo não expõe username de nenhum pesquisador."""
        _populate_full_scenario(db, auth_as_user, admin_user)

        resp = client.get("/dashboard/video?video_id=vid_alpha")
        text = resp.text
        assert admin_user.username not in text
        assert auth_as_user.username not in text
